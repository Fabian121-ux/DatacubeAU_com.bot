from __future__ import annotations

import pytest
from sqlalchemy import text

from app.api.inbound import _build_idempotency_key
from app.services.inbound_idempotency_service import InboundIdempotencyService, InboundReceipt


def test_idempotency_key_is_shared_by_message_event_variants():
    payload = {
        "id": "ABCD1234",
        "chatId": "15550000001@c.us",
    }
    message_event = {"event": "message", "session": "default", "payload": payload}
    message_any_event = {"event": "message.any", "session": "default", "payload": payload}

    assert _build_idempotency_key(message_event, payload) == _build_idempotency_key(message_any_event, payload)


def test_idempotency_key_scopes_same_message_id_by_chat():
    event = {"event": "message", "session": "default"}
    first = {"id": "SAME-ID", "chatId": "15550000001@c.us"}
    second = {"id": "SAME-ID", "chatId": "15550000002@c.us"}

    assert _build_idempotency_key(event, first) != _build_idempotency_key(event, second)


def test_idempotency_key_requires_transport_message_id():
    payload = {"chatId": "15550000001@c.us", "text": "hello"}
    assert _build_idempotency_key({"event": "message", "payload": payload}, payload) is None


def test_opt_out_fallback_key_is_stable_across_message_event_variants():
    from app.api.inbound import _build_opt_out_intent_key

    payload = {
        "chatId": "15550000001@c.us",
        "body": "STOP",
        "timestamp": 1782470000,
    }
    first = {"event": "message", "session": "test", "payload": payload}
    duplicate_variant = {"event": "message.any", "session": "test", "payload": payload}
    changed_message = {"chatId": payload["chatId"], "body": "UNSUBSCRIBE", "timestamp": 1782470000}

    assert _build_opt_out_intent_key(first, payload) == _build_opt_out_intent_key(
        duplicate_variant, payload
    )
    assert _build_opt_out_intent_key(first, payload) != _build_opt_out_intent_key(
        {"event": "message", "session": "test", "payload": changed_message},
        changed_message,
    )


@pytest.mark.asyncio
async def test_idempotency_claim_blocks_duplicate_until_failed_claim_is_released(db_session):
    service = InboundIdempotencyService(db_session)
    receipt = InboundReceipt(
        event_key="test-session:15550000001@c.us:IDEMPOTENCY-TEST-1",
        session_name="test-session",
        chat_id="15550000001@c.us",
        message_id="IDEMPOTENCY-TEST-1",
    )

    await service.release_failed(receipt.event_key)
    assert await service.claim(receipt) is True
    assert await service.claim(receipt) is False

    await service.release_failed(receipt.event_key)
    assert await service.claim(receipt) is True
    await service.mark_completed(receipt.event_key)
    assert await service.claim(receipt) is False

@pytest.mark.asyncio
async def test_failed_opt_out_claim_preserves_pending_intent_for_retry(db_session):
    receipt = InboundReceipt(
        event_key="test:222@c.us:STOP-RETRY",
        session_name="test",
        chat_id="222@c.us",
        message_id="STOP-RETRY",
        opt_out_intent=True,
    )
    service = InboundIdempotencyService(db_session)

    assert await service.claim(receipt) is True
    await service.release_failed(receipt.event_key)

    pending = (
        await db_session.execute(
            text(
                "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                "WHERE event_key = :event_key"
            ),
            {"event_key": receipt.event_key},
        )
    ).one()
    assert pending.opt_out_intent is True
    assert pending.status == "processing"

    # The stale lease is immediately reclaimable, but the veto remains monotonic.
    assert await service.claim(receipt) is True
    await service.mark_completed(receipt.event_key)


@pytest.mark.asyncio
async def test_opt_out_claim_locks_dispatch_boundary_before_receipt_insert_and_commit(monkeypatch):
    from app.services.contact_messaging_consent_service import ContactMessagingConsentService

    events = []

    class FakeResult:
        @staticmethod
        def scalar_one_or_none():
            return "claim-token"

    class FakeSession:
        async def execute(self, statement, params):
            events.append(("insert", params["chat_id"], params["opt_out_intent"]))
            return FakeResult()

        async def commit(self):
            events.append(("commit",))

    async def record_boundary_lock(session, exact_chat_id):
        assert session is fake_session
        events.append(("boundary", exact_chat_id))

    fake_session = FakeSession()
    monkeypatch.setattr(
        ContactMessagingConsentService,
        "lock_opt_out_dispatch_boundary",
        record_boundary_lock,
    )
    receipt = InboundReceipt(
        event_key="test:333@c.us:STOP-BOUNDARY-ORDER",
        session_name="test",
        chat_id="333@c.us",
        message_id="STOP-BOUNDARY-ORDER",
        opt_out_intent=True,
    )

    assert await InboundIdempotencyService(fake_session).claim(receipt) is True
    assert events == [
        ("boundary", "333@c.us"),
        ("insert", "333@c.us", True),
        ("commit",),
    ]
