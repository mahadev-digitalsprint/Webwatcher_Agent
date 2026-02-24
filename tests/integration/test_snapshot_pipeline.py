import os

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from webwatcher.db.models import Base
from webwatcher.normalization.html_normalizer import normalize_html
from webwatcher.storage.snapshot_manager import SnapshotManager
from webwatcher.storage.storage_service import StorageService


@pytest.mark.asyncio
async def test_noisy_html_change_does_not_create_new_snapshot(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    os.environ["BASE_DOWNLOAD_PATH"] = str(tmp_path / "downloads")
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    html_v1 = "<html><body><h1>Investor Update</h1><p>Revenue 100</p></body></html>"
    html_v2 = (
        "<html><head><script>var ts=123</script></head>"
        "<body><h1>Investor Update</h1><p>Revenue 100</p></body></html>"
    )
    norm1 = normalize_html(html_v1, "https://example.com/investor")
    norm2 = normalize_html(html_v2, "https://example.com/investor")

    manager = SnapshotManager(StorageService())
    async with session_maker() as session:
        first = await manager.create_snapshot_if_changed(
            session, company_id=1, scan_run_id=1, source_url="https://example.com/investor", normalized=norm1, raw_html=html_v1.encode()
        )
        second = await manager.create_snapshot_if_changed(
            session, company_id=1, scan_run_id=2, source_url="https://example.com/investor", normalized=norm2, raw_html=html_v2.encode()
        )
        await session.commit()
    assert first.changed is True
    assert second.changed is False

