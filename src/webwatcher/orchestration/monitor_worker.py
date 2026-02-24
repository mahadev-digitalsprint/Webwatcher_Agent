import asyncio
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import desc, select

from webwatcher.core.config import get_settings
from webwatcher.core.database import session_scope
from webwatcher.core.logger import get_logger
from webwatcher.crawler.fetcher import Fetcher
from webwatcher.db.models import Change, Company, FinancialMetric, ScanRun, ScanStatus, Snapshot
from webwatcher.financial.financial_extractor import FinancialExtractor
from webwatcher.intelligence.change_detector import ChangeDetector
from webwatcher.intelligence.confidence_engine import ConfidenceEngine
from webwatcher.intelligence.materiality_engine import MaterialityEngine
from webwatcher.llm.llm_client import LlmClient
from webwatcher.llm.llm_financial_validator import LlmFinancialValidator
from webwatcher.normalization.html_normalizer import normalize_html
from webwatcher.observability.metrics import Timer, metrics
from webwatcher.orchestration.locks import DistributedLockError, company_scan_lock
from webwatcher.pdf.pdf_monitor import PdfMonitor
from webwatcher.pdf.pdf_parser import PdfParser
from webwatcher.storage.snapshot_manager import SnapshotManager
from webwatcher.storage.storage_service import StorageService


def _window_key(company_id: int, window_minutes: int = 30) -> str:
    now = datetime.now(timezone.utc)
    minute_bucket = now.minute - (now.minute % window_minutes)
    floor = now.replace(minute=minute_bucket, second=0, microsecond=0)
    return f"{company_id}:{floor.isoformat()}"


async def _load_company(session, company_id: int) -> Company | None:
    result = await session.execute(select(Company).where(Company.id == company_id))
    return result.scalar_one_or_none()


async def _latest_snapshot(session, company_id: int) -> Snapshot | None:
    result = await session.execute(
        select(Snapshot).where(Snapshot.company_id == company_id).order_by(desc(Snapshot.created_at)).limit(1)
    )
    return result.scalar_one_or_none()


async def _metrics_for_snapshot(session, snapshot_id: int | None) -> dict[str, float]:
    if snapshot_id is None:
        return {}
    result = await session.execute(
        select(FinancialMetric).where(FinancialMetric.snapshot_id == snapshot_id)
    )
    rows = result.scalars().all()
    return {row.metric_name: row.metric_value for row in rows}


async def _get_or_create_scan_run(session, company_id: int) -> ScanRun:
    key = _window_key(company_id)
    existing = await session.execute(select(ScanRun).where(ScanRun.idempotency_key == key))
    run = existing.scalar_one_or_none()
    if run:
        return run
    run = ScanRun(
        company_id=company_id,
        status=ScanStatus.queued.value,
        idempotency_key=key,
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    await session.flush()
    return run


async def run_monitor(company_id: int) -> dict:
    settings = get_settings()
    logger = get_logger("webwatcher.monitor", company_id=company_id)
    with Timer("scan_duration_ms"):
        try:
            with company_scan_lock(company_id):
                async with session_scope() as session:
                    company = await _load_company(session, company_id)
                    if company is None:
                        return {"status": "error", "message": f"Company {company_id} not found"}

                    scan_run = await _get_or_create_scan_run(session, company_id)
                    scan_run.status = ScanStatus.running.value
                    scan_run.started_at = datetime.now(timezone.utc)
                    await session.flush()

                    fetcher = Fetcher()
                    storage_service = StorageService()
                    snapshot_manager = SnapshotManager(storage_service)
                    pdf_monitor = PdfMonitor(fetcher, storage_service, PdfParser())

                    target_url = company.ir_url or company.base_url
                    response = await fetcher.get(target_url)
                    normalized = normalize_html(response.text, source_url=target_url)

                    old_snapshot = await _latest_snapshot(session, company_id)
                    decision = await snapshot_manager.create_snapshot_if_changed(
                        session=session,
                        company_id=company_id,
                        scan_run_id=scan_run.id,
                        source_url=target_url,
                        normalized=normalized,
                        raw_html=response.content,
                    )

                    snapshot = decision.snapshot
                    pdf_result = await pdf_monitor.process_pdf_links(
                        session,
                        company_id=company_id,
                        snapshot_id=snapshot.id if snapshot else None,
                        links=normalized.pdf_links,
                    )

                    extractor = FinancialExtractor()
                    merged_text = normalized.clean_text + "\n" + "\n".join(pdf_result.parsed_texts)
                    extracted = extractor.extract(merged_text)

                    llm_validator = LlmFinancialValidator(LlmClient())
                    llm_validation = llm_validator.validate(merged_text, extracted.metrics)
                    final_metrics = llm_validation.merged_metrics

                    confidence_engine = ConfidenceEngine()
                    confidence = confidence_engine.score(
                        has_tables="table" in response.text.lower(),
                        heading_match_ratio=0.8 if extracted.metrics else 0.3,
                        unit_consistency=0.8,
                        llm_agreement=llm_validation.agreement_score,
                        metrics=final_metrics,
                    )

                    if snapshot:
                        for metric_name, metric_value in final_metrics.items():
                            session.add(
                                FinancialMetric(
                                    snapshot_id=snapshot.id,
                                    company_id=company_id,
                                    metric_name=metric_name,
                                    metric_value=metric_value,
                                    unit=None,
                                    currency=extracted.currency,
                                    period=extracted.quarter,
                                    report_type=extracted.report_type,
                                    confidence=confidence.metric_confidence.get(metric_name, 0.5),
                                )
                            )

                    previous_metrics = await _metrics_for_snapshot(
                        session, old_snapshot.id if old_snapshot else None
                    )
                    detector = ChangeDetector()
                    detection = detector.detect(
                        old_snapshot.normalized_json if old_snapshot else None,
                        snapshot.normalized_json if snapshot else normalized.as_json(),
                        previous_metrics,
                        final_metrics,
                        pdf_result.changed > 0,
                    )
                    materiality = MaterialityEngine().score(detection.score)

                    if snapshot and detection.score > 0:
                        session.add(
                            Change(
                                company_id=company_id,
                                from_snapshot_id=old_snapshot.id if old_snapshot else None,
                                to_snapshot_id=snapshot.id,
                                change_type=detection.change_type,
                                severity=materiality.severity,
                                score=materiality.score,
                                confidence=confidence.snapshot_confidence,
                                summary=detection.summary,
                                details=detection.details,
                            )
                        )

                    company.last_scanned_at = datetime.now(timezone.utc)
                    company.next_scan_at = company.last_scanned_at + timedelta(
                        minutes=company.scan_interval_minutes or settings.webwatch_scan_interval_minutes
                    )

                    scan_run.status = ScanStatus.succeeded.value
                    scan_run.completed_at = datetime.now(timezone.utc)
                    await fetcher.close()
                    metrics.inc("scan_success_total")
                    logger.info(
                        "Scan completed",
                        extra={
                            "scan_run_id": scan_run.id,
                            "snapshot_id": snapshot.id if snapshot else None,
                        },
                    )
                    return {
                        "status": "ok",
                        "scan_run_id": scan_run.id,
                        "snapshot_id": snapshot.id if snapshot else None,
                        "metrics_found": len(final_metrics),
                        "pdf_downloaded": pdf_result.downloaded,
                        "pdf_changed": pdf_result.changed,
                    }
        except DistributedLockError as exc:
            metrics.inc("scan_lock_skipped_total")
            return {"status": "skipped", "reason": str(exc)}
        except Exception as exc:
            metrics.inc("scan_failed_total")
            logger.exception("Scan failed", extra={"event_name": "scan_failed"})
            async with session_scope() as session:
                scan_run = await _get_or_create_scan_run(session, company_id)
                scan_run.status = ScanStatus.failed.value
                scan_run.completed_at = datetime.now(timezone.utc)
                scan_run.error_message = str(exc)
            return {"status": "error", "message": str(exc)}


@shared_task(name="webwatcher.orchestration.monitor_worker.run_monitor_task")
def run_monitor_task(company_id: int) -> dict:
    return asyncio.run(run_monitor(company_id))

