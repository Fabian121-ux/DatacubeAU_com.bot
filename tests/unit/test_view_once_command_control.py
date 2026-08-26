from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, CommandCatalogEntry, OutboundMessage
from app.services.bot_config_service import BotConfigService
from app.services.command_catalog_service import CommandCatalogService
from app.services.command_control_service import CommandControlService
from app.services.view_once_command_service import ViewOnceCommandService


OWNER_ID = "2348000000001@c.us"
PEER_ID = "2348000000002@c.us"


async def _seed_owner(db_session) -> AdminAccount:
    owner = (
        await db_session.execute(
            select(AdminAccount).where(AdminAccount.normalized_whatsapp_id == OWNER_ID).limit(1)
        )
    ).scalar_one_or_none()
    if owner is None:
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
    else:
        owner.name = "Fabian"
        owner.whatsapp_number = "2348000000001"
        owner.normalized_whatsapp_id = OWNER_ID
        owner.role = "primary_admin"
        owner.permission_level = "owner"
        owner.is_primary = True
        owner.is_enabled = True
    await db_session.flush()
    return owner


def _trusted_media_url() -> str:
    return settings.waha_service_url.rstrip("/") + "/api/files/view-once.jpg"


def _event(
    body: str,
    *,
    command_id: str = "VV-CMD-1",
    view_once: bool | None = True,
    media_url: str | None = None,
    media_size: int | None = None,
) -> dict:
    reply = {
        "id": "VV-SOURCE-1",
        "hasMedia": True,
        "media": {
            "mimetype": "image/jpeg",
            "type": "image",
        },
    }
    effective_media_url = _trusted_media_url() if media_url is None else media_url
    if effective_media_url:
        reply["media"]["url"] = effective_media_url
    if media_size is not None:
        reply["media"]["fileSize"] = media_size
    if view_once is not None:
        reply["viewOnce"] = view_once
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": command_id,
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "body": body,
            "replyTo": reply,
        },
    }


@pytest.mark.asyncio
async def test_owner_peer_reply_vv_queues_media_only_to_private_self_dm(db_session):
    await _seed_owner(db_session)
    message = MessageNormalizer().normalize(_event("@Zina .vv"))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-CMD-1",
        request_id="VV-CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/vvopen"
    assert result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert queued[0].chat_id != PEER_ID
    assert queued[0].media_url == _trusted_media_url()
    assert queued[0].media_type == "image"
    assert queued[0].formatting_json["source"] == "view_once_command"
    assert queued[0].formatting_json["source_message_id"] == "VV-SOURCE-1"


@pytest.mark.asyncio
async def test_plain_quoted_media_is_not_falsely_opened_as_view_once(db_session):
    await _seed_owner(db_session)
    message = MessageNormalizer().normalize(_event(".vvopen", view_once=None))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-PLAIN-MEDIA",
    )

    assert result is not None and result.consumed is True
    assert result.error == "view-once capability unproven"
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert queued[0].media_url is None
    assert "no explicit view-once evidence" in queued[0].message_text.lower()


@pytest.mark.asyncio
async def test_untrusted_media_url_is_blocked_before_outbound_delivery(db_session):
    await _seed_owner(db_session)
    message = MessageNormalizer().normalize(
        _event(".vv", command_id="VV-UNTRUSTED", media_url="https://example.invalid/private.jpg")
    )

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-UNTRUSTED",
    )

    assert result is not None
    assert result.error == "untrusted media url"
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].media_url is None
    assert "outside the configured waha file origin" in queued[0].message_text.lower()


@pytest.mark.asyncio
async def test_oversized_view_once_media_is_blocked_when_waha_reports_size(db_session):
    await _seed_owner(db_session)
    message = MessageNormalizer().normalize(
        _event(
            ".vv",
            command_id="VV-TOO-LARGE",
            media_size=ViewOnceCommandService.MAX_MEDIA_BYTES + 1,
        )
    )

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-TOO-LARGE",
    )

    assert result is not None
    assert result.error == "media too large"
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].media_url is None
    assert "50 mb" in queued[0].message_text.lower()


@pytest.mark.asyncio
async def test_vv_info_and_list_dispatch_as_subcommands_not_open(db_session):
    await _seed_owner(db_session)
    info = MessageNormalizer().normalize(_event("@Zina .vv info", command_id="VV-INFO"))
    info_result = await CommandControlService(db_session).handle_from_me(info, transport_message_id="VV-INFO")
    assert info_result is not None and info_result.error is None

    listing = MessageNormalizer().normalize(_event(".vv list 5", command_id="VV-LIST"))
    list_result = await CommandControlService(db_session).handle_from_me(listing, transport_message_id="VV-LIST")
    assert list_result is not None and list_result.error is None

    queued = (await db_session.execute(select(OutboundMessage).order_by(OutboundMessage.id.asc()))).scalars().all()
    assert len(queued) == 2
    assert "VIEW-ONCE INFO" in queued[0].message_text
    assert "VIEW-ONCE ITEMS" in queued[1].message_text
    assert queued[0].media_url is None
    assert queued[1].media_url is None


@pytest.mark.asyncio
async def test_vvretain_off_persists_and_on_fails_closed(db_session):
    await _seed_owner(db_session)
    off_message = MessageNormalizer().normalize(_event(".vvretain off", command_id="VV-RET-OFF"))
    off_result = await CommandControlService(db_session).handle_from_me(off_message, transport_message_id="VV-RET-OFF")
    assert off_result is not None and off_result.error is None
    assert (await BotConfigService(db_session).get(ViewOnceCommandService.CONFIG_RETENTION_KEY, "")) == "false"

    on_message = MessageNormalizer().normalize(_event(".vvretain on", command_id="VV-RET-ON"))
    on_result = await CommandControlService(db_session).handle_from_me(on_message, transport_message_id="VV-RET-ON")
    assert on_result is not None
    assert on_result.error == "retention unsupported"
    assert (await BotConfigService(db_session).get(ViewOnceCommandService.CONFIG_RETENTION_KEY, "")) == "false"


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["user", "admin"])
async def test_view_once_service_denies_non_owner_before_media_access(db_session, permission):
    message = MessageNormalizer().normalize(_event(".vv"))
    result = await ViewOnceCommandService(db_session).handle(
        ".vv",
        "",
        message=message,
        owner=SimpleNamespace(normalized_whatsapp_id=OWNER_ID, whatsapp_number="2348000000001"),
        permission=permission,
        request_id="VV-DENY",
        transport_message_id="VV-DENY",
    )

    assert result.consumed is True
    assert result.error == "owner permission required"
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert queued == []


@pytest.mark.asyncio
async def test_view_once_catalog_default_is_owner_only_and_recoverable(db_session):
    await db_session.execute(
        CommandCatalogEntry.__table__.delete().where(CommandCatalogEntry.name == "/vvopen")
    )
    await CommandCatalogService(db_session).ensure_defaults()
    row = (
        await db_session.execute(
            select(CommandCatalogEntry).where(CommandCatalogEntry.name == "/vvopen").limit(1)
        )
    ).scalar_one()

    assert row.permissions == "owner"
    assert row.trigger_syntax == ".vv"
    assert row.handler_target == "command_control:view_once"
    assert row.is_enabled is True


def test_view_once_aliases_parse_and_do_not_resume_takeover():
    expected = {
        ".vv": (".vv", ""),
        "@Zina .vvopen": (".vvopen", ""),
        "@Zina .vv info": (".vv", "info"),
        ".vv list 10": (".vv", "list 10"),
        ".vv delete SOURCE-9": (".vv", "delete SOURCE-9"),
        "@Zina .vvretain on": (".vvretain", "on"),
        ".vvretain off": (".vvretain", "off"),
        "/vvopen": ("/vvopen", ""),
    }
    for raw, parsed in expected.items():
        assert CommandControlService.parse(raw) == parsed
        assert CommandControlService.is_non_takeover_control(raw) is True
