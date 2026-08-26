from __future__ import annotations

from fastapi import BackgroundTasks
import pytest
from sqlalchemy import delete, select, text

from app.api.inbound import waha_webhook
from app.core.message_normalizer import MessageNormalizer
from app.db import SessionLocal
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


class _Request:
    def __init__(self, event: dict):
        self._event = event
        self.headers: dict[str, str] = {}

    async def json(self):
        return self._event


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


@pytest.mark.asyncio
async def test_push_does_not_resume_or_cancel_active_takeover(monkeypatch):
    import app.api.inbound as inbound_module
    import app.services.admin_management_service as admin_module

    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")
    monkeypatch.setattr(admin_module.settings, "owner_whatsapp_ids", OWNER_NUMBER)

    async def _must_not_record_owner_reply(*_args, **_kwargs):
        raise AssertionError(".push must not be treated as Fabian resuming the peer conversation")

    async def _must_not_generate_handback(*_args, **_kwargs):
        raise AssertionError(".push must not generate a conversation handback")

    monkeypatch.setattr(
        inbound_module.ConversationTakeoverService,
        "record_owner_reply",
        _must_not_record_owner_reply,
    )
    monkeypatch.setattr(
        inbound_module.ConversationHandbackService,
        "generate_if_needed",
        _must_not_generate_handback,
    )

    async with SessionLocal() as db:
        await db.execute(delete(OutboundMessage))
        await db.execute(delete(AdminAccount))
        await db.execute(text("DELETE FROM inbound_webhook_receipts"))
        await db.commit()

    try:
        result = await waha_webhook(
            _Request(_push_event(message_id="PUSH-NO-HANDBACK")),
            BackgroundTasks(),
        )

        assert result["status"] == "accepted"
        assert result["command_consumed"] is True
        assert result["command"] == "/push"
        assert result["handback_generated"] is False

        async with SessionLocal() as db:
            queued = (await db.execute(select(OutboundMessage))).scalars().all()
            assert len(queued) == 1
            assert queued[0].chat_id == OWNER_ID
    finally:
        async with SessionLocal() as db:
            await db.execute(delete(OutboundMessage))
            await db.execute(delete(AdminAccount))
            await db.execute(text("DELETE FROM inbound_webhook_receipts"))
            await db.commit()
