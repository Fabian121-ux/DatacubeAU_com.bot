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
    is_enabled: bool = True


DEFAULT_COMMANDS = [
    CommandDefinition("/help", "User Commands", "Show available user commands.", "/help", "user"),
    CommandDefinition("/status", "User Commands", "Check bot availability and basic status.", "/status", "user"),
    CommandDefinition("/whoami", "User Commands", "Show sender identity keys and owner-command permission status.", "/whoami", "user"),
    CommandDefinition("/owner-help", "Owner Commands", "Show owner-only command help.", "/owner-help", "owner"),
    CommandDefinition("/faq-import", "Owner Commands", "Import text or Markdown into the FAQ approval queue.", "/faq-import\nWho is Fabian?\n\nFabian is an AI systems builder.", "owner"),
    CommandDefinition("/teach", "Owner Commands", "Create or update one approved FAQ entry.", "/teach\nQuestion:\nWhat is Zina?\n\nAnswer:\nZina is Fabian's AI assistant.", "owner"),
    CommandDefinition("/create-command", "Owner Commands", "Create a custom slash command reply.", "/create-command\nCommand:\n/scholarship\nReply:\nCheck School Info updates.", "owner"),
    CommandDefinition("/edit-command", "Owner Commands", "Edit a custom slash command reply.", "/edit-command\nCommand:\n/scholarship\nReply:\nUpdated reply.", "owner"),
    CommandDefinition("/delete-command", "Owner Commands", "Delete a custom slash command reply.", "/delete-command /scholarship", "owner"),
    CommandDefinition("/internet", "Owner Commands", "Enable or disable internet services.", "/internet on", "owner"),
    CommandDefinition("/web", "Owner Commands", "Enable or disable web search.", "/web on", "owner"),
    CommandDefinition("/internet-status", "Owner Commands", "Show internet service status.", "/internet-status", "owner"),
    CommandDefinition("!search", "Internet Commands", "Run a web search when internet access is enabled.", "!search latest AI news", "user"),
    CommandDefinition("!news", "Internet Commands", "Search recent news when enabled.", "!news artificial intelligence", "user"),
    CommandDefinition("!weather", "Internet Commands", "Search weather information when enabled.", "!weather Lagos", "user"),
    CommandDefinition("!currency", "Internet Commands", "Convert or search currency rates when enabled.", "!currency 100 USD to NGN", "user"),
    CommandDefinition("!image", "Media Commands", "Search images when enabled.", "!image Datacube AU", "user"),
    CommandDefinition("!gif", "Media Commands", "Search GIFs when enabled.", "!gif celebration", "user"),
    CommandDefinition("/remember", "Memory Commands", "Store an owner-provided memory fact.", "/remember Fabian prefers concise replies.", "owner"),
    CommandDefinition("/memory-search", "Memory Commands", "Search saved memory.", "/memory-search Datacube", "owner"),
    CommandDefinition("/enable-ai", "Owner Commands", "Enable AI fallback.", "/enable-ai", "owner"),
    CommandDefinition("/disable-ai", "Owner Commands", "Disable AI fallback.", "/disable-ai", "owner"),
]


class CommandCatalogService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_defaults(self) -> None:
        rows = await self._fetch_all()
        existing = {row.name: row for row in rows}
        for item in DEFAULT_COMMANDS:
            row = existing.get(item.name)
            if row:
                row.category = item.category
                row.description = item.description
                row.example = item.example
                row.permissions = item.permissions
                row.updated_at = utcnow()
                continue
            self.session.add(
                CommandCatalogEntry(
                    name=item.name,
                    category=item.category,
                    description=item.description,
                    example=item.example,
                    permissions=item.permissions,
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

    async def _fetch_all(self) -> list[CommandCatalogEntry]:
        return (await self.session.execute(select(CommandCatalogEntry).order_by(CommandCatalogEntry.category, CommandCatalogEntry.name))).scalars().all()

    @staticmethod
    def serialize(row: CommandCatalogEntry) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "category": row.category,
            "description": row.description,
            "example": row.example,
            "permissions": row.permissions,
            "is_enabled": row.is_enabled,
            "enabled": row.is_enabled,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def serialize_default(item: CommandDefinition) -> dict[str, Any]:
        return {
            "id": None,
            "name": item.name,
            "category": item.category,
            "description": item.description,
            "example": item.example,
            "permissions": item.permissions,
            "is_enabled": item.is_enabled,
            "enabled": item.is_enabled,
            "created_at": None,
            "updated_at": None,
        }
