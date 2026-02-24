from fastapi import APIRouter, Depends
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.api.schemas import ChangeOut
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Change, Snapshot

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=list[ChangeOut])
async def list_changes(
    company_id: int | None = None,
    severity: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
) -> list[ChangeOut]:
    stmt = select(Change)
    if company_id is not None:
        stmt = stmt.where(Change.company_id == company_id)
    if severity is not None:
        stmt = stmt.where(Change.severity == severity)
    result = await db.execute(stmt.order_by(desc(Change.created_at)).limit(limit))
    return [ChangeOut.model_validate(row, from_attributes=True) for row in result.scalars().all()]


@router.get("/compare")
async def compare_snapshots(
    from_snapshot_id: int,
    to_snapshot_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    from_snapshot = await db.get(Snapshot, from_snapshot_id)
    to_snapshot = await db.get(Snapshot, to_snapshot_id)
    if not from_snapshot or not to_snapshot:
        return {"found": False}
    from_sections = from_snapshot.section_hashes or {}
    to_sections = to_snapshot.section_hashes or {}
    added = [k for k in to_sections if k not in from_sections]
    removed = [k for k in from_sections if k not in to_sections]
    changed = [k for k in to_sections if k in from_sections and to_sections[k] != from_sections[k]]
    return {
        "found": True,
        "from_snapshot_id": from_snapshot_id,
        "to_snapshot_id": to_snapshot_id,
        "added_sections": added,
        "removed_sections": removed,
        "changed_sections": changed,
    }

