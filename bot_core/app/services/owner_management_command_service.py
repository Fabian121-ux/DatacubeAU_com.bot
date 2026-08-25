from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, Contact
from app.services.bot_config_service import BotConfigService
from app.services.command_catalog_service import CommandCatalogService
from app.services.contact_intelligence_service import ContactIntelligenceService
from app.services.contact_sync_service import ContactSyncService
from app.utils.time import utcnow


@dataclass(slots=True)
class ManagementCommandResult:
    command: str
    reply_text: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SafeConfigSpec:
    key: str
    value_type: str
    description: str
    default: str
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str, ...] = ()


SAFE_CONFIG: dict[str, SafeConfigSpec] = {
    "bot_enabled": SafeConfigSpec("bot_enabled", "bool", "Allow Zina to reply normally.", "true"),
    "maintenance_mode": SafeConfigSpec("maintenance_mode", "bool", "Put Zina in maintenance mode.", "false"),
    "ai_enabled": SafeConfigSpec("ai_enabled", "bool", "Enable AI fallback/reasoning.", "false"),
    "auto_assist_enabled": SafeConfigSpec("auto_assist_enabled", "bool", "Allow automatic DM takeover when Fabian is unavailable.", "true"),
    "auto_assist_wait_for_fabian_first": SafeConfigSpec(
        "auto_assist_wait_for_fabian_first",
        "bool",
        "Wait for Fabian before Zina assists an eligible DM.",
        "false",
    ),
    "auto_assist_inactivity_seconds": SafeConfigSpec(
        "auto_assist_inactivity_seconds",
        "int",
        "Seconds Zina waits before an eligible takeover.",
        "120",
        minimum=5,
        maximum=3600,
    ),
    "group_default_reply_mode": SafeConfigSpec(
        "group_default_reply_mode",
        "enum",
        "Default group reply policy.",
        "mention_only",
        choices=("mention_only", "off"),
    ),
    "global_chat_enabled": SafeConfigSpec("global_chat_enabled", "bool", "Allow personal Global Chat mode.", "true"),
    "internet_enabled": SafeConfigSpec("internet_enabled", "bool", "Allow configured internet tools.", "false"),
    "whatsapp_message_format": SafeConfigSpec(
        "whatsapp_message_format",
        "enum",
        "Default WhatsApp response formatting mode.",
        "automatic",
        choices=("standard", "quote", "automatic"),
    ),
}


class OwnerManagementCommandService:
    """Thin owner/admin management adapters over existing Zina sources of truth."""

    COMMANDS = {
        "/commands",
        "/cmdinfo",
        "/cmdon",
        "/cmdoff",
        "/config",
        "/contacts",
        "/contact",
        "/contactsync",
    }
    PROTECTED_ENABLEMENT_COMMANDS = frozenset({"/commands", "/cmdinfo", "/cmdon", "/cmdoff"})
    DEFAULT_LIST_LIMIT = 20
    MAX_LIST_LIMIT = 50

    def __init__(self, session: AsyncSession):
        self.session = session
        self.catalog = CommandCatalogService(session)
        self.config = BotConfigService(session)
        self.contacts = ContactIntelligenceService(session)

    async def handle(
        self,
        command: str,
        args: str,
        *,
        permission: str,
        request_id: str | None = None,
        transport_message_id: str | None = None,
    ) -> ManagementCommandResult | None:
        command = command.strip().lower()
        if command not in self.COMMANDS:
            return None
        normalized_permission = (permission or "").strip().lower()
        if normalized_permission != "owner":
            await self._audit(command, "denied", request_id, transport_message_id, {"reason": "owner_required"})
            return ManagementCommandResult(command, "Owner command. Access denied.", "owner permission required")

        try:
            if command == "/commands":
                reply = await self._commands(normalized_permission)
            elif command == "/cmdinfo":
                reply = await self._cmdinfo(args)
            elif command in {"/cmdon", "/cmdoff"}:
                reply = await self._toggle_command(args, enabled=command == "/cmdon")
            elif command == "/config":
                reply = await self._config(args)
            elif command == "/contacts":
                reply = await self._contact_list(args)
            elif command == "/contact":
                reply = await self._contact_info(args)
            else:
                reply = await self._contact_sync()
        except ValueError as exc:
            await self._audit(command, "invalid", request_id, transport_message_id, {"reason": str(exc)[:180]})
            return ManagementCommandResult(command, f"Command error: {exc}", str(exc))

        await self.catalog.record_usage(command)
        await self._audit(command, "ok", request_id, transport_message_id, {})
        return ManagementCommandResult(command, reply)

    async def _commands(self, permission: str) -> str:
        rows = await self.catalog.list_commands()
        allowed = [row for row in rows if self._permission_allows(permission, str(row.get("permissions") or "user"))]
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in allowed:
            grouped.setdefault(str(row.get("category") or "Other"), []).append(row)

        lines = [f"ZINA COMMANDS — {len(allowed)} available"]
        for category in sorted(grouped):
            lines.append(f"\n{category}")
            for row in grouped[category]:
                name = str(row.get("name") or "")
                trigger = str(row.get("trigger_syntax") or name)
                state = "on" if row.get("is_enabled") else "off"
                display = trigger if trigger != name else name
                lines.append(f"• {display} [{state}]")
        lines.append("\nUse .cmdinfo <command> for details.")
        return "\n".join(lines)

    async def _cmdinfo(self, reference: str) -> str:
        row = await self._resolve_command(reference)
        if row is None:
            raise ValueError("command not found")
        required = str(row.get("permissions") or "user").strip().lower()
        risk = self._risk_for(row)
        trigger = str(row.get("trigger_syntax") or row.get("name"))
        aliases = trigger if trigger != row.get("name") else "—"
        return (
            f"COMMAND {row.get('name')}\n\n"
            f"Alias/trigger: {aliases}\n"
            f"Category: {row.get('category')}\n"
            f"Authority: {required.upper()}\n"
            f"Risk: {risk}\n"
            f"Enabled: {'yes' if row.get('is_enabled') else 'no'}\n"
            f"Implementation: connected\n"
            f"Handler: {row.get('handler_target') or '—'}\n"
            f"Used: {int(row.get('usage_count') or 0)} times\n"
            f"Description: {row.get('description') or '—'}\n"
            f"Example: {row.get('example') or '—'}"
        )

    async def _toggle_command(self, reference: str, *, enabled: bool) -> str:
        row = await self._resolve_command(reference)
        if row is None:
            raise ValueError("command not found")
        canonical = str(row.get("name") or "")
        if not enabled and canonical in self.PROTECTED_ENABLEMENT_COMMANDS:
            raise ValueError("this management recovery command cannot be disabled from WhatsApp")
        updated = await self.catalog.set_enabled(canonical, enabled)
        return f"{canonical} is now {'enabled' if updated.is_enabled else 'disabled'}."

    async def _config(self, args: str) -> str:
        text_value = (args or "").strip()
        if not text_value:
            lines = ["ZINA SAFE CONFIG"]
            for key, spec in SAFE_CONFIG.items():
                value = await self.config.get(key, spec.default)
                lines.append(f"• {key}: {value}")
            lines.append("\nUse .config get <key> or .config set <key> <value>.")
            return "\n".join(lines)

        action, _, remainder = text_value.partition(" ")
        action = action.lower()
        remainder = remainder.strip()
        if action == "get":
            key = remainder.lower()
            spec = self._config_spec(key)
            value = await self.config.get(key, spec.default)
            return f"{key} = {value}\nType: {spec.value_type}\n{spec.description}"
        if action == "set":
            key, separator, raw_value = remainder.partition(" ")
            if not separator:
                raise ValueError("usage: .config set <key> <value>")
            key = key.strip().lower()
            spec = self._config_spec(key)
            normalized = self._normalize_config_value(spec, raw_value)
            await self.config.set(key, normalized)
            return f"Updated {key} = {normalized}."
        raise ValueError("usage: .config, .config get <key>, or .config set <key> <value>")

    async def _contact_list(self, args: str) -> str:
        parts = [part for part in (args or "").strip().split() if part]
        mode = "summary"
        limit = self.DEFAULT_LIST_LIMIT
        if parts:
            if parts[0].lower() in {"saved", "unsaved", "recent"}:
                mode = parts[0].lower()
                if len(parts) > 1:
                    limit = self._bounded_limit(parts[1])
            else:
                limit = self._bounded_limit(parts[0])

        rows = await self._person_contacts()
        saved = [row for row in rows if self._is_saved(row)]
        unsaved = [row for row in rows if not self._is_saved(row)]
        saved_evidence_times = [self._saved_evidence_at(row) for row in rows]
        last_sync = max((value for value in saved_evidence_times if value is not None), default=None)

        if mode == "summary":
            return (
                "WHATSAPP CONTACTS\n\n"
                f"Known people: {len(rows)}\n"
                f"Saved: {len(saved)}\n"
                f"Unsaved: {len(unsaved)}\n"
                f"Last saved-contact sync evidence: {last_sync.isoformat() if last_sync else 'never'}\n\n"
                "Use .contacts saved 20, .contacts unsaved 20, .contacts recent 20, "
                ".contact <name>, or .contactsync."
            )

        selected = saved if mode == "saved" else unsaved if mode == "unsaved" else rows
        selected = selected[:limit]
        lines = [f"CONTACTS — {mode.upper()} ({len(selected)} shown)"]
        for row in selected:
            name = row.contact_name or row.display_name or row.push_name or "Unknown"
            identity = row.normalized_phone or row.whatsapp_phone or row.whatsapp_id
            lines.append(f"• {name} — {identity}")
        if not selected:
            lines.append("No matching contacts.")
        return "\n".join(lines)

    async def _contact_info(self, query: str) -> str:
        query = (query or "").strip()
        if not query:
            raise ValueError("usage: .contact <name-or-phone>")
        result = await self.contacts.resolve(query, limit=5)
        if result["status"] == "not_found":
            return "No matching contact found."
        if result["status"] == "ambiguous":
            lines = ["Contact is ambiguous. Be more specific:"]
            for item in result["candidates"]:
                name = item.get("contact_name") or item.get("display_name") or item.get("push_name") or "Unknown"
                identity = item.get("normalized_phone") or item.get("whatsapp_id")
                lines.append(f"• {name} — {identity} ({item.get('matched_field')})")
            return "\n".join(lines)

        match = result["match"]
        row = await self.session.get(Contact, int(match["contact_id"]))
        saved = bool(row and self._is_saved(row))
        return (
            f"CONTACT\n\n"
            f"Name: {match.get('contact_name') or match.get('display_name') or match.get('push_name') or 'Unknown'}\n"
            f"Phone: {match.get('normalized_phone') or '—'}\n"
            f"WhatsApp ID: {match.get('whatsapp_id')}\n"
            f"Saved: {'yes' if saved else 'no'}\n"
            f"Confidence: {match.get('confidence')}\n"
            f"Matched by: {match.get('matched_field')}"
        )

    async def _contact_sync(self) -> str:
        result = await ContactSyncService(self.session).sync()
        return (
            "CONTACT SYNC COMPLETE\n\n"
            f"Fetched: {result['fetched']}\n"
            f"Created: {result['created']}\n"
            f"Updated: {result['updated']}\n"
            f"Skipped: {result['skipped']}"
        )

    async def _resolve_command(self, reference: str) -> dict[str, Any] | None:
        ref = (reference or "").strip().lower()
        if not ref:
            raise ValueError("command name required")
        rows = await self.catalog.list_commands()
        exact: list[dict[str, Any]] = []
        for row in rows:
            values = {
                str(row.get("name") or "").lower(),
                str(row.get("trigger_syntax") or "").lower(),
            }
            bare = {value.lstrip("./!") for value in values if value}
            if ref in values or ref.lstrip("./!") in bare:
                exact.append(row)
        if len(exact) == 1:
            return exact[0]
        if len(exact) > 1:
            raise ValueError("command reference is ambiguous")
        return None

    async def _person_contacts(self) -> list[Contact]:
        rows = (
            await self.session.execute(
                select(Contact).order_by(Contact.last_active_at.desc().nullslast(), Contact.updated_at.desc(), Contact.id.desc()).limit(10000)
            )
        ).scalars().all()
        return [row for row in rows if self._is_person_id(row.whatsapp_id)]

    @staticmethod
    def _is_person_id(value: str | None) -> bool:
        lowered = (value or "").strip().lower()
        if not lowered:
            return False
        return not (
            lowered.endswith("@g.us")
            or lowered == "status@broadcast"
            or lowered.endswith("@newsletter")
            or lowered.endswith("@broadcast")
        )

    @staticmethod
    def _is_saved(row: Contact) -> bool:
        identity = row.identity_json if isinstance(row.identity_json, dict) else {}
        if "is_saved_contact" in identity:
            return identity.get("is_saved_contact") is True
        return bool((row.contact_name or "").strip())

    @staticmethod
    def _saved_evidence_at(row: Contact):
        identity = row.identity_json if isinstance(row.identity_json, dict) else {}
        raw = identity.get("saved_contact_synced_at")
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @classmethod
    def _bounded_limit(cls, value: str) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("contact list limit must be a number") from exc
        if parsed < 1 or parsed > cls.MAX_LIST_LIMIT:
            raise ValueError(f"contact list limit must be between 1 and {cls.MAX_LIST_LIMIT}")
        return parsed

    @staticmethod
    def _permission_allows(actor: str, required: str) -> bool:
        rank = {"user": 0, "admin": 1, "owner": 2}
        return rank.get(actor, -1) >= rank.get(required.strip().lower(), 0)

    @staticmethod
    def _risk_for(row: dict[str, Any]) -> str:
        permission = str(row.get("permissions") or "user").lower()
        name = str(row.get("name") or "")
        if name in {"/broadcast", "/broadcast-groups", "/broadcast-users", "/delete-command", "/stopbot"}:
            return "high"
        if permission == "owner":
            return "medium"
        return "low"

    @staticmethod
    def _config_spec(key: str) -> SafeConfigSpec:
        spec = SAFE_CONFIG.get((key or "").strip().lower())
        if spec is None:
            raise ValueError("unknown or protected config key")
        return spec

    @staticmethod
    def _normalize_config_value(spec: SafeConfigSpec, raw_value: str) -> str:
        value = (raw_value or "").strip()
        if spec.value_type == "bool":
            lowered = value.lower()
            if lowered in {"true", "1", "yes", "on"}:
                return "true"
            if lowered in {"false", "0", "no", "off"}:
                return "false"
            raise ValueError(f"{spec.key} expects on/off or true/false")
        if spec.value_type == "int":
            try:
                parsed = int(value)
            except ValueError as exc:
                raise ValueError(f"{spec.key} expects a whole number") from exc
            if spec.minimum is not None and parsed < spec.minimum:
                raise ValueError(f"{spec.key} must be at least {spec.minimum}")
            if spec.maximum is not None and parsed > spec.maximum:
                raise ValueError(f"{spec.key} must be at most {spec.maximum}")
            return str(parsed)
        if spec.value_type == "enum":
            lowered = value.lower()
            if lowered not in spec.choices:
                raise ValueError(f"{spec.key} must be one of: {', '.join(spec.choices)}")
            return lowered
        raise ValueError("unsupported config type")

    async def _audit(
        self,
        command: str,
        result: str,
        request_id: str | None,
        transport_message_id: str | None,
        details: dict[str, Any],
    ) -> None:
        self.session.add(
            AuditLog(
                action="owner_management_command",
                entity_type="command_control",
                entity_id=command,
                details_json={
                    "command": command,
                    "result": result,
                    "request_id": request_id,
                    "transport_message_id": transport_message_id,
                    **details,
                },
                created_at=utcnow(),
            )
        )
        await self.session.flush()
