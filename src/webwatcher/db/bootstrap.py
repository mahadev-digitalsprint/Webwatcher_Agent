from sqlalchemy import text

from webwatcher.core.database import get_engine
from webwatcher.db.models import Base


async def bootstrap_database() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if conn.dialect.name != "postgresql":
            return
        try:
            await _repair_legacy_companies_table(conn)
        except Exception:
            # Keep API startup available even if compatibility DDL cannot acquire locks.
            pass


async def _repair_legacy_companies_table(conn) -> None:
    columns = await _columns_meta(conn)
    if not columns:
        return

    # Avoid hanging startup when table is busy.
    await conn.execute(text("SET LOCAL lock_timeout = '2s'"))

    # Some environments already contain an older companies schema. Add missing columns
    # non-destructively so API queries do not fail with UndefinedColumn errors.
    await _add_if_missing(conn, columns, "name", "VARCHAR(255)")
    await _add_if_missing(conn, columns, "base_url", "VARCHAR(1024)")
    await _add_if_missing(conn, columns, "ir_url", "VARCHAR(1024)")
    await _add_if_missing(conn, columns, "ir_confidence", "DOUBLE PRECISION DEFAULT 0")
    await _add_if_missing(conn, columns, "scan_interval_minutes", "INTEGER DEFAULT 90")
    await _add_if_missing(conn, columns, "is_active", "BOOLEAN DEFAULT TRUE")
    await _add_if_missing(conn, columns, "last_scanned_at", "TIMESTAMPTZ")
    await _add_if_missing(conn, columns, "next_scan_at", "TIMESTAMPTZ")
    await _add_if_missing(conn, columns, "updated_at", "TIMESTAMPTZ")
    columns = await _columns_meta(conn)

    name_expr_items = ["name"]
    if "company_name" in columns:
        name_expr_items.append("company_name")
    if "company_slug" in columns:
        name_expr_items.append("company_slug")
    name_expr_items.append("'company-' || id::text")
    name_expr = "COALESCE(" + ", ".join(name_expr_items) + ")"

    await conn.execute(
        text(
            f"""
            UPDATE companies
            SET name = {name_expr}
            WHERE name IS NULL
            """
        )
    )

    base_expr_items = ["base_url"]
    if "website_url" in columns:
        base_expr_items.append("website_url")
    base_expr_items.append("'https://example.com/company-' || id::text")
    base_expr = "COALESCE(" + ", ".join(base_expr_items) + ")"
    await conn.execute(
        text(
            f"""
            UPDATE companies
            SET base_url = {base_expr}
            WHERE base_url IS NULL
            """
        )
    )

    scan_expr_items = ["scan_interval_minutes"]
    if "crawl_depth" in columns:
        scan_expr_items.append("crawl_depth")
    scan_expr_items.append("90")
    scan_expr = "COALESCE(" + ", ".join(scan_expr_items) + ")"
    await conn.execute(
        text(
            f"""
            UPDATE companies
            SET scan_interval_minutes = {scan_expr}
            WHERE scan_interval_minutes IS NULL
            """
        )
    )

    active_expr_items = ["is_active"]
    if "active" in columns:
        active_expr_items.append("active")
    active_expr_items.append("TRUE")
    active_expr = "COALESCE(" + ", ".join(active_expr_items) + ")"
    await conn.execute(
        text(
            f"""
            UPDATE companies
            SET is_active = {active_expr}
            WHERE is_active IS NULL
            """
        )
    )
    await conn.execute(text("UPDATE companies SET ir_confidence = COALESCE(ir_confidence, 0)"))
    await conn.execute(text("UPDATE companies SET updated_at = COALESCE(updated_at, created_at, NOW())"))

    # Legacy schema compatibility: old columns may still be NOT NULL and break inserts
    # from the new model that only writes name/base_url.
    if columns.get("company_name", {}).get("is_nullable") == "NO":
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN company_name DROP NOT NULL"))
    if columns.get("company_slug", {}).get("is_nullable") == "NO":
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN company_slug DROP NOT NULL"))
    if columns.get("website_url", {}).get("is_nullable") == "NO":
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN website_url DROP NOT NULL"))

    if "company_name" in columns:
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN company_name SET DEFAULT ''"))
        await conn.execute(
            text(
                """
                UPDATE companies
                SET company_name = COALESCE(NULLIF(company_name, ''), name, company_slug, 'company-' || id::text)
                WHERE company_name IS NULL OR company_name = ''
                """
            )
        )
    if "website_url" in columns:
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN website_url SET DEFAULT ''"))
        await conn.execute(
            text(
                """
                UPDATE companies
                SET website_url = COALESCE(NULLIF(website_url, ''), base_url)
                WHERE website_url IS NULL OR website_url = ''
                """
            )
        )
    if "company_slug" in columns:
        await conn.execute(text("ALTER TABLE companies ALTER COLUMN company_slug DROP DEFAULT"))
        await conn.execute(text("UPDATE companies SET company_slug = NULL WHERE company_slug = ''"))


async def _columns_meta(conn) -> dict[str, dict[str, str | None]]:
    rows = await conn.execute(
        text(
            """
            SELECT column_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name='companies'
            """
        )
    )
    return {
        row.column_name: {
            "is_nullable": row.is_nullable,
            "column_default": row.column_default,
        }
        for row in rows.fetchall()
    }


async def _add_if_missing(conn, columns: dict[str, dict[str, str | None]], name: str, ddl_type: str) -> None:
    if name not in columns:
        await conn.execute(text(f"ALTER TABLE companies ADD COLUMN {name} {ddl_type}"))
