"""Regression for two Codex review findings on PR #50 itself.

**Round 2 finding**: `IdentityRegistryService.answer()`/`_special_answer()` were fixed
to stop resurrecting a deleted default via their own hardcoded fallback, but
`BotConfigService.identity_reply()` -- the actual production entry point
`reply_planner.py` calls -- has its own, separate, older hardcoded fallback that
fires whenever the registry returns a falsy answer. That fallback did not know about
tombstones at all, so deleting a default identity fact had zero observable effect on
the real WhatsApp reply path even after the registry fix.

**Round 3 finding**: even after the round-2 fix, `IdentityRegistryService.answer()`
itself could still leak a deleted fact through its own scored-fallback layer: once
`_special_answer()` returned `None` for an explicitly-targeted deleted key (e.g.
"datacube_au" for a "what is datacube" query), `answer()` fell through to scoring,
where the still-active "projects" entry -- whose own answer text separately lists
every project by name -- could win and re-state the "deleted" fact. Because that
happened *before* `identity_reply()` ever got a falsy registry result, its own
deleted-key checks (round 2's fix) never even ran. Fixed by
`IdentityRegistryService._explicit_target_key()`: `answer()` now refuses outright,
before scoring, whenever a query unambiguously targets one specific default key that
is unavailable.

These tests exercise `identity_reply()` directly, since that is the actual
production path the round-2 reviewer pointed out the original tests were missing.
With the round-3 fix, most of these are now true end-to-end tests (no mocking): the
registry layer itself no longer leaks. The one exception is a bare "moxiz" query
outside the registry's own explicit-target set for a case in `_project_identity_reply`
that has no `_special_answer` counterpart at all -- covered separately below.
"""

from __future__ import annotations

import pytest

from app.services.bot_config_service import BotConfigService
from app.services.identity_registry_service import IdentityRegistryService

PROFILE = {"owner_name": "Fabian", "assistant_name": "Zina"}


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_zina_end_to_end(db_session):
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    assert await bot_config.identity_reply("who are you?") == "I am Zina, Fabian's AI assistant."

    await registry.delete("zina")

    assert await bot_config.identity_reply("who are you?") == BotConfigService._DELETED_FALLBACK_MESSAGE
    # The unconditional final catch-all must also honor the deletion, not just the
    # dedicated "who are you" phrase branch.
    assert await bot_config.identity_reply("some unmatched message") == BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_unrelated_delete_does_not_suppress_other_defaults(db_session):
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    await registry.delete("fabian")

    # Deleting "fabian" must not suppress "zina"'s own, unrelated identity answer.
    assert await bot_config.identity_reply("who are you?") == "I am Zina, Fabian's AI assistant."


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_fabian_end_to_end(db_session):
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    before = await bot_config.identity_reply("who is fabian")
    assert before and before != BotConfigService._DELETED_FALLBACK_MESSAGE

    await registry.delete("fabian")
    assert await bot_config.identity_reply("who is fabian") == BotConfigService._DELETED_FALLBACK_MESSAGE
    assert await bot_config.identity_reply("who created you") == BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_projects_end_to_end(db_session):
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    before = await bot_config.identity_reply("what are fabian's projects")
    assert "Datacube AU" in before

    await registry.delete("projects")
    assert await bot_config.identity_reply("what are fabian's projects") == BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_project_fallback_honors_deleted_datacube_and_zinax_end_to_end(db_session):
    """Regression for the round-3 finding specifically: before the

    `_explicit_target_key` fix, deleting "datacube_au" or "zinax" still let the
    "projects" entry's own scored answer (which separately lists both by name) win
    at the registry layer, so `identity_reply()` never even reached its own,
    already-fixed deleted-key check for these two.
    """
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    before_datacube = await bot_config.identity_reply("what is datacube")
    assert "Datacube AU" in before_datacube
    await registry.delete("datacube_au")
    assert await bot_config.identity_reply("what is datacube") == BotConfigService._DELETED_FALLBACK_MESSAGE

    before_zinax = await bot_config.identity_reply("tell me about zinax")
    assert "ZinaX" in before_zinax
    await registry.delete("zinax")
    assert await bot_config.identity_reply("tell me about zinax") == BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_moxiz_end_to_end(db_session):
    """"moxiz" has no `_special_answer` branch of its own (unlike datacube/zinax),

    so it needed its own addition to `_explicit_target_key` to close the same
    "projects" entry leak for it specifically.
    """
    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)

    before = await bot_config.identity_reply("what is moxiz")
    assert "Moxiz Gateway" in before

    await registry.delete("moxiz_gateway")
    assert await bot_config.identity_reply("what is moxiz") == BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_honors_a_default_revived_as_disabled(db_session):
    """Regression for a second round-3 finding: recreating a deleted default via the

    admin API with `enabled=False` clears `deleted_at` (no longer tombstoned) but
    leaves the row inactive. `unavailable_default_keys()` must still flag it --
    otherwise `_special_answer`/`identity_reply()` would treat "disabled" the same
    as "never configured" and serve the hardcoded default again.
    """
    from app.api.admin import IdentityRegistryUpdate, upsert_identity_registry

    registry = IdentityRegistryService(db_session)
    await registry.ensure_defaults_from_profile(PROFILE)
    bot_config = BotConfigService(db_session)
    await registry.delete("zina")

    await upsert_identity_registry(
        IdentityRegistryUpdate(
            registry_key="zina",
            name="Zina",
            description="revived but intentionally disabled",
            answer="revived but intentionally disabled",
            enabled=False,
        ),
        db=db_session,
    )

    assert await bot_config.identity_reply("who are you?") == BotConfigService._DELETED_FALLBACK_MESSAGE
    assert "zina" in await registry.unavailable_default_keys()


@pytest.mark.asyncio
async def test_project_identity_reply_is_unaffected_by_a_default_call_with_no_unavailable_keys(db_session):
    # Direct call with the default unavailable_keys=None must behave exactly as
    # before this fix -- a regression guard on the classmethod's new optional
    # parameter.
    result = BotConfigService._project_identity_reply("what is datacube", "Fabian")
    assert "Datacube AU" in result
