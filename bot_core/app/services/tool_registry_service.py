from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.bot_config_service import BotConfigService


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    category: str
    description: str
    risk: str
    permission: str
    input_schema: dict[str, Any]
    handler_target: str
    default_enabled: bool = True


DEFAULT_TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        name="whatsapp.find_contact",
        category="WhatsApp",
        description="Resolve a saved WhatsApp contact through Contact Intelligence.",
        risk="low",
        permission="owner",
        input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
        handler_target="contact_intelligence.resolve",
    ),
    ToolDefinition(
        name="whatsapp.send_message",
        category="WhatsApp",
        description="Send or schedule an owner-authorized WhatsApp text message through the existing action/outbound pipeline.",
        risk="medium",
        permission="owner",
        input_schema={
            "type": "object",
            "required": ["target", "text"],
            "properties": {
                "target": {"type": "string"},
                "text": {"type": "string"},
                "scheduled_for": {"type": ["string", "null"], "format": "date-time"},
                "timezone": {"type": ["string", "null"]},
            },
        },
        handler_target="scheduled_action.whatsapp_send_message",
    ),
    ToolDefinition(
        name="task.create",
        category="Automation",
        description="Create a durable scheduled action using the existing ScheduledAction service.",
        risk="medium",
        permission="owner",
        input_schema={
            "type": "object",
            "required": ["action", "scheduled_for"],
            "properties": {
                "action": {"type": "string"},
                "scheduled_for": {"type": "string", "format": "date-time"},
                "timezone": {"type": "string"},
                "arguments": {"type": "object"},
            },
        },
        handler_target="scheduled_action.create",
    ),
    ToolDefinition(
        name="task.cancel",
        category="Automation",
        description="Cancel an existing durable scheduled action.",
        risk="medium",
        permission="owner",
        input_schema={"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "integer"}}},
        handler_target="scheduled_action.cancel",
    ),
    ToolDefinition(
        name="memory.search",
        category="Memory",
        description="Search Zina's existing managed memory for owner-authorized context.",
        risk="low",
        permission="owner",
        input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
        handler_target="memory.search",
    ),
    ToolDefinition(
        name="chat.read",
        category="Conversation",
        description="Read owner-authorized stored conversation history without mutating it.",
        risk="low",
        permission="owner",
        input_schema={
            "type": "object",
            "required": ["contact"],
            "properties": {
                "contact": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 500},
            },
        },
        handler_target="conversation.read",
    ),
    ToolDefinition(
        name="web.search",
        category="Internet",
        description="Run Zina's existing web-search capability when internet access is enabled.",
        risk="low",
        permission="owner",
        input_schema={"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}}},
        handler_target="internet.search",
    ),
    ToolDefinition(
        name="group.tag",
        category="Groups",
        description="Tag group participants through the future group action adapter after deterministic authorization checks.",
        risk="medium",
        permission="owner",
        input_schema={
            "type": "object",
            "required": ["group_id", "text"],
            "properties": {"group_id": {"type": "string"}, "text": {"type": "string"}},
        },
        handler_target="group.tag",
        default_enabled=False,
    ),
)


class ToolRegistryService:
    """Central capability metadata and durable enable/disable state.

    The registry describes executable capabilities but intentionally does not execute
    them. Existing subsystem services remain authoritative for permission checks and
    side effects.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = BotConfigService(session)
        self._definitions = {tool.name: tool for tool in DEFAULT_TOOLS}

    async def list_tools(self, *, permission: str | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for tool in DEFAULT_TOOLS:
            if permission and tool.permission != permission:
                continue
            items.append(await self.serialize(tool))
        return items

    async def get_tool(self, name: str) -> dict[str, Any] | None:
        tool = self._definitions.get(self.normalize_name(name))
        if not tool:
            return None
        return await self.serialize(tool)

    async def set_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        normalized = self.normalize_name(name)
        tool = self._definitions.get(normalized)
        if not tool:
            raise ValueError(f"tool {name} not found")
        await self.config.set(self.enabled_key(normalized), str(bool(enabled)).lower())
        return await self.serialize(tool)

    async def is_enabled(self, name: str) -> bool:
        normalized = self.normalize_name(name)
        tool = self._definitions.get(normalized)
        if not tool:
            return False
        return await self.config.get_bool(self.enabled_key(normalized), tool.default_enabled)

    async def serialize(self, tool: ToolDefinition) -> dict[str, Any]:
        return {
            "name": tool.name,
            "category": tool.category,
            "description": tool.description,
            "risk": tool.risk,
            "permission": tool.permission,
            "input_schema": tool.input_schema,
            "handler_target": tool.handler_target,
            "enabled": await self.is_enabled(tool.name),
        }

    @staticmethod
    def normalize_name(name: str) -> str:
        return (name or "").strip().lower()

    @staticmethod
    def enabled_key(name: str) -> str:
        return f"tool.{name}.enabled"
