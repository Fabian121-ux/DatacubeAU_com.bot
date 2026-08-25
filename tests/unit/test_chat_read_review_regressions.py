from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.schema import AuditLog, Contact, Message, OutboundMessage
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
async def test_chat_read_filters_successful_queue_rows_before_candidate_limit(db_session):
    amanda = Contact(
        whatsapp_id="2348055555704@c.us",
        display_name="Amanda Queue Success",
        contact_name="Amanda Queue Success",
    )
    db_session.add(amanda)
    await db_session.flush()

    base = datetime(2026, 8, 25, 1, 0, tzinfo=UTC)
    db_session.add(
        OutboundMessage(
            chat_id=amanda.whatsapp_id,
            message_text="older successful delivery",
            status="sent",
            retry_count=0,
            max_retries=3,
            next_attempt_at=base,
            created_at=base,
            updated_at=base,
        )
    )
    for index in range(120):
        created_at = base + timedelta(minutes=index + 1)
        db_session.add(
            OutboundMessage(
                chat_id=amanda.whatsapp_id,
                message_text=f"newer failed row {index}",
                status="failed",
                retry_count=3,
                max_retries=3,
                next_attempt_at=created_at,
                created_at=created_at,
                updated_at=created_at,
            )
        )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Queue Success", limit=1)

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "older successful delivery"
    assert messages[0]["delivery_status"] == "sent"


@pytest.mark.asyncio
async def test_legacy_outbound_projection_scan_stops_at_candidate_budget(db_session):
    amanda = Contact(
        whatsapp_id="2348055555705@c.us",
        display_name="Amanda Bounded Projection Scan",
        contact_name="Amanda Bounded Projection Scan",
    )
    db_session.add(amanda)
    await db_session.flush()

    base = datetime(2026, 8, 25, 1, 0, tzinfo=UTC)
    db_session.add(
        Message(
            contact_id=amanda.id,
            chat_id=amanda.whatsapp_id,
            chat_type="dm",
            direction="outbound",
            message_text="legacy row beyond bounded scan",
            normalized_text="legacy row beyond bounded scan",
            message_type="text",
            created_at=base,
        )
    )
    for index in range(850):
        db_session.add(
            Message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                chat_type="dm",
                direction="outbound",
                message_text=f"linked projection {index}",
                normalized_text=f"linked projection {index}",
                message_type="text",
                raw_payload_json={"outbound_queue_id": 20_000 + index},
                created_at=base + timedelta(seconds=index + 1),
            )
        )
    await db_session.flush()

    rows, linked = await ToolDispatcherService(db_session)._fetch_legacy_outbound_rows(
        scope_conditions=[Message.contact_id == amanda.id],
        limit=1,
        after=None,
        before=None,
    )

    assert rows == []
    assert len(linked) == 200


@pytest.mark.asyncio
async def test_chat_read_keeps_queue_context_for_audited_resend_in_pending_state(db_session):
    amanda = Contact(
        whatsapp_id="2348055555706@c.us",
        display_name="Amanda Audited Resend",
        contact_name="Amanda Audited Resend",
    )
    db_session.add(amanda)
    await db_session.flush()

    delivered_at = datetime(2026, 8, 25, 2, 0, tzinfo=UTC)
    queue_row = OutboundMessage(
        chat_id=amanda.whatsapp_id,
        message_text="message delivered before resend",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=delivered_at + timedelta(hours=1),
        created_at=delivered_at - timedelta(minutes=5),
        updated_at=delivered_at + timedelta(hours=1),
    )
    db_session.add(queue_row)
    await db_session.flush()
    db_session.add(
        AuditLog(
            action="outbound_queue_sent",
            entity_type="outbound_queue",
            entity_id=str(queue_row.id),
            details_json={"chat_id": amanda.whatsapp_id},
            created_at=delivered_at,
        )
    )
    await db_session.flush()

    result = await _read_chat(db_session, "Amanda Audited Resend", limit=1)

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "message delivered before resend"
    assert messages[0]["created_at"] == delivered_at


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
