from sqlalchemy import text

from webwatcher.core.database import get_engine
from webwatcher.db.models import Base


async def bootstrap_database() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name != "postgresql":
            return
        await _repair_legacy_companies_table(conn)


async def _repair_legacy_companies_table(conn) -> None:
    # Some environments already contain an older companies schema. Add missing columns
    # non-destructively so API queries do not fail with UndefinedColumn errors.
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS name VARCHAR(255)"))
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS base_url VARCHAR(1024)"))
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS ir_url VARCHAR(1024)"))
    await conn.execute(
        text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS ir_confidence DOUBLE PRECISION DEFAULT 0")
    )
    await conn.execute(
        text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS scan_interval_minutes INTEGER DEFAULT 90")
    )
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_scanned_at TIMESTAMPTZ"))
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS next_scan_at TIMESTAMPTZ"))
    await conn.execute(text("ALTER TABLE companies ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))

    await conn.execute(
        text(
            """
            UPDATE companies
            SET name = COALESCE(name, company_name, company_slug, 'company-' || id::text)
            WHERE name IS NULL
            """
        )
    )
    await conn.execute(
        text(
            """
            UPDATE companies
            SET base_url = COALESCE(base_url, website_url, 'https://example.com/company-' || id::text)
            WHERE base_url IS NULL
            """
        )
    )
    await conn.execute(
        text(
            """
            UPDATE companies
            SET scan_interval_minutes = COALESCE(scan_interval_minutes, crawl_depth, 90)
            WHERE scan_interval_minutes IS NULL
            """
        )
    )
    await conn.execute(
        text(
            """
            UPDATE companies
            SET is_active = COALESCE(is_active, active, TRUE)
            WHERE is_active IS NULL
            """
        )
    )
    await conn.execute(text("UPDATE companies SET ir_confidence = COALESCE(ir_confidence, 0)"))
    await conn.execute(text("UPDATE companies SET updated_at = COALESCE(updated_at, created_at, NOW())"))

