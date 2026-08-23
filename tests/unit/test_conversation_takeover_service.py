from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import delete, select

from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import OutboundMessage
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.utils.time import utcnow


@pytest.mark.asyncio
async def test_takeover_waits_then_owner_reply_cancels(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    scheduled = await service.schedule_if_eligible(
        chat_id="15550001001@c.us",
        chat_type="dm",
        message_id="msg-1",
        router_replied=False,
    )
    assert scheduled is True

    row = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001001@c.us")
        )
    ).scalar_one()
    assert row.state == "waiting_for_fabian"
    assert row.inactivity_seconds == 120
    assert row.takeover_due_at is not None
    assert row.pending_since is not None
    assert row.takeover_due_at >= row.pending_since + timedelta(seconds=119)

    cancelled = await service.record_owner_reply(chat_id="15550001001@c.us")
    await db_session.commit()
    assert cancelled is True
    assert row.state == "fabian_resumed"
    assert row.takeover_due_at is None

    claimed = await service.claim_due()
    assert claimed == 0
    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.chat_id == "15550001001@c.us")
        )
    ).scalars().all()
    assert queued == []


@pytest.mark.asyncio
async def test_due_takeover_queues_transparent_handoff_once(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    await service.schedule_if_eligible(
        chat_id="15550001002@c.us",
        chat_type="dm",
        message_id="msg-2",
        router_replied=False,
    )
    row = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001002@c.us")
        )
    ).scalar_one()
    row.takeover_due_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    claimed = await service.claim_due()
    await db_session.commit()
    assert claimed == 1
    assert row.state == "zina_assisting"
    assert row.assisting_since is not None
    assert row.handoff_sent_at is not None

    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.chat_id == "15550001002@c.us")
        )
    ).scalars().all()
    assert len(queued) == 1
    assert "I'm Zina" in queued[0].message_text
    assert "Fabian is busy" in queued[0].message_text
    assert queued[0].formatting_json["transparent_assistant_handoff"] is True

    claimed_again = await service.claim_due()
    await db_session.commit()
    assert claimed_again == 0
    queued_again = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.chat_id == "15550001002@c.us")
        )
    ).scalars().all()
    assert len(queued_again) == 1


@pytest.mark.asyncio
async def test_takeover_not_scheduled_when_router_already_replied(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.commit()

    scheduled = await ConversationTakeoverService(db_session).schedule_if_eligible(
        chat_id="15550001003@c.us",
        chat_type="dm",
        message_id="msg-3",
        router_replied=True,
    )
    assert scheduled is False
    rows = (await db_session.execute(select(ConversationTakeover))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_chat_control_can_disable_pending_takeover(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    await service.schedule_if_eligible(
        chat_id="15550001004@c.us",
        chat_type="dm",
        message_id="msg-4",
        router_replied=False,
    )

    control = await service.set_chat_control(
        chat_id="15550001004@c.us",
        auto_assist_enabled=False,
        inactivity_seconds=90,
    )
    await db_session.commit()

    assert control["auto_assist_enabled"] is False
    assert control["state"] == "do_not_auto_assist"
    assert control["inactivity_seconds"] == 90

    row = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001004@c.us")
        )
    ).scalar_one()
    assert row.takeover_due_at is None
    assert row.pending_since is None

    claimed = await service.claim_due()
    assert claimed == 0


@pytest.mark.asyncio
async def test_chat_control_reenable_preserves_custom_threshold(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    disabled = await service.set_chat_control(
        chat_id="15550001005@c.us",
        auto_assist_enabled=False,
        inactivity_seconds=45,
    )
    assert disabled["state"] == "do_not_auto_assist"

    enabled = await service.set_chat_control(
        chat_id="15550001005@c.us",
        auto_assist_enabled=True,
        inactivity_seconds=45,
    )
    assert enabled["state"] == "fabian_active"
    assert enabled["auto_assist_enabled"] is True
    assert enabled["inactivity_seconds"] == 45

    scheduled = await service.schedule_if_eligible(
        chat_id="15550001005@c.us",
        chat_type="dm",
        message_id="msg-5",
        router_replied=False,
    )
    assert scheduled is True
    row = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001005@c.us")
        )
    ).scalar_one()
    assert row.inactivity_seconds == 45
    assert row.takeover_due_at >= row.pending_since + timedelta(seconds=44)


@pytest.mark.asyncio
async def test_human_first_policy_is_persisted_and_exposed(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    control = await service.set_chat_control(
        chat_id="15550001006@c.us",
        auto_assist_enabled=True,
        inactivity_seconds=75,
        wait_for_fabian_first=True,
    )
    await db_session.commit()

    assert control["wait_for_fabian_first"] is True
    assert control["inactivity_seconds"] == 75
    assert await service.should_wait_for_fabian_first(chat_id="15550001006@c.us") is True

    fetched = await service.get_chat_control(chat_id="15550001006@c.us")
    assert fetched["wait_for_fabian_first"] is True


@pytest.mark.asyncio
async def test_owner_reply_cancels_prepared_human_first_reply(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    await service.set_chat_control(
        chat_id="15550001007@c.us",
        auto_assist_enabled=True,
        inactivity_seconds=60,
        wait_for_fabian_first=True,
    )
    prepared = OutboundMessage(
        chat_id="15550001007@c.us",
        message_text="Prepared Zina answer",
        status="deferred",
        next_attempt_at=utcnow(),
        formatting_json={"delivery_policy": "wait_for_fabian_first"},
    )
    db_session.add(prepared)
    await db_session.flush()

    scheduled = await service.schedule_if_eligible(
        chat_id="15550001007@c.us",
        chat_type="dm",
        message_id="msg-7",
        router_replied=True,
        reply_deferred=True,
        outbound_queue_id=prepared.id,
    )
    assert scheduled is True
    assert prepared.status == "deferred"

    cancelled = await service.record_owner_reply(chat_id="15550001007@c.us")
    await db_session.commit()

    assert cancelled is True
    assert prepared.status == "cancelled"
    assert prepared.error_message == "owner_message_detected"
    assert await service.claim_due() == 0


@pytest.mark.asyncio
async def test_due_human_first_takeover_releases_handoff_before_prepared_reply(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    await service.set_chat_control(
        chat_id="15550001008@c.us",
        auto_assist_enabled=True,
        inactivity_seconds=30,
        wait_for_fabian_first=True,
    )
    prepared = OutboundMessage(
        chat_id="15550001008@c.us",
        message_text="Prepared intelligent response",
        status="deferred",
        next_attempt_at=utcnow(),
        formatting_json={"delivery_policy": "wait_for_fabian_first"},
    )
    db_session.add(prepared)
    await db_session.flush()

    assert await service.schedule_if_eligible(
        chat_id="15550001008@c.us",
        chat_type="dm",
        message_id="msg-8",
        router_replied=True,
        reply_deferred=True,
        outbound_queue_id=prepared.id,
    ) is True
    takeover = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001008@c.us")
        )
    ).scalar_one()
    takeover.takeover_due_at = utcnow() - timedelta(seconds=1)
    await db_session.commit()

    assert await service.claim_due() == 1
    await db_session.commit()

    queued = (
        await db_session.execute(
            select(OutboundMessage)
            .where(OutboundMessage.chat_id == "15550001008@c.us")
            .order_by(OutboundMessage.next_attempt_at, OutboundMessage.id)
        )
    ).scalars().all()
    assert len(queued) == 2
    assert queued[0].formatting_json["transparent_assistant_handoff"] is True
    assert queued[1].id == prepared.id
    assert queued[1].status == "pending"
    assert queued[1].formatting_json["released_by_conversation_takeover"] is True
    assert queued[1].next_attempt_at > queued[0].next_attempt_at


@pytest.mark.asyncio
async def test_newer_deferred_reply_supersedes_older_prepared_reply(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.commit()

    service = ConversationTakeoverService(db_session)
    await service.set_chat_control(
        chat_id="15550001009@c.us",
        auto_assist_enabled=True,
        inactivity_seconds=30,
        wait_for_fabian_first=True,
    )
    first = OutboundMessage(
        chat_id="15550001009@c.us",
        message_text="Older prepared answer",
        status="deferred",
        next_attempt_at=utcnow(),
    )
    db_session.add(first)
    await db_session.flush()
    assert await service.schedule_if_eligible(
        chat_id="15550001009@c.us",
        chat_type="dm",
        message_id="msg-9a",
        router_replied=True,
        reply_deferred=True,
        outbound_queue_id=first.id,
    ) is True

    second = OutboundMessage(
        chat_id="15550001009@c.us",
        message_text="Latest prepared answer",
        status="deferred",
        next_attempt_at=utcnow(),
    )
    db_session.add(second)
    await db_session.flush()
    assert await service.schedule_if_eligible(
        chat_id="15550001009@c.us",
        chat_type="dm",
        message_id="msg-9b",
        router_replied=True,
        reply_deferred=True,
        outbound_queue_id=second.id,
    ) is True
    await db_session.commit()

    assert first.status == "cancelled"
    assert first.error_message == "superseded_by_newer_inbound"
    assert second.status == "deferred"
    takeover = (
        await db_session.execute(
            select(ConversationTakeover).where(ConversationTakeover.chat_id == "15550001009@c.us")
        )
    ).scalar_one()
    assert takeover.last_inbound_message_id == "msg-9b"
    assert takeover.metadata_json["deferred_outbound_queue_id"] == second.id
