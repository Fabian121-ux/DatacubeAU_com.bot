from __future__ import annotations

import pytest

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
