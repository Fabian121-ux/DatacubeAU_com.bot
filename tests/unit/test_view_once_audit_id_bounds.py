from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.config import settings
from app.models.schema import AuditLog, OutboundMessage
from app.services.view_once_command_service import ViewOnceCommandService
from app.utils.time import utcnow
from app.workers.background_workers import (
    _delivery_snapshot,
    _finalize_view_once_delivery_success,
    _mark_delivery_failed,
    _view_once_audit_entity_id,
)


OWNER_ID = "2348000000001@c.us"


async def _insert_metadata(db_session, source_id: str) -> None:
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
            ON CONFLICT (source_message_id) DO NOTHING
            """
        ),
        {"source_id": source_id},
    )


def test_view_once_audit_entity_id_is_bounded_to_schema_limit():
    source_id = "S" * 200
    assert _view_once_audit_entity_id(source_id) == source_id[:120]
    assert len(_view_once_audit_entity_id(source_id)) == 120


def test_view_once_command_audit_entity_id_is_bounded_to_schema_limit():
    transport_id = "T" * 255
    assert ViewOnceCommandService._audit_entity_id(transport_id) == transport_id[:120]
    assert len(ViewOnceCommandService._audit_entity_id(transport_id)) == 120


@pytest.mark.asyncio
async def test_long_view_once_command_transport_id_can_flush_audit(db_session):
    transport_id = "C" * 255
    service = ViewOnceCommandService(db_session)
    await service._audit(
        "view_once_command_denied",
        ".vv",
        "request-short",
        transport_id,
        {"reason": "owner_required"},
    )

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_command_denied")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert audit.entity_id == transport_id[:120]
    assert len(audit.entity_id) == 120


@pytest.mark.asyncio
async def test_long_view_once_source_id_can_commit_success_lifecycle_audit(db_session):
    source_id = "V" * 200
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=settings.waha_service_url.rstrip("/") + "/api/files/long-source.jpg",
        media_type="image",
        media_caption="private view-once",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        formatting_json={"source": "view_once_command", "source_message_id": source_id},
        updated_at=utcnow(),
    )
    db_session.add(queued)
    await db_session.flush()

    await _finalize_view_once_delivery_success(db_session, queued, _delivery_snapshot(queued))
    await db_session.commit()

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_returned_to_owner")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert audit.entity_id == source_id[:120]
    assert len(audit.entity_id) == 120
    assert queued.media_url is None
    assert queued.formatting_json["resendable"] is False

    lifecycle = (
        await db_session.execute(
            text(
                """
                SELECT source_message_id, capability_state, returned_to_owner_at
                FROM view_once_media_metadata
                WHERE source_message_id = :source_id
                """
            ),
            {"source_id": source_id},
        )
    ).mappings().one()
    assert lifecycle["source_message_id"] == source_id
    assert lifecycle["capability_state"] == "returned_to_owner"
    assert lifecycle["returned_to_owner_at"] is not None


@pytest.mark.asyncio
async def test_long_view_once_source_id_can_commit_terminal_failure_audit(db_session):
    source_id = "F" * 200
    await _insert_metadata(db_session, source_id)
    queued = OutboundMessage(
        chat_id=OWNER_ID,
        message_text="",
        media_url=settings.waha_service_url.rstrip("/") + "/api/files/long-failure.jpg",
        media_type="image",
        media_caption="private view-once",
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

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "view_once_delivery_terminal_failed")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalar_one()
    assert audit.entity_id == source_id[:120]
    assert len(audit.entity_id) == 120
    assert queued.media_url is None
    assert queued.formatting_json["resendable"] is False
