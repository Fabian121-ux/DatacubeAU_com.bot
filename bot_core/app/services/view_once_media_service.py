from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
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
    original_message_at: str | None
    capability_expires_at: str | None


class ViewOnceMediaService:
    """Durable metadata boundary for Zina view-once commands."""

    DEFAULT_LIST_LIMIT = 10
    MAX_LIST_LIMIT = 25
    MAX_SOURCE_MESSAGE_ID_CHARS = 200
    _MAX_TIMESTAMP_DEPTH = 8

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    def valid_source_message_id(cls, value: Any) -> str | None:
        source_id = str(value or "").strip()
        if not source_id or len(source_id) > cls.MAX_SOURCE_MESSAGE_ID_CHARS:
            return None
        return source_id

    async def observe_reply(self, message: Any) -> tuple[ViewOnceCapability, ViewOnceMetadataRecord | None]:
        payload = getattr(message, "payload", None)
        capability = ViewOnceCapabilityService.inspect_reply_snapshot(payload)
        source_id = self.valid_source_message_id(capability.source_message_id)
        if not source_id:
            return capability, None

        state = self._state(capability)
        metadata = {
            "reason": capability.reason[:500],
            "view_once_explicit": capability.is_view_once,
        }
        original_message_at = self._reply_original_message_at(payload)
        if original_message_at is not None:
            metadata["original_message_at"] = original_message_at
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
                        media_type = COALESCE(EXCLUDED.media_type, view_once_media_metadata.media_type),
                        media_mime = COALESCE(EXCLUDED.media_mime, view_once_media_metadata.media_mime),
                        capability_state = CASE
                            WHEN view_once_media_metadata.deleted_at IS NOT NULL
                                THEN 'deleted'
                            WHEN view_once_media_metadata.returned_to_owner_at IS NOT NULL
                                THEN 'returned_to_owner'
                            ELSE EXCLUDED.capability_state
                        END,
                        evidence_source = EXCLUDED.evidence_source,
                        transport_available = CASE
                            WHEN view_once_media_metadata.deleted_at IS NOT NULL
                                THEN FALSE
                            WHEN view_once_media_metadata.returned_to_owner_at IS NOT NULL
                                THEN FALSE
                            ELSE EXCLUDED.transport_available
                        END,
                        metadata_json = jsonb_strip_nulls(
                            COALESCE(view_once_media_metadata.metadata_json, '{}'::jsonb)
                            || EXCLUDED.metadata_json
                        ),
                        last_observed_at = NOW(),
                        deleted_at = view_once_media_metadata.deleted_at
                    RETURNING id, source_message_id, source_chat_id, media_type, media_mime,
                              capability_state, evidence_source, transport_available,
                              retention_mode, first_observed_at, last_observed_at,
                              returned_to_owner_at, deleted_at, metadata_json
                    """
                ),
                {
                    "source_message_id": source_id,
                    "source_chat_id": str(getattr(message, "chat_id", "") or "unknown-chat")[:120],
                    "media_type": (capability.media_type or "")[:40] or None,
                    "media_mime": (capability.media_mime or "")[:160] or None,
                    "capability_state": state,
                    "evidence_source": capability.evidence_source[:80],
                    "transport_available": bool(capability.retrievable_now),
                    "metadata_json": json.dumps(metadata),
                },
            )
        ).mappings().one()
        return capability, self._record(row)

    async def mark_capability_expiry(self, source_message_id: str, expires_at: Any) -> None:
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return
        expiry = expires_at.isoformat() if hasattr(expires_at, "isoformat") else str(expires_at)
        await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET metadata_json = jsonb_strip_nulls(
                        COALESCE(metadata_json, '{}'::jsonb)
                        || jsonb_build_object('capability_expires_at', CAST(:expiry AS text))
                    ),
                    last_observed_at = NOW()
                WHERE source_message_id = :source_message_id AND deleted_at IS NULL
                """
            ),
            {"source_message_id": source_id, "expiry": expiry},
        )

    async def mark_returned(self, source_message_id: str) -> None:
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return
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
            {"source_message_id": source_id},
        )

    async def mark_delivery_unavailable(self, source_message_id: str) -> None:
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return
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
            {"source_message_id": source_id},
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
                           returned_to_owner_at, deleted_at, metadata_json
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
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return None
        row = (
            await self.session.execute(
                text(
                    """
                    SELECT id, source_message_id, source_chat_id, media_type, media_mime,
                           capability_state, evidence_source, transport_available,
                           retention_mode, first_observed_at, last_observed_at,
                           returned_to_owner_at, deleted_at, metadata_json
                    FROM view_once_media_metadata
                    WHERE source_message_id = :source_message_id
                    LIMIT 1
                    """
                ),
                {"source_message_id": source_id},
            )
        ).mappings().one_or_none()
        return self._record(row) if row else None

    async def delete_metadata(self, source_message_id: str) -> bool:
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return False
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
            {"source_message_id": source_id},
        )
        return bool(result.rowcount)

    async def delete(self, source_message_id: str) -> ViewOnceMetadataRecord | None:
        source_id = self.valid_source_message_id(source_message_id)
        if not source_id:
            return None
        existing = await self.get(source_id)
        if existing is None:
            return None
        if existing.deleted_at is None:
            await self.delete_metadata(source_id)
        return await self.get(source_id)

    @staticmethod
    def retention_supported() -> bool:
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

    @classmethod
    def _reply_original_message_at(cls, payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return None
        values: list[str] = []

        def visit(node: Any, depth: int = 0) -> None:
            if depth > cls._MAX_TIMESTAMP_DEPTH or not isinstance(node, dict):
                return
            for key in ("timestamp", "messageTimestamp", "t"):
                parsed = cls._normalize_timestamp(node.get(key))
                if parsed and parsed not in values:
                    values.append(parsed)
            for key in ("message", "_data"):
                visit(node.get(key), depth + 1)

        visit(reply_to)
        return values[0] if len(values) == 1 else None

    @staticmethod
    def _normalize_timestamp(value: Any) -> str | None:
        if value is None or isinstance(value, bool):
            return None
        try:
            if isinstance(value, (int, float)) or str(value).strip().replace(".", "", 1).isdigit():
                numeric = float(value)
                if numeric > 10_000_000_000:
                    numeric /= 1000.0
                if numeric <= 0:
                    return None
                return datetime.fromtimestamp(numeric, tz=timezone.utc).isoformat()
        except (OverflowError, OSError, TypeError, ValueError):
            return None
        text_value = str(value).strip()
        if not text_value:
            return None
        try:
            parsed = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()

    @staticmethod
    def _record(row: Any) -> ViewOnceMetadataRecord:
        metadata = row.get("metadata_json") or {}
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
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
            original_message_at=metadata.get("original_message_at"),
            capability_expires_at=metadata.get("capability_expires_at"),
        )
