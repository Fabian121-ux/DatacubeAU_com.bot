from __future__ import annotations

from sqlalchemy import select, text

import pytest

from app.config import settings
from app.models.schema import AuditLog, OutboundMessage
from app.utils.time import utcnow
from app.workers.background_workers import _deliver_due_outbound_messages, _mark_delivery_failed


OWNER_ID = "2348000000001@c.us"


class SuccessfulMediaClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    async def send_media(self, chat_id: str, *, media_url: str, caption: str | None = None):
        self.calls.append({"chat_id": chat_id, "media_url": media_url, "caption": caption or ""})
        return {"id": "WAHA-SENT-1"}

    async def send_text(self, chat_id: str, text: str):  # pragma: no cover - media path only
        raise AssertionError("view-once delivery must use the media branch")


def _media_url(source_id: str) -> str:
    return settings.waha_service_url.rstrip("/") + f"/api/files/{source_id}.jpg"


async def _insert_metadata(db_session, source_id: str) -> None:
    await db_session.execute(
        text(
            """
            DELETE FROM view_once_media_metadata WHERE source_message_id = :source_id;
            INSERT INTO view_once_media_metadata (
                source_message_id, source_chat_id, media_type, media_mime,
                capability_state, evidence_source, transport_available,
                retention_mode, metadata_json, first_observed_at, last_observed_at
            ) VALUES (
                :source_id, '2348000000002@c.us', 'image', 'image/jpeg',
                'available_from_transport', 'test', TRUE,
                'none', '{}'::jsonb, NOW(), NOW()
            )
            """
        ),
        {"source_id": source_id},
    )


@pytest.mark.asyncio
async def test_successful_view_once_delivery_marks_returned_only_after_waha_success_and_clears_private_url(db_session):
    source_id = "VV-DELIVERY-SUCCESS"
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id),
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.commit()
    queue_id = queued.id

    client = SuccessfulMediaClient()
    processed = await _deliver_due_outbound_messages(client)

    assert processed == 1
    assert len(client.calls) == 1
    assert client.calls[0]["media_url"] == _media_url(source_id)

    db_session.expire_all()
    stored = (
        await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == queue_id))
    ).scalar_one()
    assert stored.status == "sent"
    assert stored.media_url is None

    lifecycle = (
        await db_session.execute(
            text(
                """
                SELECT capability_state, transport_available, returned_to_owner_at
                FROM view_once_media_metadata
                WHERE source_message_id = :source_id
                """
            ),
            {"source_id": source_id},
        )
    ).mappings().one()
    assert lifecycle["capability_state"] == "returned_to_owner"
    assert lifecycle["transport_available"] is False
    assert lifecycle["returned_to_owner_at"] is not None

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_returned_to_owner")
            .where(AuditLog.entity_id == source_id)
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert "media_url" not in str(audit.details_json).lower()
    assert _media_url(source_id) not in str(audit.details_json)


@pytest.mark.asyncio
async def test_terminal_view_once_delivery_failure_clears_private_url_and_marks_unavailable(db_session):
    source_id = "VV-DELIVERY-FAILED"
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id),
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="sending",
        retry_count=3,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    await _mark_delivery_failed(db_session, queued, "synthetic terminal failure")

    assert queued.status == "failed"
    assert queued.media_url is None
    lifecycle = (
        await db_session.execute(
            text(
                """
                SELECT capability_state, transport_available, returned_to_owner_at
                FROM view_once_media_metadata
                WHERE source_message_id = :source_id
                """
            ),
            {"source_id": source_id},
        )
    ).mappings().one()
    assert lifecycle["capability_state"] == "unavailable"
    assert lifecycle["transport_available"] is False
    assert lifecycle["returned_to_owner_at"] is None


@pytest.mark.asyncio
async def test_retryable_view_once_failure_keeps_url_only_for_the_next_bounded_retry(db_session):
    source_id = "VV-DELIVERY-RETRY"
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id),
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    await _mark_delivery_failed(db_session, queued, "synthetic retryable failure")

    assert queued.status == "retrying"
    assert queued.media_url == _media_url(source_id)
    lifecycle = (
        await db_session.execute(
            text(
                """
                SELECT capability_state, transport_available, returned_to_owner_at
                FROM view_once_media_metadata
                WHERE source_message_id = :source_id
                """
            ),
            {"source_id": source_id},
        )
    ).mappings().one()
    assert lifecycle["capability_state"] == "available_from_transport"
    assert lifecycle["transport_available"] is True
    assert lifecycle["returned_to_owner_at"] is None
