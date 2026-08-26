from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.api import waha_events
from app.models.schema import Contact, Message


AMANDA_ID = "2348000000002@c.us"


class _ReusableSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_authenticated_revoked_event_marks_observed_message_and_deduplicates(db_session, monkeypatch):
    contact = Contact(
        whatsapp_id=AMANDA_ID,
        chat_id=AMANDA_ID,
        display_name="Amanda",
        contact_name="Amanda",
    )
    db_session.add(contact)
    await db_session.flush()
    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="Please bring the file",
        normalized_text="please bring the file",
        message_type="chat",
        raw_payload_json={"id": "REVOKE-E2E-1", "chatId": AMANDA_ID, "body": "Please bring the file"},
    )
    db_session.add(message)
    await db_session.commit()

    monkeypatch.setattr(waha_events, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(waha_events.inbound.settings, "waha_session_name", "test")
    monkeypatch.setattr(waha_events.inbound.settings, "environment", "development")
    monkeypatch.setattr(waha_events.inbound.settings, "waha_api_key", "")

    app = FastAPI()
    app.include_router(waha_events.router)
    event = {
        "id": "revoke-event-e2e-1",
        "event": "message.revoked",
        "session": "test",
        "timestamp": 1787731200000,
        "payload": {
            "revokedMessageId": "REVOKE-E2E-1",
            "before": {
                "id": "REVOKE-E2E-1",
                "chatId": AMANDA_ID,
                "from": AMANDA_ID,
                "fromMe": False,
                "type": "chat",
            },
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/webhooks/waha-events", json=event)
        second = await client.post("/webhooks/waha-events", json=event)

    assert first.status_code == 202
    assert first.json()["status"] == "accepted"
    assert first.json()["matched"] is True
    assert first.json()["changed"] is True
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"

    row = (
        await db_session.execute(
            text("SELECT lifecycle_status, source_message_id, revoked_at FROM messages WHERE id=:id"),
            {"id": message.id},
        )
    ).mappings().one()
    assert row["lifecycle_status"] == "revoked"
    assert row["source_message_id"] == "REVOKE-E2E-1"
    assert row["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoked_event_without_observed_message_reports_unmatched_not_recovered(db_session, monkeypatch):
    monkeypatch.setattr(waha_events, "SessionLocal", lambda: _ReusableSessionContext(db_session))
    monkeypatch.setattr(waha_events.inbound.settings, "waha_session_name", "test")
    monkeypatch.setattr(waha_events.inbound.settings, "environment", "development")
    monkeypatch.setattr(waha_events.inbound.settings, "waha_api_key", "")

    app = FastAPI()
    app.include_router(waha_events.router)
    event = {
        "id": "revoke-event-unseen",
        "event": "message.revoked",
        "session": "test",
        "payload": {"revokedMessageId": "NEVER-OBSERVED"},
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/waha-events", json=event)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["matched"] is False
    assert response.json()["changed"] is False
    assert (await db_session.execute(select(Message))).scalars().all() == []
