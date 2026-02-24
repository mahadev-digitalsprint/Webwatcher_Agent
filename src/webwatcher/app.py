import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from webwatcher.api.router import api_router
from webwatcher.core.config import get_settings
from webwatcher.core.logger import configure_logging
from webwatcher.db.bootstrap import bootstrap_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await asyncio.wait_for(bootstrap_database(), timeout=12)
    except TimeoutError:
        # Keep API available even if compatibility bootstrap is slow on remote DBs.
        pass
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
