import pytest

from app.models.schema import OutboundMessage
from app.services.outbound_authorization_service import AuthorizationDecision
from app.workers import background_workers


def _message(*, chat_id: str, formatting_json: dict | None) -> OutboundMessage:
    return OutboundMessage(
        chat_id=chat_id,
        message_text="hello",
        formatting_json=formatting_json,
        status="pending",
        retry_count=0,
        max_retries=3,
    )


class _Authority:
    def __init__(self, decision: AuthorizationDecision | None = None):
        self.decision = decision or AuthorizationDecision(False, "none", "no authority")
        self.calls = 0

    async def authorize_queue_message(self, message):
        self.calls += 1
        return object(), self.decision


@pytest.mark.asyncio
async def test_immediate_router_reply_to_external_contact_fails_closed(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "immediate"},
    )
    authority = _Authority()

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is False
    assert "legacy external immediate" in reason
    assert approval_id is None
    assert authority.calls == 0


@pytest.mark.asyncio
async def test_immediate_router_reply_to_exact_owner_chat_remains_authorized(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us,333@c.us")
    message = _message(
        chat_id="333@c.us",
        formatting_json={"delivery_policy": "immediate"},
    )
    authority = _Authority()

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is True
    assert reason == "exact configured owner chat"
    assert approval_id is None
    assert authority.calls == 0


@pytest.mark.asyncio
async def test_owner_push_and_other_non_router_queue_paths_are_not_reclassified(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="111@c.us",
        formatting_json={"source": "owner_push", "command": ".push"},
    )
    authority = _Authority()

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is True
    assert reason == "existing owner-controlled queue path"
    assert approval_id is None
    assert authority.calls == 0


@pytest.mark.asyncio
async def test_unknown_router_policy_fails_closed(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "wait_for_fabian_first"},
    )
    authority = _Authority()

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is False
    assert "unknown router delivery policy" in reason
    assert approval_id is None
    assert authority.calls == 0


@pytest.mark.asyncio
async def test_approval_required_router_reply_delegates_to_exact_durable_authority(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "approval_required"},
    )
    authority = _Authority(
        AuthorizationDecision(
            True,
            "owner_approval",
            "exact active owner approval",
            approval_id=77,
        )
    )

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is True
    assert reason == "exact active owner approval"
    assert approval_id == 77
    assert authority.calls == 1


@pytest.mark.asyncio
async def test_approval_required_router_reply_without_authority_fails_closed(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    message = _message(
        chat_id="222@c.us",
        formatting_json={"delivery_policy": "approval_required"},
    )
    authority = _Authority(AuthorizationDecision(False, "none", "content hash mismatch"))

    allowed, reason, approval_id = await background_workers._delivery_authorized(None, authority, message)

    assert allowed is False
    assert reason == "content hash mismatch"
    assert approval_id is None
    assert authority.calls == 1
