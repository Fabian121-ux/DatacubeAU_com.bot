from __future__ import annotations

import pytest
from sqlalchemy import func, select, text

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, AuditLog, Contact, Message, OutboundMessage
from app.services.command_control_service import CommandControlService
from app.services.deleted_message_service import DeletedMessageService
from app.services.owner_management_command_service import OwnerManagementCommandService


OWNER_ID = "2348000000001@c.us"
AMANDA_ID = "2348000000002@c.us"


async def _owner(db_session) -> AdminAccount:
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id=OWNER_ID,
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()
    return owner


async def _message(db_session, *, source_id: str = "DEL-1", chat_type: str = "dm") -> Message:
    contact = (
        await db_session.execute(select(Contact).where(Contact.whatsapp_id == AMANDA_ID).limit(1))
    ).scalar_one_or_none()
    if contact is None:
        contact = Contact(
            whatsapp_id=AMANDA_ID,
            chat_id=AMANDA_ID,
            display_name="Amanda Christabel",
            contact_name="Amanda Christabel",
        )
        db_session.add(contact)
        await db_session.flush()
    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID if chat_type == "dm" else "120363000000000000@g.us",
        chat_type=chat_type,
        direction="inbound",
        message_text="The meeting is now 4pm",
        normalized_text="the meeting is now 4pm",
        message_type="chat",
        raw_payload_json={"id": source_id, "chatId": AMANDA_ID, "body": "The meeting is now 4pm"},
    )
    db_session.add(message)
    await db_session.flush()
    return message


def _revoke(source_id: str = "DEL-1", *, event_id: str = "evt-delete-1") -> dict:
    return {
        "id": event_id,
        "timestamp": 1787731200000,
        "event": "message.revoked",
        "session": "default",
        "payload": {
            "revokedMessageId": source_id,
            "before": {"id": source_id, "chatId": AMANDA_ID, "from": AMANDA_ID, "type": "chat", "fromMe": False},
        },
    }


@pytest.mark.asyncio
async def test_observed_message_is_marked_revoked_and_dm_returns_evidence(db_session):
    original = await _message(db_session)

    result = await DeletedMessageService(db_session).record_revocation(_revoke())

    assert result is not None and result.matched is True and result.changed is True
    row = (
        await db_session.execute(
            text("SELECT source_message_id, lifecycle_status, revoked_at, revoked_event_id FROM messages WHERE id=:id"),
            {"id": original.id},
        )
    ).mappings().one()
    assert row["source_message_id"] == "DEL-1"
    assert row["lifecycle_status"] == "revoked"
    assert row["revoked_at"] is not None
    assert row["revoked_event_id"] == "evt-delete-1"

    rendered = await DeletedMessageService(db_session).render_command("")
    assert "DELETED MESSAGE" in rendered
    assert "Amanda Christabel" in rendered
    assert "The meeting is now 4pm" in rendered


@pytest.mark.asyncio
async def test_duplicate_revoke_is_idempotent_and_audited_once(db_session):
    await _message(db_session)
    service = DeletedMessageService(db_session)

    first = await service.record_revocation(_revoke())
    second = await service.record_revocation(_revoke(event_id="evt-delete-2"))

    assert first is not None and first.changed is True
    assert second is not None and second.matched is True and second.changed is False
    count = (
        await db_session.execute(
            select(func.count(AuditLog.id)).where(AuditLog.action == "message_revoked")
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_unmatched_revoke_never_creates_fake_message_content(db_session):
    result = await DeletedMessageService(db_session).record_revocation(_revoke("NEVER-SEEN"))

    assert result is not None and result.matched is False and result.changed is False
    messages = (await db_session.execute(select(Message))).scalars().all()
    assert messages == []
    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "message_revocation_unmatched",
                AuditLog.entity_id == "NEVER-SEEN",
            )
        )
    ).scalars().one()
    assert audit.details_json["content_recovered"] is False
    rendered = await DeletedMessageService(db_session).render_command("")
    assert "only show content that was observed" in rendered


@pytest.mark.asyncio
async def test_dm_list_is_dm_scoped_and_info_is_truthful_about_media(db_session):
    dm = await _message(db_session, source_id="DM-1")
    group = await _message(db_session, source_id="GROUP-1", chat_type="group")
    service = DeletedMessageService(db_session)
    await service.record_revocation(_revoke("DM-1", event_id="evt-dm"))
    group_event = _revoke("GROUP-1", event_id="evt-group")
    group_event["payload"]["before"]["chatId"] = group.chat_id
    group_event["payload"]["before"]["from"] = group.chat_id
    await service.record_revocation(group_event)

    listing = await service.render_command("list")
    assert "The meeting is now 4pm" in listing
    assert "1 shown" in listing
    info = await service.render_command("info")
    assert f"Database ID: {dm.id}" in info
    assert "Media retained: no dedicated media archive" in info


@pytest.mark.asyncio
async def test_owner_self_dm_dot_dm_queues_private_response(db_session):
    await _owner(db_session)
    await _message(db_session)
    await DeletedMessageService(db_session).record_revocation(_revoke())
    event = {
        "event": "message.any",
        "session": "default",
        "payload": {"id": "DM-CMD-1", "chatId": OWNER_ID, "from": OWNER_ID, "fromMe": True, "body": "@Zina .dm"},
    }
    normalized = MessageNormalizer().normalize(event)

    result = await CommandControlService(db_session).handle_from_me(
        normalized,
        transport_message_id="DM-CMD-1",
        request_id="DM-CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command in {".dm", "/deleted-message"}
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert "The meeting is now 4pm" in queued[0].message_text


@pytest.mark.asyncio
async def test_deleted_message_management_denies_non_owner(db_session):
    service = OwnerManagementCommandService(db_session)

    result = await service.handle(".dm", "", permission="admin")

    assert result is not None
    assert result.error == "owner permission required"
    assert "Access denied" in result.reply_text
