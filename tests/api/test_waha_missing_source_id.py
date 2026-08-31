from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import waha_events
from app.main import app as production_app


def test_production_app_exposes_only_canonical_waha_event_gateway():
    paths = {getattr(route, "path", None) for route in production_app.routes}

    assert "/webhooks/waha-events" in paths
    assert "/webhooks/waha" not in paths


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
