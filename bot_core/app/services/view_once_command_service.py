from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, OutboundMessage
from app.services.admin_management_service import AdminManagementService
from app.services.bot_config_service import BotConfigService
from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.services.view_once_media_service import ViewOnceMediaService
from app.utils.time import utcnow


@dataclass(slots=True)
class ViewOnceCommandResult:
    consumed: bool
    command: str
    reply_text: str | None = None
    outbound_queue_id: int | None = None
    error: str | None = None


class ViewOnceCommandService:
    """OWNER-only view-once command implementation over real WAHA evidence.

    Persistent media retention is deliberately unavailable until Zina has a private,
    bounded byte-storage boundary. `.vv` can still perform one immediate private
    delivery when the authenticated quoted WAHA snapshot contains both explicit
    view-once evidence and a retrievable media URL. The URL exists only in memory and
    in the existing transient outbound queue needed to deliver it; it is never copied
    into view-once metadata or audit records.
    """

    CONFIG_RETENTION_KEY = "view_once.retention_enabled"
    OPEN_COMMANDS = frozenset({".vv", ".vvopen", "/vvopen"})

    def __init__(self, session: AsyncSession):
        self.session = session
        self.media = ViewOnceMediaService(session)
        self.config = BotConfigService(session)

    async def handle(
        self,
        command: str,
        args: str,
        *,
        message: Any,
        owner: Any,
        permission: str,
        request_id: str | None = None,
        transport_message_id: str | None = None,
    ) -> ViewOnceCommandResult:
        canonical = "/vvopen"
        if (permission or "").strip().lower() != "owner":
            await self._audit("view_once_command_denied", command, request_id, transport_message_id, {"reason": "owner_required"})
            return ViewOnceCommandResult(True, canonical, reply_text="Owner command. Access denied.", error="owner permission required")

        owner_chat_id = owner.normalized_whatsapp_id or AdminManagementService.normalize_whatsapp_id(owner.whatsapp_number)
        if not owner_chat_id:
            return ViewOnceCommandResult(True, canonical, reply_text="Owner self-DM identity is unavailable.", error="owner chat unavailable")

        normalized_args = (args or "").strip()
        if command in self.OPEN_COMMANDS:
            return await self._open(message, owner_chat_id, request_id, transport_message_id)
        if command == ".vv":
            return await self._open(message, owner_chat_id, request_id, transport_message_id)
        if command == ".vvretain":
            return await self._retention(normalized_args, owner_chat_id, request_id, transport_message_id)

        subcommand = ""
        rest = ""
        if command == ".vv":
            subcommand, _, rest = normalized_args.partition(" ")
        elif command.startswith(".vv "):
            subcommand = command[4:].strip()
            rest = normalized_args
        else:
            subcommand, _, rest = normalized_args.partition(" ")
        subcommand = subcommand.lower().strip()

        if subcommand == "info":
            return await self._info(message, owner_chat_id, request_id, transport_message_id)
        if subcommand == "list":
            return await self._list(rest, owner_chat_id, request_id, transport_message_id)
        if subcommand == "delete":
            return await self._delete(message, rest, owner_chat_id, request_id, transport_message_id)

        return ViewOnceCommandResult(
            True,
            canonical,
            reply_text="View-once commands: .vv, .vvopen, .vv info, .vv list [limit], .vv delete [source-id], .vvretain off. Persistent .vvretain on is unavailable until private byte retention is implemented.",
            error="unsupported view-once subcommand",
        )

    async def _open(self, message: Any, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        capability, record = await self.media.observe_reply(message)
        if record is None:
            return await self._text(owner_chat_id, "/vvopen", capability.reason, "source message unavailable")
        if capability.is_view_once is not True:
            await self._audit("view_once_retrieval_denied", "/vvopen", request_id, transport_message_id, {"source_message_id": record.source_message_id, "state": record.capability_state})
            return await self._text(owner_chat_id, "/vvopen", capability.reason, "view-once capability unproven")
        if not capability.retrievable_now or not capability.media_url:
            await self._audit("view_once_media_unavailable", "/vvopen", request_id, transport_message_id, {"source_message_id": record.source_message_id, "state": record.capability_state})
            return await self._text(owner_chat_id, "/vvopen", capability.reason, "media unavailable")

        media_type = self._safe_media_type(capability.media_type, capability.media_mime)
        if media_type is None:
            return await self._text(owner_chat_id, "/vvopen", "View-once media type is unsupported for safe outbound delivery.", "unsupported media type")

        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text="",
            media_url=capability.media_url,
            media_type=media_type,
            media_caption=f"View-once source {record.source_message_id}",
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={"source": "view_once_command", "source_message_id": record.source_message_id},
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()
        await self.media.mark_returned(record.source_message_id)
        await self._audit("view_once_returned_to_owner", "/vvopen", request_id, transport_message_id, {"source_message_id": record.source_message_id, "media_type": media_type})
        return ViewOnceCommandResult(True, "/vvopen", outbound_queue_id=queued.id)

    async def _info(self, message: Any, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        capability, record = await self.media.observe_reply(message)
        if record is None:
            return await self._text(owner_chat_id, "/vvopen", capability.reason, "source message unavailable")
        text_value = (
            "VIEW-ONCE INFO\n"
            f"Source ID: {record.source_message_id}\n"
            f"Source chat: {record.source_chat_id}\n"
            f"State: {record.capability_state}\n"
            f"Type: {record.media_type or 'unknown'}\n"
            f"MIME: {record.media_mime or 'unknown'}\n"
            f"Transport available now: {'yes' if capability.retrievable_now else 'no'}\n"
            f"Evidence: {record.evidence_source}\n"
            "Persistent media retained: no"
        )
        await self._audit("view_once_info", "/vvopen", request_id, transport_message_id, {"source_message_id": record.source_message_id, "state": record.capability_state})
        return await self._text(owner_chat_id, "/vvopen", text_value)

    async def _list(self, raw_limit: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        try:
            limit = int((raw_limit or "").strip()) if (raw_limit or "").strip() else self.media.DEFAULT_LIST_LIMIT
        except ValueError:
            return await self._text(owner_chat_id, "/vvopen", "List limit must be a number.", "invalid list limit")
        rows = await self.media.list_recent(limit)
        if not rows:
            return await self._text(owner_chat_id, "/vvopen", "No view-once metadata has been observed yet.")
        lines = [f"VIEW-ONCE ITEMS — {len(rows)} shown"]
        for row in rows:
            lines.append(f"#{row.id} | {row.source_message_id} | {row.media_type or 'unknown'} | {row.capability_state}")
        await self._audit("view_once_list", "/vvopen", request_id, transport_message_id, {"count": len(rows)})
        return await self._text(owner_chat_id, "/vvopen", "\n".join(lines))

    async def _delete(self, message: Any, explicit_id: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        source_id = (explicit_id or "").strip()[:200]
        if not source_id:
            capability = ViewOnceCapabilityService.inspect_reply_snapshot(getattr(message, "payload", None))
            source_id = capability.source_message_id or ""
        if not source_id:
            return await self._text(owner_chat_id, "/vvopen", "Reply to an observed item or provide its source message ID.", "source id required")
        changed = await self.media.delete_metadata(source_id)
        if not changed:
            return await self._text(owner_chat_id, "/vvopen", "No active retained/observed metadata exists for that source ID.", "item not found")
        await self._audit("view_once_metadata_deleted", "/vvopen", request_id, transport_message_id, {"source_message_id": source_id})
        return await self._text(owner_chat_id, "/vvopen", f"View-once metadata deleted for {source_id}. No media bytes were retained by Zina.")

    async def _retention(self, raw_value: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        value = (raw_value or "").strip().lower()
        if value == "off":
            await self.config.set(self.CONFIG_RETENTION_KEY, "false")
            await self._audit("view_once_retention_disabled", "/vvopen", request_id, transport_message_id, {"enabled": False})
            return await self._text(owner_chat_id, "/vvopen", "View-once automatic retention is OFF. Zina does not persist view-once media bytes.")
        if value == "on":
            await self.config.set(self.CONFIG_RETENTION_KEY, "false")
            await self._audit("view_once_retention_enable_rejected", "/vvopen", request_id, transport_message_id, {"reason": "private_byte_storage_unavailable"})
            return await self._text(owner_chat_id, "/vvopen", "Automatic view-once retention cannot be enabled yet: Zina has no approved private byte-retention store. Retention remains OFF.", "retention unsupported")
        current = (await self.config.get(self.CONFIG_RETENTION_KEY, "false")).strip().lower() == "true"
        return await self._text(owner_chat_id, "/vvopen", f"View-once automatic retention: {'ON' if current else 'OFF'}. Persistent byte retention is currently unsupported.")

    async def _text(self, owner_chat_id: str, command: str, text_value: str, error: str | None = None) -> ViewOnceCommandResult:
        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=text_value[:3500],
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={"source": "view_once_command", "command": command},
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()
        return ViewOnceCommandResult(True, command, reply_text=text_value, outbound_queue_id=queued.id, error=error)

    async def _audit(self, action: str, command: str, request_id: str | None, transport_message_id: str | None, details: dict[str, Any]) -> None:
        self.session.add(
            AuditLog(
                action=action,
                entity_type="view_once_media",
                entity_id=str(details.get("source_message_id") or "") or None,
                details_json={
                    "command": command,
                    "request_id": request_id,
                    "transport_message_id": transport_message_id,
                    **details,
                },
            )
        )
        await self.session.flush()

    @staticmethod
    def _safe_media_type(media_type: str | None, mime: str | None) -> str | None:
        candidate = (media_type or "").strip().lower()
        mime_value = (mime or "").strip().lower()
        if candidate in {"image", "video", "audio"}:
            return candidate
        if mime_value.startswith("image/"):
            return "image"
        if mime_value.startswith("video/"):
            return "video"
        if mime_value.startswith("audio/"):
            return "audio"
        return None
