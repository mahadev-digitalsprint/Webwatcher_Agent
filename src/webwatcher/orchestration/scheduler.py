import asyncio
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import or_, select

from webwatcher.core.database import session_scope
from webwatcher.db.models import Company, SchedulerState
from webwatcher.observability.metrics import metrics
from webwatcher.orchestration.monitor_worker import run_monitor_task


async def _due_company_ids() -> list[int]:
    now = datetime.now(timezone.utc)
    async with session_scope() as session:
        result = await session.execute(
            select(Company.id).where(
                Company.is_active.is_(True),
                or_(Company.next_scan_at.is_(None), Company.next_scan_at <= now),
            )
        )
        return [row[0] for row in result.all()]


async def _touch_scheduler_state() -> None:
    async with session_scope() as session:
        state = await session.get(SchedulerState, 1)
        if state is None:
            state = SchedulerState(id=1, last_tick_at=datetime.now(timezone.utc), heartbeat_meta={})
            session.add(state)
        else:
            state.last_tick_at = datetime.now(timezone.utc)
        await session.flush()


async def run_scheduler_tick() -> dict:
    company_ids = await _due_company_ids()
    for company_id in company_ids:
        run_monitor_task.delay(company_id)
    await _touch_scheduler_state()
    metrics.inc("scheduler_ticks_total")
    metrics.inc("scheduler_jobs_enqueued_total", len(company_ids))
    return {"enqueued": len(company_ids), "company_ids": company_ids}


@shared_task(name="webwatcher.orchestration.scheduler.tick_scheduler")
def tick_scheduler() -> dict:
    return asyncio.run(run_scheduler_tick())

