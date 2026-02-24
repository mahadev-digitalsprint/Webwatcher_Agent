from fastapi import APIRouter

from webwatcher.api.routes_changes import router as changes_router
from webwatcher.api.routes_company import router as company_router
from webwatcher.api.routes_monitor import router as monitor_router
from webwatcher.observability.metrics import metrics

api_router = APIRouter()
api_router.include_router(company_router)
api_router.include_router(monitor_router)
api_router.include_router(changes_router)


@api_router.get("/health")
async def health() -> dict:
    return {"ok": True}


@api_router.get("/metrics")
async def get_metrics() -> dict:
    return metrics.snapshot()

