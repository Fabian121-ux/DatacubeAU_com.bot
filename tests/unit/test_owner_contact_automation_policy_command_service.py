from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.services.owner_contact_automation_policy_command_service import (
    OwnerContactAutomationPolicyCommandService,
)


@dataclass
class _MutationResult:
    ok: bool
    policy_id: int | None = None
    error: str | None = None


class _Mutations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def upsert_exact(self, **kwargs):
        self.calls.append(("upsert", kwargs))
        return _MutationResult(True, 41)

    async def disable_exact(self, **kwargs):
        self.calls.append(("disable", kwargs))
        return _MutationResult(True, 41)


@pytest.mark.asyncio
async def test_owner_set_delegates_only_exact_identity_and_categories():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        "17 2348012345678@c.us support,faq",
        permission="OWNER",
        owner_identity="admin:1",
    )

    assert result.consumed is True
    assert result.error is None
    assert result.policy_id == 41
    assert len(mutations.calls) == 1
    action, payload = mutations.calls[0]
    assert action == "upsert"
    assert payload["contact_id"] == 17
    assert payload["exact_chat_id"] == "2348012345678@c.us"
    assert payload["allowed_categories"] == ("support", "faq")
    assert payload["enabled"] is True
    assert payload["permission"] == "owner"


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["user", "admin", "", "ADMIN"])
async def test_non_owner_cannot_mutate_contact_policy(permission):
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        "17 2348012345678@c.us support",
        permission=permission,
        owner_identity="admin:2",
    )

    assert result.consumed is True
    assert result.error == "owner permission required"
    assert mutations.calls == []


@pytest.mark.asyncio
async def test_ambiguous_or_display_name_target_is_rejected_before_mutation():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        "17 Amanda support",
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error == "invalid contact automation command arguments"
    assert "ambiguous names are not accepted" in result.reply_text
    assert mutations.calls == []


@pytest.mark.asyncio
async def test_disable_requires_exact_contact_and_chat_pair():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "disable",
        "17 2348012345678@c.us",
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error is None
    action, payload = mutations.calls[0]
    assert action == "disable"
    assert payload["contact_id"] == 17
    assert payload["exact_chat_id"] == "2348012345678@c.us"


@pytest.mark.asyncio
async def test_set_rejects_missing_allowed_categories():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        "17 2348012345678@c.us",
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error == "invalid contact automation command arguments"
    assert mutations.calls == []
