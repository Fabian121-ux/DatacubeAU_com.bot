from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import CommandCatalogEntry
from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class CommandDefinition:
    name: str
    category: str
    description: str
    example: str
    permissions: str
    handler_target: str = ""
    trigger_syntax: str | None = None
    is_enabled: bool = True


DEFAULT_COMMANDS = [
    CommandDefinition("/help", "User Commands", "Show available user commands.", "/help", "user"),
    CommandDefinition("/start", "User Commands", "Start or restart the assistant introduction flow.", "/start", "user"),
    CommandDefinition("/status", "User Commands", "Check bot availability and basic status.", "/status", "user"),
    CommandDefinition("/review", "User Commands", "Send feedback for owner review.", "/review The reply was helpful.", "user"),
    CommandDefinition("/whoami", "User Commands", "Show sender identity keys and owner-command permission status.", "/whoami", "user"),
    CommandDefinition("/global", "User Commands", "Turn personal Global Chat mode on or off.", "/global on", "user"),
    CommandDefinition("!ask", "User Commands", "Ask one AI-backed question without changing Global Chat mode.", "!ask Compare these options.", "user"),

    CommandDefinition("/owner-help", "Admin Commands", "Show owner-only command help.", "/owner-help", "owner"),
    CommandDefinition(
        "/schedule",
        "Admin Commands",
        "Start a guided owner scheduling draft in the WhatsApp self-DM control inbox.",
        "@Zina .sch",
        "owner",
        handler_target="command_control:schedule",
        trigger_syntax=".sch",
    ),
    CommandDefinition(
        "/push",
        "Admin Commands",
        "Push the exact quoted peer-DM message into Fabian's private self-DM control inbox.",
        "Reply to a message, then send @Zina .push",
        "owner",
        handler_target="command_control:push",
        trigger_syntax=".push",
    ),
    CommandDefinition(
        "/deleted-message",
        "Admin Commands",
        "Inspect bounded deleted-message evidence that Zina observed before WAHA revocation.",
        "@Zina .dm",
        "owner",
        handler_target="command_control:deleted_message",
        trigger_syntax=".dm",
    ),
    CommandDefinition(
        "/vvopen",
        "Admin Commands",
        "Open or inspect explicitly detected WAHA view-once media for Fabian's private owner inbox.",
        "Reply to a view-once item, then send @Zina .vv",
        "owner",
        handler_target="command_control:view_once",
        trigger_syntax=".vv",
    ),
    CommandDefinition(
        "/commands",
        "Admin Commands",
        "List commands visible to the current authority.",
        "@Zina .commands",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".commands",
    ),
    CommandDefinition(
        "/cmdinfo",
        "Admin Commands",
        "Inspect command metadata, authority, state, and handler.",
        ".cmdinfo .sch",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".cmdinfo",
    ),
    CommandDefinition(
        "/cmdon",
        "Admin Commands",
        "Enable a registered Command Center command.",
        ".cmdon /weather",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".cmdon",
    ),
    CommandDefinition(
        "/cmdoff",
        "Admin Commands",
        "Disable a registered Command Center command.",
        ".cmdoff /weather",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".cmdoff",
    ),
    CommandDefinition(
        "/config",
        "Admin Commands",
        "Inspect or change allow-listed non-secret Zina runtime configuration.",
        ".config get auto_assist_inactivity_seconds",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".config",
    ),
    CommandDefinition(
        "/contacts",
        "Admin Commands",
        "Summarize or list known saved and unsaved WhatsApp people.",
        ".contacts saved 20",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".contacts",
    ),
    CommandDefinition(
        "/contact",
        "Admin Commands",
        "Resolve and inspect one WhatsApp contact safely.",
        ".contact Amanda Christabel",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".contact",
    ),
    CommandDefinition(
        "/contactsync",
        "Admin Commands",
        "Refresh saved WhatsApp contacts through the existing WAHA contact sync.",
        ".contactsync",
        "owner",
        handler_target="command_control:management",
        trigger_syntax=".contactsync",
    ),
    CommandDefinition("/create-command", "Admin Commands", "Create a custom slash command reply.", "/create-command\nCommand:\n/scholarship\nReply:\nCheck School Info updates.", "owner"),
    CommandDefinition("/edit-command", "Admin Commands", "Edit a custom slash command reply.", "/edit-command\nCommand:\n/scholarship\nReply:\nUpdated reply.", "owner"),
    CommandDefinition("/delete-command", "Admin Commands", "Delete a custom slash command reply.", "/delete-command /scholarship", "owner"),
    CommandDefinition("/groups", "Admin Commands", "List known WhatsApp groups.", "/groups", "owner"),
    CommandDefinition("/communities", "Admin Commands", "List known communities.", "/communities", "owner"),
    CommandDefinition("/my-groups", "Admin Commands", "List groups visible to the WAHA session.", "/my-groups", "owner"),
    CommandDefinition("/my-communities", "Admin Commands", "List communities visible to the WAHA session.", "/my-communities", "owner"),
    CommandDefinition("/group-info", "Admin Commands", "Show metadata for a group.", "/group-info 120363000000000000@g.us", "owner"),
    CommandDefinition("/find-group", "Admin Commands", "Search known groups by name or note.", "/find-group Datacube", "owner"),
    CommandDefinition("/inventory", "Admin Commands", "Show bot inventory and known assets.", "/inventory", "owner"),
    CommandDefinition("/group-sync", "Admin Commands", "Refresh group metadata from WAHA.", "/group-sync", "owner"),
    CommandDefinition("/tag-group", "Admin Commands", "Create owner metadata for a group.", "/tag-group 120363000000000000@g.us\npurpose=Testing", "owner"),
    CommandDefinition("/group-notes", "Admin Commands", "Update notes for an existing group.", "/group-notes 120363000000000000@g.us\nnotes=Important group", "owner"),
    CommandDefinition("/group-update", "Admin Commands", "Update saved group metadata.", "/group-update 120363000000000000@g.us\npurpose=Support", "owner"),
    CommandDefinition("/force", "Admin Commands", "Force replies for a target user.", "/force 2348000000000@c.us", "owner"),
    CommandDefinition("/unforce", "Admin Commands", "Remove forced replies for a target user.", "/unforce 2348000000000@c.us", "owner"),
    CommandDefinition("/trigger", "Admin Commands", "Create a user-specific trigger response.", "/trigger 2348000000000@c.us\nWhen: pricing\nReply: Please contact Fabian.", "owner"),
    CommandDefinition("/broadcast", "Admin Commands", "Broadcast a message to selected users.", "/broadcast\nMessage text", "owner"),
    CommandDefinition("/broadcast-groups", "Admin Commands", "Broadcast a message to groups.", "/broadcast-groups\nMessage text", "owner"),
    CommandDefinition("/broadcast-users", "Admin Commands", "Broadcast a message to users.", "/broadcast-users\nMessage text", "owner"),
    CommandDefinition("/system", "Admin Commands", "Show system status and runtime configuration.", "/system", "owner"),
    CommandDefinition("/storage", "Admin Commands", "Show storage and database usage.", "/storage", "owner"),
    CommandDefinition("/logs", "Admin Commands", "Show recent operational logs.", "/logs", "owner"),
    CommandDefinition("/errors", "Admin Commands", "Show recent errors.", "/errors", "owner"),
    CommandDefinition("/queue", "Admin Commands", "Show outbound queue status.", "/queue", "owner"),
    CommandDefinition("/reviews", "Admin Commands", "Show pending user feedback reviews.", "/reviews", "owner"),
    CommandDefinition("/stopbot", "Admin Commands", "Disable bot replies.", "/stopbot", "owner"),
    CommandDefinition("/startbot", "Admin Commands", "Enable bot replies.", "/startbot", "owner"),
    CommandDefinition("/maintenance", "Admin Commands", "Toggle maintenance behavior.", "/maintenance on", "owner"),
    CommandDefinition("/mentiononly", "Admin Commands", "Force group replies to mention-only mode.", "/mentiononly", "owner"),
    CommandDefinition("/top-users", "Admin Commands", "Show most active users.", "/top-users", "owner"),
    CommandDefinition("/top-questions", "Admin Commands", "Show most common questions.", "/top-questions", "owner"),
    CommandDefinition("/ai-usage", "Admin Commands", "Show AI usage and token statistics.", "/ai-usage", "owner"),
    CommandDefinition("/enable-ai", "Admin Commands", "Enable AI fallback.", "/enable-ai", "owner"),
    CommandDefinition("/disable-ai", "Admin Commands", "Disable AI fallback.", "/disable-ai", "owner"),

    CommandDefinition("/internet", "Internet Commands", "Enable or disable all internet services.", "/internet on", "owner"),
    CommandDefinition("/web", "Internet Commands", "Enable or disable web search.", "/web on", "owner"),
    CommandDefinition("/internet-status", "Internet Commands", "Show internet service status.", "/internet-status", "owner"),
    CommandDefinition("/internet-usage", "Internet Commands", "Show internet usage analytics.", "/internet-usage", "owner"),
    CommandDefinition("!search", "Internet Commands", "Run a web search when internet access is enabled.", "!search latest AI news", "user"),
    CommandDefinition("!google", "Internet Commands", "Run a web search alias when enabled.", "!google Datacube AU", "user"),
    CommandDefinition("!news", "Internet Commands", "Search recent news when enabled.", "!news artificial intelligence", "user"),
    CommandDefinition("!weather", "Internet Commands", "Search weather information when enabled.", "!weather Lagos", "user"),
    CommandDefinition("!currency", "Internet Commands", "Convert or search currency rates when enabled.", "!currency 100 USD to NGN", "user"),
    CommandDefinition("!youtube", "Internet Commands", "Search YouTube/video results when enabled.", "!youtube Python FastAPI tutorial", "user"),

    CommandDefinition("!image", "Media Commands", "Search images when enabled.", "!image Datacube AU", "user"),
    CommandDefinition("!sticker", "Media Commands", "Search sticker-style images when enabled.", "!sticker happy coding", "user"),
    CommandDefinition("!gif", "Media Commands", "Search GIFs when enabled.", "!gif celebration", "user"),

    CommandDefinition("/faq-import", "Memory Commands", "Import text or Markdown into the FAQ approval queue.", "/faq-import\nWho is Fabian?\n\nFabian is an AI systems builder.", "owner"),
    CommandDefinition("/teach", "Memory Commands", "Create or update one approved FAQ entry.", "/teach\nQuestion:\nWhat is Zina?\n\nAnswer:\nZina is Fabian's AI assistant.", "owner"),
    CommandDefinition("/remember", "Memory Commands", "Store an owner-provided memory fact.", "/remember Fabian prefers concise replies.", "owner"),
    CommandDefinition("/forget", "Memory Commands", "Delete stored memory for a target user.", "/forget 2348000000000@c.us", "owner"),
    CommandDefinition("/memory-search", "Memory Commands", "Search saved memory.", "/memory-search Datacube", "owner"),
    CommandDefinition("/recent-memory", "Memory Commands", "Show recent memory timeline entries.", "/recent-memory", "owner"),
    CommandDefinition("/user", "Memory Commands", "Show a user's relationship profile.", "/user 2348000000000@c.us", "owner"),
    CommandDefinition("/timeline", "Memory Commands", "Show a user's conversation timeline.", "/timeline 2348000000000@c.us", "owner"),
    CommandDefinition("/summary", "Memory Commands", "Show conversation summaries for a user.", "/summary 2348000000000@c.us", "owner"),
    CommandDefinition("/memory-stats", "Memory Commands", "Show memory profile and timeline statistics.", "/memory-stats", "owner"),
]


class CommandCatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_defaults(self) -> None:
        rows = await self._fetch_all()
        existing = {row.name: row for row in rows}
        for item in DEFAULT_COMMANDS:
            trigger_syntax = item.trigger_syntax or item.name
            handler_target = item.handler_target or self.default_handler_target(item.name)
            row = existing.get(item.name)
            if row:
                row.category = item.category
                row.description = item.description
                row.example = item.example
                row.permissions = item.permissions
                row.trigger_syntax = trigger_syntax
                row.handler_target = handler_target
                row.updated_at = utcnow()
                continue
            self.session.add(
                CommandCatalogEntry(
                    name=item.name,
                    trigger_syntax=trigger_syntax,
                    category=item.category,
                    description=item.description,
                    example=item.example,
                    permissions=item.permissions,
                    handler_target=handler_target,
                    is_enabled=item.is_enabled,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
        await self.session.flush()

    async def list_commands(self) -> list[dict[str, Any]]:
        try:
            await self.ensure_defaults()
            rows = await self._fetch_all()
        except Exception:
            rows = []

        by_name = {row.name: row for row in rows if hasattr(row, "name")}
        items = []
        for default in DEFAULT_COMMANDS:
            row = by_name.get(default.name)
            items.append(self.serialize(row) if row else self.serialize_default(default))
        extras = [row for row in rows if row.name not in {item.name for item in DEFAULT_COMMANDS}]
        items.extend(self.serialize(row) for row in extras)
        return sorted(items, key=lambda item: (item["category"], item["name"]))

    async def is_enabled(self, name: str) -> bool:
        try:
            await self.ensure_defaults()
            row = (
                await self.session.execute(select(CommandCatalogEntry).where(CommandCatalogEntry.name == name).limit(1))
            ).scalar_one_or_none()
            if row:
                return bool(row.is_enabled)
        except Exception:
            return True
        default = next((item for item in DEFAULT_COMMANDS if item.name == name), None)
        return True if default is None else default.is_enabled

    async def set_enabled(self, name: str, enabled: bool) -> CommandCatalogEntry:
        await self.ensure_defaults()
        row = (
            await self.session.execute(select(CommandCatalogEntry).where(CommandCatalogEntry.name == name).limit(1))
        ).scalar_one_or_none()
        if not row:
            raise ValueError(f"command {name} not found")
        row.is_enabled = enabled
        row.updated_at = utcnow()
        await self.session.flush()
        return row

    async def record_usage(self, name: str) -> CommandCatalogEntry | None:
        await self.ensure_defaults()
        row = (
            await self.session.execute(select(CommandCatalogEntry).where(CommandCatalogEntry.name == name).limit(1))
        ).scalar_one_or_none()
        if not row:
            return None
        row.usage_count = int(row.usage_count or 0) + 1
        row.last_used_at = utcnow()
        row.updated_at = utcnow()
        await self.session.flush()
        return row

    async def _fetch_all(self) -> list[CommandCatalogEntry]:
        return (await self.session.execute(select(CommandCatalogEntry).order_by(CommandCatalogEntry.category, CommandCatalogEntry.name))).scalars().all()

    @staticmethod
    def default_handler_target(name: str) -> str:
        if name in {"/help", "/start", "/status", "/review", "/whoami"}:
            return f"user_command:{name}"
        if name == "/global":
            return "memory:global_chat"
        if name == "!ask":
            return "ai:one_shot"
        if name.startswith("!"):
            return f"internet_command:{name}"
        if name.startswith("/"):
            return f"owner_command:{name}"
        return f"command:{name}"

    @staticmethod
    def serialize(row: CommandCatalogEntry) -> dict[str, Any]:
        trigger_syntax = getattr(row, "trigger_syntax", None) or row.name
        handler_target = getattr(row, "handler_target", None) or CommandCatalogService.default_handler_target(row.name)
        return {
            "id": row.id,
            "name": row.name,
            "trigger_syntax": trigger_syntax,
            "category": row.category,
            "description": row.description,
            "example": row.example,
            "permissions": row.permissions,
            "handler_target": handler_target,
            "usage_count": getattr(row, "usage_count", 0) or 0,
            "last_used_at": getattr(row, "last_used_at", None),
            "is_enabled": row.is_enabled,
            "enabled": row.is_enabled,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def serialize_default(item: CommandDefinition) -> dict[str, Any]:
        trigger_syntax = item.trigger_syntax or item.name
        handler_target = item.handler_target or CommandCatalogService.default_handler_target(item.name)
        return {
            "id": None,
            "name": item.name,
            "trigger_syntax": trigger_syntax,
            "category": item.category,
            "description": item.description,
            "example": item.example,
            "permissions": item.permissions,
            "handler_target": handler_target,
            "usage_count": 0,
            "last_used_at": None,
            "is_enabled": item.is_enabled,
            "enabled": item.is_enabled,
            "created_at": None,
            "updated_at": None,
        }