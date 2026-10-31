from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.scheduled_action import ScheduledAction
from app.models.schema import Contact
from app.services.natural_action_planner_service import NaturalActionPlannerService


LAGOS = ZoneInfo("Africa/Lagos")


def test_parse_exact_owner_style_instruction_with_named_date_and_time():
    now = datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS)
    plan = NaturalActionPlannerService.parse("@Zina message Amanda Christabel at 9:00am on Aug 25 and tell her the document is ready", timezone="Africa/Lagos", now=now)
    assert plan is not None
    assert plan.target_reference == "Amanda Christabel"
    assert plan.message_text == "the document is ready"
    assert plan.scheduled_for == datetime(2026, 8, 25, 9, 0, tzinfo=LAGOS)


def test_parse_tomorrow_instruction_with_colon_message_body_does_not_split_time_colon():
    now = datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS)
    plan = NaturalActionPlannerService.parse("message Amanda at 9:00am tomorrow: the document is ready", timezone="Africa/Lagos", now=now)
    assert plan is not None
    assert plan.target_reference == "Amanda"
    assert plan.message_text == "the document is ready"
    assert plan.scheduled_for == datetime(2026, 8, 25, 9, 0, tzinfo=LAGOS)


def test_parse_rejects_past_explicit_time():
    now = datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS)
    with pytest.raises(ValueError, match="future"):
        NaturalActionPlannerService.parse("message Amanda at 9am on Aug 24 2026 and tell her hello", timezone="Africa/Lagos", now=now)


def test_parse_ignores_unstructured_or_unrelated_chat():
    now = datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS)
    assert NaturalActionPlannerService.parse("How is Amanda?", now=now) is None
    assert NaturalActionPlannerService.parse("message Amanda sometime tomorrow", now=now) is None
    assert NaturalActionPlannerService.parse("/broadcast hello", now=now) is None


@pytest.mark.asyncio
async def test_create_from_instruction_reuses_contact_intelligence_and_scheduler(db_session):
    contact = Contact(whatsapp_id="2348011111111@c.us", display_name="Amanda Christabel", contact_name="Amanda Christabel")
    db_session.add(contact)
    await db_session.flush()

    result = await NaturalActionPlannerService(db_session).create_from_instruction(
        "message Amanda Christabel at 9am on Aug 25 and tell her the document is ready",
        actor_permission="owner",
        timezone="Africa/Lagos",
        now=datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS),
        requested_by_contact_id=contact.id,
        idempotency_key="natural-amanda-test",
    )

    assert result is not None
    assert result["action"] == "whatsapp.send_message"
    assert result["handler_target"] == "scheduled_action.whatsapp_send_message"
    assert result["scheduled_action"]["target_contact_id"] == contact.id
    assert result["scheduled_action"]["target_chat_id"] == contact.whatsapp_id
    row = (await db_session.execute(select(ScheduledAction).where(ScheduledAction.idempotency_key == "natural-amanda-test"))).scalar_one()
    assert row.status == "scheduled"
    assert row.payload_json["text"] == "the document is ready"


@pytest.mark.asyncio
async def test_create_from_instruction_preserves_ambiguous_contact_safety(db_session):
    db_session.add_all([Contact(whatsapp_id="2348011111111@c.us", contact_name="Amanda Christabel"), Contact(whatsapp_id="2348022222222@c.us", contact_name="Amanda Christine")])
    await db_session.flush()

    with pytest.raises(ValueError, match="ambiguous"):
        await NaturalActionPlannerService(db_session).create_from_instruction(
            "message Amanda at 9am tomorrow and tell her hello",
            actor_permission="owner",
            timezone="Africa/Lagos",
            now=datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS),
        )
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_create_from_instruction_cannot_bypass_owner_tool_permission(db_session):
    db_session.add(Contact(whatsapp_id="2348011111111@c.us", contact_name="Amanda Christabel"))
    await db_session.flush()

    with pytest.raises(ValueError, match="permission denied"):
        await NaturalActionPlannerService(db_session).create_from_instruction(
            "message Amanda Christabel at 9am tomorrow and tell her hello",
            actor_permission="admin",
            timezone="Africa/Lagos",
            now=datetime(2026, 8, 24, 18, 30, tzinfo=LAGOS),
        )
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []
