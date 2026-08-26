from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, Contact, OutboundMessage
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


async def _released_action_and_outbound(db_session, *, suffix: str):
    contact = Contact(whatsapp_id=f"23480555555{suffix}@c.us", contact_name=f"Delivery {suffix}")
    db_session.add(contact)
    await db_session.flush()
    service = ScheduledActionService(db_session)
    await service.create_whatsapp_message(
        target_reference=f"Delivery {suffix}",
        text="Delivery reconciliation test",
        scheduled_for=utcnow() - timedelta(seconds=1),
        timezone="Africa/Lagos",
        idempotency_key=f"delivery-reconciliation-{suffix}",
    )
    assert await service.release_due() == 1
    action = (
        await db_session.execute(
            select(ScheduledAction).where(ScheduledAction.idempotency_key == f"delivery-reconciliation-{suffix}")
        )
    ).scalar_one()
    outbound = await db_session.get(OutboundMessage, action.outbound_queue_id)
    return service, action, outbound


@pytest.mark.asyncio
async def test_successful_outbound_delivery_completes_scheduled_action(db_session):
    service, action, outbound = await _released_action_and_outbound(db_session, suffix="1")
    outbound.status = "sent"
    outbound.retry_count = 1
    outbound.error_message = None

    result = await service.reconcile_outbound_delivery(outbound)

    assert result["status"] == "completed"
    assert result["is_enabled"] is False
    assert result["retry_count"] == 1
    assert result["last_error"] is None
    assert result["metadata"]["delivery"]["status"] == "sent"
    assert result["metadata"]["delivery"]["completed_at"]
    audits = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "scheduled_action_completed",
                AuditLog.entity_id == str(action.id),
            )
        )
    ).scalars().all()
    assert len(audits) == 1

    await service.reconcile_outbound_delivery(outbound)
    audits = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "scheduled_action_completed",
                AuditLog.entity_id == str(action.id),
            )
        )
    ).scalars().all()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_retrying_outbound_delivery_keeps_action_queued_with_attempt_evidence(db_session):
    service, action, outbound = await _released_action_and_outbound(db_session, suffix="2")
    outbound.status = "retrying"
    outbound.retry_count = 2
    outbound.error_message = "temporary WAHA timeout"

    result = await service.reconcile_outbound_delivery(outbound)

    assert result["status"] == "queued"
    assert result["is_enabled"] is True
    assert result["retry_count"] == 2
    assert result["last_error"] == "temporary WAHA timeout"
    assert result["metadata"]["delivery"]["status"] == "retrying"
    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "scheduled_action_delivery_retrying",
                AuditLog.entity_id == str(action.id),
            )
        )
    ).scalar_one()
    assert audit.details_json["retry_count"] == 2


@pytest.mark.asyncio
async def test_terminal_outbound_failure_fails_and_disables_scheduled_action(db_session):
    service, action, outbound = await _released_action_and_outbound(db_session, suffix="3")
    outbound.status = "failed"
    outbound.retry_count = 4
    outbound.max_retries = 3
    outbound.error_message = "WAHA delivery exhausted retries"

    result = await service.reconcile_outbound_delivery(outbound)

    assert result["status"] == "failed"
    assert result["is_enabled"] is False
    assert result["retry_count"] == 4
    assert result["last_error"] == "WAHA delivery exhausted retries"
    assert result["metadata"]["delivery"]["status"] == "failed"
    assert result["metadata"]["delivery"]["failed_at"]
    audit = (
        await db_session.execute(
            select(AuditLog).where(
                AuditLog.action == "scheduled_action_delivery_failed",
                AuditLog.entity_id == str(action.id),
            )
        )
    ).scalar_one()
    assert audit.details_json["max_retries"] == 3
