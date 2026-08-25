from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text

from app.core.message_normalizer import MessageNormalizer
from app.main import app
from app.models.schema import AdminAccount, OutboundMessage
from app.services.command_control_service import CommandControlService


def _event(body: str, *, chat_id: str, message_id: str = "CMD-REVIEW-1", event_name: str = "message.any") -> dict:
    return {
        "event": event_name,
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": True,
            "body": body,
        },
    }


def _owner(number: str, *, primary: bool) -> AdminAccount:
    return AdminAccount(
        name="Fabian" if primary else "Secondary Owner",
        whatsapp_number=number,
        normalized_whatsapp_id=f"{number}@c.us",
        role="primary_admin" if primary else "admin",
        permission_level="owner",
        is_primary=primary,
        is_enabled=True,
    )


@pytest.mark.asyncio
async def test_secondary_owner_peer_chat_is_not_treated_as_fabian_self_dm(db_session):
    await db_session.execute(delete(AdminAccount))
    primary = _owner("2348000000001", primary=True)
    secondary = _owner("2348000000009", primary=False)
    db_session.add_all([primary, secondary])
    await db_session.flush()

    message = MessageNormalizer().normalize(
        _event("@Zina .status", chat_id="2348000000009@c.us", message_id="PEER-OWNER")
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PEER-OWNER",
        request_id="PEER-OWNER",
    )

    assert result is None
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []


@pytest.mark.asyncio
async def test_at_zina_direct_slash_is_canonicalized_before_existing_handler(db_session):
    await db_session.execute(delete(AdminAccount))
    owner = _owner("2348000000001", primary=True)
    db_session.add(owner)
    await db_session.flush()

    message = MessageNormalizer().normalize(
        _event("@Zina /status", chat_id="2348000000001@c.us", message_id="DIRECT-SLASH")
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="DIRECT-SLASH",
        request_id="DIRECT-SLASH",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/status"
    assert "Online and ready" in (result.reply_text or "")


@pytest.mark.asyncio
async def test_duplicate_from_me_webhook_executes_owner_command_once(db_session):
    await db_session.execute(delete(AdminAccount))
    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    owner = _owner("2348000000001", primary=True)
    db_session.add(owner)
    await db_session.commit()

    first_event = _event(
        "@Zina .status",
        chat_id="2348000000001@c.us",
        message_id="DUP-OWNER-CMD",
        event_name="message.any",
    )
    duplicate_variant = _event(
        "@Zina .status",
        chat_id="2348000000001@c.us",
        message_id="DUP-OWNER-CMD",
        event_name="message",
    )

    client = TestClient(app)
    first = client.post("/webhooks/waha", json=first_event)
    second = client.post("/webhooks/waha", json=duplicate_variant)

    assert first.status_code == 202
    assert first.json()["command_consumed"] is True
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"

    db_session.expire_all()
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].formatting_json["source"] == "command_control"
