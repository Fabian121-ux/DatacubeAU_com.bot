from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, AuditLog, OutboundMessage
from app.services.command_control_service import CommandControlService
from app.services.view_once_media_service import ViewOnceMediaService


OWNER_ID = "2348000000001@c.us"
PEER_ID = "2348000000002@c.us"
SOURCE_ID = "VV-DELETE-NO-RETENTION"


async def _seed_owner(db_session) -> None:
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


def _event(body: str) -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": "VV-DELETE-CMD",
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "body": body,
            "replyTo": {
                "id": SOURCE_ID,
                "viewOnce": True,
                "hasMedia": True,
                "media": {
                    "url": "http://waha:3000/api/files/ephemeral.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            },
        },
    }


@pytest.mark.asyncio
async def test_vv_delete_reports_no_retained_media_and_preserves_observation_metadata(db_session):
    await _seed_owner(db_session)
    message = MessageNormalizer().normalize(_event(".vv delete"))

    # Observe the source first without creating any retained byte artifact.
    capability, before = await ViewOnceMediaService(db_session).observe_reply(message)
    assert capability.is_view_once is True
    assert before is not None
    assert before.retention_mode == "none"
    assert before.deleted_at is None

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-DELETE-CMD",
        request_id="VV-DELETE-CMD",
    )

    assert result is not None and result.consumed is True
    assert result.error == "no retained media"
    assert "no retained media exists" in (result.reply_text or "").lower()

    after = await ViewOnceMediaService(db_session).get(SOURCE_ID)
    assert after is not None
    assert after.retention_mode == "none"
    assert after.deleted_at is None

    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID
    assert queued[0].media_url is None
    assert "nothing was deleted" in queued[0].message_text.lower()

    audits = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "view_once_delete_no_retained_media",
                AuditLog.entity_id == "VV-DELETE-CMD",
            )
        )
    ).scalars().all()
    assert len(audits) == 1
    assert audits[0].details_json.get("source_message_id") == SOURCE_ID
    assert audits[0].details_json.get("retention_mode") == "none"
