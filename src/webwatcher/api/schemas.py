from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class CompanyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    base_url: HttpUrl
    ir_url: HttpUrl | None = None
    scan_interval_minutes: int = Field(default=90, ge=30, le=720)


class CompanyUpdate(BaseModel):
    ir_url: HttpUrl | None = None
    scan_interval_minutes: int | None = Field(default=None, ge=30, le=720)
    is_active: bool | None = None


class CompanyOut(BaseModel):
    id: int
    name: str
    base_url: str
    ir_url: str | None
    ir_confidence: float
    scan_interval_minutes: int
    is_active: bool
    last_scanned_at: datetime | None
    next_scan_at: datetime | None


class SnapshotOut(BaseModel):
    id: int
    company_id: int
    scan_run_id: int | None
    source_url: str
    page_hash: str
    numbers_hash: str
    raw_blob_path: str | None
    pdf_links: list[str]
    created_at: datetime


class DocumentOut(BaseModel):
    id: int
    company_id: int
    snapshot_id: int | None
    url: str
    doc_hash: str
    file_size: int | None
    content_type: str | None
    storage_path: str | None
    created_at: datetime


class ScanTriggerResponse(BaseModel):
    queued: bool
    company_id: int


class ScanRunOut(BaseModel):
    id: int
    company_id: int
    status: str
    idempotency_key: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class ChangeOut(BaseModel):
    id: int
    company_id: int
    from_snapshot_id: int | None
    to_snapshot_id: int
    change_type: str
    severity: str
    score: float
    confidence: float
    summary: str
    details: dict[str, Any]
    created_at: datetime
