from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
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
    DELIVERY_CAPABILITY_TTL = timedelta(minutes=15)

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

        if command == ".vv" and not normalized_args:
            return await self._open(message, owner_chat_id, request_id, transport_message_id)

        parts = normalized_args.split(maxsplit=1)
        subcommand = parts[0].lower().strip() if parts else ""
        rest = parts[1] if len(parts) > 1 else ""

        if subcommand == "info":
            return await self._info(message, owner_chat_id, request_id, transport_message_id)
        if subcommand == "list":
            return await self._list(rest, owner_chat_id, request_id, transport_message_id)
        if subcommand == "delete":
            return await self._delete(message, rest, owner_chat_id, request_id, transport_message_id)

        return await self._text(
            owner_chat_id,
            canonical,
            "View-once commands: .vv, .vvopen, .vv info, .vv list [limit], .vv delete [source-id], .vvretain off. Persistent .vvretain on is unavailable until private byte retention is implemented.",
            "unsupported view-once subcommand",
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
                {"source_message_id": record.source_message_id, "reported_size": media_size},
            )
            return await self._text(
                owner_chat_id,
                "/vvopen",
                "WAHA reports this view-once media is larger than the 50 MB safety limit, so it was not queued or retained.",
                "media too large",
            )

        capability_expires_at = utcnow() + self.DELIVERY_CAPABILITY_TTL
        outbound = OutboundMessage(
            chat_id=owner_chat_id,
            message_text="",
            media_url=capability.media_url,
            media_type="image",
            status="pending",
            retry_count=0,
            formatting_json={
                "source": "view_once_command",
                "source_message_id": record.source_message_id,
                "capability_expires_at": capability_expires_at.isoformat(),
                "resendable": True,
            },
        )
        self.session.add(outbound)
        await self.session.flush()
        await self._audit(
            "view_once_media_queued",
            "/vvopen",
            request_id,
            transport_message_id,
            {
                "source_message_id": record.source_message_id,
                "outbound_queue_id": outbound.id,
                "media_type": "image",
                "capability_expires_at": capability_expires_at.isoformat(),
            },
        )
        await self.session.commit()
        return ViewOnceCommandResult(
            consumed=True,
            command="/vvopen",
            reply_text="View-once image queued for private owner delivery.",
            outbound_queue_id=outbound.id,
        )

    async def _info(self, message: Any, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        capability, record = await self.media.observe_reply(message)
        if record is None:
            return await self._text(owner_chat_id, "/vvopen", capability.reason, "source message unavailable")
        body = (
            "VIEW-ONCE INFO\n"
            f"Source ID: {record.source_message_id}\n"
            f"Source chat: {record.source_chat_id or 'unknown'}\n"
            f"Media type: {record.media_type or 'unknown'}\n"
            f"MIME: {record.media_mime or 'unknown'}\n"
            f"Capability state: {record.capability_state}\n"
            f"Transport available: {'yes' if record.transport_available else 'no'}\n"
            f"Retention: {record.retention_mode}\n"
            f"Observed: {record.first_observed_at.isoformat() if record.first_observed_at else 'unknown'}\n"
            f"Returned: {record.returned_to_owner_at.isoformat() if record.returned_to_owner_at else 'not returned'}\n"
            f"Deleted: {record.deleted_at.isoformat() if record.deleted_at else 'no'}\n"
            f"Evidence: {record.evidence_source}"
        )
        return await self._text(owner_chat_id, "/vvopen", body, None)

    async def _list(self, args: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        limit = 10
        raw = (args or "").strip()
        if raw:
            try:
                limit = int(raw)
            except ValueError:
                return await self._text(owner_chat_id, "/vvopen", "Usage: .vv list [1-25]", "invalid list limit")
        limit = max(1, min(limit, 25))
        rows = await self.media.list_recent(limit=limit)
        if not rows:
            return await self._text(owner_chat_id, "/vvopen", "VIEW-ONCE ITEMS\nNo observed view-once metadata yet.", None)

        lines = ["VIEW-ONCE ITEMS"]
        displayed = 0
        for row in rows:
            line = (
                f"{displayed + 1}. {row.source_message_id} | {row.source_chat_id or 'unknown'} | "
                f"{row.media_type or 'unknown'} | {row.capability_state} | "
                f"{row.last_observed_at.isoformat() if row.last_observed_at else 'unknown'}"
            )
            prospective = "\n".join(lines + [line])
            if len(prospective) > self.MAX_LIST_BODY_CHARS:
                break
            lines.append(line)
            displayed += 1
        lines.insert(1, f"{displayed} shown of {len(rows)} matched")
        if displayed < len(rows):
            lines.append("Additional matched rows were omitted to keep the WhatsApp reply bounded.")
        return await self._text(owner_chat_id, "/vvopen", "\n".join(lines), None)

    async def _delete(self, message: Any, args: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        source_id = (args or "").strip()
        if not source_id:
            capability = ViewOnceCapabilityService.inspect_reply_snapshot(getattr(message, "payload", None))
            source_id = capability.source_message_id or ""
        if not source_id:
            return await self._text(owner_chat_id, "/vvopen", "Reply to a view-once item or provide its source ID: .vv delete <source-id>", "source message unavailable")
        record = await self.media.delete(source_id)
        if record is None:
            return await self._text(owner_chat_id, "/vvopen", "No matching view-once metadata was found.", "view-once item not found")
        await self._audit("view_once_metadata_deleted", "/vvopen", request_id, transport_message_id, {"source_message_id": source_id})
        return await self._text(owner_chat_id, "/vvopen", f"View-once metadata for {source_id} is marked deleted. No retained media bytes exist in this version.", None)

    async def _retention(self, args: str, owner_chat_id: str, request_id: str | None, transport_message_id: str | None) -> ViewOnceCommandResult:
        value = (args or "").strip().lower()
        if value == "off":
            await self.config.set(self.CONFIG_RETENTION_KEY, "false")
            await self._audit("view_once_retention_changed", "/vvopen", request_id, transport_message_id, {"enabled": False})
            return await self._text(owner_chat_id, "/vvopen", "View-once automatic retention is OFF. Zina will not silently archive ephemeral media.", None)
        if value == "on":
            await self.config.set(self.CONFIG_RETENTION_KEY, "false")
            await self._audit("view_once_retention_enable_rejected", "/vvopen", request_id, transport_message_id, {"reason": "persistent_byte_store_unavailable"})
            return await self._text(owner_chat_id, "/vvopen", "Persistent view-once retention cannot be enabled yet because Zina has no approved private media-byte store. Retention remains OFF.", "retention unsupported")
        return await self._text(owner_chat_id, "/vvopen", "Usage: .vvretain on|off", "invalid retention value")

    async def _text(self, owner_chat_id: str, command: str, text: str, error: str | None) -> ViewOnceCommandResult:
        safe = text[: self.MAX_TEXT_REPLY_CHARS]
        outbound = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=safe,
            status="pending",
            retry_count=0,
            formatting_json={"source": "view_once_command", "resendable": True},
        )
        self.session.add(outbound)
        await self.session.flush()
        await self.session.commit()
        return ViewOnceCommandResult(True, command, reply_text=safe, outbound_queue_id=outbound.id, error=error)

    async def _audit(
        self,
        event_type: str,
        command: str,
        request_id: str | None,
        transport_message_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self.session.add(
            AuditLog(
                event_type=event_type,
                entity_type="view_once_command",
                entity_id=transport_message_id or request_id,
                metadata_json={"command": command, "request_id": request_id, **metadata},
            )
        )
        await self.session.flush()

    @staticmethod
    def _safe_media_type(media_type: str | None, media_mime: str | None) -> str | None:
        type_value = str(media_type or "").strip().lower()
        mime_value = str(media_mime or "").strip().lower()
        type_category = type_value if type_value in {"image", "video"} else None
        mime_category = None
        if mime_value.startswith("image/"):
            mime_category = "image"
        elif mime_value.startswith("video/"):
            mime_category = "video"
        if type_category and mime_category and type_category != mime_category:
            return None
        return type_category or mime_category

    @staticmethod
    def _trusted_waha_media_url(url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if not parsed.path.startswith("/api/files/"):
            return False
        trusted_origins = {settings.waha_service_url.rstrip("/"), settings.waha_base_url.rstrip("/")}
        candidate_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
        return candidate_origin in trusted_origins
