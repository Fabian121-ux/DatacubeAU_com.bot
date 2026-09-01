from datetime import timedelta
import json

import pytest

from app.services.owner_contact_automation_policy_service import OwnerContactAutomationPolicyService
from app.utils.time import utcnow


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, result_value=17):
        self.result_value = result_value
        self.calls = []
        self.flush_count = 0

    async def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return FakeResult(self.result_value)

    async def flush(self):
        self.flush_count += 1


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["user", "admin", "", "ADMIN"])
async def test_non_owner_cannot_create_or_disable_policy(permission):
    session = FakeSession()
    service = OwnerContactAutomationPolicyService(session)

    created = await service.upsert_exact(
        permission=permission,
        owner_identity="owner:1",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
        enabled=True,
        allowed_categories=["normal_reply"],
    )
    disabled = await service.disable_exact(
        permission=permission,
        owner_identity="owner:1",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
    )

    assert created.ok is False
    assert created.error == "owner permission required"
    assert disabled.ok is False
    assert disabled.error == "owner permission required"
    assert session.calls == []


@pytest.mark.asyncio
async def test_exact_contact_policy_is_bound_to_durable_contact_and_chat():
    session = FakeSession(result_value=23)
    service = OwnerContactAutomationPolicyService(session)

    result = await service.upsert_exact(
        permission="OWNER",
        owner_identity="admin:9",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
        enabled=True,
        allowed_categories=[" Normal_Reply ", "smalltalk"],
        prohibited_categories=["payment"],
        approval_required_categories=["sensitive_action"],
        relationship_context="friend",
        tone_guidance="warm but concise",
        quiet_hours={"timezone": "Africa/Lagos", "start": "22:00", "end": "07:00"},
        expires_at=utcnow() + timedelta(days=7),
    )

    assert result.ok is True
    assert result.policy_id == 23
    assert result.error is None
    assert session.flush_count == 1
    assert len(session.calls) == 1
    sql, params = session.calls[0]
    assert "ON CONFLICT (contact_id, exact_chat_id)" in sql
    assert params["contact_id"] == 41
    assert params["exact_chat_id"] == "2348012345678@c.us"
    assert json.loads(params["allowed_categories"]) == ["normal_reply", "smalltalk"]
    assert json.loads(params["prohibited_categories"]) == ["payment"]
    assert json.loads(params["approval_required_categories"]) == ["sensitive_action"]
    assert json.loads(params["quiet_hours_json"])["timezone"] == "Africa/Lagos"


@pytest.mark.asyncio
async def test_policy_requires_exact_identity_and_explicit_allowed_category():
    session = FakeSession()
    service = OwnerContactAutomationPolicyService(session)

    missing_identity = await service.upsert_exact(
        permission="owner",
        owner_identity="owner",
        contact_id=0,
        exact_chat_id="",
        enabled=True,
        allowed_categories=["normal_reply"],
    )
    empty_allowed = await service.upsert_exact(
        permission="owner",
        owner_identity="owner",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
        enabled=True,
        allowed_categories=[],
    )

    assert missing_identity.error == "exact contact identity required"
    assert empty_allowed.error == "at least one allowed category required"
    assert session.calls == []


@pytest.mark.asyncio
async def test_policy_rejects_category_conflict_and_expired_configuration():
    session = FakeSession()
    service = OwnerContactAutomationPolicyService(session)

    overlap = await service.upsert_exact(
        permission="owner",
        owner_identity="owner",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
        enabled=True,
        allowed_categories=["normal_reply"],
        prohibited_categories=["NORMAL_REPLY"],
    )
    expired = await service.upsert_exact(
        permission="owner",
        owner_identity="owner",
        contact_id=41,
        exact_chat_id="2348012345678@c.us",
        enabled=True,
        allowed_categories=["normal_reply"],
        expires_at=utcnow() - timedelta(seconds=1),
    )

    assert overlap.error == "allowed and prohibited categories overlap"
    assert expired.error == "policy expiry must be in the future"
    assert session.calls == []


@pytest.mark.asyncio
async def test_disable_is_immediate_and_exact_target_only():
    session = FakeSession(result_value=31)
    service = OwnerContactAutomationPolicyService(session)

    result = await service.disable_exact(
        permission="owner",
        owner_identity="owner:1",
        contact_id=77,
        exact_chat_id="2348099999999@c.us",
    )

    assert result.ok is True
    assert result.policy_id == 31
    assert session.flush_count == 1
    sql, params = session.calls[0]
    assert "SET enabled = false" in sql
    assert "contact_id = :contact_id AND exact_chat_id = :exact_chat_id" in sql
    assert params["contact_id"] == 77
    assert params["exact_chat_id"] == "2348099999999@c.us"


@pytest.mark.asyncio
async def test_disable_missing_active_policy_fails_closed():
    session = FakeSession(result_value=None)
    service = OwnerContactAutomationPolicyService(session)

    result = await service.disable_exact(
        permission="owner",
        owner_identity="owner:1",
        contact_id=77,
        exact_chat_id="2348099999999@c.us",
    )

    assert result.ok is False
    assert result.error == "active exact-contact policy not found"
    assert session.flush_count == 0
