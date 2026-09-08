from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.logging_service import log_event
from app.services.view_once_capability_service import ViewOnceCapabilityService


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ViewOnceObservation:
    recorded: bool
    capability_state: str
    reason: str


class ViewOnceObservationService:
    """Record bounded view-once capability metadata for one observed inbound message.

    This is an observer, not an actor. It never sends, queues, replies, or authorizes
    anything: finding `is_view_once = true` is capability evidence, not authority. The
    OWNER command path plus the existing P0 outbound fence remain the only way media
    can leave Zina.

    It is also deliberately non-fatal. Ingress persistence must not fail because a
    capability record could not be written, so every error is logged and swallowed.
    """

    # Explicit evidence only. `TRANSIENT_AVAILABLE` means WAHA exposed a retrievable
    # locator at observation time; that capability expires and is re-checked at command
    # time rather than trusted from this record.
    STATE_TRANSIENT_AVAILABLE = "transient_available"
    STATE_CAPABILITY_VERIFIED = "capability_verified"
    STATE_UNAVAILABLE = "unavailable"

    MAX_SOURCE_ID_LENGTH = 200

    def __init__(self, session: AsyncSession):
        self.session = session

    async def observe(
        self,
        *,
        payload: Any,
        source_message_id: str,
        source_chat_id: str,
        source_contact_id: int | None,
    ) -> ViewOnceObservation:
        """Persist metadata only when explicit view-once evidence is present."""
        canonical_id = str(source_message_id or "").strip()
        chat_id = str(source_chat_id or "").strip()
        if not canonical_id or len(canonical_id) > self.MAX_SOURCE_ID_LENGTH or not chat_id:
            return ViewOnceObservation(False, self.STATE_UNAVAILABLE, "missing or invalid canonical source identity")

        capability = ViewOnceCapabilityService.inspect_message_payload(payload)

        # Ordinary media is never promoted. Only an explicit positive marker is recorded;
        # `False` (explicit negative) and `None` (no evidence) are both non-observations.
        if capability.is_view_once is not True:
            return ViewOnceObservation(False, self.STATE_UNAVAILABLE, capability.reason)

        # The detector derives its own source ID from the payload. If that disagrees with
        # the canonical ingress ID, the evidence may describe a different message, so we
        # fail closed rather than attaching it to the wrong source.
        if capability.source_message_id and capability.source_message_id != canonical_id:
            return ViewOnceObservation(
                False,
                self.STATE_UNAVAILABLE,
                "view-once evidence source ID disagrees with the canonical ingress source ID",
            )

        transport_available = bool(capability.media_url)
        state = self.STATE_TRANSIENT_AVAILABLE if transport_available else self.STATE_CAPABILITY_VERIFIED

        try:
            await self._upsert(
                source_message_id=canonical_id,
                source_chat_id=chat_id,
                source_contact_id=source_contact_id,
                media_type=capability.media_type,
                media_mime=capability.media_mime,
                capability_state=state,
                evidence_source=capability.evidence_source,
                transport_available=transport_available,
            )
        except Exception as exc:  # noqa: BLE001 - observation must never break ingress
            log_event(
                logger,
                logging.WARNING,
                "view_once_observation_failed",
                source_message_id=canonical_id,
                error=str(exc),
            )
            return ViewOnceObservation(False, state, f"observation could not be persisted: {exc}")

        log_event(
            logger,
            logging.INFO,
            "view_once_observed",
            source_message_id=canonical_id,
            capability_state=state,
            media_type=capability.media_type,
        )
        return ViewOnceObservation(True, state, capability.reason)

    async def _upsert(
        self,
        *,
        source_message_id: str,
        source_chat_id: str,
        source_contact_id: int | None,
        media_type: str | None,
        media_mime: str | None,
        capability_state: str,
        evidence_source: str,
        transport_available: bool,
    ) -> None:
        """Idempotent per canonical source message.

        `message` and `message.any` deliveries of one source, and webhook retries, must
        converge on a single row. A deleted record is not resurrected by a later
        duplicate delivery, so OWNER deletion stays durable across restarts.

        No media bytes, base64, or transport locator is stored: only whether a locator
        existed at observation time.
        """
        await self.session.execute(
            text(
                """
                INSERT INTO view_once_media_metadata (
                    source_message_id, source_chat_id, source_contact_id,
                    media_type, media_mime, capability_state, evidence_source,
                    transport_available, retention_mode,
                    first_observed_at, last_observed_at
                ) VALUES (
                    :source_message_id, :source_chat_id, :source_contact_id,
                    :media_type, :media_mime, :capability_state, :evidence_source,
                    :transport_available, 'none',
                    now(), now()
                )
                ON CONFLICT (source_message_id) DO UPDATE SET
                    media_type = COALESCE(EXCLUDED.media_type, view_once_media_metadata.media_type),
                    media_mime = COALESCE(EXCLUDED.media_mime, view_once_media_metadata.media_mime),
                    capability_state = EXCLUDED.capability_state,
                    evidence_source = EXCLUDED.evidence_source,
                    transport_available = EXCLUDED.transport_available,
                    last_observed_at = now()
                WHERE view_once_media_metadata.deleted_at IS NULL
                """
            ),
            {
                "source_message_id": source_message_id,
                "source_chat_id": source_chat_id,
                "source_contact_id": source_contact_id,
                "media_type": media_type,
                "media_mime": media_mime,
                "capability_state": capability_state,
                "evidence_source": evidence_source,
                "transport_available": transport_available,
            },
        )
