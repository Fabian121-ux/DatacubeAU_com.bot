from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, text

from app.config import Settings
from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount
from app.services.command_control_service import CommandControlService
from app.services.inbound_idempotency_service import (
    InboundClaimLostError,
    InboundIdempotencyService,
    InboundReceipt,
)
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
async def test_stale_worker_cannot_release_replacement_claim(db_session):
    event_key = "default:chat:fenced"
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts WHERE event_key = :key"), {"key": event_key})
    await db_session.commit()

    service = InboundIdempotencyService(db_session)
    assert await service.claim(
        InboundReceipt(
            event_key=event_key,
            session_name="default",
            chat_id="chat",
            message_id="fenced",
        )
    ) is True

    original_token = (
        await db_session.execute(
            text("SELECT claim_token FROM inbound_webhook_receipts WHERE event_key = :key"),
            {"key": event_key},
        )
    ).scalar_one()
    assert original_token

    replacement_token = "replacement-generation-token"
    await db_session.execute(
        text(
            """
            UPDATE inbound_webhook_receipts
            SET claim_token = :replacement, status = 'processing', updated_at = NOW()
            WHERE event_key = :key
            """
        ),
        {"replacement": replacement_token, "key": event_key},
    )
    await db_session.commit()

    await service.release_failed(event_key)

    row = (
        await db_session.execute(
            text("SELECT status, claim_token FROM inbound_webhook_receipts WHERE event_key = :key"),
            {"key": event_key},
        )
    ).one()
    assert row.status == "processing"
    assert row.claim_token == replacement_token


@pytest.mark.asyncio
async def test_stale_worker_aborts_before_committing_side_effects(db_session):
    event_key = "default:chat:lease-lost-before-commit"
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts WHERE event_key = :key"), {"key": event_key})
    await db_session.commit()

    service = InboundIdempotencyService(db_session)
    assert await service.claim(
        InboundReceipt(
            event_key=event_key,
            session_name="default",
            chat_id="chat",
            message_id="lease-lost-before-commit",
        )
    ) is True

    await db_session.execute(
        text("INSERT INTO audit_logs (action, entity_type, details_json) VALUES ('stale_side_effect', 'test', '{}'::jsonb)")
    )

    replacement_token = "replacement-generation-token-2"
    await db_session.execute(
        text(
            """
            UPDATE inbound_webhook_receipts
            SET claim_token = :replacement, status = 'processing', updated_at = NOW()
            WHERE event_key = :key
            """
        ),
        {"replacement": replacement_token, "key": event_key},
    )
    await db_session.commit()

    await db_session.execute(
        text("INSERT INTO audit_logs (action, entity_type, details_json) VALUES ('must_rollback', 'test', '{}'::jsonb)")
    )
    with pytest.raises(InboundClaimLostError, match="lease lost"):
        await service.mark_completed(event_key, commit=False)

    assert (
        await db_session.execute(text("SELECT COUNT(*) FROM audit_logs WHERE action = 'must_rollback'"))
    ).scalar_one() == 0
    row = (
        await db_session.execute(
            text("SELECT status, claim_token FROM inbound_webhook_receipts WHERE event_key = :key"),
            {"key": event_key},
        )
    ).one()
    assert row.status == "processing"
    assert row.claim_token == replacement_token


@pytest.mark.asyncio
async def test_commit_false_retains_token_for_failure_release(db_session):
    event_key = "default:chat:commit-failure-release"
    await db_session.execute(text("DELETE FROM inbound_webhook_receipts WHERE event_key = :key"), {"key": event_key})
    await db_session.commit()

    service = InboundIdempotencyService(db_session)
    assert await service.claim(
        InboundReceipt(
            event_key=event_key,
            session_name="default",
            chat_id="chat",
            message_id="commit-failure-release",
        )
    ) is True

    await service.mark_completed(event_key, commit=False)
    await db_session.rollback()
    await service.release_failed(event_key)

    assert (
        await db_session.execute(
            text("SELECT COUNT(*) FROM inbound_webhook_receipts WHERE event_key = :key"),
            {"key": event_key},
        )
    ).scalar_one() == 0


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


def _production_settings(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "ADMIN_PASSWORD": "long-enough-admin-password",
        "ADMIN_SESSION_SECRET": "x" * 32,
        "WAHA_API_KEY": "valid-webhook-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_runtime_requires_waha_webhook_secret():
    settings = _production_settings(WAHA_API_KEY="")
    with pytest.raises(RuntimeError, match="WAHA_API_KEY is required in production"):
        settings.validate_runtime()


def test_production_runtime_normalizes_environment_before_secret_validation():
    settings = _production_settings(ENVIRONMENT="  Production  ", WAHA_API_KEY="")
    with pytest.raises(RuntimeError, match="WAHA_API_KEY is required in production"):
        settings.validate_runtime()


def test_production_runtime_rejects_whitespace_only_waha_secret():
    settings = _production_settings(WAHA_API_KEY="   \t  ")
    with pytest.raises(RuntimeError, match="WAHA_API_KEY is required in production"):
        settings.validate_runtime()


def test_deployment_smoke_sends_waha_authentication_header():
    smoke = open("deploy/scripts/smoke-test.sh", encoding="utf-8").read()
    assert 'if [ -z "${WAHA_API_KEY:-}" ]' in smoke
    assert '-H "X-Api-Key: ${WAHA_API_KEY}"' in smoke


def test_deployment_guide_manual_webhooks_send_waha_authentication_header():
    guide = open("deploy/DEPLOYMENT_GUIDE.md", encoding="utf-8").read()
    assert guide.count('-H "X-Api-Key: ${WAHA_API_KEY}"') >= 2
    assert guide.count(". ./.env.production") >= 2
