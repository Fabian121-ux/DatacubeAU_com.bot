from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.schema import Contact, Message, OutboundMessage
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext


UTC = timezone.utc


def _sent_outbound(
    *,
    chat_id: str,
    text: str,
    updated_at: datetime,
    media_type: str | None = None,
    media_caption: str | None = None,
) -> OutboundMessage:
    return OutboundMessage(
        chat_id=chat_id,
        message_text=text,
        media_type=media_type,
        media_caption=media_caption,
        status="sent",
        retry_count=0,
        max_retries=3,
        next_attempt_at=updated_at,
        created_at=updated_at,
        updated_at=updated_at,
    )


@pytest.mark.asyncio
async def test_chat_read_excludes_sent_group_queue_rows_from_contact_dm_history(db_session):
    amanda = Contact(
        whatsapp_id="2348055555577@c.us",
        display_name="Amanda Group Scope",
        contact_name="Amanda Group Scope",
        chat_id="120363000000000777@g.us",
    )
    db_session.add(amanda)
    await db_session.flush()

    db_session.add_all(
        [
            _sent_outbound(
                chat_id=amanda.whatsapp_id,
                text="direct message delivered to Amanda",
                updated_at=datetime(2026, 8, 25, 0, 1, tzinfo=UTC),
            ),
            _sent_outbound(
                chat_id=amanda.chat_id,
                text="group broadcast must not appear in Amanda DM history",
                updated_at=datetime(2026, 8, 25, 0, 2, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "chat.read",
        {"contact": "Amanda Group Scope", "limit": 20},
        context=ToolExecutionContext(permission="owner"),
    )

    texts = [item["text"] for item in result["result"]["messages"]]
    assert texts == ["direct message delivered to Amanda"]
    assert "group broadcast must not appear in Amanda DM history" not in texts


@pytest.mark.asyncio
async def test_chat_read_returns_media_caption_that_waha_actually_delivered(db_session):
    amanda = Contact(
        whatsapp_id="2348055555588@c.us",
        display_name="Amanda Media",
        contact_name="Amanda Media",
    )
    db_session.add(amanda)
    await db_session.flush()

    media = _sent_outbound(
        chat_id=amanda.whatsapp_id,
        text="formatted search answer that was not used as the media caption",
        media_type="image",
        media_caption="Giphy: celebration",
        updated_at=datetime(2026, 8, 25, 0, 3, tzinfo=UTC),
    )
    db_session.add(media)
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "chat.read",
        {"contact": "Amanda Media", "limit": 20},
        context=ToolExecutionContext(permission="owner"),
    )

    messages = result["result"]["messages"]
    assert len(messages) == 1
    assert messages[0]["message_type"] == "image"
    assert messages[0]["text"] == "Giphy: celebration"


def test_chat_read_sort_key_preserves_numeric_message_order_for_equal_timestamps():
    created_at = datetime(2026, 8, 25, 0, 4, tzinfo=UTC)
    items = [
        {
            "id": 10,
            "source": "message",
            "direction": "outbound",
            "message_type": "text",
            "text": "second",
            "created_at": created_at,
        },
        {
            "id": 9,
            "source": "message",
            "direction": "inbound",
            "message_type": "text",
            "text": "first",
            "created_at": created_at,
        },
    ]

    items.sort(key=ToolDispatcherService._chat_message_sort_key)

    assert [item["id"] for item in items] == [9, 10]
