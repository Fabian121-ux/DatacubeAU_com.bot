from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, Contact, Message, OutboundMessage
from app.services.command_control_service import CommandControlService


OWNER_ID = "2348000000001@c.us"
AMANDA_ID = "2348000000002@c.us"


def _owner() -> AdminAccount:
    return AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id=OWNER_ID,
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )


def _push_event(*, command_id: str = "PUSH-CMD-1", body: str = "@Zina .push", quoted_id: str | None = "SRC-1") -> dict:
    payload = {
        "id": command_id,
        "chatId": AMANDA_ID,
        "from": AMANDA_ID,
        "fromMe": True,
        "body": body,
    }
    if quoted_id is not None:
        payload["replyTo"] = {"id": quoted_id, "body": "Please bring the signed document"}
    return {"event": "message.any", "session": "default", "payload": payload}


async def _seed_source(db_session, *, message_type: str = "text", text: str = "Please bring the signed document") -> Message:
    owner = (
        await db_session.execute(
            select(AdminAccount).where(AdminAccount.normalized_whatsapp_id == OWNER_ID).limit(1)
        )
    ).scalar_one_or_none()
    if owner is None:
        owner = _owner()
        db_session.add(owner)
    else:
        owner.name = "Fabian"
        owner.whatsapp_number = "2348000000001"
        owner.role = "primary_admin"
        owner.permission_level = "owner"
        owner.is_primary = True
        owner.is_enabled = True

    amanda = (
        await db_session.execute(select(Contact).where(Contact.whatsapp_id == AMANDA_ID).limit(1))
    ).scalar_one_or_none()
    if amanda is None:
        amanda = Contact(
            whatsapp_id=AMANDA_ID,
            chat_id=AMANDA_ID,
            display_name="Amanda Christabel",
            contact_name="Amanda Christabel",
        )
        db_session.add(amanda)
    else:
        amanda.chat_id = AMANDA_ID
        amanda.display_name = "Amanda Christabel"
        amanda.contact_name = "Amanda Christabel"

    await db_session.flush()
    source = Message(
        contact_id=amanda.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text=text,
        normalized_text=text.lower(),
        message_type=message_type,
        raw_payload_json={"id": "SRC-1", "chatId": AMANDA_ID, "body": text},
    )
    db_session.add(source)
    await db_session.flush()
    return source


@pytest.mark.asyncio
async def test_owner_can_push_quoted_peer_message_to_private_self_dm(db_session):
    source = await _seed_source(db_session)
    message = MessageNormalizer().normalize(_push_event())

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-CMD-1",
        request_id="PUSH-CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/push"
    assert result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert queued[0].chat_id != AMANDA_ID
    assert "Amanda Christabel" in queued[0].message_text
    assert "Please bring the signed document" in queued[0].message_text
    assert "Source ID: SRC-1" in queued[0].message_text
    assert queued[0].formatting_json["source"] == "owner_push"
    assert queued[0].formatting_json["source_db_message_id"] == source.id


@pytest.mark.asyncio
async def test_push_without_reply_queues_private_guidance_not_peer_chat(db_session):
    await _seed_source(db_session)
    message = MessageNormalizer().normalize(_push_event(quoted_id=None))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-NO-REPLY",
    )

    assert result is not None and result.consumed is True
    assert result.error is not None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert "Reply to the WhatsApp message" in queued[0].message_text


@pytest.mark.asyncio
async def test_push_command_is_idempotent_by_transport_message_id(db_session):
    await _seed_source(db_session)
    message = MessageNormalizer().normalize(_push_event(command_id="PUSH-ONCE"))
    service = CommandControlService(db_session)

    first = await service.handle_from_me(message, transport_message_id="PUSH-ONCE")
    second = await CommandControlService(db_session).handle_from_me(message, transport_message_id="PUSH-ONCE")

    assert first is not None and second is not None
    assert first.outbound_queue_id == second.outbound_queue_id
    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.formatting_json["source"].as_string() == "owner_push")
        )
    ).scalars().all()
    assert len(queued) == 1


@pytest.mark.asyncio
async def test_push_media_preserves_caption_and_does_not_claim_media_forwarding(db_session):
    await _seed_source(db_session, message_type="image", text="Signed page")
    message = MessageNormalizer().normalize(_push_event(command_id="PUSH-MEDIA"))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-MEDIA",
    )

    assert result is not None and result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert "Signed page" in queued.message_text
    assert "original media is not forwarded" in queued.message_text
    assert queued.media_url is None
