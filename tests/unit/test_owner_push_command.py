from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, CommandCatalogEntry, Contact, Message, OutboundMessage
from app.services.command_catalog_service import CommandCatalogService
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


def _push_event(
    *,
    command_id: str = "PUSH-CMD-1",
    body: str = "@Zina .push",
    quoted_id: str | None = "SRC-1",
    quoted_body: str = "Please bring the signed document",
    quoted_has_media: bool = False,
) -> dict:
    payload = {
        "id": command_id,
        "chatId": AMANDA_ID,
        "from": AMANDA_ID,
        "fromMe": True,
        "body": body,
    }
    if quoted_id is not None:
        payload["replyTo"] = {
            "id": quoted_id,
            "body": quoted_body,
            "hasMedia": quoted_has_media,
        }
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
    assert queued[0].formatting_json["source_evidence"] == "postgres_message"


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


@pytest.mark.asyncio
async def test_push_can_use_waha_reply_snapshot_for_unpersisted_quoted_message(db_session):
    await _seed_source(db_session)
    await db_session.execute(delete(Message))
    await db_session.flush()
    message = MessageNormalizer().normalize(
        _push_event(
            command_id="PUSH-SNAPSHOT",
            quoted_id="UNPERSISTED-SRC-9",
            quoted_body="I will bring the signed document",
        )
    )

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-SNAPSHOT",
    )

    assert result is not None and result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert "sender direction unavailable" in queued.message_text
    assert "I will bring the signed document" in queued.message_text
    assert "Source ID: UNPERSISTED-SRC-9" in queued.message_text
    assert queued.formatting_json["source_evidence"] == "waha_reply_snapshot"
    assert queued.formatting_json["source_db_message_id"] is None


@pytest.mark.asyncio
async def test_push_snapshot_media_is_metadata_only(db_session):
    await _seed_source(db_session)
    await db_session.execute(delete(Message))
    await db_session.flush()
    message = MessageNormalizer().normalize(
        _push_event(
            command_id="PUSH-SNAPSHOT-MEDIA",
            quoted_id="MEDIA-SRC-9",
            quoted_body="Signed page",
            quoted_has_media=True,
        )
    )

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-SNAPSHOT-MEDIA",
    )

    assert result is not None and result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert "Type: media" in queued.message_text
    assert "original media is not forwarded" in queued.message_text
    assert queued.media_url is None


@pytest.mark.asyncio
async def test_push_note_is_rejected_as_peer_visible_not_called_private(db_session):
    await _seed_source(db_session)
    message = MessageNormalizer().normalize(
        _push_event(command_id="PUSH-NOTE", body="@Zina .push note Follow up tonight")
    )

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-NOTE",
    )

    assert result is not None and result.error is not None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert queued.chat_id == OWNER_ID
    assert "Private notes are not accepted from a peer chat" in queued.message_text
    assert "Private note:" not in queued.message_text


@pytest.mark.asyncio
async def test_push_is_recoverable_in_default_command_catalog(db_session):
    await db_session.execute(delete(CommandCatalogEntry))
    await db_session.flush()

    catalog = CommandCatalogService(db_session)
    await catalog.ensure_defaults()
    commands = {item["name"]: item for item in await catalog.list_commands()}

    assert "/push" in commands
    assert commands["/push"]["trigger_syntax"] == ".push"
    assert commands["/push"]["permissions"] == "owner"
    assert commands["/push"]["handler_target"] == "command_control:push"
    await catalog.set_enabled("/push", False)
    assert await catalog.is_enabled("/push") is False


@pytest.mark.asyncio
async def test_disabled_push_queues_private_disabled_response(db_session):
    await _seed_source(db_session)
    catalog = CommandCatalogService(db_session)
    await catalog.ensure_defaults()
    await catalog.set_enabled("/push", False)
    message = MessageNormalizer().normalize(_push_event(command_id="PUSH-DISABLED"))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PUSH-DISABLED",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/push"
    assert result.error == "command disabled"
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert queued[0].chat_id != AMANDA_ID
    assert queued[0].message_text == "Push is currently disabled."
    assert queued[0].formatting_json["source"] == "command_control"
