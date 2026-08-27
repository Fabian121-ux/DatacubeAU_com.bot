from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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
    """OWNER-only view-once command implementation over real WAHA evidence."""

    CONFIG_RETENTION_KEY = "view_once.retention_enabled"
    OPEN_COMMANDS = frozenset({".vvopen", "/vvopen"})
    MAX_MEDIA_BYTES = 50 * 1024 * 1024
    MAX_TEXT_REPLY_CHARS = 3500
    MAX_LIST_BODY_CHARS = 3250

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
        if command == ".vvretain":
            return await self._retention(normalized_args, owner_chat_id, request_id, transport_message_id)

        # `.vv` with no arguments is the open/retrieve shorthand. With arguments it
        # is the namespace for info/list/delete; dispatch subcommands before opening.
        if command == ".vv" and not normalized_args:
            return await self._open(message, owner_chat_id, request_id, transport_message_id)

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
        if media_type == "video":
            await self._audit(
                "view_once_video_delivery_unavailable",
                "/vvopen",
                request_id,
                transport_message_id,
                {"source_message_id": record.source_message_id},
            )
            return await self._text(
                owner_chat_id,
                "/vvopen",
                "WAHA exposed this view-once video, but Zina does not yet have a verified video-capable outbound adapter. The video was not queued or retained.",
                "video delivery unavailable",
            )
        if media_type != "image":
            return await self._text(owner_chat_id, "/vvopen", "View-once media type is unsupported for safe outbound delivery. Only verified image delivery is currently enabled.", "unsupported media type")
        if not self._trusted_waha_media_url(capability.media_url):
            await self._audit(
                "view_once_media_url_rejected",
                "/vvopen",
                request_id,
                transport_message_id,
                {"source_message_id": record.source_message_id, "reason": "untrusted_waha_media_origin"},
            )
            return await self._text(owner_chat_id, "/vvopen", "WAHA exposed a media URL outside the configured WAHA file origin. Retrieval was blocked.", "untrusted media url")

        media_size = ViewOnceCapabilityService.reply_media_size(getattr(message, "payload", None))
        if media_size is not None and media_size > self.MAX_MEDIA_BYTES:
            await self._audit(
                "view_once_media_size_rejected",
                "/vvopen",
                request_id,
                transport_message_id,
                {"source_message_id": record.source_message_id, "size_bytes": media_size},
            )
            return await self._text(owner_chat_id, "/vvopen", "View-once media exceeds Zina's 50 MB safe delivery limit.", "media too large")

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
        await self._audit(
            "view_once_delivery_queued",
            "/vvopen",
            request_id,
            transport_message_id,
            {"source_message_id": record.source_message_id, "media_type": media_type, "size_bytes": media_size, "outbound_queue_id": queued.id},
        )
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
            f"Retention mode: {record.retention_mode}\n"
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

        rendered_rows: list[str] = []
        for row in rows:
            entry = (
                f"#{row.id} | {row.source_message_id} | {row.source_chat_id} | "
                f"{row.media_type or 'unknown'} | {row.capability_state} | retention={row.retention_mode}"
            )
            candidate_body = "\n".join(rendered_rows + [entry])
            if len(candidate_body) > self.MAX_LIST_BODY_CHARS:
                break
            rendered_rows.append(entry)

        header = f"VIEW-ONCE ITEMS — {len(rendered_rows)} shown of {len(rows)} matched"
        lines = [header, *rendered_rows]
        if len(rendered_rows) < len(rows):
            lines.append("Additional rows were omitted to keep the WhatsApp response within the safe size limit.")
        await self._audit(
            "view_once_list",
            "/vvopen",
            request_id,
            transport_message_id,
            {"displayed_count": len(rendered_rows), "matched_count": len(rows)},
        )
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
        safe_text = text_value[: self.MAX_TEXT_REPLY_CHARS]
        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=safe_text,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={"source": "view_once_command", "command": command},
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()
        return ViewOnceCommandResult(True, command, reply_text=safe_text, outbound_queue_id=queued.id, error=error)

    async def _audit(self, action: str, command: str, request_id: str | None, transport_message_id: str | None, details: dict[str, Any]) -> None:
        self.session.add(
            AuditLog(
                action=action,
                entity_type="view_once_media",
                entity_id=str(details.get("source_message_id") or "") or None,
                details_json={"command": command, "request_id": request_id, "transport_message_id": transport_message_id, **details},
            )
        )
        await self.session.flush()

    @staticmethod
    def _safe_media_type(media_type: str | None, mime: str | None) -> str | None:
        candidate = (media_type or "").strip().lower()
        mime_value = (mime or "").strip().lower()
        if candidate in {"image", "video"}:
            return candidate
        if mime_value.startswith("image/"):
            return "image"
        if mime_value.startswith("video/"):
            return "video"
        return None

    @classmethod
    def _trusted_waha_media_url(cls, media_url: str) -> bool:
        candidate = cls._normalized_origin(media_url)
        if candidate is None:
            return False
        scheme, host, port, path = candidate
        if scheme not in {"http", "https"} or not path.startswith("/api/files/"):
            return False

        trusted_origins = set()
        for configured in (settings.waha_service_url, settings.waha_base_url):
            origin = cls._normalized_origin(configured)
            if origin is not None:
                trusted_origins.add(origin[:3])
        return (scheme, host, port) in trusted_origins

    @staticmethod
    def _normalized_origin(value: str | None) -> tuple[str, str, int | None, str] | None:
        parsed = urlparse(str(value or "").strip())
        if not parsed.scheme or not parsed.hostname:
            return None
        scheme = parsed.scheme.lower()
        host = parsed.hostname.lower().rstrip(".")
        try:
            port = parsed.port
        except ValueError:
            return None
        if port is None:
            port = 443 if scheme == "https" else 80 if scheme == "http" else None
        return scheme, host, port, parsed.path or "/"
