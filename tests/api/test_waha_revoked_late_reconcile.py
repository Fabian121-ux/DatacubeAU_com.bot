from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.api import waha_events
from app.models.schema import Contact, Message
from app.services.deleted_message_service import DeletedMessageService


AMANDA_ID = "2348000000002@c.us"


class _ReusableSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_message_gateway_reconciles_earlier_unmatched_revoke_after_background_persistence(
    db_session,
    monkeypatch,
):
    revoke = {
        "id": "early-revoke-event",
        "event": "message.revoked",
        "session": "test",
        "timestamp": 1787731200000,
        "payload": {
            "revokedMessageId": "RACE-GATEWAY-1",
            "before": {"id": "RACE-GATEWAY-1", "chatId": AMANDA_ID, "from": AMANDA_ID, "fromMe": False, "type": "chat"},
        },
    }
    unmatched = await DeletedMessageService(db_session).record_revocation(revoke)
    assert unmatched is not None and unmatched.matched is False
    await db_session.commit()

    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.commit()

    async def persist_original(payload):
        message = Message(
            contact_id=contact.id,
            chat_id=AMANDA_ID,
            chat_type="dm",
            direction="inbound",
            message_text=payload["body"],
            normalized_text=payload["body"].lower(),
            message_type="chat",
            raw_payload_json=payload,
        )
        db_session.add(message)
        await db_session.commit()

    async def fake_inbound_handler(request, background_tasks):
        event = await request.json()
        payload = event["payload"]
        # Mirror the real inbound route: persistence happens in a background task.
        # The revoke gateway must append reconciliation *after* this task rather than
        # checking synchronously before the original Message exists.
        background_tasks.add_task(persist_original, payload)
        return {"status": "accepted", "message_id": payload["id"]}

    monkeypatch.setattr(waha_events.inbound, "waha_webhook", fake_inbound_handler)
    monkeypatch.setattr(waha_events, "SessionLocal", lambda: _ReusableSessionContext(db_session))

    app = FastAPI()
    app.include_router(waha_events.router)
    message_event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": "RACE-GATEWAY-1",
            "chatId": AMANDA_ID,
            "from": AMANDA_ID,
            "fromMe": False,
            "body": "This arrived just after its revoke webhook",
            "type": "chat",
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/waha-events", json=message_event)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    row = (
        await db_session.execute(
            text(
                "SELECT lifecycle_status, revoked_at, revoke_metadata_json "
                "FROM messages WHERE raw_payload_json->>'id'='RACE-GATEWAY-1'"
            )
        )
    ).mappings().one()
    assert row["lifecycle_status"] == "revoked"
    assert row["revoked_at"] is not None
    assert row["revoke_metadata_json"]["late_reconciled"] is True
