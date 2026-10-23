#!/usr/bin/env python3
"""Fail CI if the full test suite leaves rows in managed cleanup tables.

This CLI is CI-only: it refuses to run outside GitHub Actions, then validates that
DATABASE_URL targets the workflow's disposable local PostgreSQL database. Never use
against production. Raw tables are included because ORM cleanup cannot see every SQL-migration
table; optional tables are skipped until their migration exists on the checked-out head.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "bot_core"))


def validated_database_url() -> str:
    # This is a CI gate, not a general-purpose database inspection utility. Refuse
    # local/manual execution before parsing or opening any connection; otherwise a
    # local port-forward to a database named datacube_bot_test could satisfy the URL
    # checks below despite not being the disposable service owned by this workflow.
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit(
            "Refusing DB-leakage audit: this check may only run inside GitHub Actions."
        )
    value = os.environ.get("DATABASE_URL", "")
    parsed = urlparse(value)
    database = parsed.path.lstrip("/")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or database != "datacube_bot_test":
        raise SystemExit(
            "Refusing DB-leakage audit: DATABASE_URL must point to the isolated local "
            "datacube_bot_test database."
        )
    if not value.startswith("postgresql+asyncpg://"):
        raise SystemExit("Refusing DB-leakage audit: expected a PostgreSQL async URL.")
    # The workflow service listens on 5432. Reject alternate direct ports so a local
    # forwarded listener cannot be mistaken for the disposable service.
    try:
        port = parsed.port
    except ValueError as exc:
        raise SystemExit("Refusing DB-leakage audit: DATABASE_URL must use a valid PostgreSQL port.") from exc
    if port not in {None, 5432}:
        raise SystemExit("Refusing DB-leakage audit: expected the disposable PostgreSQL port 5432.")
    # SQLAlchemy merges URL query parameters into asyncpg connect arguments. Without
    # this check, ?host=, ?port=, or ?database= can override the values validated above.
    if parsed.query:
        raise SystemExit("Refusing DB-leakage audit: query parameters are not allowed.")

    # The workflow applies SQL migrations through DATABASE_URL_SYNC but pytest and this
    # audit use DATABASE_URL. If those variables ever drift to different databases, tests
    # could pass against a schema created by fixtures while the migrations were applied
    # elsewhere, and the leakage audit would inspect the wrong database. Validate both
    # targets before creating an engine and require the same exact endpoint/database.
    sync_value = os.environ.get("DATABASE_URL_SYNC", "")
    if not sync_value:
        raise SystemExit("Refusing DB-leakage audit: DATABASE_URL_SYNC is required.")
    sync_parsed = urlparse(sync_value)
    sync_database = sync_parsed.path.lstrip("/")
    if sync_parsed.scheme != "postgresql":
        raise SystemExit("Refusing DB-leakage audit: DATABASE_URL_SYNC must use a PostgreSQL URL.")
    if sync_parsed.hostname not in {"localhost", "127.0.0.1", "::1"} or sync_database != "datacube_bot_test":
        raise SystemExit(
            "Refusing DB-leakage audit: DATABASE_URL_SYNC must point to the same isolated local "
            "datacube_bot_test database."
        )
    try:
        sync_port = sync_parsed.port
    except ValueError as exc:
        raise SystemExit("Refusing DB-leakage audit: DATABASE_URL_SYNC must use a valid PostgreSQL port.") from exc
    if sync_port not in {None, 5432}:
        raise SystemExit("Refusing DB-leakage audit: expected the disposable PostgreSQL port 5432.")
    if sync_parsed.query:
        raise SystemExit("Refusing DB-leakage audit: query parameters are not allowed.")
    if (sync_parsed.hostname, sync_port or 5432, sync_database) != (
        parsed.hostname, port or 5432, database
    ):
        raise SystemExit(
            "Refusing DB-leakage audit: DATABASE_URL and DATABASE_URL_SYNC must target the same database endpoint."
        )
    return value


async def main() -> int:
    # Validate before importing conftest: it imports application modules, so the
    # guard must run before any of that import-time configuration can touch a URL.
    database_url = validated_database_url()
    from conftest import CLEANUP_MODELS, CLEANUP_RAW_TABLES  # noqa: E402

    engine = create_async_engine(database_url, pool_pre_ping=True)
    leaks: list[tuple[str, int]] = []
    try:
        async with engine.connect() as connection:
            for model in CLEANUP_MODELS:
                count = int((await connection.execute(select(func.count()).select_from(model))).scalar_one())
                if count:
                    leaks.append((model.__tablename__, count))

            raw_tables = tuple(CLEANUP_RAW_TABLES) + ("outbound_message_set_keys",)
            for table in raw_tables:
                exists = (
                    await connection.execute(
                        text("SELECT to_regclass(:qualified_name) IS NOT NULL"),
                        {"qualified_name": f"public.{table}"},
                    )
                ).scalar_one()
                if not exists:
                    continue
                count = int(
                    (
                        await connection.execute(
                            text(f'SELECT COUNT(*) FROM "{table}"')
                        )
                    ).scalar_one()
                )
                if count:
                    leaks.append((table, count))
    finally:
        await engine.dispose()

    if leaks:
        print("Database leakage detected after pytest:")
        for table, count in sorted(leaks):
            print(f"- {table}: {count} row(s)")
        return 1

    print("Database leakage audit passed: all CLEANUP_MODELS and existing CLEANUP_RAW_TABLES are empty.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
