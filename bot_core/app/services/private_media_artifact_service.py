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
        if media_mime is not None and (not media_mime or len(media_mime) > self.MAX_MEDIA_MIME_LENGTH):
            return PrivateMediaArtifactResult(False, error="invalid media_mime")
        if content_hash is not None and (not content_hash or len(content_hash) > self.MAX_CONTENT_HASH_LENGTH):
            return PrivateMediaArtifactResult(False, error="invalid content_hash")
        if byte_size is not None and byte_size < 0:
            return PrivateMediaArtifactResult(False, error="byte_size cannot be negative")
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
        already uses. A deleted artifact is never resurrected by a later observation — the
        caller gets a fresh row instead, same as that table's own ``deleted_at`` handling.

        Enforced at the database level by ``ux_private_media_artifacts_source`` (migration
        034), so a genuine race between two callers fails with ``IntegrityError`` rather than
        silently duplicating; callers on non-fatal observation paths should catch that the
        same way they already catch any other persistence failure here.
        """
        existing = await self._find_active_by_source(source_chat_id, source_message_id)
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

    @classmethod
    def _new_artifact_id(cls) -> str:
        return secrets.token_urlsafe(cls.ARTIFACT_ID_BYTES)
