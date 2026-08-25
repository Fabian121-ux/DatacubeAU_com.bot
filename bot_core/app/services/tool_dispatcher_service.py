from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, Contact, Message, OutboundMessage, UserMemoryTimeline
from app.services.contact_intelligence_service import ContactIntelligenceService
from app.services.memory_service import MemoryService
from app.services.scheduled_action_service import ScheduledActionService
from app.services.tool_registry_service import ToolRegistryService
from app.utils.text import normalize_text
from app.utils.time import utcnow


_PERMISSION_RANK = {"user": 10, "admin": 20, "owner": 30}


@dataclass(frozen=True, slots=True)
class ToolExecutionContext:
    permission: str
    requested_by_contact_id: int | None = None
    source_message_id: int | None = None
    idempotency_key: str | None = None


class ToolDispatcherService:
    """Deterministic authority boundary between planners and Zina subsystem tools.

    The registry defines which tools exist and their policy metadata. This dispatcher
    validates enablement, caller permission and arguments, then delegates execution to
    the subsystem that already owns the requested capability. It intentionally does not
    let an LLM or parser call WAHA or persistence primitives directly.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.registry = ToolRegistryService(session)
        self.contacts = ContactIntelligenceService(session)
        self.memory = MemoryService(session)
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

        if normalized == "whatsapp.find_contact":
            result = await self._execute_whatsapp_find_contact(arguments)
        elif normalized == "whatsapp.send_message":
            result = await self._execute_whatsapp_send_message(arguments, context=context)
        elif normalized == "memory.search":
            result = await self._execute_memory_search(arguments, context=context)
        elif normalized == "chat.read":
            result = await self._execute_chat_read(arguments)
        else:
            self._audit("tool_execution_denied", normalized, context, reason="handler_not_implemented", tool=tool)
            raise ValueError(f"tool {normalized} has no executable adapter")

        result_id = self._result_id(result)
        self._audit(
            "tool_execution_accepted",
            normalized,
            context,
            tool=tool,
            result_id=result_id,
        )
        await self.session.flush()
        return {"tool": normalized, "handler_target": tool["handler_target"], "result": result}

    async def _execute_whatsapp_find_contact(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = self._bounded_limit(arguments.get("limit"), default=5, maximum=20)
        return await self.contacts.resolve(str(arguments["query"]).strip(), limit=limit)

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

    async def _execute_memory_search(
        self,
        arguments: dict[str, Any],
        *,
        context: ToolExecutionContext,
    ) -> dict[str, Any]:
        target_reference = str(arguments.get("contact") or "").strip()
        if target_reference:
            resolution = await self.contacts.resolve(target_reference, limit=5)
            if resolution.get("status") != "resolved" or not resolution.get("match"):
                raise ValueError(f"memory target contact is {resolution.get('status') or 'not_found'}")
            contact_id = int(resolution["match"]["contact_id"])
            contact_resolution = {
                "status": "resolved",
                "contact_id": contact_id,
                "confidence": resolution.get("confidence"),
                "matched_field": resolution["match"].get("matched_field"),
            }
        else:
            if context.requested_by_contact_id is None:
                raise ValueError("memory.search requires contact or requested_by_contact_id")
            contact_id = int(context.requested_by_contact_id)
            contact_resolution = {"status": "requester", "contact_id": contact_id}

        query = str(arguments["query"]).strip()
        normalized_query = normalize_text(query)
        limit = self._bounded_limit(arguments.get("limit"), default=5, maximum=20)

        memory = await self.memory.get_memory(contact_id)
        profile = self._matching_profile(memory, contact_id, normalized_query)

        fact_rows = (
            await self.session.execute(
                select(UserMemoryTimeline)
                .where(UserMemoryTimeline.contact_id == contact_id)
                .where(UserMemoryTimeline.is_enabled.is_(True))
                .where(UserMemoryTimeline.memory_text.ilike(f"%{query}%"))
                .order_by(
                    UserMemoryTimeline.importance.desc(),
                    UserMemoryTimeline.confidence.desc(),
                    UserMemoryTimeline.updated_at.desc(),
                )
                .limit(limit)
            )
        ).scalars().all()
        memory_facts = [self._memory_fact_dict(row) for row in fact_rows]

        timeline_rows = await self.memory.search_timeline(contact_id, query=query, limit=limit)
        timeline_entries = [self.memory._timeline_dict(row) for row in timeline_rows]

        recent_summaries = await self.memory.get_recent_summaries(contact_id, limit=max(50, limit))
        summaries = []
        for row in recent_summaries:
            searchable = " ".join([row.summary, *[str(item) for item in (row.topics or [])]])
            if normalized_query and normalized_query in normalize_text(searchable):
                summaries.append(self.memory._summary_dict(row))
            if len(summaries) >= limit:
                break

        used_sections: list[str] = []
        if profile:
            used_sections.append("Relationship Profile")
        if memory_facts:
            used_sections.append("Managed Memory Fact")
        if timeline_entries:
            used_sections.append("Timeline Entry")
        if summaries:
            used_sections.append("Summary Entry")

        context_text = self._build_memory_search_context(profile, memory_facts, timeline_entries, summaries)
        return {
            "contact_id": contact_id,
            "contact_resolution": contact_resolution,
            "query_matched": bool(profile or memory_facts or timeline_entries or summaries),
            "profile": profile,
            "memory_facts": memory_facts,
            "timeline_entries": timeline_entries,
            "summaries": summaries,
            "context_text": context_text,
            "retrieved_item_count": (1 if profile else 0) + len(memory_facts) + len(timeline_entries) + len(summaries),
            "used_sections": used_sections,
        }

    async def _execute_chat_read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        target_reference = str(arguments["contact"]).strip()
        resolution = await self.contacts.resolve(target_reference, limit=5)
        if resolution.get("status") != "resolved" or not resolution.get("match"):
            raise ValueError(f"chat target contact is {resolution.get('status') or 'not_found'}")

        contact_id = int(resolution["match"]["contact_id"])
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            raise ValueError("chat target contact no longer exists")

        limit = self._bounded_limit(arguments.get("limit"), default=50, maximum=200)
        after = self._parse_datetime(arguments.get("after"))
        before = self._parse_datetime(arguments.get("before"))
        if after and before and after > before:
            raise ValueError("chat.read after must not be later than before")

        identity_chat_ids = {
            value
            for value in (
                contact.chat_id,
                contact.whatsapp_id,
                contact.waha_contact_id,
                contact.waha_participant_id,
            )
            if value
        }
        scope_conditions = [Message.contact_id == contact_id]
        if identity_chat_ids:
            scope_conditions.append(Message.chat_id.in_(sorted(identity_chat_ids)))

        inbound_stmt = (
            select(Message)
            .where(Message.chat_type == "dm")
            .where(Message.direction == "inbound")
            .where(or_(*scope_conditions))
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        legacy_outbound_stmt = (
            select(Message)
            .where(Message.chat_type == "dm")
            .where(Message.direction == "outbound")
            .where(or_(*scope_conditions))
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        if after:
            inbound_stmt = inbound_stmt.where(Message.created_at >= after)
            legacy_outbound_stmt = legacy_outbound_stmt.where(Message.created_at >= after)
        if before:
            inbound_stmt = inbound_stmt.where(Message.created_at <= before)
            legacy_outbound_stmt = legacy_outbound_stmt.where(Message.created_at <= before)

        inbound_rows = (await self.session.execute(inbound_stmt)).scalars().all()
        legacy_outbound_rows = (await self.session.execute(legacy_outbound_stmt)).scalars().all()

        delivered_outbound_rows: list[OutboundMessage] = []
        if identity_chat_ids:
            delivered_stmt = (
                select(OutboundMessage)
                .where(OutboundMessage.chat_id.in_(sorted(identity_chat_ids)))
                .where(OutboundMessage.status == "sent")
                .order_by(OutboundMessage.updated_at.desc(), OutboundMessage.id.desc())
                .limit(limit)
            )
            if after:
                delivered_stmt = delivered_stmt.where(OutboundMessage.updated_at >= after)
            if before:
                delivered_stmt = delivered_stmt.where(OutboundMessage.updated_at <= before)
            delivered_outbound_rows = (await self.session.execute(delivered_stmt)).scalars().all()

        messages = [self._chat_message_dict(row) for row in inbound_rows]
        messages.extend(
            self._chat_message_dict(row)
            for row in legacy_outbound_rows
            if not self._message_outbound_queue_id(row)
        )
        messages.extend(self._outbound_queue_chat_message_dict(row) for row in delivered_outbound_rows)
        messages.sort(key=lambda item: (item["created_at"], str(item["id"])))
        messages = messages[-limit:]

        return {
            "contact_id": contact_id,
            "contact_resolution": {
                "status": "resolved",
                "confidence": resolution.get("confidence"),
                "matched_field": resolution["match"].get("matched_field"),
            },
            "message_count": len(messages),
            "limit": limit,
            "after": after,
            "before": before,
            "messages": messages,
            "window": {
                "oldest_at": messages[0]["created_at"] if messages else None,
                "newest_at": messages[-1]["created_at"] if messages else None,
            },
        }

    @staticmethod
    def _message_outbound_queue_id(row: Message) -> int | None:
        payload = row.raw_payload_json if isinstance(row.raw_payload_json, dict) else {}
        value = payload.get("outbound_queue_id")
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _chat_message_dict(row: Message) -> dict[str, Any]:
        return {
            "id": row.id,
            "source": "message",
            "direction": row.direction,
            "message_type": row.message_type,
            "text": row.message_text,
            "created_at": row.created_at,
        }

    @staticmethod
    def _outbound_queue_chat_message_dict(row: OutboundMessage) -> dict[str, Any]:
        return {
            "id": f"outbound_queue:{row.id}",
            "source": "outbound_queue",
            "direction": "outbound",
            "message_type": row.media_type or "text",
            "text": row.message_text,
            "created_at": row.updated_at,
            "delivery_status": row.status,
        }

    @staticmethod
    def _matching_profile(memory, contact_id: int, normalized_query: str) -> dict[str, Any]:
        if not memory or not normalized_query:
            return {}
        searchable_fields = (
            "user_name",
            "preferences",
            "context_notes",
            "profession",
            "interests",
            "projects",
            "goals",
            "communication_style",
            "relationship",
            "relationship_type",
            "personality_notes",
        )
        matches: dict[str, Any] = {}
        for field in searchable_fields:
            value = getattr(memory, field, None)
            if value and normalized_query in normalize_text(str(value)):
                matches[field] = value
        if not matches:
            return {}
        return {
            "contact_id": contact_id,
            "display_name": getattr(memory, "display_name", None) or getattr(memory, "user_name", None),
            **matches,
        }

    @staticmethod
    def _memory_fact_dict(row: UserMemoryTimeline) -> dict[str, Any]:
        return {
            "id": row.id,
            "contact_id": row.contact_id,
            "memory_text": row.memory_text,
            "source": row.source,
            "memory_type": row.memory_type,
            "importance": row.importance,
            "confidence": row.confidence,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def _build_memory_search_context(
        profile: dict[str, Any],
        memory_facts: list[dict[str, Any]],
        timeline_entries: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
    ) -> str:
        lines: list[str] = []
        if profile:
            name = profile.get("display_name")
            if name:
                lines.append(f"Contact: {name}")
            for key, value in profile.items():
                if key not in {"contact_id", "display_name"} and value:
                    lines.append(f"Profile {key}: {value}")
        for fact in memory_facts:
            lines.append(f"Memory fact: {fact['memory_text']}")
        for entry in timeline_entries:
            lines.append(f"Timeline: {entry['topic']}: {entry['summary']}")
        for summary in summaries:
            lines.append(f"Summary: {summary['summary']}")
        return "\n".join(lines)[:4000]

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
            if isinstance(value, int) and not isinstance(value, bool):
                minimum = definition.get("minimum")
                maximum = definition.get("maximum")
                if minimum is not None and value < int(minimum):
                    raise ValueError(f"tool argument below minimum: {field}")
                if maximum is not None and value > int(maximum):
                    raise ValueError(f"tool argument above maximum: {field}")

    @staticmethod
    def _bounded_limit(value: Any, *, default: int, maximum: int) -> int:
        if value is None:
            return default
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("limit must be an integer")
        return max(1, min(value, maximum))

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
                raise ValueError("datetime tool arguments must be ISO 8601") from exc
        else:
            raise ValueError("datetime tool arguments must be ISO 8601")
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("datetime tool arguments must include a timezone offset")
        return parsed

    @staticmethod
    def _result_id(result: dict[str, Any]) -> str | None:
        if result.get("id") is not None:
            return str(result["id"])
        match = result.get("match")
        if isinstance(match, dict) and match.get("contact_id") is not None:
            return str(match["contact_id"])
        if result.get("contact_id") is not None:
            return str(result["contact_id"])
        return None

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