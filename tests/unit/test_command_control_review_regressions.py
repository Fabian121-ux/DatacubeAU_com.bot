from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.inbound import waha_webhook
from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, OutboundMessage
from app.services.command_control_service import CommandControlService


def _event(body: str, *, chat_id: str, message_id: str = "CMD-REVIEW-1", event_name: str = "message.any", session: str = "default") -> dict:
    return {
        "event": event_name,
        "session": session,
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": True,
            "body": body,
        },
    }


def _owner(number: str, *, primary: bool) -> AdminAccount:
    return AdminAccount(
        name="Fabian" if primary else "Secondary Owner",
        whatsapp_number=number,
        normalized_whatsapp_id=f"{number}@c.us",
        role="primary_admin" if primary else "admin",
        permission_level="owner",
        is_primary=primary,
        is_enabled=True,
    )


class _Request:
    def __init__(self, event: dict, *, headers: dict[str, str] | None = None):
        self._event = event
        self.headers: dict[str, str] = headers or {}

    async def json(self):
        return self._event


@pytest.mark.asyncio
async def test_secondary_owner_peer_chat_is_not_treated_as_fabian_self_dm(db_session):
    await db_session.execute(delete(AdminAccount))
    primary = _owner("2348000000001", primary=True)
    secondary = _owner("2348000000009", primary=False)
    db_session.add_all([primary, secondary])
    await db_session.flush()

    message = MessageNormalizer().normalize(
        _event("@Zina .status", chat_id="2348000000009@c.us", message_id="PEER-OWNER")
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="PEER-OWNER",
        request_id="PEER-OWNER",
    )

    assert result is None
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []


@pytest.mark.asyncio
async def test_at_zina_direct_slash_is_canonicalized_before_existing_handler(db_session):
    await db_session.execute(delete(AdminAccount))
    owner = _owner("2348000000001", primary=True)
    db_session.add(owner)
    await db_session.flush()

    message = MessageNormalizer().normalize(
        _event("@Zina /status", chat_id="2348000000001@c.us", message_id="DIRECT-SLASH")
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="DIRECT-SLASH",
        request_id="DIRECT-SLASH",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/status"
    assert "Online and ready" in (result.reply_text or "")


def test_command_parser_preserves_multiline_arguments():
    parsed = CommandControlService.parse("@Zina /teach\nQuestion:\nWho is Amanda?\nAnswer:\nA contact")
    assert parsed == (
        "/teach",
        "Question:\nWho is Amanda?\nAnswer:\nA contact",
    )


@pytest.mark.asyncio
async def test_multiline_command_reaches_existing_handler_with_dispatchable_prefix(db_session, monkeypatch):
    await db_session.execute(delete(AdminAccount))
    db_session.add(_owner("2348000000001", primary=True))
    await db_session.flush()

    captured: dict[str, str] = {}

    async def _fake_handle(_service, message, _contact):
        captured["text"] = message.message_text
        return SimpleNamespace(reply_text="captured")

    monkeypatch.setattr("app.services.command_control_service.OwnerCommandService.handle", _fake_handle)

    message = MessageNormalizer().normalize(
        _event(
            "@Zina /teach\nQuestion:\nWho is Amanda?\nAnswer:\nA contact",
            chat_id="2348000000001@c.us",
            message_id="MULTILINE-DISPATCH",
        )
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="MULTILINE-DISPATCH",
        request_id="MULTILINE-DISPATCH",
    )

    assert result is not None and result.consumed is True
    assert captured["text"] == "/teach Question:\nWho is Amanda?\nAnswer:\nA contact"


@pytest.mark.asyncio
async def test_forged_owner_webhook_is_rejected_when_waha_key_configured(monkeypatch):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "test-waha-secret")
    monkeypatch.setattr(inbound_module.settings, "environment", "production")

    event = _event("@Zina .status", chat_id="2348000000001@c.us", message_id="FORGED")
    result = await waha_webhook(_Request(event), BackgroundTasks())

    assert result == {"status": "ignored", "reason": "unauthorized_webhook"}


@pytest.mark.asyncio
async def test_authenticated_owner_webhook_rejects_unexpected_session(monkeypatch):
    import app.api.inbound as inbound_module

    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "test-waha-secret")
    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")

    event = _event(
        "@Zina .status",
        chat_id="2348000000001@c.us",
        message_id="WRONG-SESSION",
        session="other-session",
    )
    result = await waha_webhook(
        _Request(event, headers={"x-api-key": "test-waha-secret"}),
        BackgroundTasks(),
    )

    assert result["status"] == "ignored"
    assert result["reason"] == "unexpected_session"


@pytest.mark.asyncio
async def test_duplicate_from_me_webhook_executes_owner_command_once(monkeypatch):
    import app.api.inbound as inbound_module

    # Make the test independent of the workflow's WAHA_SESSION_NAME environment.
    # This case is about duplicate delivery/idempotency, not session mismatch.
    monkeypatch.setattr(inbound_module.settings, "waha_session_name", "default")
    monkeypatch.setattr(inbound_module.settings, "waha_api_key", "")
    monkeypatch.setattr(inbound_module.settings, "environment", "test")

    # The production module-level SessionLocal can retain pooled asyncpg connections
    # created by earlier pytest event loops. Give this committed idempotency regression
    # an engine/sessionmaker owned entirely by the current loop, and route the real
    # webhook through it. This preserves production behavior while preventing the test
    # harness from reusing a Future bound to a closed/different loop.
    test_engine = create_async_engine(
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
        ),
        pool_pre_ping=True,
    )
    TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    monkeypatch.setattr(inbound_module, "SessionLocal", TestSessionLocal)

    async with TestSessionLocal() as db:
        await db.execute(delete(OutboundMessage))
        await db.execute(delete(AdminAccount))
        await db.execute(text("DELETE FROM inbound_webhook_receipts"))
        db.add(_owner("2348000000001", primary=True))
        await db.commit()

    first_event = _event(
        "@Zina .status",
        chat_id="2348000000001@c.us",
        message_id="DUP-OWNER-CMD",
        event_name="message.any",
    )
    duplicate_variant = _event(
        "@Zina .status",
        chat_id="2348000000001@c.us",
        message_id="DUP-OWNER-CMD",
        event_name="message",
    )

    try:
        first = await waha_webhook(_Request(first_event), BackgroundTasks())
        second = await waha_webhook(_Request(duplicate_variant), BackgroundTasks())

        assert first["status"] == "accepted"
        assert first["command_consumed"] is True
        assert second["status"] == "duplicate"

        async with TestSessionLocal() as db:
            queued = (await db.execute(select(OutboundMessage))).scalars().all()
            assert len(queued) == 1
            assert queued[0].formatting_json["source"] == "command_control"
            receipt_status = (
                await db.execute(
                    text(
                        "SELECT status FROM inbound_webhook_receipts "
                        "WHERE event_key = :key"
                    ),
                    {"key": "default:2348000000001@c.us:DUP-OWNER-CMD"},
                )
            ).scalar_one()
            assert receipt_status == "completed"
    finally:
        async with TestSessionLocal() as db:
            await db.execute(delete(OutboundMessage))
            await db.execute(delete(AdminAccount))
            await db.execute(text("DELETE FROM inbound_webhook_receipts"))
            await db.commit()
        await test_engine.dispose()
