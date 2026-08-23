from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import delete, select

from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, Message, OutboundMessage
from app.services.conversation_handback_service import ConversationHandbackService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.utils.time import utcnow


@pytest.mark.asyncio
async def test_owner_resume_generates_private_handback_once(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(delete(Message))
    await db_session.execute(delete(AuditLog))
    await db_session.commit()

    now = utcnow()
    chat_id = "15550001101@c.us"
    takeover = ConversationTakeover(
        chat_id=chat_id,
        state="zina_assisting",
        auto_assist_enabled=True,
        inactivity_seconds=120,
        pending_since=now - timedelta(minutes=4),
        assisting_since=now - timedelta(minutes=3),
        handoff_sent_at=now - timedelta(minutes=3),
        updated_at=now - timedelta(minutes=3),
    )
    db_session.add(takeover)
    db_session.add_all(
        [
            Message(
                chat_id=chat_id,
                chat_type="dm",
                direction="inbound",
                message_text="Can Fabian confirm the meeting time?",
                normalized_text="can fabian confirm the meeting time",
                message_type="text",
                created_at=now - timedelta(minutes=2, seconds=30),
            ),
            Message(
                chat_id=chat_id,
                chat_type="dm",
                direction="inbound",
                message_text="I can also do 4pm if that works.",
                normalized_text="i can also do 4pm if that works",
                message_type="text",
                created_at=now - timedelta(minutes=1),
            ),
        ]
    )
    db_session.add_all(
        [
            OutboundMessage(
                chat_id=chat_id,
                message_text="I'm Zina, Fabian's assistant.",
                status="sent",
                next_attempt_at=now - timedelta(minutes=3),
                created_at=now - timedelta(minutes=3),
                updated_at=now - timedelta(minutes=2, seconds=50),
                formatting_json={"source": "conversation_takeover"},
            ),
            OutboundMessage(
                chat_id=chat_id,
                message_text="I can help with the scheduling details.",
                status="sent",
                next_attempt_at=now - timedelta(minutes=2),
                created_at=now - timedelta(minutes=2),
                updated_at=now - timedelta(minutes=1, seconds=50),
            ),
        ]
    )
    await db_session.commit()

    assert await ConversationTakeoverService(db_session).record_owner_reply(chat_id=chat_id) is True
    handback_service = ConversationHandbackService(db_session)
    summary = await handback_service.generate_if_needed(chat_id=chat_id)
    await db_session.commit()

    assert summary is not None
    assert summary["contact_messages"] == 2
    assert summary["zina_messages_sent"] == 2
    assert summary["zina_messages_pending"] == 0
    assert summary["latest_contact_message"] == "I can also do 4pm if that works."
    assert summary["recent_questions_to_review"] == ["Can Fabian confirm the meeting time?"]
    assert "2 contact message(s)" in summary["summary_text"]
    assert "Zina sent 2 WhatsApp message(s)" in summary["summary_text"]

    stored = await handback_service.get_latest(chat_id=chat_id)
    assert stored == summary

    generated_again = await handback_service.generate_if_needed(chat_id=chat_id)
    await db_session.commit()
    assert generated_again == summary

    audit_rows = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "conversation_handback_summary_generated")
        )
    ).scalars().all()
    assert len(audit_rows) == 1


@pytest.mark.asyncio
async def test_owner_reply_without_zina_assistance_does_not_generate_handback(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(AuditLog))
    await db_session.commit()

    now = utcnow()
    chat_id = "15550001102@c.us"
    db_session.add(
        ConversationTakeover(
            chat_id=chat_id,
            state="waiting_for_fabian",
            auto_assist_enabled=True,
            inactivity_seconds=120,
            pending_since=now - timedelta(seconds=30),
            takeover_due_at=now + timedelta(seconds=90),
            updated_at=now,
        )
    )
    await db_session.commit()

    assert await ConversationTakeoverService(db_session).record_owner_reply(chat_id=chat_id) is True
    summary = await ConversationHandbackService(db_session).generate_if_needed(chat_id=chat_id)
    await db_session.commit()

    assert summary is None
    assert await ConversationHandbackService(db_session).get_latest(chat_id=chat_id) is None
