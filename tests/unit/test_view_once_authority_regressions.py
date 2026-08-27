from __future__ import annotations

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, AuditLog, OutboundMessage
from app.services.command_control_service import CommandControlService


OWNER_ID = "2348000000001@c.us"
PEER_ID = "2348000000002@c.us"


async def _seed_primary(db_session, permission: str) -> AdminAccount:
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
            permission_level=permission,
            is_primary=True,
            is_enabled=True,
        )
        db_session.add(owner)
    else:
        owner.name = "Fabian"
        owner.whatsapp_number = "2348000000001"
        owner.normalized_whatsapp_id = OWNER_ID
        owner.role = "primary_admin"
        owner.permission_level = permission
        owner.is_primary = True
        owner.is_enabled = True
    await db_session.flush()
    return owner


def _event(body: str) -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": "VV-AUTH-CMD",
            "chatId": PEER_ID,
            "from": PEER_ID,
            "fromMe": True,
            "body": body,
            "replyTo": {
                "id": "VV-AUTH-SOURCE",
                "hasMedia": True,
                "viewOnce": True,
                "media": {
                    "type": "image",
                    "mimetype": "image/jpeg",
                    "url": settings.waha_service_url.rstrip("/") + "/api/files/auth-test.jpg",
                },
            },
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["admin", "user"])
async def test_downgraded_primary_account_cannot_use_view_once_peer_control(db_session, permission):
    await _seed_primary(db_session, permission)
    message = MessageNormalizer().normalize(_event("@Zina .vv"))

    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="VV-AUTH-CMD",
        request_id="VV-AUTH-CMD",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/vvopen"
    assert result.error == "owner permission required"
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_command_denied")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert audit.details_json["reason"] == "owner_required"
    assert audit.details_json["permission"] == permission
