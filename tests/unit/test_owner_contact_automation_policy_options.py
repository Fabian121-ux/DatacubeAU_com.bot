from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pytest

from app.services.owner_contact_automation_policy_command_service import OwnerContactAutomationPolicyCommandService


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
        return _MutationResult(True, 51)

    async def disable_exact(self, **kwargs):
        self.calls.append(("disable", kwargs))
        return _MutationResult(True, 51)


@pytest.mark.asyncio
async def test_owner_can_define_bounded_exact_contact_policy_options():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        (
            "17 2348012345678@c.us "
            "allowed=normal_reply,followup; "
            "prohibited=payments; "
            "approval=external_action; "
            "relationship=long-term client; "
            "tone=warm and concise; "
            "quiet=22:00-07:00@Africa/Lagos; "
            "expires=2026-09-30T23:59:00+01:00"
        ),
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error is None
    action, payload = mutations.calls[0]
    assert action == "upsert"
    assert payload["contact_id"] == 17
    assert payload["exact_chat_id"] == "2348012345678@c.us"
    assert payload["allowed_categories"] == ("normal_reply", "followup")
    assert payload["prohibited_categories"] == ("payments",)
    assert payload["approval_required_categories"] == ("external_action",)
    assert payload["relationship_context"] == "long-term client"
    assert payload["tone_guidance"] == "warm and concise"
    assert payload["quiet_hours"] == {
        "start": "22:00",
        "end": "07:00",
        "timezone": "Africa/Lagos",
    }
    assert payload["expires_at"] == datetime.fromisoformat("2026-09-30T23:59:00+01:00")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "policy_spec, expected_text",
    [
        ("allowed=normal_reply; quiet=25:00-07:00@Africa/Lagos", "valid 00:00-23:59"),
        ("allowed=normal_reply; quiet=22:00-07:00@No/Such_Zone", "timezone is not recognized"),
        ("allowed=normal_reply; expires=2026-09-30T23:59:00", "timezone offset"),
        ("allowed=normal_reply; allowed=followup", "Duplicate policy option"),
        ("allowed=normal_reply; unknown=value", "Unsupported policy option"),
    ],
)
async def test_invalid_policy_options_fail_before_mutation(policy_spec, expected_text):
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "set",
        f"17 2348012345678@c.us {policy_spec}",
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error == "invalid contact automation command arguments"
    assert expected_text in result.reply_text
    assert mutations.calls == []


@pytest.mark.asyncio
async def test_disable_refuses_policy_options_and_remains_exact_target_only():
    mutations = _Mutations()
    service = OwnerContactAutomationPolicyCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "disable",
        "17 2348012345678@c.us allowed=normal_reply",
        permission="owner",
        owner_identity="admin:1",
    )

    assert result.error == "invalid contact automation command arguments"
    assert mutations.calls == []
