from __future__ import annotations

from datetime import timedelta

import pytest

from app.config import settings
from app.models.schema import OutboundMessage
from app.utils.time import utcnow
from app.workers.background_workers import _mark_delivery_failed


OWNER_ID = "2348000000001@c.us"


def _media_url(source_id: str) -> str:
    return settings.waha_service_url.rstrip("/") + f"/api/files/{source_id}.jpg"


@pytest.mark.asyncio
async def test_view_once_retry_never_schedules_past_capability_expiry(db_session):
    source_id = "VV-RETRY-TTL-BOUND"
    expires_at = utcnow() + timedelta(minutes=1)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id),
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="sending",
        retry_count=2,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={
            "source": "view_once_command",
            "source_message_id": source_id,
            "capability_expires_at": expires_at.isoformat(),
        },
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    await _mark_delivery_failed(db_session, queued, "synthetic retryable failure")

    assert queued.status == "retrying"
    assert queued.media_url == _media_url(source_id)
    assert queued.next_attempt_at == expires_at
    assert queued.next_attempt_at <= expires_at
