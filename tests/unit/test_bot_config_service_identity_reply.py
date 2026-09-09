"""Regression for a Codex review finding on PR #50 itself: `IdentityRegistryService

.answer()`/`_special_answer()` were fixed to stop resurrecting a deleted default via
their own hardcoded fallback, but `BotConfigService.identity_reply()` -- the actual
production entry point `reply_planner.py` calls -- has its own, separate, older
hardcoded fallback that fires whenever the registry returns a falsy answer. That
fallback did not know about tombstones at all, so deleting a default identity fact
had zero observable effect on the real WhatsApp reply path even after the registry
fix, exactly the gap the reviewer flagged. These tests exercise `identity_reply()`
directly (not `IdentityRegistryService.answer()`), since that is the path the
reviewer pointed out these tests were missing.

Most of `identity_reply()`'s hardcoded branches (fabian/datacube/zinax) are, in
practice, pre-empted by `IdentityRegistryService.answer()`'s own scored-fallback
layer finding a *different*, legitimately-matching default entry before
`identity_reply()` ever reaches its own branches (e.g. deleting "datacube_au" still
lets the "projects" entry's answer, which happens to mention Datacube AU, win on a
"what is datacube" query) -- that layer is separately tested in
test_identity_registry_service.py and is not a regression. To test
`identity_reply()`'s own deleted-key handling in isolation from that separate layer,
the registry call is patched to return no match (as it would once, e.g., that
scored-fallback also finds nothing), with a controlled `deleted_default_keys()`
result standing in for a real delete.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.services.bot_config_service import BotConfigService
from app.services.identity_registry_service import IdentityRegistryService

PROFILE = {"owner_name": "Fabian", "assistant_name": "Zina"}


def _patched_registry(deleted_keys: set[str]):
    return patch.multiple(
        IdentityRegistryService,
        answer=AsyncMock(return_value=None),
        deleted_default_keys=AsyncMock(return_value=deleted_keys),
    )


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_zina_end_to_end(db_session):
    """End-to-end (no mocking): for this phrase, no other default entry scores highly

    enough to pre-empt identity_reply()'s own branch, so this exercises the real
    registry -> bot_config fallthrough exactly as it happens in production.
    """
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
async def test_identity_reply_honors_deleted_fabian_when_registry_has_no_other_match(db_session):
    bot_config = BotConfigService(db_session)
    with _patched_registry({"fabian"}):
        assert await bot_config.identity_reply("who is fabian") == BotConfigService._DELETED_FALLBACK_MESSAGE
        assert await bot_config.identity_reply("who created you") == BotConfigService._DELETED_FALLBACK_MESSAGE

    with _patched_registry(set()):
        result = await bot_config.identity_reply("who is fabian")
        assert result and result != BotConfigService._DELETED_FALLBACK_MESSAGE


@pytest.mark.asyncio
async def test_identity_reply_honors_deleted_projects(db_session):
    bot_config = BotConfigService(db_session)
    with _patched_registry({"projects"}):
        result = await bot_config.identity_reply("what are fabian's projects")
        assert result == BotConfigService._DELETED_FALLBACK_MESSAGE

    with _patched_registry(set()):
        result = await bot_config.identity_reply("what are fabian's projects")
        assert "Datacube AU" in result


@pytest.mark.asyncio
async def test_identity_reply_project_fallback_honors_deleted_datacube_zinax_moxiz(db_session):
    bot_config = BotConfigService(db_session)

    with _patched_registry({"datacube_au"}):
        assert await bot_config.identity_reply("what is datacube") == BotConfigService._DELETED_FALLBACK_MESSAGE
    with _patched_registry(set()):
        assert "Datacube AU" in await bot_config.identity_reply("what is datacube")

    with _patched_registry({"zinax"}):
        assert await bot_config.identity_reply("tell me about zinax") == BotConfigService._DELETED_FALLBACK_MESSAGE
    with _patched_registry(set()):
        assert "ZinaX" in await bot_config.identity_reply("tell me about zinax")

    with _patched_registry({"moxiz_gateway"}):
        assert await bot_config.identity_reply("what is moxiz") == BotConfigService._DELETED_FALLBACK_MESSAGE
    with _patched_registry(set()):
        assert "Moxiz Gateway" in await bot_config.identity_reply("what is moxiz")


@pytest.mark.asyncio
async def test_project_identity_reply_is_unaffected_by_a_default_call_with_no_deleted_keys(db_session):
    # Direct call with the default deleted_keys=None must behave exactly as before
    # this fix -- a regression guard on the classmethod's new optional parameter.
    result = BotConfigService._project_identity_reply("what is datacube", "Fabian")
    assert "Datacube AU" in result
