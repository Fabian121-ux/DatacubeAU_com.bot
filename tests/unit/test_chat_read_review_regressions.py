from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.schema import AuditLog, Contact, Message
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext


UTC = timezone.utc


async def _read_chat(db_session, contact_name: str, **arguments):
    payload = {"contact": contact_name, "limit": 20, **arguments}
    return await ToolDispatcherService(db_session).execute(
        "chat.read",
        payload,
        context=ToolExecutionContext(permission="owner"),
    )


@pytest.mark.asyncio
async def test_chat_read_pages_past_linked_outbound_rows_to_fill_legacy_limit(db_session):
    amanda = Contact(
        whatsapp_id="2348055555701@c.us",
        display_name="Amanda Legacy Fill",
        contact_name="Amanda Legacy Fill",
    )
    db_session.add(amanda)
    await db_session.flush()

    db_session.add(
        Message(
            contact_id=amanda.id,
            chat_id=amanda.whatsapp_id,
            chat_type="dm",
            direction="outbound",
            message_text="older delivered legacy message",
            normalized_text="older delivered legacy message",
            message_type="text",
            created_at=datetime(2026, 8, 25, 1, 0, tzinfo=UTC),
        )
    )
    for index in range(120):
        db_session.add(
            Message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                chat_type="dm",
                direction="outbound",
                message_text=f"linked projection {index}",
                normalized_text=f"linked projection {index}",
                message_type="text",
                raw_payload_json={"outbound_queue_id": 10_000 + index},
                created_at=datetime(2026, 8, 25, 2, 0, index % 60, tzinfo=UTC),
            )
        )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Legacy Fill", limit=1)

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "older delivered legacy message"


@pytest.mark.asyncio
async def test_chat_read_uses_delivery_snapshot_after_queue_row_is_deleted(db_session):
    amanda = Contact(
        whatsapp_id="2348055555702@c.us",
        display_name="Amanda Deleted Queue",
        contact_name="Amanda Deleted Queue",
    )
    db_session.add(amanda)
    await db_session.flush()

    delivered_at = datetime(2026, 8, 25, 3, 0, tzinfo=UTC)
    db_session.add(
        AuditLog(
            action="outbound_queue_sent",
            entity_type="outbound_queue",
            entity_id="999999",
            details_json={
                "chat_id": amanda.whatsapp_id,
                "delivery_snapshot": {
                    "text": "scheduled message survives queue cleanup",
                    "message_type": "text",
                },
            },
            created_at=delivered_at,
        )
    )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Deleted Queue")

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "scheduled message survives queue cleanup"
    assert messages[0]["created_at"] == delivered_at
    assert messages[0]["delivery_status"] == "sent"


@pytest.mark.asyncio
async def test_chat_read_applies_delivery_time_window_to_audit_candidates(db_session):
    amanda = Contact(
        whatsapp_id="2348055555703@c.us",
        display_name="Amanda Audit Window",
        contact_name="Amanda Audit Window",
    )
    db_session.add(amanda)
    await db_session.flush()

    for queue_id, hour, text in (
        (7001, 1, "before window"),
        (7002, 3, "inside window"),
        (7003, 5, "after window"),
    ):
        db_session.add(
            AuditLog(
                action="outbound_queue_sent",
                entity_type="outbound_queue",
                entity_id=str(queue_id),
                details_json={
                    "chat_id": amanda.whatsapp_id,
                    "delivery_snapshot": {"text": text, "message_type": "text"},
                },
                created_at=datetime(2026, 8, 25, hour, 0, tzinfo=UTC),
            )
        )
    await db_session.flush()

    result = await _read_chat(
        db_session,
        "Amanda Audit Window",
        after="2026-08-25T02:00:00+00:00",
        before="2026-08-25T04:00:00+00:00",
    )

    assert [item["text"] for item in result["result"]["messages"]] == ["inside window"]
