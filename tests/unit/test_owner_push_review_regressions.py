from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, OutboundMessage
from app.services.command_control_service import CommandControlService


OWNER_NUMBER = "2348000000001"
OWNER_ID = f"{OWNER_NUMBER}@c.us"
PEER_ID = "2348000000002@c.us"


def _push_event(
    *,
    message_id: str,
    quoted_id: str = "QUOTED-1",
    quoted_body: str = "Please keep this",
    has_media: bool = False,
) -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "body": "@Zina .push",
            "replyTo": {
                "id": quoted_id,
                "body": quoted_body,
                "hasMedia": has_media,
            },
        },
    }


@pytest.mark.asyncio
async def test_push_seeds_configured_primary_owner_before_first_command(db_session, monkeypatch):
    import app.services.admin_management_service as admin_module

    await db_session.execute(delete(AdminAccount))
    await db_session.execute(delete(OutboundMessage))
    await db_session.flush()
    monkeypatch.setattr(admin_module.settings, "owner_whatsapp_ids", OWNER_NUMBER)

    message = MessageNormalizer().normalize(_push_event(message_id="FRESH-OWNER-PUSH"))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="FRESH-OWNER-PUSH",
        request_id="FRESH-OWNER-PUSH",
    )

    assert result is not None and result.consumed is True
    owner = (
        await db_session.execute(
            select(AdminAccount).where(
                AdminAccount.is_primary.is_(True),
                AdminAccount.is_enabled.is_(True),
            )
        )
    ).scalar_one()
    assert owner.normalized_whatsapp_id == OWNER_ID
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert queued.chat_id == OWNER_ID


@pytest.mark.asyncio
async def test_push_accepts_captionless_media_reply_snapshot(db_session, monkeypatch):
    import app.services.admin_management_service as admin_module

    await db_session.execute(delete(AdminAccount))
    await db_session.execute(delete(OutboundMessage))
    await db_session.flush()
    monkeypatch.setattr(admin_module.settings, "owner_whatsapp_ids", OWNER_NUMBER)

    message = MessageNormalizer().normalize(
        _push_event(
            message_id="CAPTIONLESS-MEDIA-PUSH",
            quoted_id="MEDIA-NO-CAPTION",
            quoted_body="",
            has_media=True,
        )
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="CAPTIONLESS-MEDIA-PUSH",
    )

    assert result is not None and result.error is None
    queued = (await db_session.execute(select(OutboundMessage))).scalars().one()
    assert "Type: media" in queued.message_text
    assert "(no text/caption captured)" in queued.message_text
    assert "original media is not forwarded" in queued.message_text


def test_push_is_control_only_and_does_not_count_as_owner_conversation_reply():
    assert CommandControlService.is_non_takeover_control("@Zina .push") is True
    assert CommandControlService.is_non_takeover_control(".push") is True
    assert CommandControlService.is_non_takeover_control("/push") is True
    assert CommandControlService.is_non_takeover_control("@Zina .status") is False
    assert CommandControlService.is_non_takeover_control("message Amanda tomorrow at 9am") is False
