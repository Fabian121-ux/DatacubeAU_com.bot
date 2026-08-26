from __future__ import annotations

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import delete, select, text

from app.api.inbound import waha_webhook
from app.db import SessionLocal
from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, OutboundMessage
from app.services.outbound_origin_service import OutboundOriginService
from app.services.push_command_service import PushCommandService, PushSource


PEER_ID = "2348000000002@c.us"


class _Request:
    def __init__(self, event: dict):
        self._event = event
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._event


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
async def test_outbound_origin_matches_nested_waha_transport_id(db_session):
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


@pytest.mark.asyncio
async def test_zina_outbound_echo_does_not_resume_takeover(monkeypatch):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")

    async with SessionLocal() as db:
        await db.execute(delete(OutboundMessage))
        await db.execute(delete(ConversationTakeover))
        await db.execute(text("DELETE FROM inbound_webhook_receipts"))
        db.add(
            ConversationTakeover(
                chat_id=PEER_ID,
                state="zina_assisting",
                auto_assist_enabled=True,
                inactivity_seconds=120,
            )
        )
        db.add(
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
        await db.commit()

    try:
        result = await waha_webhook(
            _Request(_from_me_event(message_id="ZINA-TRANSPORT-92")),
            BackgroundTasks(),
        )

        assert result["status"] == "ignored"
        assert result["reason"] == "zina_outbound_echo"

        async with SessionLocal() as db:
            takeover = (
                await db.execute(
                    select(ConversationTakeover).where(ConversationTakeover.chat_id == PEER_ID)
                )
            ).scalar_one()
            assert takeover.state == "zina_assisting"
            assert takeover.last_owner_message_at is None
            queue_rows = (await db.execute(select(OutboundMessage))).scalars().all()
            assert queue_rows == []
            receipt_status = (
                await db.execute(
                    text(
                        "SELECT status FROM inbound_webhook_receipts "
                        "WHERE event_key = :key"
                    ),
                    {"key": "default:2348000000002@c.us:ZINA-TRANSPORT-92"},
                )
            ).scalar_one()
            assert receipt_status == "completed"
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(OutboundMessage))
            await db.execute(delete(ConversationTakeover))
            await db.execute(text("DELETE FROM inbound_webhook_receipts"))
            await db.execute(
                delete(AuditLog).where(
                    AuditLog.entity_type == "outbound_queue",
                    AuditLog.entity_id == "92",
                )
            )
            await db.commit()


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
