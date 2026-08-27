from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.view_once_capability_service import ViewOnceCapability, ViewOnceCapabilityService


@dataclass(frozen=True, slots=True)
class ViewOnceMetadataRecord:
    id: int
    source_message_id: str
    source_chat_id: str
    media_type: str | None
    media_mime: str | None
    capability_state: str
    evidence_source: str
    transport_available: bool
    retention_mode: str
    first_observed_at: Any | None
    last_observed_at: Any | None
    returned_to_owner_at: Any | None
    deleted_at: Any | None


class ViewOnceMediaService:
    """Durable metadata boundary for Zina view-once commands.

    This service intentionally persists metadata only. It never persists WAHA media
    URLs, media bytes, base64 data, or raw webhook payloads. A caller may use the
    returned capability's in-memory media URL for one immediate OWNER-only outbound
    delivery, but that URL must not be written to this metadata table or audit logs.
    """

    DEFAULT_LIST_LIMIT = 10
    MAX_LIST_LIMIT = 25

    def __init__(self, session: AsyncSession):
        self.session = session

    async def observe_reply(self, message: Any) -> tuple[ViewOnceCapability, ViewOnceMetadataRecord | None]:
        payload = getattr(message, "payload", None)
        capability = ViewOnceCapabilityService.inspect_reply_snapshot(payload)
        if not capability.source_message_id:
            return capability, None

        state = self._state(capability)
        metadata = {
            "reason": capability.reason[:500],
            "view_once_explicit": capability.is_view_once,
        }
        row = (
            await self.session.execute(
                text(
                    """
                    INSERT INTO view_once_media_metadata (
                        source_message_id, source_chat_id, media_type, media_mime,
                        capability_state, evidence_source, transport_available,
                        retention_mode, metadata_json, first_observed_at, last_observed_at
                    ) VALUES (
                        :source_message_id, :source_chat_id, :media_type, :media_mime,
                        :capability_state, :evidence_source, :transport_available,
                        'none', CAST(:metadata_json AS jsonb), NOW(), NOW()
                    )
                    ON CONFLICT (source_message_id) DO UPDATE SET
                        source_chat_id = EXCLUDED.source_chat_id,
                        media_type = EXCLUDED.media_type,
                        media_mime = EXCLUDED.media_mime,
                        capability_state = CASE
                            WHEN view_once_media_metadata.returned_to_owner_at IS NOT NULL
                                THEN 'returned_to_owner'
                            ELSE EXCLUDED.capability_state
                        END,
                        evidence_source = EXCLUDED.evidence_source,
                        transport_available = CASE
                            WHEN view_once_media_metadata.returned_to_owner_at IS NOT NULL
                                THEN FALSE
                            ELSE EXCLUDED.transport_available
                        END,
                        metadata_json = EXCLUDED.metadata_json,
                        last_observed_at = NOW(),
                        deleted_at = NULL
                    RETURNING id, source_message_id, source_chat_id, media_type, media_mime,
                              capability_state, evidence_source, transport_available,
                              retention_mode, first_observed_at, last_observed_at,
                              returned_to_owner_at, deleted_at
                    """
                ),
                {
                    "source_message_id": capability.source_message_id,
                    "source_chat_id": str(getattr(message, "chat_id", "") or "unknown-chat")[:120],
                    "media_type": (capability.media_type or "")[:40] or None,
                    "media_mime": (capability.media_mime or "")[:160] or None,
                    "capability_state": state,
                    "evidence_source": capability.evidence_source[:80],
                    "transport_available": bool(capability.retrievable_now),
                    "metadata_json": __import__("json").dumps(metadata),
                },
            )
        ).mappings().one()
        return capability, self._record(row)

    async def mark_returned(self, source_message_id: str) -> None:
        await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET returned_to_owner_at = COALESCE(returned_to_owner_at, NOW()),
                    capability_state = 'returned_to_owner',
                    transport_available = FALSE,
                    last_observed_at = NOW()
                WHERE source_message_id = :source_message_id AND deleted_at IS NULL
                """
            ),
            {"source_message_id": source_message_id[:200]},
        )

    async def mark_delivery_unavailable(self, source_message_id: str) -> None:
        """Mark transport unavailable without regressing a successful return."""
        await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET capability_state = 'unavailable',
                    transport_available = FALSE,
                    last_observed_at = NOW()
                WHERE source_message_id = :source_message_id
                  AND deleted_at IS NULL
                  AND returned_to_owner_at IS NULL
                """
            ),
            {"source_message_id": source_message_id[:200]},
        )

    async def list_recent(self, limit: int | None = None) -> list[ViewOnceMetadataRecord]:
        effective = max(1, min(int(limit or self.DEFAULT_LIST_LIMIT), self.MAX_LIST_LIMIT))
        rows = (
            await self.session.execute(
                text(
                    """
                    SELECT id, source_message_id, source_chat_id, media_type, media_mime,
                           capability_state, evidence_source, transport_available,
                           retention_mode, first_observed_at, last_observed_at,
                           returned_to_owner_at, deleted_at
                    FROM view_once_media_metadata
                    WHERE deleted_at IS NULL
                    ORDER BY last_observed_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": effective},
            )
        ).mappings().all()
        return [self._record(row) for row in rows]

    async def get(self, source_message_id: str) -> ViewOnceMetadataRecord | None:
        row = (
            await self.session.execute(
                text(
                    """
                    SELECT id, source_message_id, source_chat_id, media_type, media_mime,
                           capability_state, evidence_source, transport_available,
                           retention_mode, first_observed_at, last_observed_at,
                           returned_to_owner_at, deleted_at
                    FROM view_once_media_metadata
                    WHERE source_message_id = :source_message_id
                    LIMIT 1
                    """
                ),
                {"source_message_id": source_message_id[:200]},
            )
        ).mappings().one_or_none()
        return self._record(row) if row else None

    async def delete_metadata(self, source_message_id: str) -> bool:
        result = await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET deleted_at = COALESCE(deleted_at, NOW()),
                    capability_state = 'deleted',
                    transport_available = FALSE,
                    retention_mode = 'none',
                    last_observed_at = NOW()
                WHERE source_message_id = :source_message_id AND deleted_at IS NULL
                """
            ),
            {"source_message_id": source_message_id[:200]},
        )
        return bool(result.rowcount)

    async def delete(self, source_message_id: str) -> ViewOnceMetadataRecord | None:
        """Soft-delete exactly one metadata record and return its lifecycle state.

        Repeated deletion is idempotent: an existing already-deleted record is returned
        as deleted, while an unknown source returns None. No media bytes are involved.
        """
        existing = await self.get(source_message_id)
        if existing is None:
            return None
        if existing.deleted_at is None:
            await self.delete_metadata(source_message_id)
        return await self.get(source_message_id)

    @staticmethod
    def retention_supported() -> bool:
        """Persistent view-once byte retention is deliberately unavailable for now."""
        return False

    @staticmethod
    def _state(capability: ViewOnceCapability) -> str:
        if capability.is_view_once is True and capability.retrievable_now:
            return "available_from_transport"
        if capability.is_view_once is True:
            return "unavailable"
        if capability.is_view_once is False:
            return "not_view_once"
        return "capability_unknown"

    @staticmethod
    def _record(row: Any) -> ViewOnceMetadataRecord:
        return ViewOnceMetadataRecord(
            id=int(row["id"]),
            source_message_id=str(row["source_message_id"]),
            source_chat_id=str(row["source_chat_id"]),
            media_type=row["media_type"],
            media_mime=row["media_mime"],
            capability_state=str(row["capability_state"]),
            evidence_source=str(row["evidence_source"]),
            transport_available=bool(row["transport_available"]),
            retention_mode=str(row["retention_mode"]),
            first_observed_at=row["first_observed_at"],
            last_observed_at=row["last_observed_at"],
            returned_to_owner_at=row["returned_to_owner_at"],
            deleted_at=row["deleted_at"],
        )
