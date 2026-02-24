from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.api.schemas import CompanyCreate, CompanyOut, CompanyUpdate
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
async def add_company(payload: CompanyCreate, db: AsyncSession = Depends(get_db_session)) -> CompanyOut:
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


@router.get("", response_model=list[CompanyOut])
async def list_companies(db: AsyncSession = Depends(get_db_session)) -> list[CompanyOut]:
    result = await db.execute(select(Company).order_by(Company.id.asc()))
    return [CompanyOut.model_validate(row, from_attributes=True) for row in result.scalars().all()]


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

