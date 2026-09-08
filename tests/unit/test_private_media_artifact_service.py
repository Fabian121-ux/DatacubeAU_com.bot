"""Foundational metadata layer for PrivateMediaArtifactService.

This service is metadata-only (docs/VIEW_ONCE_MEDIA_PIPELINE.md roadmap phase 5): no
private byte storage exists yet, and no producer or delivery path calls it. These
tests cover create/get/disable/delete lifecycle and the fail-closed retention gate
that refuses any retention policy beyond "none" until a byte-storage backend exists.
"""

from __future__ import annotations

import pytest

from app.models.schema import AdminAccount, AuditLog, PrivateMediaArtifact
from app.services.private_media_artifact_service import PrivateMediaArtifactService


def _owner():
    return AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id="2348000000001@c.us",
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )


@pytest.mark.asyncio
async def test_create_persists_metadata_only_and_stamps_audit(db_session, test_contact):
    owner = _owner()
    db_session.add(owner)
    await db_session.flush()

    service = PrivateMediaArtifactService(db_session)
    result = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        source_contact_id=test_contact.id,
        owner_admin_account_id=owner.id,
        media_mime="image/jpeg",
        byte_size=1024,
        content_hash="deadbeef",
        request_id="req-1",
    )

    assert result.ok is True
    assert result.artifact_id

    artifact = await service.get(result.artifact_id)
    assert artifact is not None
    assert artifact.source_message_id == "SRC-1"
    assert artifact.retention_policy == "none"
    # No byte storage exists yet at this layer.
    assert artifact.storage_locator is None

    audit = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "private_media_artifact_created")
        )
    ).mappings().first()
    assert audit is not None
    assert audit["entity_id"] == result.artifact_id


@pytest.mark.asyncio
async def test_create_generates_distinct_opaque_artifact_ids(db_session):
    service = PrivateMediaArtifactService(db_session)
    first = await service.create(
        source_message_id="SRC-A",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
    )
    second = await service.create(
        source_message_id="SRC-B",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
    )

    assert first.ok and second.ok
    assert first.artifact_id != second.artifact_id
    assert first.artifact_id not in (None, "")


@pytest.mark.asyncio
async def test_create_rejects_any_retention_policy_other_than_none(db_session):
    service = PrivateMediaArtifactService(db_session)
    result = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        retention_policy="persistent",
    )

    assert result.ok is False
    assert result.artifact_id is None
    assert "not enabled" in (result.error or "")

    count = (await db_session.execute(PrivateMediaArtifact.__table__.select())).mappings().all()
    assert count == []


@pytest.mark.asyncio
async def test_create_rejects_invalid_inputs(db_session):
    service = PrivateMediaArtifactService(db_session)

    missing_source = await service.create(
        source_message_id="",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
    )
    assert missing_source.ok is False

    missing_kind = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="",
    )
    assert missing_kind.ok is False

    negative_size = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        byte_size=-1,
    )
    assert negative_size.ok is False


@pytest.mark.asyncio
async def test_create_rejects_unknown_transport_provenance(db_session):
    """transport_provenance is a closed set of producer labels, never arbitrary text.

    A caller passing a temporary transport URL, token, or other capability as
    provenance must be refused here rather than have it land verbatim in AuditLog.
    """
    service = PrivateMediaArtifactService(db_session)
    result = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="http://waha:3000/api/files/secret-token.jpg",
        media_kind="image",
    )

    assert result.ok is False
    assert result.artifact_id is None
    assert "not a known producer label" in (result.error or "")

    rows = (await db_session.execute(PrivateMediaArtifact.__table__.select())).mappings().all()
    assert rows == []
    audit_rows = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "private_media_artifact_created")
        )
    ).mappings().all()
    assert audit_rows == []


@pytest.mark.asyncio
async def test_create_rejects_oversized_bounded_fields_cleanly(db_session):
    """An oversized field must return a validation error, never an unhandled DB exception.

    Regression for a Codex review finding on PR #44: media_kind/media_mime/
    transport_provenance/content_hash were unbounded before the row reached flush(),
    so an oversized value crashed with asyncpg's StringDataRightTruncationError
    instead of the result-based validation API this service otherwise exposes.
    """
    service = PrivateMediaArtifactService(db_session)

    oversized_kind = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="x" * 41,
    )
    assert oversized_kind.ok is False
    assert "media_kind" in (oversized_kind.error or "")

    oversized_mime = await service.create(
        source_message_id="SRC-2",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        media_mime="x" * 161,
    )
    assert oversized_mime.ok is False
    assert "media_mime" in (oversized_mime.error or "")

    oversized_hash = await service.create(
        source_message_id="SRC-3",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        content_hash="x" * 129,
    )
    assert oversized_hash.ok is False
    assert "content_hash" in (oversized_hash.error or "")

    # Nothing was ever added to the session for any of the three rejected calls.
    rows = (await db_session.execute(PrivateMediaArtifact.__table__.select())).mappings().all()
    assert rows == []


@pytest.mark.asyncio
async def test_get_returns_none_for_unknown_or_deleted_artifact(db_session):
    service = PrivateMediaArtifactService(db_session)
    assert await service.get("does-not-exist") is None

    created = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
    )
    await service.delete(created.artifact_id)
    assert await service.get(created.artifact_id) is None


@pytest.mark.asyncio
async def test_disable_then_delete_lifecycle_is_monotonic_and_tombstones(db_session):
    service = PrivateMediaArtifactService(db_session)
    created = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        content_hash="abc123",
    )
    artifact_id = created.artifact_id

    disable_result = await service.disable(artifact_id, request_id="req-2")
    assert disable_result.ok is True

    artifact = await service.get(artifact_id)
    assert artifact is not None
    assert artifact.disabled_at is not None

    # Disabling an already-disabled artifact is idempotent, not an error.
    second_disable = await service.disable(artifact_id)
    assert second_disable.ok is True

    delete_result = await service.delete(artifact_id, request_id="req-3")
    assert delete_result.ok is True

    # get() returns None once deleted, but the tombstone row itself survives with
    # content_hash/storage_locator cleared as the minimum audit-preserving state.
    assert await service.get(artifact_id) is None
    tombstone = (
        await db_session.execute(
            PrivateMediaArtifact.__table__.select().where(
                PrivateMediaArtifact.artifact_id == artifact_id
            )
        )
    ).mappings().first()
    assert tombstone is not None
    assert tombstone["deleted_at"] is not None
    assert tombstone["content_hash"] is None
    assert tombstone["storage_locator"] is None

    # Deletion is idempotent, not a re-raised error.
    repeat_delete = await service.delete(artifact_id)
    assert repeat_delete.ok is True


@pytest.mark.asyncio
async def test_disable_and_delete_on_unknown_artifact_fail_closed(db_session):
    service = PrivateMediaArtifactService(db_session)
    disable_result = await service.disable("does-not-exist")
    assert disable_result.ok is False

    delete_result = await service.delete("does-not-exist")
    assert delete_result.ok is False


@pytest.mark.asyncio
async def test_list_for_owner_is_bounded_and_excludes_deleted(db_session):
    owner = _owner()
    db_session.add(owner)
    await db_session.flush()

    service = PrivateMediaArtifactService(db_session)
    ids = []
    for index in range(3):
        result = await service.create(
            source_message_id=f"SRC-{index}",
            source_chat_id="2348000000001@c.us",
            transport_provenance="view_once_command",
            media_kind="image",
            owner_admin_account_id=owner.id,
        )
        ids.append(result.artifact_id)
    await service.delete(ids[0])

    listed = await service.list_for_owner(owner.id, limit=10)
    listed_ids = {artifact.artifact_id for artifact in listed}
    assert ids[0] not in listed_ids
    assert ids[1] in listed_ids and ids[2] in listed_ids


@pytest.mark.asyncio
async def test_list_for_owner_only_returns_that_owners_artifacts(db_session):
    owner_a = _owner()
    owner_b = AdminAccount(
        name="Other",
        whatsapp_number="2348000000009",
        normalized_whatsapp_id="2348000000009@c.us",
        role="admin",
        permission_level="owner",
        is_primary=False,
        is_enabled=True,
    )
    db_session.add_all([owner_a, owner_b])
    await db_session.flush()

    service = PrivateMediaArtifactService(db_session)
    await service.create(
        source_message_id="SRC-A",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        owner_admin_account_id=owner_a.id,
    )
    await service.create(
        source_message_id="SRC-B",
        source_chat_id="2348000000009@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        owner_admin_account_id=owner_b.id,
    )

    listed_a = await service.list_for_owner(owner_a.id, limit=10)
    assert len(listed_a) == 1
    assert listed_a[0].source_message_id == "SRC-A"


# --------------------------------------------------------------------------------------
# get_or_create_from_observation: idempotent per (source_chat_id, source_message_id)
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_or_create_from_observation_creates_when_absent(db_session):
    service = PrivateMediaArtifactService(db_session)
    result = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    assert result.ok is True
    artifact = await service.get(result.artifact_id)
    assert artifact is not None
    assert artifact.transport_provenance == "waha_webhook_observation"


@pytest.mark.asyncio
async def test_get_or_create_from_observation_converges_on_one_row_for_the_same_source(db_session):
    service = PrivateMediaArtifactService(db_session)
    first = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )
    second = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    assert first.artifact_id == second.artifact_id
    rows = (await db_session.execute(PrivateMediaArtifact.__table__.select())).mappings().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_get_or_create_from_observation_backfills_missing_fields_without_overwriting(db_session):
    owner = _owner()
    db_session.add(owner)
    await db_session.flush()

    service = PrivateMediaArtifactService(db_session)
    await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
        content_hash="original-hash",
    )
    result = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        media_mime="image/jpeg",
        owner_admin_account_id=owner.id,
        content_hash="a-different-hash-that-must-not-overwrite",
    )

    artifact = await service.get(result.artifact_id)
    assert artifact.media_mime == "image/jpeg"
    assert artifact.owner_admin_account_id == owner.id
    # The first-observed content hash is authoritative; a later call never overwrites it.
    assert artifact.content_hash == "original-hash"


@pytest.mark.asyncio
async def test_get_or_create_from_observation_does_not_resurrect_a_deleted_artifact(db_session):
    service = PrivateMediaArtifactService(db_session)
    first = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )
    await service.delete(first.artifact_id)

    second = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    assert second.artifact_id != first.artifact_id
    assert await service.get(second.artifact_id) is not None


@pytest.mark.asyncio
async def test_source_identity_is_enforced_unique_at_the_database_level(db_session):
    """Regression for migration 034: a raw duplicate insert must fail, not silently land.

    This proves the constraint that makes get_or_create_from_observation's
    find-then-write pattern safe under a genuine race actually exists in the schema,
    independent of the service's own application-level lookup.
    """
    from sqlalchemy.exc import IntegrityError

    service = PrivateMediaArtifactService(db_session)
    await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    duplicate = PrivateMediaArtifact(
        artifact_id="duplicate-artifact-id",
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        media_kind="image",
        transport_provenance="waha_webhook_observation",
    )
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_get_or_create_from_observation_backfill_rejects_oversized_fields_cleanly(db_session):
    """The backfill path bypasses create()'s row construction, so it must repeat the
    same bounds validation rather than let an oversized value reach flush() as an
    unhandled StringDataRightTruncationError (regression for a Codex review finding
    on this PR).
    """
    service = PrivateMediaArtifactService(db_session)
    created = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    result = await service.get_or_create_from_observation(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="view_once_command",
        media_kind="image",
        media_mime="x" * 161,
    )

    assert result.ok is False
    assert "media_mime" in (result.error or "")
    # The existing row must be untouched, not partially mutated then rolled back.
    artifact = await service.get(created.artifact_id)
    assert artifact.media_mime is None


# --------------------------------------------------------------------------------------
# delete_by_source
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_by_source_tombstones_the_matching_artifact(db_session):
    service = PrivateMediaArtifactService(db_session)
    created = await service.create(
        source_message_id="SRC-1",
        source_chat_id="2348000000001@c.us",
        transport_provenance="waha_webhook_observation",
        media_kind="image",
    )

    result = await service.delete_by_source("2348000000001@c.us", "SRC-1")

    assert result.ok is True
    assert await service.get(created.artifact_id) is None


@pytest.mark.asyncio
async def test_delete_by_source_is_a_noop_when_nothing_was_ever_recorded(db_session):
    service = PrivateMediaArtifactService(db_session)

    result = await service.delete_by_source("2348000000001@c.us", "NEVER-OBSERVED")

    assert result.ok is True
    assert result.artifact_id is None
