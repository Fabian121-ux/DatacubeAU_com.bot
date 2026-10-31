from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import waha_events


def test_production_app_registers_only_canonical_waha_event_gateway():
    """Keep the deployment route contract explicit without importing app.main.

    Importing the production application from an API test can bind the process-wide
    async SQLAlchemy engine to that test's event loop and contaminate later tests.
    The production composition root is declarative, so inspect that exact source file
    instead: WAHA must enter through one canonical gateway and the legacy direct
    inbound router must not be mounted alongside it.
    """
    main_source = (
        Path(__file__).resolve().parents[2] / "bot_core" / "app" / "main.py"
    ).read_text(encoding="utf-8")

    assert "app.include_router(waha_events.router)" in main_source
    assert "app.include_router(inbound.router)" not in main_source


@pytest.mark.asyncio
@pytest.mark.parametrize("event_name", ["message", "message.any"])
async def test_message_without_durable_source_id_fails_closed_before_inbound_routing(monkeypatch, event_name):
    delegated = False

    async def exploding_inbound(*args, **kwargs):
        nonlocal delegated
        delegated = True
        raise AssertionError("message without durable source ID must not enter inbound routing")

    monkeypatch.setattr(waha_events.inbound, "waha_webhook", exploding_inbound)

    app = FastAPI()
    app.include_router(waha_events.router)
    event = {
        "event": event_name,
        "session": "test",
        "payload": {
            "chatId": "2348000000002@c.us",
            "from": "2348000000002@c.us",
            "fromMe": False,
            "type": "chat",
            "body": "hello",
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/waha-events", json=event)

    assert response.status_code == 202
    assert response.json() == {
        "status": "ignored",
        "reason": "missing_source_message_id",
        "event_name": event_name,
    }
    assert delegated is False


@pytest.mark.asyncio
async def test_message_with_durable_source_id_still_delegates_to_established_inbound_router(monkeypatch):
    delegated = False

    async def accepted_inbound(*args, **kwargs):
        nonlocal delegated
        delegated = True
        return {
            "status": "accepted",
            "event_name": "message",
            "message_id": "MSG-EXACT-1",
        }

    monkeypatch.setattr(waha_events.inbound, "waha_webhook", accepted_inbound)

    app = FastAPI()
    app.include_router(waha_events.router)
    event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": "MSG-EXACT-1",
            "chatId": "2348000000002@c.us",
            "from": "2348000000002@c.us",
            "fromMe": False,
            "type": "chat",
            "body": "hello",
        },
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/waha-events", json=event)

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert delegated is True


def test_historical_quote_snapshots_never_replace_current_source_identity():
    """A quoted historical snapshot is context, never a new inbound source event.

    WAHA engines can expose reply/quoted snapshots in engine-specific nested fields.
    P0 source identity must remain bound to the current top-level message ID so a
    historical quoted object cannot become the idempotency key or independently
    re-enter response consideration.
    """
    chat_id = "2348000000002@c.us"
    event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": "MSG-CURRENT-2",
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": False,
            "type": "chat",
            "body": "replying to the old message",
            "replyTo": {
                "id": "MSG-HISTORICAL-1",
                "body": "old quoted text",
            },
            "_data": {
                "quotedMsg": {
                    "id": {"_serialized": "MSG-HISTORICAL-1"},
                    "body": "old quoted text",
                }
            },
        },
    }
    payload = waha_events.inbound._resolve_payload(event)

    assert waha_events.inbound._resolve_message_id(payload) == "MSG-CURRENT-2"
    assert waha_events.inbound._build_idempotency_key(event, payload) == (
        f"test:{chat_id}:MSG-CURRENT-2"
    )
    assert "MSG-HISTORICAL-1" not in waha_events.inbound._build_idempotency_key(event, payload)
