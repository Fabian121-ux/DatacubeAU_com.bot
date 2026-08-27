from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, text

import pytest

from app.config import settings
from app.models.schema import AuditLog, OutboundMessage
from app.utils.time import utcnow
from app.workers.background_workers import (
    _block_scrubbed_view_once_resend,
    _delivery_snapshot,
    _expire_stale_view_once_capability,
    _finalize_view_once_delivery_success,
    _mark_delivery_failed,
    _waha_response_for_audit,
)


OWNER_ID = "2348000000001@c.us"


def _media_url(source_id: str) -> str:
    return settings.waha_service_url.rstrip("/") + f"/api/files/{source_id}.jpg"


async def _insert_metadata(db_session, source_id: str) -> None:
    await db_session.execute(
        text("DELETE FROM view_once_media_metadata WHERE source_message_id = :source_id"),
        {"source_id": source_id},
    )
    await db_session.execute(
        text(
            """
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


def test_view_once_waha_audit_response_redacts_nested_media_capabilities():
    source_id = "VV-AUDIT-REDACTION"
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id),
        media_type="image",
        media_caption="private view-once",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    private_url = _media_url("WAHA-RESPONSE-CAPABILITY")
    response = {
        "id": "WAHA-DELIVERY-123",
        "status": "sent",
        "source": "api",
        "media": {
            "url": private_url,
            "mimetype": "image/jpeg",
            "base64": "should-not-be-retained",
        },
        "message": {"body": "private view-once", "file": {"url": private_url}},
    }

    audit_response = _waha_response_for_audit(queued, response)

    assert audit_response == {
        "redacted": True,
        "response_type": "dict",
        "id": "WAHA-DELIVERY-123",
        "status": "sent",
        "source": "api",
    }
    serialized = str(audit_response)
    assert private_url not in serialized
    assert "base64" not in serialized
    assert "private view-once" not in serialized


def test_non_view_once_waha_audit_response_preserves_existing_behavior():
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="ordinary",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={},
        updated_at=utcnow(),
    )
    response = {"id": "ordinary-response", "status": "sent"}

    assert _waha_response_for_audit(queued, response) is response


@pytest.mark.asyncio
async def test_successful_view_once_delivery_finalization_marks_returned_and_clears_private_url(db_session):
    source_id = "VV-DELIVERY-SUCCESS"
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

    delivery_snapshot = _delivery_snapshot(queued)
    queued.status = "sent"
    await _finalize_view_once_delivery_success(db_session, queued, delivery_snapshot)
    await db_session.commit()

    assert queued.status == "sent"
    assert queued.media_url is None
    assert queued.formatting_json["resendable"] is False
    assert delivery_snapshot == {
        "text": f"View-once source {source_id}",
        "message_type": "image",
    }

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
    assert queued.formatting_json["resendable"] is False
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
    assert queued.formatting_json.get("resendable") is not False
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


@pytest.mark.asyncio
async def test_expired_pending_view_once_capability_is_scrubbed_before_transport(db_session):
    source_id = "VV-EXPIRED-PENDING"
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
        formatting_json={
            "source": "view_once_command",
            "source_message_id": source_id,
            "capability_expires_at": (utcnow() - timedelta(seconds=1)).isoformat(),
        },
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    expired = await _expire_stale_view_once_capability(db_session, queued)

    assert expired is True
    assert queued.status == "failed"
    assert queued.media_url is None
    assert queued.formatting_json["resendable"] is False
    assert "expired" in queued.error_message.lower()
    lifecycle = (
        await db_session.execute(
            text(
                """
                SELECT capability_state, transport_available
                FROM view_once_media_metadata
                WHERE source_message_id = :source_id
                """
            ),
            {"source_id": source_id},
        )
    ).mappings().one()
    assert lifecycle["capability_state"] == "unavailable"
    assert lifecycle["transport_available"] is False


@pytest.mark.asyncio
async def test_late_duplicate_failure_cannot_regress_successful_view_once_lifecycle(db_session):
    source_id = "VV-DUPLICATE-OUTCOME"
    await _insert_metadata(db_session, source_id)

    successful = OutboundMessage(
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
    failed_duplicate = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=_media_url(source_id + "-duplicate"),
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="sending",
        retry_count=3,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    db_session.add_all([successful, failed_duplicate])
    await db_session.flush()

    await _finalize_view_once_delivery_success(db_session, successful, _delivery_snapshot(successful))
    await db_session.commit()
    await _mark_delivery_failed(db_session, failed_duplicate, "late duplicate failure")

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


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_status", ["sent", "failed"])
async def test_scrubbed_view_once_media_is_non_resendable_before_any_transport_send(db_session, terminal_status):
    source_id = f"VV-RESEND-BLOCKED-{terminal_status.upper()}"
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=None,
        media_type="image",
        media_caption=f"View-once source {source_id}",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={
            "source": "view_once_command",
            "source_message_id": source_id,
            "resendable": False,
        },
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    queued.status = terminal_status
    await db_session.flush()
    queued.status = "sending"

    blocked = await _block_scrubbed_view_once_resend(db_session, queued)

    assert blocked is True
    assert queued.status == "failed"
    assert queued.media_url is None
    assert queued.formatting_json["resendable"] is False
    assert "no longer available for resend" in queued.error_message

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_resend_blocked")
            .where(AuditLog.entity_id == source_id)
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert audit.details_json["outbound_queue_id"] == queued.id
    assert "media_url" not in str(audit.details_json).lower()
