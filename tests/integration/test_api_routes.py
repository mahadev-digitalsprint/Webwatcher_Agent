from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from webwatcher.app import create_app
from webwatcher.core.database import get_db_session
from webwatcher.db.models import Base, Document, Snapshot


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


@pytest.mark.asyncio
async def test_trigger_scan_falls_back_to_local_when_queue_unavailable(monkeypatch, tmp_path) -> None:
    db_path = tmp_path / "api_unavailable.db"
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

    ran_local = {"value": False}
    monkeypatch.setattr(routes_monitor, "_queue_available", lambda: False)
    monkeypatch.setattr(
        routes_monitor,
        "_launch_local_monitor",
        lambda _background_tasks, _company_id: ran_local.__setitem__("value", True),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/companies",
            json={
                "name": "Queue Test Co",
                "base_url": "https://queuetest.example.com",
                "scan_interval_minutes": 90,
            },
        )
        assert created.status_code == 201
        company_id = created.json()["id"]

        trigger = await client.post(f"/api/v1/monitor/trigger/{company_id}")
        assert trigger.status_code == 200
        assert trigger.json()["queued"] is True
        assert ran_local["value"] is True

    await engine.dispose()


@pytest.mark.asyncio
async def test_snapshot_and_document_visibility_routes(tmp_path) -> None:
    db_path = tmp_path / "api_visibility.db"
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post(
            "/api/v1/companies",
            json={
                "name": "Artifact Co",
                "base_url": "https://artifact.example.com",
                "scan_interval_minutes": 90,
            },
        )
        assert created.status_code == 201
        company_id = created.json()["id"]

        async with session_maker() as session:
            snapshot = Snapshot(
                company_id=company_id,
                scan_run_id=None,
                source_url="https://artifact.example.com/investor",
                page_hash="hash-page-1",
                numbers_hash="hash-num-1",
                section_hashes={"0": "abc"},
                normalized_json={
                    "pdf_links": ["https://artifact.example.com/docs/q1.pdf"],
                    "crawled_links": [
                        "https://artifact.example.com/investor",
                        "https://artifact.example.com/investor/results",
                    ],
                },
                raw_blob_path="1/20260224T000000Z/page.html",
            )
            session.add(snapshot)
            await session.flush()

            doc = Document(
                company_id=company_id,
                snapshot_id=snapshot.id,
                url="https://artifact.example.com/docs/q1.pdf",
                doc_hash="doc-hash-1",
                content_type="application/pdf",
                storage_path="1/20260224T000000Z/document.pdf",
            )
            session.add(doc)
            await session.commit()

        snapshots = await client.get(f"/api/v1/companies/{company_id}/snapshots")
        assert snapshots.status_code == 200
        assert len(snapshots.json()) == 1
        assert snapshots.json()[0]["pdf_links"] == ["https://artifact.example.com/docs/q1.pdf"]

        documents = await client.get(f"/api/v1/companies/{company_id}/documents")
        assert documents.status_code == 200
        assert len(documents.json()) == 1

        links = await client.get(f"/api/v1/companies/{company_id}/crawl-links")
        assert links.status_code == 200
        payload = links.json()
        assert "https://artifact.example.com/investor" in payload["page_urls"]
        assert "https://artifact.example.com/investor/results" in payload["page_urls"]
        assert "https://artifact.example.com/docs/q1.pdf" in payload["pdf_links_found"]
        assert "https://artifact.example.com/docs/q1.pdf" in payload["pdf_documents_stored"]

    await engine.dispose()
