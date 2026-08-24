from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.models.schema import AuditLog, Contact, Message
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext


UTC = timezone.utc


def _message(
    *,
    contact_id: int | None,
    chat_id: str,
    text: str,
    created_at: datetime,
    direction: str = "inbound",
    chat_type: str = "dm",
) -> Message:
    return Message(
        contact_id=contact_id,
        chat_id=chat_id,
        chat_type=chat_type,
        direction=direction,
        message_text=text,
        normalized_text=text.lower(),
        message_type="text",
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_chat_read_returns_bounded_chronological_dm_history_for_resolved_contact(db_session):
    amanda = Contact(
        whatsapp_id="2348055555555@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        chat_id="2348055555555@c.us",
    )
    other = Contact(
        whatsapp_id="2348066666666@c.us",
        display_name="Christa Other",
        contact_name="Christa Other",
    )
    db_session.add_all([amanda, other])
    await db_session.flush()

    db_session.add_all(
        [
            _message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                text="old message outside limit",
                created_at=datetime(2026, 8, 24, 7, 0, tzinfo=UTC),
            ),
            _message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                text="Amanda asked about the proposal",
                created_at=datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
            ),
            _message(
                contact_id=None,
                chat_id=amanda.whatsapp_id,
                text="Fabian replied that it is ready",
                created_at=datetime(2026, 8, 24, 8, 5, tzinfo=UTC),
                direction="outbound",
            ),
            _message(
                contact_id=other.id,
                chat_id=other.whatsapp_id,
                text="private message from another contact",
                created_at=datetime(2026, 8, 24, 8, 6, tzinfo=UTC),
            ),
            _message(
                contact_id=amanda.id,
                chat_id="120363000000000000@g.us",
                text="Amanda group message must not leak into DM history",
                created_at=datetime(2026, 8, 24, 8, 7, tzinfo=UTC),
                chat_type="group",
            ),
        ]
    )
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "chat.read",
        {"contact": "Amanda Christabel", "limit": 2},
        context=ToolExecutionContext(permission="owner"),
    )

    payload = result["result"]
    assert result["handler_target"] == "conversation.read"
    assert payload["contact_id"] == amanda.id
    assert payload["message_count"] == 2
    assert [item["text"] for item in payload["messages"]] == [
        "Amanda asked about the proposal",
        "Fabian replied that it is ready",
    ]
    assert [item["direction"] for item in payload["messages"]] == ["inbound", "outbound"]
    assert all("raw_payload_json" not in item for item in payload["messages"])

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "tool_execution_accepted")
            .where(AuditLog.entity_id == str(amanda.id))
            .where(AuditLog.details_json["tool"].as_string() == "chat.read")
        )
    ).scalar_one()
    assert "proposal" not in str(audit.details_json).lower()


@pytest.mark.asyncio
async def test_chat_read_honors_timezone_aware_window(db_session):
    amanda = Contact(
        whatsapp_id="2348077777777@c.us",
        display_name="Amanda Window",
        contact_name="Amanda Window",
    )
    db_session.add(amanda)
    await db_session.flush()
    db_session.add_all(
        [
            _message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                text="before window",
                created_at=datetime(2026, 8, 24, 7, 59, tzinfo=UTC),
            ),
            _message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                text="inside window",
                created_at=datetime(2026, 8, 24, 8, 30, tzinfo=UTC),
            ),
            _message(
                contact_id=amanda.id,
                chat_id=amanda.whatsapp_id,
                text="after window",
                created_at=datetime(2026, 8, 24, 9, 1, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "chat.read",
        {
            "contact": "Amanda Window",
            "after": "2026-08-24T08:00:00+00:00",
            "before": "2026-08-24T09:00:00+00:00",
            "limit": 20,
        },
        context=ToolExecutionContext(permission="owner"),
    )
    assert [item["text"] for item in result["result"]["messages"]] == ["inside window"]

    with pytest.raises(ValueError, match="after must not be later"):
        await ToolDispatcherService(db_session).execute(
            "chat.read",
            {
                "contact": "Amanda Window",
                "after": "2026-08-24T10:00:00+00:00",
                "before": "2026-08-24T09:00:00+00:00",
            },
            context=ToolExecutionContext(permission="owner"),
        )

    with pytest.raises(ValueError, match="timezone offset"):
        await ToolDispatcherService(db_session).execute(
            "chat.read",
            {"contact": "Amanda Window", "after": "2026-08-24T08:00:00"},
            context=ToolExecutionContext(permission="owner"),
        )


@pytest.mark.asyncio
async def test_chat_read_refuses_ambiguous_contact(db_session):
    db_session.add_all(
        [
            Contact(whatsapp_id="2348088888801@c.us", display_name="Amanda James", contact_name="Amanda James"),
            Contact(whatsapp_id="2348088888802@c.us", display_name="Amanda Jones", contact_name="Amanda Jones"),
        ]
    )
    await db_session.flush()

    with pytest.raises(ValueError, match="chat target contact is ambiguous"):
        await ToolDispatcherService(db_session).execute(
            "chat.read",
            {"contact": "Amanda", "limit": 20},
            context=ToolExecutionContext(permission="owner"),
        )
