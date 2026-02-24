from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.db.models import Snapshot
from webwatcher.normalization.html_normalizer import NormalizedPage
from webwatcher.storage.storage_service import StorageService


@dataclass
class SnapshotDecision:
    changed: bool
    snapshot: Snapshot | None
    reason: str


class SnapshotManager:
    def __init__(self, storage_service: StorageService) -> None:
        self.storage_service = storage_service

    async def latest_snapshot(self, session: AsyncSession, company_id: int) -> Snapshot | None:
        stmt = (
            select(Snapshot)
            .where(Snapshot.company_id == company_id)
            .order_by(desc(Snapshot.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_snapshot_if_changed(
        self,
        session: AsyncSession,
        company_id: int,
        scan_run_id: int | None,
        source_url: str,
        normalized: NormalizedPage,
        raw_html: bytes,
    ) -> SnapshotDecision:
        latest = await self.latest_snapshot(session, company_id)
        if latest and latest.page_hash == normalized.page_hash and latest.numbers_hash == normalized.numbers_hash:
            return SnapshotDecision(changed=False, snapshot=latest, reason="No meaningful change")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        relative = self.storage_service.build_path(company_id, timestamp, "page.html")
        raw_blob_path = self.storage_service.upload("raw", relative, raw_html)

        snapshot = Snapshot(
            company_id=company_id,
            scan_run_id=scan_run_id,
            source_url=source_url,
            page_hash=normalized.page_hash,
            numbers_hash=normalized.numbers_hash,
            section_hashes=normalized.section_hashes,
            normalized_json=normalized.as_json(),
            raw_blob_path=raw_blob_path,
        )
        session.add(snapshot)
        await session.flush()
        return SnapshotDecision(changed=True, snapshot=snapshot, reason="Snapshot created")

