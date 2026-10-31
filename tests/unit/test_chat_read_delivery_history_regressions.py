from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.schema import AuditLog, Contact, Message, OutboundMessage
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext


UTC = timezone.utc


async def _read_chat(db_session, contact_name: str):
    return await ToolDispatcherService(db_session).execute(
        "chat.read",
        {"contact": contact_name, "limit": 20},
        context=ToolExecutionContext(permission="owner"),
    )


@pytest.mark.asyncio
async def test_chat_read_preserves_each_successful_delivery_when_queue_row_is_resent(db_session):
    amanda = Contact(
        whatsapp_id="2348055555599@c.us",
        display_name="Amanda Resend",
        contact_name="Amanda Resend",
    )
    db_session.add(amanda)
    await db_session.flush()

    queue = OutboundMessage(
        chat_id=amanda.whatsapp_id,
        message_text="same message delivered twice",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=datetime(2026, 8, 25, 2, 30, tzinfo=UTC),
        created_at=datetime(2026, 8, 25, 2, 0, tzinfo=UTC),
        updated_at=datetime(2026, 8, 25, 2, 30, tzinfo=UTC),
    )
    db_session.add(queue)
    await db_session.flush()

    db_session.add_all(
        [
            AuditLog(
                action="outbound_queue_sent",
                entity_type="outbound_queue",
                entity_id=str(queue.id),
                details_json={"chat_id": amanda.whatsapp_id},
                created_at=datetime(2026, 8, 25, 2, 5, tzinfo=UTC),
            ),
            AuditLog(
                action="outbound_queue_sent",
                entity_type="outbound_queue",
                entity_id=str(queue.id),
                details_json={"chat_id": amanda.whatsapp_id},
                created_at=datetime(2026, 8, 25, 2, 20, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Resend")

    messages = result["result"]["messages"]
    assert [item["text"] for item in messages] == [
        "same message delivered twice",
        "same message delivered twice",
    ]
    assert [item["created_at"] for item in messages] == [
        datetime(2026, 8, 25, 2, 5, tzinfo=UTC),
        datetime(2026, 8, 25, 2, 20, tzinfo=UTC),
    ]
    assert all(":delivery:" in str(item["id"]) for item in messages)


@pytest.mark.asyncio
async def test_chat_read_includes_legacy_delivered_queue_status(db_session):
    amanda = Contact(
        whatsapp_id="2348055555600@c.us",
        display_name="Amanda Delivered",
        contact_name="Amanda Delivered",
    )
    db_session.add(amanda)
    await db_session.flush()

    delivered_at = datetime(2026, 8, 25, 2, 40, tzinfo=UTC)
    db_session.add(
        OutboundMessage(
            chat_id=amanda.whatsapp_id,
            message_text="legacy delivered status",
            status="delivered",
            retry_count=0,
            max_retries=3,
            next_attempt_at=delivered_at,
            created_at=delivered_at,
            updated_at=delivered_at,
        )
    )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Delivered")

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "legacy delivered status"
    assert messages[0]["delivery_status"] == "delivered"


@pytest.mark.asyncio
async def test_chat_read_excludes_status_and_newsletter_rows_mislabeled_as_dm(db_session):
    amanda = Contact(
        whatsapp_id="2348055555601@c.us",
        display_name="Amanda Broadcast",
        contact_name="Amanda Broadcast",
    )
    db_session.add(amanda)
    await db_session.flush()

    db_session.add_all(
        [
            Message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                chat_type="dm",
                direction="inbound",
                message_text="real private message",
                normalized_text="real private message",
                message_type="text",
                created_at=datetime(2026, 8, 25, 2, 50, tzinfo=UTC),
            ),
            Message(
                contact_id=amanda.id,
                chat_id="status@broadcast",
                chat_type="dm",
                direction="inbound",
                message_text="status content must not leak",
                normalized_text="status content must not leak",
                message_type="text",
                created_at=datetime(2026, 8, 25, 2, 51, tzinfo=UTC),
            ),
            Message(
                contact_id=amanda.id,
                chat_id="120363123456789@newsletter",
                chat_type="dm",
                direction="inbound",
                message_text="newsletter content must not leak",
                normalized_text="newsletter content must not leak",
                message_type="text",
                created_at=datetime(2026, 8, 25, 2, 52, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Broadcast")

    texts = [item["text"] for item in result["result"]["messages"]]
    assert texts == ["real private message"]
