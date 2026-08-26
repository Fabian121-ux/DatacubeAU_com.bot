from __future__ import annotations

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import text

from app.api.inbound import waha_webhook


PEER_ID = "2348000000002@c.us"


class _Request:
    def __init__(self, event: dict):
        self._event = event
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._event


class _SharedSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_webhook_source_is_passed_to_outbound_origin_guard(monkeypatch, db_session):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")
    monkeypatch.setattr(
        inbound_module,
        "SessionLocal",
        lambda: _SharedSessionContext(db_session),
    )

    observed: dict[str, str | None] = {}

    async def fake_is_zina_originated(
        self,
        *,
        chat_id: str,
        transport_message_id: str | None,
        transport_source: str | None = None,
    ) -> bool:
        observed["chat_id"] = chat_id
        observed["message_id"] = transport_message_id
        observed["source"] = transport_source
        return transport_source == "api"

    monkeypatch.setattr(
        inbound_module.OutboundOriginService,
        "is_zina_originated",
        fake_is_zina_originated,
    )

    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    await db_session.commit()

    event = {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": "EARLY-API-ECHO-1",
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "source": "api",
            "body": "Zina generated reply",
        },
    }

    result = await waha_webhook(_Request(event), BackgroundTasks())

    assert result["status"] == "ignored"
    assert result["reason"] == "zina_outbound_echo"
    assert observed == {
        "chat_id": PEER_ID,
        "message_id": "EARLY-API-ECHO-1",
        "source": "api",
    }
