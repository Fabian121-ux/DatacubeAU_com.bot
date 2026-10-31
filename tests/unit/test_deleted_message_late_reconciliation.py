from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.models.schema import AuditLog, Contact, Message
from app.services.deleted_message_service import DeletedMessageService


AMANDA_ID = "2348000000002@c.us"


def _revoke(source_id: str, chat_id: str = AMANDA_ID) -> dict:
    return {
        "id": f"revoke-{source_id}",
        "event": "message.revoked",
        "session": "test",
        "timestamp": 1787731200000,
        "payload": {
            "revokedMessageId": source_id,
            "before": {"id": source_id, "chatId": chat_id, "from": chat_id, "fromMe": False, "type": "chat"},
        },
    }


@pytest.mark.asyncio
async def test_unmatched_revoke_reconciles_after_original_message_is_persisted(db_session):
    service = DeletedMessageService(db_session)
    first = await service.record_revocation(_revoke("RACE-1"))
    assert first is not None and first.matched is False
    await db_session.commit()

    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()
    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="Delete race evidence",
        normalized_text="delete race evidence",
        message_type="chat",
        raw_payload_json={"id": "RACE-1", "chatId": AMANDA_ID, "body": "Delete race evidence"},
    )
    db_session.add(message)
    await db_session.flush()

    reconciled = await service.reconcile_pending_for_message(source_message_id="RACE-1", chat_id=AMANDA_ID)

    assert reconciled is True
    row = (
        await db_session.execute(
            text("SELECT lifecycle_status, source_message_id, revoked_at, revoke_metadata_json FROM messages WHERE id=:id"),
            {"id": message.id},
        )
    ).mappings().one()
    assert row["lifecycle_status"] == "revoked"
    assert row["source_message_id"] == "RACE-1"
    assert row["revoked_at"] is not None
    assert row["revoke_metadata_json"]["late_reconciled"] is True
    audit = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "message_revocation_late_reconciled"))
    ).scalars().one()
    assert audit.details_json["content_recovered"] is True


@pytest.mark.asyncio
async def test_pending_revoke_never_crosses_chat_identity(db_session):
    service = DeletedMessageService(db_session)
    await service.record_revocation(_revoke("RACE-2", chat_id=AMANDA_ID))
    await db_session.commit()

    other_chat = "2348000000099@c.us"
    contact = Contact(whatsapp_id=other_chat, chat_id=other_chat, display_name="Other")
    db_session.add(contact)
    await db_session.flush()
    message = Message(
        contact_id=contact.id,
        chat_id=other_chat,
        chat_type="dm",
        direction="inbound",
        message_text="Same ID wrong chat",
        normalized_text="same id wrong chat",
        message_type="chat",
        raw_payload_json={"id": "RACE-2", "chatId": other_chat, "body": "Same ID wrong chat"},
    )
    db_session.add(message)
    await db_session.flush()

    reconciled = await service.reconcile_pending_for_message(source_message_id="RACE-2", chat_id=other_chat)

    assert reconciled is False
    status = (
        await db_session.execute(text("SELECT lifecycle_status FROM messages WHERE id=:id"), {"id": message.id})
    ).scalar_one()
    assert status == "active"
