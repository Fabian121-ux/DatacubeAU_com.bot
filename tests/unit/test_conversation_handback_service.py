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
    assert summary["contact_requests"] == ["Can Fabian confirm the meeting time?"]
    assert summary["zina_responses_sent"] == ["I can help with the scheduling details."]
    assert summary["explicit_time_references"] == [
        {
            "source": "contact",
            "message": "I can also do 4pm if that works.",
            "references": ["4pm"],
        }
    ]
    assert summary["zina_commitment_evidence"] == [
        {
            "message": "I can help with the scheduling details.",
            "delivery_status": "sent",
        }
    ]
    assert "Can Fabian confirm the meeting time?" in summary["needs_fabian_attention"]
    assert "2 contact message(s)" in summary["summary_text"]
    assert "Zina sent 2 WhatsApp message(s)" in summary["summary_text"]
    assert "What the contact wanted" in summary["summary_text"]

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
    assert audit_rows[0].details_json["contact_requests"] == ["Can Fabian confirm the meeting time?"]
    assert audit_rows[0].details_json["time_reference_count"] == 1
    assert audit_rows[0].details_json["commitment_evidence_count"] == 1


@pytest.mark.asyncio
async def test_handback_includes_message_that_started_waiting_window(db_session):
    await db_session.execute(delete(ConversationTakeover))
    await db_session.execute(delete(OutboundMessage))
    await db_session.execute(delete(Message))
    await db_session.execute(delete(AuditLog))
    await db_session.commit()

    now = utcnow()
    chat_id = "15550001103@c.us"
    waiting_started = now - timedelta(minutes=4)
    assisting_started = now - timedelta(minutes=2)
    db_session.add(
        ConversationTakeover(
            chat_id=chat_id,
            state="zina_assisting",
            auto_assist_enabled=True,
            inactivity_seconds=120,
            pending_since=waiting_started,
            assisting_since=assisting_started,
            handoff_sent_at=assisting_started,
            updated_at=assisting_started,
        )
    )
    db_session.add(
        AuditLog(
            action="conversation_takeover_waiting",
            entity_type="conversation_takeover",
            entity_id=chat_id,
            details_json={"chat_id": chat_id, "inactivity_seconds": 120},
            created_at=waiting_started,
        )
    )
    db_session.add_all(
        [
            Message(
                chat_id=chat_id,
                chat_type="dm",
                direction="inbound",
                message_text="Can Fabian send the proposal today?",
                normalized_text="can fabian send the proposal today",
                message_type="text",
                created_at=waiting_started + timedelta(seconds=1),
            ),
            Message(
                chat_id=chat_id,
                chat_type="dm",
                direction="inbound",
                message_text="Please let him know it is urgent.",
                normalized_text="please let him know it is urgent",
                message_type="text",
                created_at=assisting_started + timedelta(seconds=20),
            ),
        ]
    )
    db_session.add_all(
        [
            OutboundMessage(
                chat_id=chat_id,
                message_text="I'll let Fabian know you need the proposal today.",
                status="sent",
                next_attempt_at=assisting_started,
                created_at=assisting_started,
                updated_at=assisting_started + timedelta(seconds=15),
            ),
            OutboundMessage(
                chat_id=chat_id,
                message_text="A second reply is waiting.",
                status="deferred",
                next_attempt_at=now + timedelta(minutes=1),
                created_at=now - timedelta(seconds=20),
                updated_at=now - timedelta(seconds=10),
            ),
        ]
    )
    await db_session.commit()

    assert await ConversationTakeoverService(db_session).record_owner_reply(chat_id=chat_id) is True
    summary = await ConversationHandbackService(db_session).generate_if_needed(chat_id=chat_id)
    await db_session.commit()

    assert summary is not None
    assert summary["contact_messages"] == 2
    assert summary["window_start"] == waiting_started.isoformat()
    assert summary["recent_questions_to_review"] == ["Can Fabian send the proposal today?"]
    assert summary["latest_contact_message"] == "Please let him know it is urgent."
    assert summary["contact_requests"] == [
        "Can Fabian send the proposal today?",
        "Please let him know it is urgent.",
    ]
    assert summary["explicit_time_references"] == [
        {
            "source": "contact",
            "message": "Can Fabian send the proposal today?",
            "references": ["today"],
        },
        {
            "source": "zina",
            "message": "I'll let Fabian know you need the proposal today.",
            "delivery_status": "sent",
            "references": ["today"],
        },
    ]
    assert summary["zina_commitment_evidence"] == [
        {
            "message": "I'll let Fabian know you need the proposal today.",
            "delivery_status": "sent",
        }
    ]
    assert "Please let him know it is urgent." in summary["needs_fabian_attention"]
    assert "1 Zina message(s) are still pending delivery." in summary["needs_fabian_attention"]


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
