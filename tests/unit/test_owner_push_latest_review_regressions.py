from __future__ import annotations

from datetime import timedelta

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import delete, select, text

from app.api.inbound import waha_webhook
from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, OutboundMessage
from app.services.outbound_origin_service import OutboundOriginService
from app.services.push_command_service import PushCommandService, PushSource
from app.utils.time import utcnow


PEER_ID = "2348000000002@c.us"


class _Request:
    def __init__(self, event: dict):
        self._event = event
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._event


class _SharedSessionContext:
    """Keep inbound webhook contexts on the per-test db_session connection."""

    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _bind_inbound_session(monkeypatch, inbound_module, db_session) -> None:
    monkeypatch.setattr(
        inbound_module,
        "SessionLocal",
        lambda: _SharedSessionContext(db_session),
    )


def _from_me_event(*, message_id: str, body: str = "Zina generated reply") -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "body": body,
        },
    }


@pytest.mark.asyncio
async def test_outbound_origin_matches_completed_and_inflight_evidence(db_session):
    db_session.add(
        AuditLog(
            action="outbound_queue_sent",
            entity_type="outbound_queue",
            entity_id="91",
            details_json={
                "chat_id": PEER_ID,
                "waha_response": {"message": {"id": {"_serialized": "ZINA-TRANSPORT-91"}}},
            },
        )
    )
    await db_session.flush()

    service = OutboundOriginService(db_session)
    assert await service.is_zina_originated(
        chat_id=PEER_ID,
        transport_message_id="ZINA-TRANSPORT-91",
    ) is True
    assert await service.is_zina_originated(
        chat_id=PEER_ID,
        transport_message_id="FABIAN-MANUAL-1",
    ) is False

    row = OutboundMessage(
        chat_id=PEER_ID,
        message_text="Zina generated reply",
        status="sending",
        next_attempt_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(row)
    await db_session.flush()

    assert await service.is_zina_originated(
        chat_id=PEER_ID,
        transport_message_id="ECHO-BEFORE-SEND-RETURN",
    ) is True

    row.updated_at = utcnow() - timedelta(minutes=6)
    await db_session.flush()
    assert await service.is_zina_originated(
        chat_id=PEER_ID,
        transport_message_id="STALE-MANUAL-OWNER-EVENT",
    ) is False


@pytest.mark.asyncio
async def test_zina_outbound_echo_does_not_resume_takeover(monkeypatch, db_session):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")
    _bind_inbound_session(monkeypatch, inbound_module, db_session)

    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    db_session.add(
        ConversationTakeover(
            chat_id=PEER_ID,
            state="zina_assisting",
            auto_assist_enabled=True,
            inactivity_seconds=120,
        )
    )
    db_session.add(
        AuditLog(
            action="outbound_queue_sent",
            entity_type="outbound_queue",
            entity_id="92",
            details_json={
                "chat_id": PEER_ID,
                "waha_response": {"id": "ZINA-TRANSPORT-92"},
            },
        )
    )
    await db_session.commit()

    result = await waha_webhook(
        _Request(_from_me_event(message_id="ZINA-TRANSPORT-92")),
        BackgroundTasks(),
    )

    assert result["status"] == "ignored"
    assert result["reason"] == "zina_outbound_echo"

    takeover = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == PEER_ID)
        )
    ).scalar_one()
    assert takeover.state == "zina_assisting"
    assert takeover.last_owner_message_at is None
    queue_rows = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert queue_rows == []
    receipt_status = (
        await db_session.execute(
            text(
                "SELECT status FROM inbound_webhook_receipts "
                "WHERE event_key = :key"
            ),
            {"key": "default:2348000000002@c.us:ZINA-TRANSPORT-92"},
        )
    ).scalar_one()
    assert receipt_status == "completed"

    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    await db_session.execute(
        delete(AuditLog).where(
            AuditLog.entity_type == "outbound_queue",
            AuditLog.entity_id == "92",
        )
    )
    await db_session.commit()


@pytest.mark.asyncio
async def test_inflight_outbound_echo_does_not_resume_takeover(monkeypatch, db_session):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")
    _bind_inbound_session(monkeypatch, inbound_module, db_session)

    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    db_session.add(
        ConversationTakeover(
            chat_id=PEER_ID,
            state="zina_assisting",
            auto_assist_enabled=True,
            inactivity_seconds=120,
        )
    )
    db_session.add(
        OutboundMessage(
            chat_id=PEER_ID,
            message_text="Zina generated reply",
            status="sending",
            next_attempt_at=utcnow(),
            updated_at=utcnow(),
        )
    )
    await db_session.commit()

    result = await waha_webhook(
        _Request(_from_me_event(message_id="ECHO-BEFORE-SEND-RETURN")),
        BackgroundTasks(),
    )
    assert result["status"] == "ignored"
    assert result["reason"] == "zina_outbound_echo"

    takeover = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == PEER_ID)
        )
    ).scalar_one()
    assert takeover.state == "zina_assisting"
    assert takeover.last_owner_message_at is None

    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    await db_session.commit()


def test_push_treats_waha_chat_type_as_text_without_media_warning():
    projection = PushCommandService._render_projection(
        PushSource(
            source_message_id="TEXT-CHAT-1",
            chat_id=PEER_ID,
            db_message_id=1,
            contact_id=None,
            direction="inbound",
            message_text="Normal WhatsApp text",
            message_type="chat",
            created_at=None,
            evidence_source="postgres_message",
        ),
        None,
    )

    assert "Type: chat" in projection
    assert "Normal WhatsApp text" in projection
    assert "original media is not forwarded" not in projection
