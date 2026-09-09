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


@pytest.mark.asyncio
async def test_deleted_default_is_not_resurrected_by_the_special_answer_fallback(db_session):
    """Regression (Codex review on PR #47, landed after merge): `_special_answer`'s

    hardcoded fallback text fired whenever no active entry existed for a default key,
    regardless of *why* it was missing -- so deleting a seeded default (e.g. "fabian")
    had zero observable effect on that exact phrase-matched answer, silently undoing
    the OWNER's delete. Each phrase below must stop returning the deleted entry's own
    stale text once it is gone.

    A later round found that `answer()` could still leak the deleted fact through a
    *different* door: once `_special_answer` refused, `answer()` fell through to its
    scored-match loop, where the still-active "projects" entry -- whose own answer
    text separately lists every project by name -- could win and re-state the exact
    fact that was just deleted. `_explicit_target_key` now refuses outright, before
    scoring, whenever a query unambiguously targets one specific unavailable key --
    so these assertions are `is None`, not just "not the old text".
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.answer("who is fabian") == "Fabian is the owner and creator I assist."
    await service.delete("fabian")
    assert await service.answer("who is fabian") is None

    assert await service.answer("who are you?") == "I am Zina, Fabian's AI assistant."
    await service.delete("zina")
    assert await service.answer("who are you?") is None

    datacube_answer = "Datacube AU is an AI-powered assistant and knowledge automation project created by Fabian."
    assert await service.answer("what is datacube") == datacube_answer
    await service.delete("datacube_au")
    # Must not leak the old hardcoded _special_answer literal, the real entry's own
    # answer, NOR the "projects" entry's answer (which separately mentions Datacube AU).
    assert await service.answer("what is datacube") is None


@pytest.mark.asyncio
async def test_special_answer_still_serves_non_deleted_defaults_after_an_unrelated_delete(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.delete("fabian")

    # "zina"/"zinax" were never deleted -- unrelated deletions must not suppress them.
    assert await service.answer("who are you?") == "I am Zina, Fabian's AI assistant."
    assert "ZinaX" in (await service.answer("what is zinax") or "")


@pytest.mark.asyncio
async def test_named_entity_queries_are_blocked_too_not_only_the_specific_phrases(db_session):
    """Regression (Codex, round 4 on PR #50): "who is zina?"/"what is zina" match no

    `_special_answer` phrase branch at all (only "what is *your* name"/"who are
    *you*" do), so they were missed by the first version of `_explicit_target_keys`
    and still leaked through the "projects" entry's scored answer after deleting
    "zina". A bare mention of "zina"/"fabian" by name must be treated as targeting
    that key too, not just the specific pre-canned phrases.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.delete("zina")

    assert await service.answer("who is zina?") is None
    assert await service.answer("what is zina") is None
    assert await service.answer("tell me about fabian and zina") is None

    # A query naming only the non-deleted party must still work normally.
    assert await service.answer("who is fabian") == "Fabian is the owner and creator I assist."


@pytest.mark.asyncio
async def test_deleting_zina_does_not_suppress_an_unrelated_zinax_query(db_session):
    """Regression (Codex, round 7 on PR #50): the bare "zina" target check used

    plain substring matching, and "zina" is itself a substring of "zinax" -- so
    `_explicit_target_keys("what is zinax")` incorrectly returned {"zina", "zinax"}
    and an unrelated "zina" tombstone blocked a ZinaX query that has nothing to do
    with it, discarding the still-active (possibly administrator-customized) ZinaX
    answer in favor of the generic fallback. Fixed with a word-boundary regex.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.delete("zina")

    # "zinax" was never deleted -- a query naming only it must be unaffected by the
    # unrelated "zina" tombstone.
    result = await service.answer("what is zinax")
    assert result is not None
    assert "ZinaX" in result

    # A query about "zina" itself (word boundary, not "zinax") must still be blocked.
    assert await service.answer("who is zina?") is None


@pytest.mark.asyncio
async def test_compound_queries_naming_multiple_targets_are_blocked_on_any_deleted_one(db_session):
    """Regression (Codex, round 6 on PR #50): `_explicit_target_keys` used to

    short-circuit on the first matching branch, so a compound query like "what is
    Fabian's Datacube project?" matched only the "project"+"fabian" branch
    (returning {"projects"}) and never noticed "datacube" was *also* explicitly
    named -- deleting "datacube_au" alone didn't block it, and `_special_answer`'s
    "projects" branch then leaked the still-active projects summary (which lists
    Datacube AU by name). Every matching condition must now be accumulated, not
    just the first one.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    before = await service.answer("what is fabian's datacube project?")
    assert "Datacube AU" in before or before is not None

    await service.delete("datacube_au")
    assert await service.answer("what is fabian's datacube project?") is None

    # A compound query naming only still-available targets must be unaffected.
    assert await service.answer("what are fabian's projects") is not None


@pytest.mark.asyncio
async def test_scored_match_does_not_disturb_backfill_eligibility(db_session):
    """Regression (Codex, round 6 on PR #50): `answer()`'s scored-match branch used

    to advance `updated_at` on every successful lookup as a side effect of a mere
    read, which made migration 035's `updated_at = created_at` backfill-eligibility
    check permanently (and incorrectly) treat any row ever served this way as
    "edited". Serving an answer must not touch `updated_at` -- only an actual
    content edit (via `upsert_identity_registry`) should.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    moxiz = await service.get_by_key("moxiz_gateway")
    assert moxiz.updated_at == moxiz.created_at  # backfill-eligible before the read

    # "moxiz" has no _special_answer branch -- this can only be served via the
    # scored-match loop, exactly the path that used to touch updated_at.
    result = await service.answer("what is moxiz gateway")
    assert result is not None

    await db_session.refresh(moxiz)
    # Still backfill-eligible: migration 035's actual criterion is
    # `updated_at = created_at`, which a mere read/lookup must not disturb.
    assert moxiz.updated_at == moxiz.created_at


@pytest.mark.asyncio
async def test_unavailable_default_keys_includes_disabled_not_only_deleted(db_session):
    """A default that is merely disabled (not deleted) must also count as

    "unavailable" -- otherwise reviving a tombstoned key via the admin API with
    `enabled=False` would clear the tombstone and immediately look "never
    configured" again to `_special_answer`, resurrecting the hardcoded default text
    for a key the OWNER just asked to keep off.
    """
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)

    assert await service.unavailable_default_keys() == set()

    zina = await service.get_by_key("zina")
    zina.is_enabled = False
    await db_session.flush()

    assert "zina" in await service.unavailable_default_keys()
    assert await service.answer("who are you?") is None

    await service.delete("fabian")
    unavailable = await service.unavailable_default_keys()
    assert {"zina", "fabian"} <= unavailable
