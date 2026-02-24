from fastapi import FastAPI

from webwatcher.api.router import api_router
from webwatcher.core.config import get_settings
from webwatcher.core.logger import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_env)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()

