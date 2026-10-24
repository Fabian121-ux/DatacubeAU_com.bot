from __future__ import annotations

from dataclasses import dataclass
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, PrivateMediaArtifact
from app.utils.time import utcnow


@dataclass(slots=True)
class PrivateMediaArtifactResult:
    ok: bool
    artifact_id: str | None = None
    error: str | None = None


class PrivateMediaArtifactService:
    """PostgreSQL authoritative metadata for private media artifacts.

    This is the foundational metadata layer described in
    docs/VIEW_ONCE_MEDIA_PIPELINE.md (roadmap phase 5): opaque artifact ID, exact
    source identifiers, media kind/MIME/size/hash, transport provenance, retention
    policy, and lifecycle timestamps. It intentionally does not implement private byte
    storage. ``ViewOnceObservationService`` (ingress) and ``ViewOnceCommandService``
    (``.vvopen`` owner return) both call ``get_or_create_from_observation`` to record
    metadata-only provenance; no delivery path depends on this service's data, and a
    failure here never blocks or fails the message it describes.

    Retention is fail-closed at this layer: only ``retention_policy="none"`` (no byte
    retention) may be written. Any other value is refused until a private byte-storage
    backend, TTL enforcement, and quota bounds exist behind this service, per the
    documented privacy defaults. This is deliberate: expanding the allowed set here is
    the trigger for that future work, not a value to loosen ahead of it.

    ``transport_provenance`` is similarly restricted to a closed set of known producer
    labels rather than arbitrary caller-supplied text: the media pipeline's privacy
    contract (docs/VIEW_ONCE_MEDIA_PIPELINE.md) requires that transport URLs, tokens,
    or other capabilities never enter durable logs, and this value is written verbatim
    into ``AuditLog``. Adding a new producer means adding its label here deliberately,
    not passing whatever string it happens to have on hand.

    Every bounded field is length-checked against its column limit before the row is
    ever added to the session, so a malformed caller gets a clean
    ``PrivateMediaArtifactResult(False, ...)`` instead of an unhandled
    ``StringDataRightTruncationError`` surfacing from ``flush()``.
    """

    ALLOWED_RETENTION_POLICIES = frozenset({"none"})
    ALLOWED_TRANSPORT_PROVENANCES = frozenset({"view_once_command", "waha_webhook_observation"})
    # A caller may not yet have real evidence of the media category (see
    # ViewOnceCapabilityService.infer_media_kind). This sentinel marks that row as
    # backfillable once real evidence arrives, rather than permanently misclassified.
    UNKNOWN_MEDIA_KIND = "unknown"
    ARTIFACT_ID_BYTES = 24
    MAX_SOURCE_ID_LENGTH = 200
    MAX_CHAT_ID_LENGTH = 120
    MAX_MEDIA_KIND_LENGTH = 40
    MAX_MEDIA_MIME_LENGTH = 160
    MAX_CONTENT_HASH_LENGTH = 128

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        *,
        source_message_id: str,
        source_chat_id: str,
        transport_provenance: str,
        media_kind: str,
        source_contact_id: int | None = None,
        owner_admin_account_id: int | None = None,
        media_mime: str | None = None,
        byte_size: int | None = None,
        content_hash: str | None = None,
        retention_policy: str = "none",
        request_id: str | None = None,
    ) -> PrivateMediaArtifactResult:
        source_message_id = str(source_message_id or "").strip()
        source_chat_id = str(source_chat_id or "").strip()
        transport_provenance = str(transport_provenance or "").strip()
        media_kind = str(media_kind or "").strip()

        media_mime = str(media_mime).strip() if media_mime is not None else None
        content_hash = str(content_hash).strip() if content_hash is not None else None

        if not source_message_id or len(source_message_id) > self.MAX_SOURCE_ID_LENGTH:
            return PrivateMediaArtifactResult(False, error="invalid source_message_id")
        if not source_chat_id or len(source_chat_id) > self.MAX_CHAT_ID_LENGTH:
            return PrivateMediaArtifactResult(False, error="invalid source_chat_id")
        if not transport_provenance:
            return PrivateMediaArtifactResult(False, error="transport_provenance is required")
        if transport_provenance not in self.ALLOWED_TRANSPORT_PROVENANCES:
            return PrivateMediaArtifactResult(
                False,
                error=(
                    f"transport_provenance {transport_provenance!r} is not a known producer label; "
                    f"only {sorted(self.ALLOWED_TRANSPORT_PROVENANCES)} is accepted"
                ),
            )
        if not media_kind or len(media_kind) > self.MAX_MEDIA_KIND_LENGTH:
            return PrivateMediaArtifactResult(False, error="invalid media_kind")
        optional_error = self._validate_optional_fields(
            media_mime=media_mime, content_hash=content_hash, byte_size=byte_size
        )
        if optional_error:
            return PrivateMediaArtifactResult(False, error=optional_error)
        if retention_policy not in self.ALLOWED_RETENTION_POLICIES:
            return PrivateMediaArtifactResult(
                False,
                error=(
                    f"retention_policy {retention_policy!r} is not enabled yet; "
                    f"only {sorted(self.ALLOWED_RETENTION_POLICIES)} is accepted"
                ),
            )

        artifact_id = self._new_artifact_id()
        artifact = PrivateMediaArtifact(
            artifact_id=artifact_id,
            source_message_id=source_message_id,
            source_chat_id=source_chat_id,
            source_contact_id=source_contact_id,
            owner_admin_account_id=owner_admin_account_id,
            media_kind=media_kind,
            media_mime=media_mime,
            byte_size=byte_size,
            content_hash=content_hash,
            storage_locator=None,
            transport_provenance=transport_provenance,
            retention_policy=retention_policy,
            created_at=utcnow(),
            last_observed_at=utcnow(),
        )
        self.session.add(artifact)
        await self.session.flush()

        self.session.add(
            AuditLog(
                action="private_media_artifact_created",
                entity_type="private_media_artifact",
                entity_id=artifact_id,
                details_json={
                    "request_id": request_id,
                    "media_kind": media_kind,
                    "transport_provenance": transport_provenance,
                    "retention_policy": retention_policy,
                },
            )
        )
        await self.session.flush()
        return PrivateMediaArtifactResult(True, artifact_id=artifact_id)

    async def get_or_create_from_observation(
        self,
        *,
        source_message_id: str,
        source_chat_id: str,
        transport_provenance: str,
        media_kind: str,
        source_contact_id: int | None = None,
        owner_admin_account_id: int | None = None,
        media_mime: str | None = None,
        byte_size: int | None = None,
        content_hash: str | None = None,
        request_id: str | None = None,
    ) -> PrivateMediaArtifactResult:
        """Idempotent per exact ``(source_chat_id, source_message_id)``.

        Producers observe or re-open the same source message more than once (webhook
        retries, repeated ``.vv info`` / ``.vvopen`` / ``.vv list`` on one item). This must
        converge on one artifact identity rather than minting a new opaque ``artifact_id``
        every time, matching the idempotent-per-source pattern ``view_once_media_metadata``
        already uses.

        A deletion tombstone for this exact source is a durable no-op, never a signal to
        mint a replacement: ``view_once_media_metadata`` deliberately stays deleted across
        re-observation (its own upsert only updates rows where ``deleted_at IS NULL``), so
        an OWNER's ``.vv delete`` must stay durable here too. Silently recreating an active
        artifact after deletion — which a later webhook retry or another ``.vvopen`` could
        otherwise trigger — would undo that deletion behind the OWNER's back and leave the
        two tables inconsistent.

        Enforced at the database level by ``ux_private_media_artifacts_source`` (migration
        034) for the active-row case, so a genuine race between two callers fails with
        ``IntegrityError`` rather than silently duplicating; callers on non-fatal observation
        paths should catch that the same way they already catch any other persistence
        failure here.
        """
        media_mime = str(media_mime).strip() if media_mime is not None else None
        content_hash = str(content_hash).strip() if content_hash is not None else None
        media_kind = str(media_kind or "").strip()
        if not media_kind or len(media_kind) > self.MAX_MEDIA_KIND_LENGTH:
            return PrivateMediaArtifactResult(False, error="invalid media_kind")

        existing = await self._find_any_by_source(source_chat_id, source_message_id)
        if existing is not None and existing.deleted_at is not None:
            return PrivateMediaArtifactResult(True)
        if existing is None:
            return await self.create(
                source_message_id=source_message_id,
                source_chat_id=source_chat_id,
                transport_provenance=transport_provenance,
                media_kind=media_kind,
                source_contact_id=source_contact_id,
                owner_admin_account_id=owner_admin_account_id,
                media_mime=media_mime,
                byte_size=byte_size,
                content_hash=content_hash,
                request_id=request_id,
            )

        # The backfill path bypasses create()'s row construction entirely, so it must
        # repeat the same bounds validation here rather than let an oversized value
        # reach flush() as an unhandled StringDataRightTruncationError.
        optional_error = self._validate_optional_fields(
            media_mime=media_mime, content_hash=content_hash, byte_size=byte_size
        )
        if optional_error:
            return PrivateMediaArtifactResult(False, error=optional_error)

        # media_kind is otherwise permanent once set (unlike the fields below, it's
        # required and non-null), but the UNKNOWN_MEDIA_KIND sentinel exists precisely
        # to mark a row as not yet classified -- real evidence arriving later (a
        # command return with a validated kind, for example) must be able to replace
        # it rather than leave the row permanently misclassified.
        if existing.media_kind == self.UNKNOWN_MEDIA_KIND and media_kind != self.UNKNOWN_MEDIA_KIND:
            existing.media_kind = media_kind
        if media_mime and not existing.media_mime:
            existing.media_mime = media_mime
        if content_hash and not existing.content_hash:
            existing.content_hash = content_hash
        if byte_size is not None and existing.byte_size is None:
            existing.byte_size = byte_size
        if source_contact_id is not None and existing.source_contact_id is None:
            existing.source_contact_id = source_contact_id
        if owner_admin_account_id is not None and existing.owner_admin_account_id is None:
            existing.owner_admin_account_id = owner_admin_account_id
        existing.last_observed_at = utcnow()
        await self.session.flush()
        return PrivateMediaArtifactResult(True, artifact_id=existing.artifact_id)

    async def delete_by_source(
        self, source_chat_id: str, source_message_id: str, *, request_id: str | None = None
    ) -> PrivateMediaArtifactResult:
        """Tombstone the artifact for an exact source, if one was ever recorded.

        A no-op (``ok=True``, no ``artifact_id``) when nothing was recorded for this
        source — callers that only want to keep an OWNER-facing metadata delete (for
        example ``.vv delete`` against ``view_once_media_metadata``) in sync with this
        newer table should not have to branch on whether observation ever ran.
        """
        existing = await self._find_active_by_source(source_chat_id, source_message_id)
        if existing is None:
            return PrivateMediaArtifactResult(True)
        return await self.delete(existing.artifact_id, request_id=request_id)

    async def get(self, artifact_id: str) -> PrivateMediaArtifact | None:
        artifact = await self._load(artifact_id)
        if artifact is None or artifact.deleted_at is not None:
            return None
        return artifact

    async def disable(self, artifact_id: str, *, request_id: str | None = None) -> PrivateMediaArtifactResult:
        artifact = await self._load(artifact_id)
        if artifact is None or artifact.deleted_at is not None:
            return PrivateMediaArtifactResult(False, error="artifact not found")
        if artifact.disabled_at is not None:
            return PrivateMediaArtifactResult(True, artifact_id=artifact_id)

        artifact.disabled_at = utcnow()
        self.session.add(
            AuditLog(
                action="private_media_artifact_disabled",
                entity_type="private_media_artifact",
                entity_id=artifact_id,
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return PrivateMediaArtifactResult(True, artifact_id=artifact_id)

    async def delete(self, artifact_id: str, *, request_id: str | None = None) -> PrivateMediaArtifactResult:
        """Tombstone the artifact. No private bytes exist yet at this layer to remove."""
        artifact = await self._load(artifact_id)
        if artifact is None:
            return PrivateMediaArtifactResult(False, error="artifact not found")
        if artifact.deleted_at is not None:
            return PrivateMediaArtifactResult(True, artifact_id=artifact_id)

        now = utcnow()
        artifact.deleted_at = now
        artifact.disabled_at = artifact.disabled_at or now
        artifact.storage_locator = None
        artifact.content_hash = None

        self.session.add(
            AuditLog(
                action="private_media_artifact_deleted",
                entity_type="private_media_artifact",
                entity_id=artifact_id,
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return PrivateMediaArtifactResult(True, artifact_id=artifact_id)

    async def list_for_owner(
        self, owner_admin_account_id: int, *, limit: int = 20
    ) -> list[PrivateMediaArtifact]:
        bounded_limit = max(1, min(int(limit), 100))
        rows = (
            await self.session.execute(
                select(PrivateMediaArtifact)
                .where(PrivateMediaArtifact.owner_admin_account_id == owner_admin_account_id)
                .where(PrivateMediaArtifact.deleted_at.is_(None))
                .order_by(PrivateMediaArtifact.last_observed_at.desc())
                .limit(bounded_limit)
            )
        ).scalars().all()
        return list(rows)

    # --------------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------------

    async def _load(self, artifact_id: str) -> PrivateMediaArtifact | None:
        artifact_id = str(artifact_id or "").strip()
        if not artifact_id:
            return None
        return (
            await self.session.execute(
                select(PrivateMediaArtifact).where(PrivateMediaArtifact.artifact_id == artifact_id)
            )
        ).scalar_one_or_none()

    async def _find_active_by_source(
        self, source_chat_id: str, source_message_id: str
    ) -> PrivateMediaArtifact | None:
        source_chat_id = str(source_chat_id or "").strip()
        source_message_id = str(source_message_id or "").strip()
        if not source_chat_id or not source_message_id:
            return None
        return (
            await self.session.execute(
                select(PrivateMediaArtifact)
                .where(PrivateMediaArtifact.source_chat_id == source_chat_id)
                .where(PrivateMediaArtifact.source_message_id == source_message_id)
                .where(PrivateMediaArtifact.deleted_at.is_(None))
                .limit(1)
            )
        ).scalar_one_or_none()

    async def _find_any_by_source(
        self, source_chat_id: str, source_message_id: str
    ) -> PrivateMediaArtifact | None:
        """Like ``_find_active_by_source`` but also returns a deleted tombstone.

        ``get_or_create_from_observation`` needs to see a tombstone (not just an active
        row) so it can treat it as a durable no-op rather than falling through to
        ``create()`` and minting a replacement for a source the OWNER already deleted.
        """
        source_chat_id = str(source_chat_id or "").strip()
        source_message_id = str(source_message_id or "").strip()
        if not source_chat_id or not source_message_id:
            return None
        return (
            await self.session.execute(
                select(PrivateMediaArtifact)
                .where(PrivateMediaArtifact.source_chat_id == source_chat_id)
                .where(PrivateMediaArtifact.source_message_id == source_message_id)
                .limit(1)
            )
        ).scalar_one_or_none()

    @classmethod
    def _new_artifact_id(cls) -> str:
        return secrets.token_urlsafe(cls.ARTIFACT_ID_BYTES)

    @classmethod
    def _validate_optional_fields(
        cls,
        *,
        media_mime: str | None,
        content_hash: str | None,
        byte_size: int | None,
    ) -> str | None:
        """Shared bounds-checking for the fields both ``create`` and the backfill path
        in ``get_or_create_from_observation`` may write. Callers must normalize
        (strip) ``media_mime``/``content_hash`` before calling this."""
        if media_mime is not None and (not media_mime or len(media_mime) > cls.MAX_MEDIA_MIME_LENGTH):
            return "invalid media_mime"
        if content_hash is not None and (not content_hash or len(content_hash) > cls.MAX_CONTENT_HASH_LENGTH):
            return "invalid content_hash"
        if byte_size is not None and byte_size < 0:
            return "byte_size cannot be negative"
        return None
