"""Identity Registry: the authoritative source for Zina/Fabian/project identity facts.

Before this file, `score_entry`/`_special_answer`/`ensure_defaults_from_profile` had no
direct test coverage at all -- other tests stub out `identity_reply()` entirely, so the
real matching logic was unexercised (matching the 16% coverage figure for this file).
These tests exercise the service directly against a real database, and cover the
delete/search/get_by_key lifecycle additions plus a regression for a real bug found
while adding them: `ensure_defaults_from_profile` used to check existence against only
*enabled* entries, so disabling (or deleting) a default and re-running it would attempt
a duplicate-key insert and crash.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.schema import AuditLog, IdentityRegistryEntry
from app.services.identity_registry_service import IdentityRegistryService

PROFILE = {"owner_name": "Fabian", "assistant_name": "Zina"}


@pytest.mark.asyncio
async def test_ensure_defaults_from_profile_seeds_all_defaults_with_source_and_type(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    rows = (await db_session.execute(select(IdentityRegistryEntry))).scalars().all()
    by_key = {row.registry_key: row for row in rows}

    expected_keys = {
        "zina",
        "fabian",
        "services",
        "datacube_au",
        "zinax",
        "moxiz_gateway",
        "projects",
        "skills",
    }
    assert expected_keys <= set(by_key)
    for key in expected_keys:
        assert by_key[key].source == "system_default"
        assert by_key[key].deleted_at is None

    assert by_key["zina"].entity_type == "assistant"
    assert by_key["fabian"].entity_type == "person"
    assert by_key["datacube_au"].entity_type == "project"
    assert by_key["zinax"].entity_type == "project"
    assert by_key["moxiz_gateway"].entity_type == "project"


@pytest.mark.asyncio
async def test_ensure_defaults_is_idempotent_across_repeated_calls(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.ensure_defaults_from_profile(PROFILE)

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "zina")
        )
    ).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_ensure_defaults_does_not_crash_or_resurrect_a_disabled_default(db_session):
    """Regression: existence used to be checked against enabled_entries() only.

    Disabling a default (without deleting it) and re-running ensure_defaults_from_profile
    used to attempt a second INSERT with the same unique registry_key and crash.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    zina = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "zina")
        )
    ).scalar_one()
    zina.is_enabled = False
    await db_session.flush()

    # Must not raise IntegrityError on a duplicate registry_key.
    await service.ensure_defaults_from_profile(PROFILE)

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "zina")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].is_enabled is False  # stays disabled, not silently re-enabled


@pytest.mark.asyncio
async def test_ensure_defaults_does_not_resurrect_a_deleted_default(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    assert await service.delete("zina") is True

    await service.ensure_defaults_from_profile(PROFILE)

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "zina")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].deleted_at is not None
    assert await service.get_by_key("zina") is None


@pytest.mark.asyncio
async def test_answer_returns_none_with_no_entries(db_session):
    service = IdentityRegistryService(db_session)
    assert await service.answer("who are you") is None


@pytest.mark.asyncio
async def test_answer_uses_special_answer_for_identity_phrases(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.answer("who are you?") == "I am Zina, Fabian's AI assistant."
    assert "Fabian created Zina" in (await service.answer("who created you") or "")
    assert await service.answer("who is fabian") == "Fabian is the owner and creator I assist."


@pytest.mark.asyncio
async def test_answer_falls_back_to_scored_match_above_threshold(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    # "moxiz" has no _special_answer branch at all (unlike "datacube"/"zinax"/"fabian"),
    # so a hit here can only come from score_entry's alias/keyword matching.
    result = await service.answer("what is moxiz gateway")
    assert result is not None
    assert "Moxiz Gateway" in result


@pytest.mark.asyncio
async def test_answer_returns_none_below_score_threshold(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.answer("what's the weather like today in paris") is None


@pytest.mark.asyncio
async def test_score_entry_rewards_alias_and_entity_matches(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    zina = await service.get_by_key("zina")

    from app.services.faq_service import FAQService

    high = IdentityRegistryService.score_entry(FAQService.semantic_normalize("what is your name zina"), zina)
    low = IdentityRegistryService.score_entry(FAQService.semantic_normalize("unrelated query about pizza"), zina)
    assert high > low


@pytest.mark.asyncio
async def test_resolve_references_substitutes_known_key_and_flags_unknown(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    resolved = await service.resolve_references("Ask {{identity:fabian}} for details.")
    assert "Fabian is the owner and creator I assist." in resolved

    resolved_unknown = await service.resolve_references("See {{identity:nonexistent_key}}.")
    assert "do not have an active identity record" in resolved_unknown

    # No token present: returned unchanged, not re-processed.
    assert await service.resolve_references("plain text") == "plain text"


@pytest.mark.asyncio
async def test_get_by_key_excludes_deleted_but_includes_disabled(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.get_by_key("does-not-exist") is None

    zina = await service.get_by_key("zina")
    zina.is_enabled = False
    await db_session.flush()
    assert (await service.get_by_key("zina")) is not None

    await service.delete("fabian")
    assert await service.get_by_key("fabian") is None


@pytest.mark.asyncio
async def test_search_matches_across_fields_and_respects_include_disabled(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    by_name = await service.search("Moxiz")
    assert any(entry.registry_key == "moxiz_gateway" for entry in by_name)

    by_category = await service.search("ZinaX")
    assert any(entry.registry_key == "zinax" for entry in by_category)

    zina = await service.get_by_key("zina")
    zina.is_enabled = False
    await db_session.flush()

    excluded = await service.search("zina")
    assert all(entry.registry_key != "zina" for entry in excluded)

    included = await service.search("zina", include_disabled=True)
    assert any(entry.registry_key == "zina" for entry in included)

    empty_query = await service.search("")
    assert len(empty_query) >= 1


@pytest.mark.asyncio
async def test_delete_tombstones_writes_audit_and_is_reported_not_found_on_repeat(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.delete("does-not-exist") is False

    result = await service.delete("skills", request_id="req-1")
    assert result is True

    row = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "skills")
        )
    ).scalar_one()
    assert row.deleted_at is not None
    assert row.is_enabled is False

    audit = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "identity_registry_deleted")
        )
    ).mappings().first()
    assert audit is not None
    assert audit["entity_id"] == "skills"

    # Deleted entries are excluded from get_by_key, so a repeat delete reports "not found"
    # rather than silently succeeding a second time -- distinct from PrivateMediaArtifact's
    # idempotent-true convention, and an intentional choice for this resource: the API
    # surfaces this as a 404, which is the correct signal for "already gone."
    assert await service.delete("skills") is False


@pytest.mark.asyncio
async def test_enabled_entries_excludes_deleted_rows(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.delete("projects")

    entries = await service.enabled_entries()
    assert all(entry.registry_key != "projects" for entry in entries)
