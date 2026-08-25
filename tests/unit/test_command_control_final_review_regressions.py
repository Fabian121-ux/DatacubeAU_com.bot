from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, text

from app.config import Settings
from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount
from app.services.command_control_service import CommandControlService
from app.services.inbound_idempotency_service import InboundIdempotencyService, InboundReceipt
from app.services.natural_action_planner_service import NaturalActionPlannerService


def _owner_event(body: str, number: str = "2348000000001") -> dict:
    chat_id = f"{number}@c.us"
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": "FINAL-REVIEW",
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": True,
            "body": body,
        },
    }


@pytest.mark.asyncio
async def test_stale_processing_receipt_can_be_reclaimed(db_session):
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts"))
    await db_session.execute(
        text(
            """
            INSERT INTO inbound_webhook_receipts
                (event_key, session_name, chat_id, message_id, status, updated_at)
            VALUES
                ('default:chat:stale', 'default', 'chat', 'stale', 'processing', NOW() - INTERVAL '10 minutes')
            """
        )
    )
    await db_session.commit()

    service = InboundIdempotencyService(db_session)
    claimed = await service.claim(
        InboundReceipt(
            event_key="default:chat:stale",
            session_name="default",
            chat_id="chat",
            message_id="stale",
        )
    )
    assert claimed is True

    await service.mark_completed("default:chat:stale")
    assert await service.claim(
        InboundReceipt(
            event_key="default:chat:stale",
            session_name="default",
            chat_id="chat",
            message_id="stale",
        )
    ) is False


@pytest.mark.asyncio
async def test_primary_owner_lookup_accepts_historical_mixed_case_permission(db_session):
    await db_session.execute(delete(AdminAccount))
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id="2348000000001@c.us",
        role="primary_admin",
        permission_level="Owner",
        is_primary=True,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()

    message = MessageNormalizer().normalize(_owner_event("@Zina .status"))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="FINAL-REVIEW",
        request_id="FINAL-REVIEW",
    )
    assert result is not None and result.consumed is True
    assert result.command == "/status"


def test_natural_action_parser_preserves_multiline_message_body():
    now = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    plan = NaturalActionPlannerService.parse(
        "message Amanda tomorrow at 09:00 and tell them First line\nSecond line\nThird line",
        now=now,
    )
    assert plan is not None
    assert plan.message_text == "First line\nSecond line\nThird line"


def test_production_runtime_requires_waha_webhook_secret():
    settings = Settings(
        ENVIRONMENT="production",
        ADMIN_PASSWORD="long-enough-admin-password",
        ADMIN_SESSION_SECRET="x" * 32,
        WAHA_API_KEY="",
    )
    with pytest.raises(RuntimeError, match="WAHA_API_KEY is required in production"):
        settings.validate_runtime()


def test_deployment_smoke_sends_waha_authentication_header():
    smoke = open("deploy/scripts/smoke-test.sh", encoding="utf-8").read()
    assert 'if [ -z "${WAHA_API_KEY:-}" ]' in smoke
    assert '-H "X-Api-Key: ${WAHA_API_KEY}"' in smoke
