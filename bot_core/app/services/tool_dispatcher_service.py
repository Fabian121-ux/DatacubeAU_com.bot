from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog
from app.services.scheduled_action_service import ScheduledActionService
from app.services.tool_registry_service import ToolRegistryService
from app.utils.time import utcnow


_PERMISSION_RANK = {"user": 10, "admin": 20, "owner": 30}


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    permission: str
    requested_by_contact_id: int | None = None
    source_message_id: int | None = None
    idempotency_key: str | None = None


class ToolDispatcherService:
    """Deterministic authority boundary between planners and Zina side effects.

    The registry defines which tools exist and their policy metadata. This dispatcher
    validates enablement, caller permission and arguments, then delegates execution to
    the subsystem that already owns the side effect. It intentionally does not let an
    LLM or parser call WAHA or persistence primitives directly.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = ToolRegistryService(session)
        self.scheduler = ScheduledActionService(session)

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        normalized = self.registry.normalize_name(name)
        tool = await self.registry.get_tool(normalized)
        if not tool:
            self._audit("tool_execution_denied", normalized or name, context, reason="tool_not_registered")
            raise ValueError(f"tool {name} is not registered")
        if not tool["enabled"]:
            self._audit("tool_execution_denied", normalized, context, reason="tool_disabled", tool=tool)
            raise ValueError(f"tool {normalized} is disabled")
        if not self._permission_allows(context.permission, tool["permission"]):
            self._audit("tool_execution_denied", normalized, context, reason="permission_denied", tool=tool)
            raise ValueError(f"permission denied for tool {normalized}")

        self._validate_arguments(tool, arguments)

        if normalized == "whatsapp.send_message":
            result = await self._execute_whatsapp_send_message(arguments, context=context)
        else:
            self._audit("tool_execution_denied", normalized, context, reason="handler_not_implemented", tool=tool)
            raise ValueError(f"tool {normalized} has no executable adapter")

        self._audit(
            "tool_execution_accepted",
            normalized,
            context,
            tool=tool,
            result_id=str(result.get("id")) if isinstance(result, dict) and result.get("id") is not None else None,
        )
        await self.session.flush()
        return {"tool": normalized, "handler_target": tool["handler_target"], "result": result}

    async def _execute_whatsapp_send_message(
        self,
        arguments: dict[str, Any],
        *,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        scheduled_for = self._parse_datetime(arguments.get("scheduled_for")) or utcnow()
        timezone = str(arguments.get("timezone") or "UTC").strip() or "UTC"
        return await self.scheduler.create_whatsapp_message(
            target_reference=str(arguments["target"]).strip(),
            text=str(arguments["text"]).strip(),
            scheduled_for=scheduled_for,
            timezone=timezone,
            source_message_id=context.source_message_id,
            requested_by_contact_id=context.requested_by_contact_id,
            idempotency_key=context.idempotency_key,
        )

    @staticmethod
    def _permission_allows(actual: str, required: str) -> bool:
        return _PERMISSION_RANK.get((actual or "").strip().lower(), 0) >= _PERMISSION_RANK.get(
            (required or "").strip().lower(),
            10_000,
        )

    @staticmethod
    def _validate_arguments(tool: dict[str, Any], arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be an object")
        schema = tool.get("input_schema") or {}
        properties = schema.get("properties") or {}
        for field in schema.get("required") or []:
            value = arguments.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"missing required tool argument: {field}")
        unknown = sorted(set(arguments) - set(properties))
        if unknown:
            raise ValueError(f"unknown tool argument: {unknown[0]}")

        for field, value in arguments.items():
            if value is None:
                continue
            definition = properties.get(field) or {}
            expected = definition.get("type")
            allowed = expected if isinstance(expected, list) else [expected]
            allowed = [item for item in allowed if item != "null"]
            if "string" in allowed and not isinstance(value, (str, datetime)):
                raise ValueError(f"invalid tool argument type: {field}")
            if "integer" in allowed and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"invalid tool argument type: {field}")
            if "object" in allowed and not isinstance(value, dict):
                raise ValueError(f"invalid tool argument type: {field}")

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                return None
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                parsed = datetime.fromisoformat(raw)
            except ValueError as exc:
                raise ValueError("scheduled_for must be an ISO 8601 datetime") from exc
        else:
            raise ValueError("scheduled_for must be an ISO 8601 datetime")
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("scheduled_for must include a timezone offset")
        return parsed

    def _audit(
        self,
        action: str,
        tool_name: str,
        context: ToolExecutionContext,
        *,
        reason: str | None = None,
        tool: dict[str, Any] | None = None,
        result_id: str | None = None,
    ) -> None:
        details: dict[str, Any] = {
            "tool": tool_name,
            "permission": context.permission,
            "reason": reason,
            "risk": tool.get("risk") if tool else None,
            "handler_target": tool.get("handler_target") if tool else None,
        }
        self.session.add(
            AuditLog(
                action=action,
                entity_type="tool_execution",
                entity_id=result_id,
                details_json=details,
            )
        )
