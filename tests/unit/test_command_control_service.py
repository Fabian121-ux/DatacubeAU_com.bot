from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AdminAccount, BotConfig, Contact, OutboundMessage
from app.services.command_control_service import CommandControlService


def _event(body: str, *, owner: str = "2348000000001@c.us", message_id: str = "CMD-1") -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": owner,
            "from": owner,
            "fromMe": True,
            "body": body,
        },
    }


@pytest.mark.asyncio
async def test_owner_self_dm_dot_alias_runs_existing_user_command(db_session):
    db_session.add(
        AdminAccount(
            name="Fabian",
            whatsapp_number="2348000000001",
            normalized_whatsapp_id="2348000000001@c.us",
            role="primary_admin",
            permission_level="owner",
            is_primary=True,
            is_enabled=True,
        )
    )
    await db_session.flush()

    message = MessageNormalizer().normalize(_event("@Zina .status"))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="CMD-1",
        request_id="CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command == "/status"
    assert "Online and ready" in (result.reply_text or "")
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == "2348000000001@c.us"
    assert queued[0].formatting_json["source"] == "command_control"


@pytest.mark.asyncio
async def test_limited_admin_cannot_start_owner_guided_schedule(db_session):
    db_session.add(
        AdminAccount(
            name="Limited Admin",
            whatsapp_number="2348000000003",
            normalized_whatsapp_id="2348000000003@c.us",
            role="admin",
            permission_level="admin",
            is_primary=False,
            is_enabled=True,
        )
    )
    await db_session.flush()

    message = MessageNormalizer().normalize(_event("@Zina .sch", owner="2348000000003@c.us"))
    result = await CommandControlService(db_session).handle_from_me(message, transport_message_id="ADMIN-SCH")

    assert result is not None and result.consumed is True
    assert result.error == "owner permission required"
    assert "Access denied" in (result.reply_text or "")
    drafts = (
        await db_session.execute(select(BotConfig).where(BotConfig.config_key.like("command_draft.schedule.%")))
    ).scalars().all()
    assert drafts == []
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_guided_schedule_draft_persists_and_saves_through_existing_scheduler(db_session, monkeypatch):
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id="2348000000001@c.us",
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )
    amanda = Contact(
        whatsapp_id="2348000000002@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        normalized_phone="2348000000002",
    )
    db_session.add_all([owner, amanda])
    await db_session.flush()

    fixed_now = datetime(2026, 8, 25, 13, 0, tzinfo=ZoneInfo("Africa/Lagos"))
    import app.services.command_control_service as control_module
    import app.services.natural_action_planner_service as planner_module

    monkeypatch.setattr(control_module, "utcnow", lambda: fixed_now)
    monkeypatch.setattr(planner_module, "utcnow", lambda: fixed_now)

    async def send(body: str, message_id: str):
        message = MessageNormalizer().normalize(_event(body, message_id=message_id))
        return await CommandControlService(db_session).handle_from_me(
            message,
            transport_message_id=message_id,
            request_id=message_id,
        )

    started = await send("@Zina .sch", "SCH-START")
    assert started is not None and "New Schedule" in (started.reply_text or "")

    # Recreate the service for every field update to prove the draft is PostgreSQL-backed,
    # not an in-process conversation object.
    await send(".target Amanda Christabel", "SCH-TARGET")
    await send(".message The document is ready", "SCH-MESSAGE")
    await send(".date tomorrow", "SCH-DATE")
    await send(".time 09:00", "SCH-TIME")

    draft_row = (
        await db_session.execute(select(BotConfig).where(BotConfig.config_key == f"command_draft.schedule.{owner.id}"))
    ).scalar_one()
    assert "Amanda Christabel" in draft_row.config_value
    assert "Africa/Lagos" in draft_row.config_value

    saved = await send(".save", "SCH-SAVE")
    assert saved is not None and saved.error is None
    assert saved.scheduled_action_id is not None
    assert "✅ Scheduled" in (saved.reply_text or "")

    action = (await db_session.execute(select(ScheduledAction))).scalar_one()
    assert action.action_type == "whatsapp.send_message"
    assert action.target_contact_id == amanda.id
    assert action.target_chat_id == amanda.whatsapp_id
    assert action.payload_json == {"text": "The document is ready"}
    assert action.timezone == "Africa/Lagos"
    assert action.scheduled_for.astimezone(ZoneInfo("Africa/Lagos")).hour == 9
    assert action.idempotency_key == f"guided-schedule:{owner.id}:SCH-SAVE"

    await db_session.refresh(draft_row)
    assert draft_row.config_value == ""


@pytest.mark.asyncio
async def test_guided_schedule_cancel_discards_only_draft(db_session):
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id="2348000000001@c.us",
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()

    service = CommandControlService(db_session)
    start = MessageNormalizer().normalize(_event(".sch", message_id="CANCEL-START"))
    await service.handle_from_me(start, transport_message_id="CANCEL-START")

    cancel = MessageNormalizer().normalize(_event(".cancel", message_id="CANCEL-END"))
    result = await CommandControlService(db_session).handle_from_me(cancel, transport_message_id="CANCEL-END")

    assert result is not None
    assert result.reply_text == "Schedule draft cancelled."
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []
    draft = (
        await db_session.execute(select(BotConfig).where(BotConfig.config_key == f"command_draft.schedule.{owner.id}"))
    ).scalar_one()
    assert draft.config_value == ""


def test_command_parser_accepts_at_zina_dot_and_slash_forms():
    assert CommandControlService.parse("@Zina .sch") == (".sch", "")
    assert CommandControlService.parse(".target Amanda Christabel") == (".target", "Amanda Christabel")
    assert CommandControlService.parse("/status") == ("/status", "")
    assert CommandControlService.parse("hello Zina") is None
