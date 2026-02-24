from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from webwatcher.app import create_app
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Base


@pytest.mark.asyncio
async def test_company_and_monitor_routes(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async def override_db() -> AsyncIterator[AsyncSession]:
        async with session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_db_session] = override_db

    from webwatcher.api import routes_monitor

    monkeypatch.setattr(routes_monitor.run_monitor_task, "delay", lambda company_id: None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/companies",
            json={
                "name": "Acme Corp",
                "base_url": "https://example.com",
                "ir_url": "https://example.com/investors",
                "scan_interval_minutes": 90,
            },
        )
        assert created.status_code == 201
        company_id = created.json()["id"]

        trigger = await client.post(f"/api/v1/monitor/trigger/{company_id}")
        assert trigger.status_code == 200
        assert trigger.json()["queued"] is True

        changes = await client.get("/api/v1/changes")
        assert changes.status_code == 200
        assert isinstance(changes.json(), list)

    await engine.dispose()

