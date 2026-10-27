"""P0 ingress safety matrix for controlled real-world testing.

Every case asserts that a non-conversational or non-new transport event produces zero
routing side effects, and that one canonical source message enters reply planning at
most once. These are release-blocker regressions: a failure here means Zina could
reply to something that is not a real inbound conversation, or reply twice.

No real WhatsApp transport is contacted.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message_id", "body_text"),
    [
        ("STOP-CLAIM-1", "STOP"),
        ("STOP-CLAIM-2", "STOP 🙏"),
        ("STOP-CLAIM-3", "Unsubscribe me 📵"),
        ("STOP-CLAIM-4", "STOP MESSAGING 🙏"),
        ("STOP-CLAIM-5", "unsubscribe please 📵"),
        ("STOP-CLAIM-6", "stop texting"),
        ("STOP-CLAIM-7", "stop contacting"),
        ("STOP-CLAIM-8", "stop sending"),
        ("STOP-CLAIM-9", "please unsubscribe"),
        ("STOP-CLAIM-10", "remove me from your list"),
        ("STOP-CLAIM-11", "take me off your list"),
    ],
)
async def test_explicit_contact_opt_out_is_claimed_before_routing(
    ingress, db_session, message_id, body_text
):
    """The final worker fence must see explicit opt-outs with harmless emoji too."""
    app, routed = ingress
    body = await _post(app, _message_event(message_id=message_id, body=body_text))

    assert body["status"] == "accepted"
    receipt = (
        await db_session.execute(
            text(
                "SELECT opt_out_intent, status, sender_identity_ids FROM inbound_webhook_receipts "
                "WHERE event_key = :event_key"
            ),
            {"event_key": f"test:{CONTACT_ID}:{message_id}"},
        )
    ).one()
    assert receipt.opt_out_intent is True
    assert receipt.status == "processing"
    assert receipt.sender_identity_ids == [CONTACT_ID]
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_explicit_opt_out_without_transport_message_id_still_claims_pending_intent(
    ingress, db_session
):
    """Missing WAHA IDs must not remove the pre-routing STOP veto."""
    _gateway_app, routed = ingress
    # The configured combined gateway rejects missing source IDs. Exercise the
    # lower-level webhook route separately to keep its defensive opt-out fence
    # safe if a legacy/direct caller reaches it.
    app = FastAPI()
    app.include_router(inbound.router)
    event = _message_event(message_id=None, body="STOP")
    event_key = inbound._build_opt_out_intent_key(event, event["payload"])

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://ingress",
    ) as client:
        response = await client.post("/webhooks/waha", json=event)
    body = response.json()

    assert body["status"] == "accepted"
    receipt = (
        await db_session.execute(
            text(
                "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                "WHERE event_key = :event_key"
            ),
            {"event_key": event_key},
        )
    ).one()
    assert receipt.opt_out_intent is True
    assert receipt.status == "processing"
    assert await inbound.ContactMessagingConsentService(db_session).has_pending_opt_out_intent(
        CONTACT_ID
    )
    assert len(routed) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("message_id", "body_text"),
    [
        ("CONTEXT-OPT-OUT-1", "stop messaging about the deployment"),
        ("CONTEXT-OPT-OUT-2", "unsubscribe please send the report"),
        ("CONTEXT-OPT-OUT-3", "don't stop"),
    ],
)
async def test_contextual_mentions_do_not_claim_opt_out(
    ingress, db_session, message_id, body_text
):
    """Contextual mentions must not become durable opt-out vetoes."""
    app, routed = ingress
    body = await _post(app, _message_event(message_id=message_id, body=body_text))

    assert body["status"] == "accepted"
    receipt = (
        await db_session.execute(
            text(
                "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                "WHERE event_key = :event_key"
            ),
            {"event_key": f"test:{CONTACT_ID}:{message_id}"},
        )
    ).one()
    assert receipt.opt_out_intent is False
    assert receipt.status == "processing"
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
async def test_message_without_exact_chat_id_is_never_claimed_or_routed(ingress, db_session):
    """Sender-ID fallback must not replace the exact transport reply target."""
    app, routed = ingress
    event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": "MISSING-CHAT-STOP",
            "sender": {"id": CONTACT_ID},
            "fromMe": False,
            "body": "STOP",
        },
    }

    body = await _post(app, event)

    assert body["status"] == "ignored"
    assert body["reason"] == "missing_exact_chat_id"
    assert routed == []
    receipt_count = (
        await db_session.execute(
            text(
                "SELECT count(*) FROM inbound_webhook_receipts "
                "WHERE event_key LIKE '%MISSING-CHAT-STOP'"
            )
        )
    ).scalar_one()
    assert receipt_count == 0


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


@pytest.mark.asyncio
async def test_opt_out_ingress_preserves_sender_identity_for_unmapped_chat_alias(
    ingress, db_session
):
    """An unmapped LID chat must retain its canonical sender ID for the worker veto."""
    from app.models.schema import Contact
    from app.services.contact_messaging_consent_service import ContactMessagingConsentService

    contact = Contact(
        whatsapp_id=CONTACT_ID,
        chat_id=CONTACT_ID,
        display_name="Unmapped alias sender identity regression",
    )
    db_session.add(contact)
    await db_session.flush()

    unmapped_chat_id = "987654321@lid"
    message_id = "UNMAPPED-ALIAS-INGRESS-STOP"
    event = _message_event(
        chat_id=unmapped_chat_id,
        message_id=message_id,
        body="STOP",
    )
    # WAHA's transport chat alias can differ from the sender's canonical identity.
    event["payload"]["sender"] = {"id": CONTACT_ID}

    app, routed = ingress
    body = await _post(app, event)

    assert body["status"] == "accepted"
    receipt = (
        await db_session.execute(
            text(
                "SELECT chat_id, sender_identity_ids, sender_contact_ids, opt_out_intent, status "
                "FROM inbound_webhook_receipts WHERE event_key = :event_key"
            ),
            {"event_key": f"test:{unmapped_chat_id}:{message_id}"},
        )
    ).one()
    assert receipt.chat_id == unmapped_chat_id
    assert set(receipt.sender_identity_ids) == {CONTACT_ID, unmapped_chat_id}
    assert set(receipt.sender_contact_ids) == {str(contact.id)}
    assert receipt.opt_out_intent is True
    assert receipt.status == "processing"
    consent = ContactMessagingConsentService(db_session)
    assert await consent.has_pending_opt_out_intent_for_contact(int(contact.id)) is True

    # The receipt must remain correlated after mutable transport aliases change. The
    # worker must not need to rediscover this STOP through Contact.whatsapp_id/chat_id.
    contact.whatsapp_id = "2348000000003@c.us"
    contact.chat_id = "2348000000003@c.us"
    await db_session.flush()
    assert await consent.has_pending_opt_out_intent_for_contact(int(contact.id)) is True
    assert len(routed) == 1


@pytest.mark.asyncio
async def test_duplicate_pending_stop_enriches_stable_contact_correlation(ingress, db_session):
    """A duplicate STOP may enrich its veto receipt without claiming routing twice."""
    from app.models.schema import Contact
    from app.services.contact_messaging_consent_service import ContactMessagingConsentService

    app, routed = ingress
    unmapped_chat_id = "987654322@lid"
    message_id = "UNMAPPED-ALIAS-STOP-RETRY"
    event = _message_event(chat_id=unmapped_chat_id, message_id=message_id, body="STOP")
    event["payload"]["sender"] = {"id": CONTACT_ID}

    first = await _post(app, event)
    assert first["status"] == "accepted"
    event_key = f"test:{unmapped_chat_id}:{message_id}"
    initial = (
        await db_session.execute(
            text("SELECT sender_contact_ids, status FROM inbound_webhook_receipts WHERE event_key = :event_key"),
            {"event_key": event_key},
        )
    ).one()
    assert initial.sender_contact_ids == []
    assert initial.status == "processing"

    contact = Contact(
        whatsapp_id=CONTACT_ID,
        chat_id=CONTACT_ID,
        display_name="Late-mapped STOP sender identity regression",
    )
    db_session.add(contact)
    await db_session.flush()

    duplicate = await _post(app, event)
    assert duplicate["status"] == "duplicate"
    assert len(routed) == 1
    enriched = (
        await db_session.execute(
            text("SELECT sender_contact_ids, status FROM inbound_webhook_receipts WHERE event_key = :event_key"),
            {"event_key": event_key},
        )
    ).one()
    assert set(enriched.sender_contact_ids) == {str(contact.id)}
    assert enriched.status == "processing"

    consent = ContactMessagingConsentService(db_session)
    assert await consent.has_pending_opt_out_intent_for_contact(int(contact.id)) is True
    contact.whatsapp_id = "2348000000004@c.us"
    contact.chat_id = "2348000000004@c.us"
    await db_session.flush()
    assert await consent.has_pending_opt_out_intent_for_contact(int(contact.id)) is True
