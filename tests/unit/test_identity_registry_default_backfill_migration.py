"""Regression for a Codex review finding (PR #47, landed after an unauthorized

self-merge -- see docs/ZINA_IMPLEMENTATION_ROADMAP.md): migration 033 added the
`source`/`entity_type` columns as nullable, but an installation whose default rows
were seeded by migrations 010/013 (or an even earlier `ensure_defaults_from_profile`
run) keeps those columns NULL forever -- the seeder only inserts a key that is
entirely absent, so it never repairs an existing row. Migration 035 is a one-time,
idempotent data backfill for exactly that gap; this test applies its actual SQL file
against rows shaped like that legacy state.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.schema import IdentityRegistryEntry
from app.utils.time import utcnow

_MIGRATION_TEXT = (
    Path(__file__).resolve().parents[2]
    / "bot_core"
    / "migrations"
    / "035_identity_registry_default_backfill.sql"
).read_text(encoding="utf-8")

# asyncpg's extended-query protocol refuses a multi-statement prepared statement (the
# real migration runner uses psql, which has no such restriction), so each `;`-terminated
# statement in the file is executed individually here -- this still runs the migration's
# actual SQL, just one statement per round-trip instead of psql's single script exec.
_WITHOUT_COMMENTS = "\n".join(
    line for line in _MIGRATION_TEXT.splitlines() if not line.strip().startswith("--")
)
MIGRATION_STATEMENTS = [statement.strip() for statement in _WITHOUT_COMMENTS.split(";") if statement.strip()]


async def _apply_migration(session) -> None:
    for statement in MIGRATION_STATEMENTS:
        await session.execute(text(statement))


@pytest.mark.asyncio
async def test_backfill_fills_null_source_and_entity_type_for_legacy_default_rows(db_session):
    now = utcnow()
    db_session.add(
        IdentityRegistryEntry(
            registry_key="fabian",
            category="Owner",
            name="Fabian",
            description="legacy seed row",
            aliases=[],
            keywords=[],
            entities=[],
            answer="legacy seed row",
            facts_json={},
            is_enabled=True,
            source=None,
            entity_type=None,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    await _apply_migration(db_session)

    row = (
        await db_session.execute(
            text("SELECT source, entity_type FROM identity_registry WHERE registry_key = 'fabian'")
        )
    ).mappings().first()
    assert row["source"] == "system_default"
    assert row["entity_type"] == "person"


@pytest.mark.asyncio
async def test_backfill_does_not_overwrite_a_row_that_already_has_a_source_or_type(db_session):
    now = utcnow()
    db_session.add(
        IdentityRegistryEntry(
            registry_key="zina",
            category="Zina",
            name="Zina",
            description="admin-edited row",
            aliases=[],
            keywords=[],
            entities=[],
            answer="admin-edited row",
            facts_json={},
            is_enabled=True,
            source="admin_dashboard",
            entity_type="custom_type",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    await _apply_migration(db_session)

    row = (
        await db_session.execute(
            text("SELECT source, entity_type FROM identity_registry WHERE registry_key = 'zina'")
        )
    ).mappings().first()
    assert row["source"] == "admin_dashboard"
    assert row["entity_type"] == "custom_type"


@pytest.mark.asyncio
async def test_backfill_is_idempotent_and_ignores_non_default_keys(db_session):
    now = utcnow()
    db_session.add(
        IdentityRegistryEntry(
            registry_key="some_custom_key",
            category="Custom",
            name="Custom",
            description="not a default",
            aliases=[],
            keywords=[],
            entities=[],
            answer="not a default",
            facts_json={},
            is_enabled=True,
            source=None,
            entity_type=None,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()

    await _apply_migration(db_session)
    await _apply_migration(db_session)  # applying twice must not raise or change anything further

    row = (
        await db_session.execute(
            text("SELECT source, entity_type FROM identity_registry WHERE registry_key = 'some_custom_key'")
        )
    ).mappings().first()
    assert row["source"] is None
    assert row["entity_type"] is None
