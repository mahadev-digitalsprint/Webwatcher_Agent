from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.api.schemas import ScanRunOut, ScanTriggerResponse
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Company, ScanRun
from webwatcher.orchestration.monitor_worker import run_monitor_task

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.post("/trigger/{company_id}", response_model=ScanTriggerResponse)
async def trigger_scan(company_id: int, db: AsyncSession = Depends(get_db_session)) -> ScanTriggerResponse:
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    run_monitor_task.delay(company_id)
    return ScanTriggerResponse(queued=True, company_id=company_id)


@router.get("/status/{company_id}", response_model=list[ScanRunOut])
async def get_scan_status(
    company_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session),
) -> list[ScanRunOut]:
    result = await db.execute(
        select(ScanRun)
        .where(ScanRun.company_id == company_id)
        .order_by(desc(ScanRun.created_at))
        .limit(limit)
    )
    rows = result.scalars().all()
    return [ScanRunOut.model_validate(row, from_attributes=True) for row in rows]

