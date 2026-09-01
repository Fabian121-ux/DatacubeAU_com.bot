"""Cross-session ingress binding regressions.

Webhook authentication only proves the caller knows the shared secret. Session binding
proves the event belongs to the configured Zina WAHA session. Both are required: a
stale or foreign WAHA session must never create conversations, contacts, or replies.

The active WAHA build populates `session` on every webhook (`populateSessionInfo` in
`core/abc/manager.abc.js`) and the `WAHAWebhook` DTO marks it `required: true`, so a
message event without a session is not a legitimate event on this transport and fails
closed.

No real WAHA transport is contacted and no session is reconnected or mutated.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.api import inbound, waha_events
from app.models.schema import Contact, Message, OutboundMessage


CONTACT_ID = "2348000000002@c.us"
OWNER_ID = "2348000000001@c.us"
CONFIGURED_SESSION = "default"


class _ReusableSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.fixture
def ingress(db_session, monkeypatch):
    """Real ingress with the configured session pinned; routing is recorded only."""
    monkeypatch.setattr(waha_events, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(inbound, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(inbound.settings, "waha_session_name", CONFIGURED_SESSION)
    monkeypatch.setattr(inbound.settings, "environment", "development")
    monkeypatch.setattr(inbound.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound.settings, "owner_whatsapp_ids", OWNER_ID)

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


def _event(
    *,
    session=CONFIGURED_SESSION,
    event_name="message",
    message_id="SESSION-1",
    chat_id=CONTACT_ID,
    from_me=False,
    body="hello",
    include_session=True,
):
    event = {
        "event": event_name,
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": from_me,
            "body": body,
        },
    }
    if include_session:
        event["session"] = session
    return event


async def _durable_state(db_session):
    """Conversational side effects that a rejected event must never produce."""
    outbound = (await db_session.execute(select(OutboundMessage))).scalars().all()
    messages = (await db_session.execute(select(Message))).scalars().all()
    contacts = (await db_session.execute(select(Contact))).scalars().all()
    receipts = (
        await db_session.execute(text("SELECT count(*) FROM inbound_webhook_receipts"))
    ).scalar_one()
    return outbound, messages, contacts, receipts


# --------------------------------------------------------------------------------------
# Expected session still works
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expected_session_routes_normally(ingress):
    app, routed = ingress

    body = await _post(app, _event(message_id="OK-1"))

    assert body["status"] == "accepted"
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_expected_session_message_any_routes_normally(ingress):
    app, routed = ingress

    body = await _post(app, _event(message_id="OK-ANY-1", event_name="message.any"))

    assert body["status"] == "accepted"
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_surrounding_whitespace_on_expected_session_is_tolerated(ingress):
    """WAHA sends the exact name; trimming transport padding is not identity widening."""
    app, routed = ingress

    body = await _post(app, _event(session="  default  ", message_id="OK-WS-1"))

    assert body["status"] == "accepted"
    assert len(routed) == 1


# --------------------------------------------------------------------------------------
# Foreign session rejected before any side effect
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "foreign_session",
    [
        "attacker-session",
        "old-session",
        "DEFAULT",
        "Default",
        "defaultx",
        "default-2",
        "",
    ],
)
async def test_foreign_or_ambiguous_session_is_rejected(ingress, foreign_session):
    app, routed = ingress

    body = await _post(app, _event(session=foreign_session, message_id=f"BAD-{foreign_session}"))

    assert body["status"] == "ignored"
    assert body["reason"] == "unexpected_session"
    assert routed == []


@pytest.mark.asyncio
async def test_missing_session_fails_closed(ingress):
    """The active WAHA contract always populates session, so absence is not legitimate."""
    app, routed = ingress

    body = await _post(app, _event(include_session=False, message_id="NO-SESSION-1"))

    assert body["status"] == "ignored"
    assert body["reason"] == "unexpected_session"
    assert routed == []


@pytest.mark.asyncio
async def test_wrong_session_message_creates_no_outbound_or_conversation(ingress, db_session):
    app, routed = ingress

    await _post(app, _event(session="attacker-session", message_id="BAD-MSG-1"))

    outbound, messages, contacts, receipts = await _durable_state(db_session)
    assert routed == []
    assert outbound == []
    assert messages == []
    assert contacts == []
    assert receipts == 0


@pytest.mark.asyncio
async def test_wrong_session_message_any_creates_no_outbound_or_conversation(ingress, db_session):
    app, routed = ingress

    await _post(
        app,
        _event(session="attacker-session", event_name="message.any", message_id="BAD-ANY-1"),
    )

    outbound, messages, contacts, receipts = await _durable_state(db_session)
    assert routed == []
    assert outbound == []
    assert messages == []
    assert contacts == []
    assert receipts == 0


@pytest.mark.asyncio
async def test_wrong_session_from_me_remains_rejected(ingress, db_session):
    """Privileged owner-authored events must still be session bound."""
    app, routed = ingress

    body = await _post(
        app,
        _event(
            session="attacker-session",
            message_id="BAD-OWNER-1",
            chat_id=OWNER_ID,
            from_me=True,
            body="@Zina .push",
        ),
    )

    outbound, _messages, _contacts, receipts = await _durable_state(db_session)
    assert body["reason"] == "unexpected_session"
    assert routed == []
    assert outbound == []
    assert receipts == 0


@pytest.mark.asyncio
async def test_repeated_rejected_events_leave_no_durable_side_effects(ingress, db_session):
    app, routed = ingress

    for index in range(5):
        body = await _post(app, _event(session="attacker-session", message_id=f"BAD-REPEAT-{index}"))
        assert body["reason"] == "unexpected_session"

    outbound, messages, contacts, receipts = await _durable_state(db_session)
    assert routed == []
    assert outbound == []
    assert messages == []
    assert contacts == []
    assert receipts == 0


@pytest.mark.asyncio
async def test_rejected_event_does_not_block_later_valid_delivery_of_same_id(ingress):
    """Rejection must not consume the idempotency key for a legitimate retry."""
    app, routed = ingress

    rejected = await _post(app, _event(session="attacker-session", message_id="SHARED-ID-1"))
    accepted = await _post(app, _event(message_id="SHARED-ID-1"))

    assert rejected["reason"] == "unexpected_session"
    assert accepted["status"] == "accepted"
    assert len(routed) == 1
