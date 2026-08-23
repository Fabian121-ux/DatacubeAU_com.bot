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
