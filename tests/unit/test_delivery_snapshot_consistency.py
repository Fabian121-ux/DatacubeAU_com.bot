from datetime import datetime, timezone

from app.models.schema import OutboundMessage
from app.services.tool_dispatcher_service import ToolDispatcherService
from app.workers.background_workers import _delivery_snapshot


def _queue_row(*, media_url=None, media_type=None, media_caption=None, message_text="fallback"):
    row = OutboundMessage(
        chat_id="2348000000000@c.us",
        message_text=message_text,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        status="sent",
        retry_count=0,
        max_retries=3,
        next_attempt_at=datetime.now(timezone.utc),
    )
    row.id = 42
    row.updated_at = datetime.now(timezone.utc)
    return row


def test_delivery_snapshot_uses_media_url_as_actual_send_condition():
    row = _queue_row(
        media_url="https://example.test/photo.jpg",
        media_type=None,
        media_caption="caption actually sent",
        message_text="internal fallback",
    )

    assert _delivery_snapshot(row) == {
        "text": "caption actually sent",
        "message_type": "image",
    }
    projected = ToolDispatcherService._outbound_queue_chat_message_dict(row)
    assert projected["text"] == "caption actually sent"
    assert projected["message_type"] == "image"


def test_delivery_snapshot_ignores_media_metadata_when_worker_sends_text():
    row = _queue_row(
        media_url=None,
        media_type="image",
        media_caption="unused caption",
        message_text="text actually sent",
    )

    assert _delivery_snapshot(row) == {
        "text": "text actually sent",
        "message_type": "text",
    }
    projected = ToolDispatcherService._outbound_queue_chat_message_dict(row)
    assert projected["text"] == "text actually sent"
    assert projected["message_type"] == "text"
