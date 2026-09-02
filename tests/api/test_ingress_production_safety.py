"""P0 ingress safety matrix for controlled real-world testing.

Every case asserts that a non-conversational or non-new transport event produces zero
routing side effects, and that one canonical source message enters reply planning at
most once. These are release-blocker regressions: a failure here means Zina could
reply to something that is not a real inbound conversation, or reply twice.

No real WhatsApp transport is contacted.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import inbound, waha_events


CONTACT_ID = "2348000000002@c.us"


class _ReusableSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def ingress(db_session, monkeypatch):
    """Webhook client with routing replaced by a recorder, so nothing can send."""
    monkeypatch.setattr(waha_events, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(inbound, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(inbound.settings, "waha_session_name", "test")
    monkeypatch.setattr(inbound.settings, "environment", "development")
    monkeypatch.setattr(inbound.settings, "waha_api_key", "")

    routed: list[dict] = []

    async def _record(event, *args, **kwargs):
        routed.append(event)

    monkeypatch.setattr(inbound, "_process_event_async", _record)

    app = FastAPI()
    app.include_router(waha_events.router)
    return app, routed


async def _post(app, event):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://ingress") as client:
        response = await client.post("/webhooks/waha-events", json=event)
    return response.json()


def _message_event(*, chat_id=CONTACT_ID, message_id="SRC-1", event_name="message", from_me=False, body="hello"):
    return {
        "event": event_name,
        "session": "test",
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": from_me,
            "body": body,
        },
    }


# --------------------------------------------------------------------------------------
# Non-conversational surfaces must never become reply candidates
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "chat_id",
    [
        "status@broadcast",
        "STATUS@BROADCAST",
        "120363000000000000@newsletter",
        "1234567890@broadcast",
    ],
)
async def test_status_channel_and_broadcast_surfaces_are_never_routed(ingress, chat_id):
    app, routed = ingress

    body = await _post(app, _message_event(chat_id=chat_id, message_id=f"STATUS-{chat_id}"))

    assert body["status"] == "ignored"
    assert body["reason"] == "non_conversational_chat"
    assert routed == []


@pytest.mark.asyncio
async def test_ordinary_contact_dm_is_still_routed(ingress):
    """The status guard must not suppress genuine conversations."""
    app, routed = ingress

    body = await _post(app, _message_event(message_id="REAL-1"))

    assert body["status"] == "accepted"
    assert len(routed) == 1


# --------------------------------------------------------------------------------------
# Transport events that are not new externally-authored messages
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event_name",
    [
        "message.ack",
        "message.waiting",
        "presence.update",
        "chat.typing",
        "state.change",
        "message.reaction",
        "poll.vote",
        "call.received",
        "group.join",
        "session.status",
    ],
)
async def test_non_message_transport_events_are_never_routed(ingress, event_name):
    app, routed = ingress

    body = await _post(app, _message_event(event_name=event_name, message_id=f"EV-{event_name}"))

    assert body["status"] == "ignored"
    assert body["reason"] == "unsupported_event"
    assert routed == []


@pytest.mark.asyncio
async def test_revocation_event_is_never_routed_for_reply(ingress):
    app, routed = ingress
    event = {
        "event": "message.revoked",
        "session": "test",
        "payload": {"after": {"id": "REV-1", "chatId": CONTACT_ID}},
    }

    body = await _post(app, event)

    assert body.get("reason") != "unsupported_event"
    assert routed == []


@pytest.mark.asyncio
async def test_event_without_source_message_id_is_never_routed(ingress):
    app, routed = ingress
    event = {"event": "message", "session": "test", "payload": {"chatId": CONTACT_ID, "body": "hi"}}

    body = await _post(app, event)

    assert body["status"] == "ignored"
    assert body["reason"] == "missing_source_message_id"
    assert routed == []


# --------------------------------------------------------------------------------------
# One canonical source -> at most one reply candidate
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_message_and_message_any_for_one_source_route_once(ingress):
    """WAHA delivers the same message twice; only one may enter reply planning."""
    app, routed = ingress

    first = await _post(app, _message_event(message_id="DUP-1", event_name="message"))
    second = await _post(app, _message_event(message_id="DUP-1", event_name="message.any"))

    assert first["status"] == "accepted"
    assert second["status"] == "duplicate"
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_repeated_webhook_delivery_is_durably_idempotent(ingress):
    """Simulates WAHA retry storms and post-restart replay of the same event."""
    app, routed = ingress

    statuses = []
    for _ in range(5):
        statuses.append((await _post(app, _message_event(message_id="RETRY-1")))["status"])

    assert statuses[0] == "accepted"
    assert statuses[1:] == ["duplicate"] * 4
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_distinct_sources_remain_independently_routable(ingress):
    """Deduplication must be per source message, not a global suppression."""
    app, routed = ingress

    await _post(app, _message_event(message_id="IND-1"))
    await _post(app, _message_event(message_id="IND-2"))

    assert len(routed) == 2


@pytest.mark.asyncio
async def test_one_source_never_routes_to_multiple_recipients(ingress):
    """One inbound event must never expand into several chat targets."""
    app, routed = ingress

    await _post(app, _message_event(message_id="FANOUT-1"))

    assert len(routed) == 1
    payload = inbound._resolve_payload(routed[0])
    assert inbound._resolve_chat_id(payload) == CONTACT_ID
