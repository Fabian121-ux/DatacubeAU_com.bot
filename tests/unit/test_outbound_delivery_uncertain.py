from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.scheduled_action import ScheduledAction
from app.models.schema import OutboundMessage
from app.services.outbound_authorization_service import AuthorizationDecision, OutboundAuthorizationService
from app.services.outbound_safety_limit_service import OutboundSafetyDecision
from app.services.scheduled_action_service import ScheduledActionService
from app.services.waha_client import WahaClientError
from app.utils.time import utcnow
from app.workers import background_workers


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ExplodingClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")


class _UncertainClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise WahaClientError("connection closed before response")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise WahaClientError("connection closed before response")


class _RecordingClient:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    async def send_text(self, *, chat_id, text):
        self.calls.append((chat_id, text))
        return {"id": "mock-waha-message-id"}

    async def send_media(self, **kwargs):
        raise AssertionError("formatted text regression must use the text send path")


@pytest.mark.asyncio
async def test_stale_sending_row_is_quarantined_without_waha_replay(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="already attempted",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(row)
    await db_session.commit()
    row_id = row.id

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    client = _ExplodingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 0
    assert client.calls == 0
    assert row.id == row_id
    assert row.status == "deferred"
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_waha_send_error_is_delivery_uncertain_not_retrying(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="attempt once",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    # This test isolates the post-authorization uncertain-send state machine. Make the
    # exact target the configured OWNER self-DM so the final authorization fence is
    # explicitly satisfied without weakening the external-contact fail-closed path.
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "222@c.us")
    client = _UncertainClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == 1
    assert row.status == "deferred"
    assert row.retry_count == 0
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_authorized_external_worker_preserves_whatsapp_formatting_exactly(db_session, monkeypatch):
    now = utcnow()
    text = "> quoted line\n\n*Important* uses `inline code`.\n\nFinal paragraph."
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": 41,
            "contact_id": 42,
            "content_sha256": OutboundAuthorizationService.content_hash(text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        return context, AuthorizationDecision(True, "contact_policy", "exact active contact policy")

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == [("222@c.us", text)]
    assert row.message_text == text
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_delivery_uncertain_state_survives_restart_style_reload(db_session):
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="uncertain",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(row)
    await db_session.flush()
    row_id = row.id

    await background_workers._mark_delivery_uncertain(
        db_session,
        row,
        reason="delivery outcome uncertain; automatic replay blocked",
    )
    db_session.expire_all()

    persisted = await db_session.get(OutboundMessage, row_id)
    assert persisted is not None
    assert persisted.status == "deferred"
    assert "automatic replay blocked" in (persisted.error_message or "")


@pytest.mark.asyncio
async def test_uncertain_scheduled_action_cannot_be_rereleased_or_replayed_after_restart(db_session, monkeypatch):
    now = utcnow()
    outbound = OutboundMessage(
        chat_id="333@c.us",
        message_text="owner scheduled exact text",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(outbound)
    await db_session.flush()

    action = ScheduledAction(
        action_type="whatsapp.send_message",
        target_contact_id=None,
        target_chat_id="333@c.us",
        payload_json={"text": "owner scheduled exact text"},
        timezone="UTC",
        scheduled_for=now - timedelta(minutes=20),
        status="queued",
        is_enabled=True,
        retry_count=0,
        max_retries=3,
        outbound_queue_id=outbound.id,
        idempotency_key="test-uncertain-scheduled-action-no-replay",
        metadata_json={},
        executed_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(action)
    await db_session.flush()
    outbound.formatting_json = {"scheduled_action_id": action.id}
    await db_session.commit()

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    client = _ExplodingClient()

    first_processed = await background_workers._deliver_due_outbound_messages(client)
    await db_session.refresh(outbound)
    await db_session.refresh(action)

    assert first_processed == 0
    assert client.calls == 0
    assert outbound.status == "deferred"
    assert action.status == "queued"
    assert action.outbound_queue_id == outbound.id
    assert (action.metadata_json or {}).get("delivery", {}).get("status") == "deferred"

    outbound_id = outbound.id
    action_id = action.id
    db_session.expire_all()
    release_count = await ScheduledActionService(db_session).release_due(limit=25)
    await db_session.commit()
    second_processed = await background_workers._deliver_due_outbound_messages(client)

    persisted_outbound = await db_session.get(OutboundMessage, outbound_id)
    persisted_action = await db_session.get(ScheduledAction, action_id)
    assert release_count == 0
    assert second_processed == 0
    assert client.calls == 0
    assert persisted_outbound is not None and persisted_outbound.status == "deferred"
    assert persisted_action is not None and persisted_action.status == "queued"
    assert persisted_action.outbound_queue_id == persisted_outbound.id
