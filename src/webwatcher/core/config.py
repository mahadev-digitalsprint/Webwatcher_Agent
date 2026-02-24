from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["dev", "staging", "prod"] = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="webwatcher-agent", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./webwatcher.db",
        alias="DATABASE_URL",
    )
    postgres_url: str | None = Field(default=None, alias="POSTGRES_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_concurrency: int = Field(default=4, alias="CELERY_CONCURRENCY")

    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_key: str | None = Field(default=None, alias="AZURE_OPENAI_KEY")
    azure_openai_deployment: str = Field(default="gpt-4.1", alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(
        default="2024-12-01-preview", alias="AZURE_OPENAI_API_VERSION"
    )
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    enable_openai_fallback: bool = Field(default=False, alias="WEBWATCH_ENABLE_OPENAI_FALLBACK")

    azure_storage_connection_string: str | None = Field(
        default=None, alias="AZURE_STORAGE_CONNECTION_STRING"
    )
    azure_storage_container_raw: str = Field(
        default="webwatcher-raw", alias="AZURE_STORAGE_CONTAINER_RAW"
    )
    azure_storage_container_docs: str = Field(
        default="webwatcher-docs", alias="AZURE_STORAGE_CONTAINER_DOCS"
    )
    base_download_path: str = Field(default="downloads", alias="BASE_DOWNLOAD_PATH")

    firecrawl_api_key: str | None = Field(default=None, alias="FIRECRAWL_API_KEY")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    no_reply_mail_password: str | None = Field(default=None, alias="NO_REPLY_MAIL_PASSWORD")
    email_from: str | None = Field(default=None, alias="EMAIL_FROM")
    email_recipients: str | None = Field(default=None, alias="EMAIL_RECIPIENTS")

    webwatch_crawl_depth: int = Field(default=2, alias="WEBWATCH_CRAWL_DEPTH")
    webwatch_scan_interval_minutes: int = Field(default=90, alias="WEBWATCH_SCAN_INTERVAL_MINUTES")
    webwatch_scan_jitter_minutes: int = Field(default=30, alias="WEBWATCH_SCAN_JITTER_MINUTES")
    webwatch_max_file_size_mb: int = Field(default=40, alias="WEBWATCH_MAX_FILE_SIZE_MB")
    webwatch_request_timeout_seconds: int = Field(default=20, alias="WEBWATCH_REQUEST_TIMEOUT_SECONDS")
    webwatch_max_retries: int = Field(default=3, alias="WEBWATCH_MAX_RETRIES")
    webwatch_rate_limit_per_domain: int = Field(default=12, alias="WEBWATCH_RATE_LIMIT_PER_DOMAIN")
    webwatch_alert_confidence_threshold: float = Field(
        default=0.75, alias="WEBWATCH_ALERT_CONFIDENCE_THRESHOLD"
    )
    webwatch_materiality_minor: float = Field(default=0.2, alias="WEBWATCH_MATERIALITY_MINOR")
    webwatch_materiality_moderate: float = Field(
        default=0.4, alias="WEBWATCH_MATERIALITY_MODERATE"
    )
    webwatch_materiality_significant: float = Field(
        default=0.7, alias="WEBWATCH_MATERIALITY_SIGNIFICANT"
    )
    webwatch_materiality_critical: float = Field(
        default=0.9, alias="WEBWATCH_MATERIALITY_CRITICAL"
    )
    webwatch_enable_ocr_on_pdf_failure: bool = Field(
        default=True, alias="WEBWATCH_ENABLE_OCR_ON_PDF_FAILURE"
    )

    @computed_field
    @property
    def effective_database_url(self) -> str:
        return _normalize_database_url(self.postgres_url or self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
