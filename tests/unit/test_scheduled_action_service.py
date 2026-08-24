from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.scheduled_action import ScheduledAction
from app.models.schema import Contact, OutboundMessage
from app.services.scheduled_action_service import ScheduledActionService
from app.utils.time import utcnow


@pytest.mark.asyncio
async def test_schedule_resolves_saved_contact_and_releases_once_to_existing_outbound_queue(db_session):
    contact = Contact(
        whatsapp_id="2348011111111@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        normalized_phone="2348011111111",
    )
    db_session.add(contact)
    await db_session.flush()

    service = ScheduledActionService(db_session)
    item = await service.create_whatsapp_message(
        target_reference="Amanda Christabel",
        text="Good morning Amanda.",
        scheduled_for=utcnow() - timedelta(seconds=1),
        timezone="Africa/Lagos",
        idempotency_key="test-amanda-message-1",
    )

    assert item["target_contact_id"] == contact.id
    assert item["target_chat_id"] == contact.whatsapp_id
    assert item["metadata"]["contact_resolution"]["matched_field"] in {"contact_name", "display_name"}

    assert await service.release_due() == 1
    assert await service.release_due() == 0

    action = (await db_session.execute(select(ScheduledAction))).scalar_one()
    outbound = (await db_session.execute(select(OutboundMessage))).scalar_one()
    assert action.status == "queued"
    assert action.outbound_queue_id == outbound.id
    assert outbound.chat_id == "2348011111111@c.us"
    assert outbound.message_text == "Good morning Amanda."
    assert outbound.status == "pending"
    assert outbound.formatting_json["scheduled_action_id"] == action.id


@pytest.mark.asyncio
async def test_schedule_refuses_ambiguous_contact_instead_of_guessing(db_session):
    db_session.add_all(
        [
            Contact(whatsapp_id="2348011111111@c.us", contact_name="Amanda Christabel"),
            Contact(whatsapp_id="2348022222222@c.us", contact_name="Amanda Christine"),
        ]
    )
    await db_session.flush()

    with pytest.raises(ValueError, match="ambiguous") as exc_info:
        await ScheduledActionService(db_session).create_whatsapp_message(
            target_reference="Amanda",
            text="Hello",
            scheduled_for=utcnow() + timedelta(hours=1),
            timezone="Africa/Lagos",
        )

    assert getattr(exc_info.value, "resolution")["status"] == "ambiguous"
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_schedule_refuses_naive_datetime_before_contact_resolution(db_session):
    with pytest.raises(ValueError, match="timezone offset"):
        await ScheduledActionService(db_session).create_whatsapp_message(
            target_reference="Amanda",
            text="Hello",
            scheduled_for=datetime(2026, 8, 25, 9, 0),
            timezone="Africa/Lagos",
        )

    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_pause_resume_reschedule_cancel_control_only_unreleased_actions(db_session):
    contact = Contact(whatsapp_id="2348033333333@c.us", contact_name="Christabel")
    db_session.add(contact)
    await db_session.flush()
    service = ScheduledActionService(db_session)
    item = await service.create_whatsapp_message(
        target_reference="Christabel",
        text="Reminder",
        scheduled_for=utcnow() + timedelta(days=1),
        timezone="Africa/Lagos",
    )

    paused = await service.pause(item["id"])
    assert paused["status"] == "paused"
    resumed = await service.resume(item["id"])
    assert resumed["status"] == "scheduled"
    rescheduled = await service.reschedule(
        item["id"], scheduled_for=utcnow() + timedelta(hours=2), timezone="Africa/Lagos"
    )
    assert rescheduled["status"] == "scheduled"
    cancelled = await service.cancel(item["id"])
    assert cancelled["status"] == "cancelled"
    assert cancelled["is_enabled"] is False
    assert await service.release_due() == 0


@pytest.mark.asyncio
async def test_run_now_makes_future_action_due(db_session):
    contact = Contact(whatsapp_id="2348044444444@c.us", contact_name="Peter")
    db_session.add(contact)
    await db_session.flush()
    service = ScheduledActionService(db_session)
    item = await service.create_whatsapp_message(
        target_reference="Peter",
        text="Please check the document.",
        scheduled_for=utcnow() + timedelta(days=2),
        timezone="Africa/Lagos",
    )

    run_now = await service.run_now(item["id"])
    assert run_now["status"] == "scheduled"
    assert await service.release_due() == 1
