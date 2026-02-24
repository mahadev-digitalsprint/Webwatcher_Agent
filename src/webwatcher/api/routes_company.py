from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.api.schemas import CompanyCreate, CompanyOut, CompanyUpdate, DocumentOut, SnapshotOut
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Company, Document, Snapshot

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def add_company(payload: CompanyCreate, db: AsyncSession = Depends(get_db_session)) -> CompanyOut:
    try:
        existing = await db.execute(select(Company).where(Company.base_url == str(payload.base_url)))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Company with this base_url already exists.")
        now = datetime.now(timezone.utc)
        company = Company(
            name=payload.name,
            base_url=str(payload.base_url),
            ir_url=str(payload.ir_url) if payload.ir_url else None,
            scan_interval_minutes=payload.scan_interval_minutes,
            next_scan_at=now + timedelta(minutes=1),
        )
        db.add(company)
        await db.flush()
        return CompanyOut.model_validate(company, from_attributes=True)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail=f"Insert conflict: {exc.orig}") from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db_session)) -> list[CompanyOut]:
    try:
        result = await db.execute(select(Company).order_by(Company.id.asc()))
        return [CompanyOut.model_validate(row, from_attributes=True) for row in result.scalars().all()]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.patch("/{company_id}", response_model=CompanyOut)
async def update_company(
    company_id: int,
    payload: CompanyUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> CompanyOut:
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    if payload.ir_url is not None:
        company.ir_url = str(payload.ir_url)
    if payload.scan_interval_minutes is not None:
        company.scan_interval_minutes = payload.scan_interval_minutes
    if payload.is_active is not None:
        company.is_active = payload.is_active
    await db.flush()
    return CompanyOut.model_validate(company, from_attributes=True)


@router.get("/{company_id}/snapshots", response_model=list[SnapshotOut])
async def list_company_snapshots(
    company_id: int,
    limit: int = 100,
    db: AsyncSession = Depends(get_db_session),
) -> list[SnapshotOut]:
    try:
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        result = await db.execute(
            select(Snapshot)
            .where(Snapshot.company_id == company_id)
            .order_by(Snapshot.created_at.desc())
            .limit(limit)
        )
        snapshots = []
        for row in result.scalars().all():
            normalized = row.normalized_json if isinstance(row.normalized_json, dict) else {}
            pdf_links = normalized.get("pdf_links", [])
            if not isinstance(pdf_links, list):
                pdf_links = []
            snapshots.append(
                SnapshotOut(
                    id=row.id,
                    company_id=row.company_id,
                    scan_run_id=row.scan_run_id,
                    source_url=row.source_url,
                    page_hash=row.page_hash,
                    numbers_hash=row.numbers_hash,
                    raw_blob_path=row.raw_blob_path,
                    pdf_links=[link for link in pdf_links if isinstance(link, str)],
                    created_at=row.created_at,
                )
            )
        return snapshots
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/{company_id}/documents", response_model=list[DocumentOut])
async def list_company_documents(
    company_id: int,
    limit: int = 200,
    db: AsyncSession = Depends(get_db_session),
) -> list[DocumentOut]:
    try:
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        result = await db.execute(
            select(Document)
            .where(Document.company_id == company_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        return [DocumentOut.model_validate(row, from_attributes=True) for row in result.scalars().all()]
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc


@router.get("/{company_id}/crawl-links")
async def list_company_crawl_links(
    company_id: int,
    limit: int = 300,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    try:
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found.")
        snap_result = await db.execute(
            select(Snapshot)
            .where(Snapshot.company_id == company_id)
            .order_by(Snapshot.created_at.desc())
            .limit(limit)
        )
        doc_result = await db.execute(
            select(Document)
            .where(Document.company_id == company_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        snapshots = snap_result.scalars().all()
        documents = doc_result.scalars().all()

        page_urls = sorted({row.source_url for row in snapshots if row.source_url})
        found_pdf_links: set[str] = set()
        for row in snapshots:
            normalized = row.normalized_json if isinstance(row.normalized_json, dict) else {}
            links = normalized.get("pdf_links", [])
            if isinstance(links, list):
                found_pdf_links.update([link for link in links if isinstance(link, str)])

        stored_pdf_urls = sorted({row.url for row in documents if row.url})
        stored_pdf_paths = sorted({row.storage_path for row in documents if row.storage_path})
        return {
            "company_id": company_id,
            "page_urls": page_urls,
            "pdf_links_found": sorted(found_pdf_links),
            "pdf_documents_stored": stored_pdf_urls,
            "pdf_storage_paths": stored_pdf_paths,
            "snapshot_count": len(snapshots),
            "document_count": len(documents),
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
