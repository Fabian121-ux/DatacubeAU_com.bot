from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AdminAccount, AuditLog, OutboundMessage
from app.services.admin_management_service import AdminManagementService
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.outbound_media_metadata_service import OutboundMediaMetadataService
from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.utils.time import utcnow


@dataclass(slots=True)
class ViewOnceCommandResult:
    consumed: bool
    reply_text: str | None = None
    outbound_queue_id: int | None = None
    error: str | None = None


class ViewOnceCommandService:
    """OWNER-only view-once inspection and private media return.

    This service is capability inspection plus queueing. It is never authority: it makes
    no WAHA call, and every row it creates still passes the existing P0 final
    authorization fence, safety limits, and typed dispatch before delivery.

    Media may only be returned when an exact same-source transient capability exists at
    command time. The durable metadata record deliberately stores whether a locator was
    once observed, never the locator itself, so a historical observation alone can never
    produce a send. When the transport no longer exposes the media, the truthful answer
    is "unavailable".
    """

    COMMAND = "/vvopen"
    LIST_LIMIT = 20
    MAX_MEDIA_BYTES = 64 * 1024 * 1024

    # Only WAHA's own file capability is trusted as a media origin.
    _TRUSTED_MEDIA_PATH = "/api/files/"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle(
        self,
        operation: str,
        *,
        message: Any,
        owner: AdminAccount,
        transport_message_id: str | None = None,
        request_id: str | None = None,
    ) -> ViewOnceCommandResult:
        owner_chat_id = self._owner_chat_id(owner)
        if not owner_chat_id:
            return ViewOnceCommandResult(True, error="owner self-DM identity unavailable")

        if operation == "retain_on":
            return self._reply(
                "Persistent private-media retention is not available yet.\n\n"
                "Zina has no private media store, so nothing can be retained. Retention is OFF."
            )
        if operation == "retain_off":
            return self._reply("Persistent private-media retention is OFF. Zina stores no view-once media bytes.")
        if operation == "list":
            return await self._list()

        quoted_id = self._quoted_source_message_id(getattr(message, "payload", None))
        if not quoted_id:
            return self._reply("Reply directly to the target message with .vvopen.")

        record = await self._record(quoted_id)

        if operation == "info":
            return self._info(record, quoted_id)
        if operation == "delete":
            return await self._delete(record, quoted_id, request_id=request_id)
        return await self._open(
            record,
            quoted_id,
            message=message,
            owner_chat_id=owner_chat_id,
            transport_message_id=transport_message_id,
            request_id=request_id,
        )

    # ----------------------------------------------------------------------------------
    # .vv / .vvopen
    # ----------------------------------------------------------------------------------

    async def _open(
        self,
        record: dict[str, Any] | None,
        quoted_id: str,
        *,
        message: Any,
        owner_chat_id: str,
        transport_message_id: str | None,
        request_id: str | None,
    ) -> ViewOnceCommandResult:
        if record is None:
            return self._reply(
                "Zina has not observed this message as view-once, so there is nothing to open."
            )
        if record["deleted_at"] is not None:
            return self._reply("Zina's metadata for this item was deleted, so it can no longer be opened.")

        # Re-derive evidence from the live command payload rather than trusting the
        # stored state. Conflicting or downgraded evidence must fail closed here too.
        capability = ViewOnceCapabilityService.inspect_reply_snapshot(getattr(message, "payload", None))
        if capability.is_view_once is False:
            return self._reply("This message is not confirmed as view-once.")
        if capability.is_view_once is None:
            return self._reply(
                "Zina cannot confirm view-once status for this message from the current WhatsApp evidence."
            )
        if capability.source_message_id and capability.source_message_id != quoted_id:
            return self._reply(
                "The quoted WhatsApp evidence does not match the exact source message, so this request was denied."
            )

        # Source A: the OWNER command's own reply snapshot. If WAHA no longer exposes a
        # locator there, the media is genuinely gone from the transport.
        if not capability.media_url:
            return self._reply(
                "This message is confirmed as view-once, but the media is no longer available "
                "from the WhatsApp transport."
            )

        if not self._is_trusted_locator(capability.media_url):
            return self._reply(
                "The media capability for this message did not come from a trusted WhatsApp transport path, "
                "so it was not returned."
            )

        size = ViewOnceCapabilityService.reply_media_size(getattr(message, "payload", None))
        if size is not None and size > self.MAX_MEDIA_BYTES:
            return self._reply("This view-once media exceeds the safe return size limit.")

        # The detector nulls both media type and MIME when the snapshot's own evidence
        # disagrees (for example type=video with an image MIME). Falling back to the
        # stored record here would launder that conflict into a send, so ambiguous live
        # evidence must fail closed instead.
        if capability.media_type is None and capability.media_mime is None:
            return self._reply(
                "The WhatsApp evidence for this media is ambiguous or conflicting, so it was not returned."
            )

        decision = OutboundMediaMetadataService.normalize(
            media_url=capability.media_url,
            media_kind=capability.media_type,
            mimetype=capability.media_mime,
            provenance="view_once_command",
        )
        if not decision.accepted:
            return self._reply(f"This view-once media could not be returned safely: {decision.reason}")

        existing = await self._existing_return(transport_message_id)
        if existing is not None:
            return ViewOnceCommandResult(True, outbound_queue_id=existing)

        caption = f"View-once {decision.media.media_kind} from your WhatsApp history."
        metadata = {
            "source": "owner_view_once",
            "command": self.COMMAND,
            "command_message_id": transport_message_id,
            "source_message_id": quoted_id,
            **decision.media.queue_metadata(),
        }
        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=caption,
            media_url=decision.media.media_url,
            media_type=decision.media.media_kind,
            media_caption=caption,
            formatting_json=metadata,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()

        # Private media crosses the owner fast path in the delivery fence, which proves
        # the destination but not the payload. Stamp the canonical media-aware authority
        # digest so any later mutation of the locator, kind, caption or text invalidates
        # this row at the fence. The shared hash contract is reused, not re-invented.
        queued.formatting_json = {
            **metadata,
            "authority_content_hash": OutboundAuthorizationService.content_hash_for_message(queued),
        }
        await self.session.flush()

        await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET returned_to_owner_at = now(), last_observed_at = now()
                WHERE source_message_id = :source_message_id AND deleted_at IS NULL
                """
            ),
            {"source_message_id": quoted_id},
        )
        self.session.add(
            AuditLog(
                action="view_once_returned_to_owner",
                entity_type="outbound_queue",
                entity_id=str(queued.id),
                details_json={
                    "request_id": request_id,
                    "source_message_id": quoted_id,
                    "media_kind": decision.media.media_kind,
                    "media_mime": decision.media.mimetype,
                },
            )
        )
        await self.session.flush()
        return ViewOnceCommandResult(True, outbound_queue_id=queued.id)

    # ----------------------------------------------------------------------------------
    # .vv info / list / delete
    # ----------------------------------------------------------------------------------

    def _info(self, record: dict[str, Any] | None, quoted_id: str) -> ViewOnceCommandResult:
        if record is None:
            return self._reply(f"No view-once metadata observed for source {quoted_id}.")

        state = "deleted" if record["deleted_at"] is not None else "active"
        # Stored availability is observation-time truth. Current availability is only
        # known when the OWNER replies to the message, so it is never asserted here.
        observed_capability = "yes" if record["transport_available"] else "no"
        return self._reply(
            "\n".join(
                [
                    "*View-once metadata*",
                    f"Source: {record['source_message_id']}",
                    "Confirmed view-once: yes",
                    f"Media kind: {record['media_type'] or 'unknown'}",
                    f"MIME: {record['media_mime'] or 'unknown'}",
                    f"Transport capability when observed: {observed_capability}",
                    "Available now: unknown until you reply with .vvopen",
                    f"First observed: {record['first_observed_at']}",
                    f"Last observed: {record['last_observed_at']}",
                    f"Returned to owner: {'yes' if record['returned_to_owner_at'] else 'no'}",
                    f"Record state: {state}",
                    "Retention: OFF",
                ]
            )
        )

    async def _list(self) -> ViewOnceCommandResult:
        rows = (
            await self.session.execute(
                text(
                    """
                    SELECT source_message_id, media_type, capability_state,
                           transport_available, last_observed_at
                    FROM view_once_media_metadata
                    WHERE deleted_at IS NULL
                    ORDER BY last_observed_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": self.LIST_LIMIT},
            )
        ).mappings().all()

        if not rows:
            return self._reply("No view-once media has been observed yet.")

        lines = ["*Recent view-once observations*", ""]
        for index, row in enumerate(rows, start=1):
            observed = "capability seen" if row["transport_available"] else "no capability"
            lines.append(
                f"{index}. {row['media_type'] or 'unknown'} — {observed} — {row['last_observed_at']}"
            )
        lines.extend(
            [
                "",
                f"Showing up to {self.LIST_LIMIT}. Reply directly to a message with .vvopen to open it;"
                " list position is not an identifier.",
            ]
        )
        return self._reply("\n".join(lines))

    async def _delete(
        self,
        record: dict[str, Any] | None,
        quoted_id: str,
        *,
        request_id: str | None,
    ) -> ViewOnceCommandResult:
        if record is None:
            return self._reply(f"No view-once metadata observed for source {quoted_id}.")
        if record["deleted_at"] is not None:
            return self._reply("Zina's metadata for this item was already deleted.")

        await self.session.execute(
            text(
                """
                UPDATE view_once_media_metadata
                SET deleted_at = now(), capability_state = 'deleted', transport_available = false
                WHERE source_message_id = :source_message_id AND deleted_at IS NULL
                """
            ),
            {"source_message_id": quoted_id},
        )
        self.session.add(
            AuditLog(
                action="view_once_metadata_deleted",
                entity_type="view_once_media_metadata",
                entity_id=quoted_id,
                details_json={"request_id": request_id, "source_message_id": quoted_id},
            )
        )
        await self.session.flush()
        return self._reply(
            "Zina's metadata for this item was deleted. Zina never stored the media itself, "
            "so no media bytes were removed."
        )

    # ----------------------------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------------------------

    async def _record(self, source_message_id: str) -> dict[str, Any] | None:
        row = (
            await self.session.execute(
                text(
                    """
                    SELECT source_message_id, source_chat_id, media_type, media_mime,
                           capability_state, transport_available, first_observed_at,
                           last_observed_at, returned_to_owner_at, deleted_at
                    FROM view_once_media_metadata
                    WHERE source_message_id = :source_message_id
                    LIMIT 1
                    """
                ),
                {"source_message_id": source_message_id},
            )
        ).mappings().first()
        return dict(row) if row is not None else None

    async def _existing_return(self, transport_message_id: str | None) -> int | None:
        """One OWNER command message must not queue two private returns."""
        if not transport_message_id:
            return None
        metadata = OutboundMessage.formatting_json
        from sqlalchemy import select

        row = (
            await self.session.execute(
                select(OutboundMessage.id)
                .where(metadata["source"].as_string() == "owner_view_once")
                .where(metadata["command_message_id"].as_string() == transport_message_id)
                .order_by(OutboundMessage.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return int(row) if row is not None else None

    @classmethod
    def _is_trusted_locator(cls, media_url: str) -> bool:
        return cls._TRUSTED_MEDIA_PATH in str(media_url or "")

    @staticmethod
    def _quoted_source_message_id(payload: Any) -> str | None:
        """Exact replied-to source only. Never a fuzzy or positional lookup."""
        if not isinstance(payload, dict):
            return None
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return None
        raw = reply_to.get("id")
        if isinstance(raw, dict):
            raw = raw.get("_serialized") or raw.get("id")
        value = str(raw or "").strip()
        return value if value and len(value) <= 200 else None

    @staticmethod
    def _owner_chat_id(owner: AdminAccount) -> str | None:
        return (
            owner.normalized_whatsapp_id
            or AdminManagementService.normalize_whatsapp_id(owner.whatsapp_number)
        )

    @staticmethod
    def _reply(text_value: str) -> ViewOnceCommandResult:
        return ViewOnceCommandResult(True, reply_text=text_value)
