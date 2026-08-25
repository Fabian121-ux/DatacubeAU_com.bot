from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, Contact, OutboundMessage
from app.services.admin_management_service import AdminManagementService
from app.services.bot_config_service import BotConfigService
from app.services.command_catalog_service import CommandCatalogService
from app.services.natural_action_planner_service import DEFAULT_OWNER_TIMEZONE, NaturalActionPlannerService
from app.services.owner_command_service import OwnerCommandService
from app.utils.time import utcnow


@dataclass(slots=True)
class CommandControlResult:
    consumed: bool
    command: str | None = None
    reply_text: str | None = None
    outbound_queue_id: int | None = None
    scheduled_action_id: int | None = None
    error: str | None = None


class CommandControlService:
    """Owner self-DM command surface backed by existing Zina subsystems.

    This is a parsing/session adapter, not a second command engine. Existing slash
    commands still execute through OwnerCommandService; guided scheduling persists a
    short-lived draft in PostgreSQL bot_config and saves through the existing
    NaturalActionPlanner -> Tool Dispatcher -> ScheduledActionService chain.
    """

    DRAFT_TTL = timedelta(minutes=30)
    SCHEDULE_COMMAND = "/schedule"
    _GUIDED = {".sch", ".target", ".message", ".date", ".time", ".save", ".cancel"}

    def __init__(self, session: AsyncSession):
        self.session = session
        self.admins = AdminManagementService(session)
        self.config = BotConfigService(session)
        self.catalog = CommandCatalogService(session)

    async def handle_from_me(
        self,
        message: Any,
        *,
        transport_message_id: str | None = None,
        request_id: str | None = None,
    ) -> CommandControlResult | None:
        parsed = self.parse(message.message_text)
        if parsed is None:
            return None
        command, args = parsed

        admin = await self.admins.resolve_admin_message(message)
        if admin is None:
            await self._audit(
                "command_control_denied",
                command=command,
                request_id=request_id,
                transport_message_id=transport_message_id,
                details={"reason": "admin_not_resolved"},
            )
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text="Zina command access denied.",
                error="owner authorization failed",
            )

        # Self-DM is the privileged control inbox. A fromMe command typed while
        # messaging another person must not silently become an owner control action.
        if not self._is_self_dm(message, admin):
            return None

        permission = (admin.permission_level or "").strip().lower()
        if command in self._GUIDED or command == self.SCHEDULE_COMMAND:
            if permission != "owner":
                await self._audit(
                    "command_control_denied",
                    command=command,
                    request_id=request_id,
                    transport_message_id=transport_message_id,
                    details={"reason": "owner_required", "permission": permission},
                )
                return await self._finish(
                    message.chat_id,
                    CommandControlResult(
                        consumed=True,
                        command=command,
                        reply_text="Owner command. Access denied.",
                        error="owner permission required",
                    ),
                )
            result = await self._guided_schedule(
                command,
                args,
                message=message,
                admin=admin,
                transport_message_id=transport_message_id,
                request_id=request_id,
            )
            return await self._finish(message.chat_id, result)

        # Dot aliases for existing Command Center commands are only syntax sugar.
        slash_command = self._slash_alias(command)
        if slash_command:
            command = slash_command
            message.message_text = f"{command}{(' ' + args) if args else ''}"

        if not command.startswith("/"):
            return None

        # Enforce authority before calling an existing handler so a limited admin
        # cannot trigger an owner side effect and only then receive a denial reply.
        definition = await self._definition(command)
        required = str((definition or {}).get("permissions") or "user").lower()
        if required == "owner" and permission != "owner":
            await self._audit(
                "command_control_denied",
                command=command,
                request_id=request_id,
                transport_message_id=transport_message_id,
                details={"reason": "owner_required", "permission": permission},
            )
            return await self._finish(
                message.chat_id,
                CommandControlResult(
                    consumed=True,
                    command=command,
                    reply_text="Owner command. Access denied.",
                    error="owner permission required",
                ),
            )

        contact = await self._control_contact(message)
        result = await OwnerCommandService(self.session).handle(message, contact)
        if result is None:
            return None

        await self._audit(
            "command_control_executed",
            command=command,
            request_id=request_id,
            transport_message_id=transport_message_id,
            details={"permission": permission},
        )
        return await self._finish(
            message.chat_id,
            CommandControlResult(consumed=True, command=command, reply_text=result.reply_text),
        )

    @classmethod
    def parse(cls, text_value: str) -> tuple[str, str] | None:
        text = " ".join((text_value or "").strip().split())
        if not text:
            return None
        text = re.sub(r"^@zina\s+", "", text, flags=re.I)
        if not text:
            return None
        first, _, rest = text.partition(" ")
        command = first.strip().lower()
        if not command.startswith((".", "/")):
            return None
        return command, rest.strip()

    @staticmethod
    def _slash_alias(command: str) -> str | None:
        aliases = {
            ".help": "/help",
            ".status": "/status",
            ".whoami": "/whoami",
            ".owner-help": "/owner-help",
            ".reviews": "/reviews",
            ".queue": "/queue",
        }
        return aliases.get(command)

    async def _guided_schedule(
        self,
        command: str,
        args: str,
        *,
        message: Any,
        admin: Any,
        transport_message_id: str | None,
        request_id: str | None,
    ) -> CommandControlResult:
        if not await self.catalog.is_enabled(self.SCHEDULE_COMMAND):
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text="Guided scheduling is currently disabled.",
                error="command disabled",
            )

        key = self._draft_key(admin.id)
        draft = await self._load_draft(key)

        if command in {".sch", self.SCHEDULE_COMMAND}:
            draft = self._new_draft()
            await self._save_draft(key, draft)
            await self.catalog.record_usage(self.SCHEDULE_COMMAND)
            await self._audit(
                "schedule_draft_started",
                command=command,
                request_id=request_id,
                transport_message_id=transport_message_id,
                details={"admin_id": admin.id},
            )
            return CommandControlResult(consumed=True, command=command, reply_text=self._render_draft(draft))

        if command == ".cancel":
            if draft is None:
                return CommandControlResult(consumed=True, command=command, reply_text="No active schedule draft.")
            await self._clear_draft(key)
            await self._audit(
                "schedule_draft_cancelled",
                command=command,
                request_id=request_id,
                transport_message_id=transport_message_id,
                details={"admin_id": admin.id},
            )
            return CommandControlResult(consumed=True, command=command, reply_text="Schedule draft cancelled.")

        if draft is None:
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text="No active schedule draft. Send .sch first.",
                error="no active draft",
            )

        field_map = {".target": "target", ".message": "message", ".date": "date", ".time": "time"}
        if command in field_map:
            if not args:
                example = (
                    "Amanda Christabel"
                    if command == ".target"
                    else "tomorrow"
                    if command == ".date"
                    else "09:00"
                    if command == ".time"
                    else "Tell her the document is ready"
                )
                return CommandControlResult(
                    consumed=True,
                    command=command,
                    reply_text=f"Value required. Example: {command} {example}",
                    error="value required",
                )
            draft[field_map[command]] = args[:2000]
            draft["updated_at"] = utcnow().isoformat()
            draft["expires_at"] = (utcnow() + self.DRAFT_TTL).isoformat()
            await self._save_draft(key, draft)
            return CommandControlResult(consumed=True, command=command, reply_text=self._render_draft(draft))

        if command != ".save":
            return CommandControlResult(consumed=False, command=command)

        missing = [field for field in ("target", "message", "date", "time") if not str(draft.get(field) or "").strip()]
        if missing:
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text="Cannot save yet. Missing: " + ", ".join(missing) + ".",
                error="incomplete draft",
            )

        instruction = (
            f"message {draft['target']} on {draft['date']} at {draft['time']} "
            f"and tell them {draft['message']}"
        )
        idempotency_key = f"guided-schedule:{admin.id}:{transport_message_id}" if transport_message_id else None
        try:
            result = await NaturalActionPlannerService(self.session).create_from_instruction(
                instruction,
                actor_permission=admin.permission_level,
                timezone=str(draft.get("timezone") or DEFAULT_OWNER_TIMEZONE),
                idempotency_key=idempotency_key,
            )
        except ValueError as exc:
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text=f"Schedule not saved: {exc}",
                error=str(exc),
            )
        if not result or not result.get("scheduled_action"):
            return CommandControlResult(
                consumed=True,
                command=command,
                reply_text="Schedule not saved: the draft could not be converted into an action.",
                error="planner rejected draft",
            )

        action = result["scheduled_action"]
        await self._clear_draft(key)
        await self._audit(
            "schedule_draft_saved",
            command=command,
            request_id=request_id,
            transport_message_id=transport_message_id,
            entity_id=str(action.get("id")) if action.get("id") is not None else None,
            details={"admin_id": admin.id, "timezone": result["plan"]["timezone"]},
        )
        return CommandControlResult(
            consumed=True,
            command=command,
            scheduled_action_id=action.get("id"),
            reply_text=(
                "✅ Scheduled\n\n"
                f"Target: {draft['target']}\n"
                f"Date: {draft['date']}\n"
                f"Time: {draft['time']}\n"
                f"Timezone: {result['plan']['timezone']}\n"
                f"Task ID: {action.get('id')}"
            ),
        )

    async def _finish(self, chat_id: str, result: CommandControlResult) -> CommandControlResult:
        if not result.consumed or not result.reply_text:
            return result
        queued = OutboundMessage(
            chat_id=chat_id,
            message_text=result.reply_text,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={"source": "command_control", "command": result.command},
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()
        result.outbound_queue_id = queued.id
        return result

    async def _control_contact(self, message: Any) -> Contact:
        keys = list(AdminManagementService.identity_keys_for_message(message))
        keys.extend([message.sender_id, message.chat_id])
        normalized = [AdminManagementService.normalize_whatsapp_id(item) for item in keys if item]
        normalized = [item for item in normalized if item]
        stmt = select(Contact).where(or_(Contact.whatsapp_id.in_(normalized), Contact.chat_id.in_(normalized))).limit(1)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row:
            return row
        whatsapp_id = AdminManagementService.normalize_whatsapp_id(message.sender_id) or AdminManagementService.normalize_whatsapp_id(message.chat_id)
        row = Contact(
            whatsapp_id=whatsapp_id or message.chat_id or "owner@local",
            chat_id=message.chat_id,
            display_name=message.sender_name or "Fabian",
            last_active_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def _definition(self, name: str) -> dict[str, Any] | None:
        commands = await self.catalog.list_commands()
        return next((item for item in commands if item.get("name") == name), None)

    @staticmethod
    def _is_self_dm(message: Any, admin: Any) -> bool:
        if getattr(message.chat_type, "value", str(message.chat_type)) != "dm":
            return False
        chat_keys = AdminManagementService.identity_keys(message.chat_id)
        admin_keys = AdminManagementService.identity_keys(admin.normalized_whatsapp_id) | AdminManagementService.identity_keys(admin.whatsapp_number)
        return bool(chat_keys & admin_keys)

    @staticmethod
    def _draft_key(admin_id: int) -> str:
        return f"command_draft.schedule.{admin_id}"

    @staticmethod
    def _new_draft() -> dict[str, Any]:
        now = utcnow()
        return {
            "target": "",
            "message": "",
            "date": "",
            "time": "",
            "timezone": DEFAULT_OWNER_TIMEZONE,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "expires_at": (now + CommandControlService.DRAFT_TTL).isoformat(),
        }

    async def _load_draft(self, key: str) -> dict[str, Any] | None:
        raw = (await self.config.get(key, "")).strip()
        if not raw:
            return None
        try:
            draft = json.loads(raw)
            expires_at = draft.get("expires_at") if isinstance(draft, dict) else None
            if not isinstance(draft, dict) or not expires_at:
                raise ValueError
            expiry = datetime.fromisoformat(str(expires_at))
            if expiry <= utcnow():
                await self._clear_draft(key)
                return None
            return draft
        except (ValueError, TypeError, json.JSONDecodeError):
            await self._clear_draft(key)
            return None

    async def _save_draft(self, key: str, draft: dict[str, Any]) -> None:
        await self.config.set(key, json.dumps(draft, separators=(",", ":")))

    async def _clear_draft(self, key: str) -> None:
        await self.config.set(key, "")

    @staticmethod
    def _render_draft(draft: dict[str, Any]) -> str:
        return (
            "🗓 New Schedule\n\n"
            f"Target: {draft.get('target') or '—'}\n"
            f"Message: {draft.get('message') or '—'}\n"
            f"Date: {draft.get('date') or '—'}\n"
            f"Time: {draft.get('time') or '—'}\n"
            f"Timezone: {draft.get('timezone') or DEFAULT_OWNER_TIMEZONE}\n\n"
            "Use .target, .message, .date and .time to fill the form.\n"
            "Send .save to save or .cancel to discard."
        )

    async def _audit(
        self,
        action: str,
        *,
        command: str,
        request_id: str | None,
        transport_message_id: str | None,
        details: dict[str, Any],
        entity_id: str | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                action=action,
                entity_type="command_control",
                entity_id=entity_id,
                details_json={
                    "command": command,
                    "request_id": request_id,
                    "transport_message_id": transport_message_id,
                    **details,
                },
            )
        )
        await self.session.flush()
