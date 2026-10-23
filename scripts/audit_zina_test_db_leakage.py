#!/usr/bin/env python3
"""Fail CI if the full test suite leaves rows in managed cleanup tables.

Restricted to the workflow's disposable local PostgreSQL database. Never use against
production. Raw tables are included because ORM cleanup cannot see every SQL-migration
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
