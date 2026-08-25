from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_open_loop import ConversationOpenLoop
from app.models.scheduled_action import ScheduledAction
from app.models.schema import Contact, ConversationSummary, UserMemory, UserMemoryTimeline
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext
from app.utils.time import utcnow


class ConversationExportService:
    """Build the stable owner-only `zina.chat.v1` conversation projection.

    The export is a projection only. Delivery-correct conversation history remains owned
    by `chat.read`; Memory Engine tables remain authoritative for managed memory and
    summaries; ConversationOpenLoop remains authoritative for unresolved state; and
    ScheduledAction remains authoritative for owner-approved actions.
    """

    SCHEMA_VERSION = "zina.chat.v1"
    MAX_FACTS = 100
    MAX_SUMMARIES = 20
    MAX_OPEN_LOOPS = 100
    MAX_ACTIONS = 50

    def __init__(self, session: AsyncSession):
        self.session = session
        self.tools = ToolDispatcherService(session)

    async def export(
        self,
        *,
        contact_reference: str,
        limit: int = 200,
        after: datetime | None = None,
        before: datetime | None = None,
        requested_by_contact_id: int | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {"contact": contact_reference, "limit": limit}
        if after is not None:
            arguments["after"] = after.isoformat()
        if before is not None:
            arguments["before"] = before.isoformat()

        chat_execution = await self.tools.execute(
            "chat.read",
            arguments,
            context=ToolExecutionContext(
                permission="owner",
                requested_by_contact_id=requested_by_contact_id,
            ),
        )
        chat = chat_execution["result"]
        contact_id = int(chat["contact_id"])
        contact = await self.session.get(Contact, contact_id)
        if not contact:
            raise ValueError("resolved contact no longer exists")

        return {
            "schema_version": self.SCHEMA_VERSION,
            "generated_at": utcnow(),
            "contact": self._contact_payload(contact),
            "relationship": await self._relationship(contact_id),
            "conversation": {
                "message_count": chat["message_count"],
                "limit": chat["limit"],
                "after": chat["after"],
                "before": chat["before"],
                "window": chat["window"],
                "messages": chat["messages"],
            },
            "memory": {
                "facts": await self._memory_facts(contact_id),
                "summaries": await self._summaries(contact_id),
            },
            "open_loops": await self._open_loops(contact_id),
            "zina_activity": {
                "scheduled_actions": await self._scheduled_actions(contact_id),
            },
            "analysis": {
                "status": "not_generated",
                "note": "Derived conversation analysis is intentionally outside zina.chat.v1 export generation.",
            },
            "provenance": {
                "chat_history_tool": "chat.read",
                "chat_history_handler": chat_execution["handler_target"],
                "contact_resolution": chat["contact_resolution"],
                "authoritative_sources": {
                    "messages": "PostgreSQL messages plus successful outbound delivery evidence",
                    "memory": "PostgreSQL user_memory/user_memory_timeline/conversation_summaries",
                    "open_loops": "PostgreSQL conversation_open_loops",
                    "scheduled_actions": "PostgreSQL scheduled_actions",
                },
            },
        }

    async def _relationship(self, contact_id: int) -> dict[str, Any]:
        row = (
            await self.session.execute(
                select(UserMemory)
                .where(UserMemory.contact_id == contact_id)
                .where(UserMemory.is_enabled.is_(True))
                .limit(1)
            )
        ).scalar_one_or_none()
        if not row:
            return {
                "type": "unknown",
                "relationship": None,
                "profession": None,
                "interests": None,
                "projects": None,
                "goals": None,
                "preferences": None,
                "communication_style": None,
                "personality_notes": None,
            }
        return {
            "type": row.relationship_type or "unknown",
            "relationship": row.relationship,
            "profession": row.profession,
            "interests": row.interests,
            "projects": row.projects,
            "goals": row.goals,
            "preferences": row.preferences,
            "communication_style": row.communication_style,
            "personality_notes": row.personality_notes,
        }

    async def _memory_facts(self, contact_id: int) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(UserMemoryTimeline)
                .where(UserMemoryTimeline.contact_id == contact_id)
                .where(UserMemoryTimeline.is_enabled.is_(True))
                .order_by(
                    UserMemoryTimeline.importance.desc(),
                    UserMemoryTimeline.updated_at.desc(),
                    UserMemoryTimeline.id.desc(),
                )
                .limit(self.MAX_FACTS)
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "text": row.memory_text,
                "type": row.memory_type,
                "source": row.source,
                "importance": row.importance,
                "confidence": row.confidence,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    async def _summaries(self, contact_id: int) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(ConversationSummary)
                .where(ConversationSummary.contact_id == contact_id)
                .where(ConversationSummary.source != "open_loop_projection")
                .order_by(ConversationSummary.created_at.desc(), ConversationSummary.id.desc())
                .limit(self.MAX_SUMMARIES)
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "summary": row.summary,
                "topics": row.topics or [],
                "message_count": row.message_count,
                "threshold": row.threshold,
                "source": row.source,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    async def _open_loops(self, contact_id: int) -> list[dict[str, Any]]:
        # The export is a private DM projection. A contact may also appear in group
        # threads, so do not let group/status/newsletter open loops leak into it.
        dm_chat = or_(
            ConversationOpenLoop.chat_id.ilike("%@c.us"),
            ConversationOpenLoop.chat_id.ilike("%@s.whatsapp.net"),
            ConversationOpenLoop.chat_id.ilike("%@lid"),
        )
        rows = (
            await self.session.execute(
                select(ConversationOpenLoop)
                .where(ConversationOpenLoop.contact_id == contact_id)
                .where(ConversationOpenLoop.status == "open")
                .where(dm_chat)
                .order_by(ConversationOpenLoop.updated_at.desc(), ConversationOpenLoop.id.desc())
                .limit(self.MAX_OPEN_LOOPS)
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "type": row.loop_type,
                "text": row.loop_text,
                "source_message_id": row.source_message_id,
                "last_message_id": row.last_message_id,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    async def _scheduled_actions(self, contact_id: int) -> list[dict[str, Any]]:
        rows = (
            await self.session.execute(
                select(ScheduledAction)
                .where(ScheduledAction.target_contact_id == contact_id)
                .order_by(ScheduledAction.updated_at.desc(), ScheduledAction.id.desc())
                .limit(self.MAX_ACTIONS)
            )
        ).scalars().all()
        return [
            {
                "id": row.id,
                "action_type": row.action_type,
                "status": row.status,
                "enabled": row.is_enabled,
                "target_chat_id": row.target_chat_id,
                "payload": row.payload_json,
                "timezone": row.timezone,
                "scheduled_for": row.scheduled_for,
                "source_message_id": row.source_message_id,
                "outbound_queue_id": row.outbound_queue_id,
                "retry_count": row.retry_count,
                "last_error": row.last_error,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "executed_at": row.executed_at,
                "cancelled_at": row.cancelled_at,
            }
            for row in rows
        ]

    @staticmethod
    def _contact_payload(contact: Contact) -> dict[str, Any]:
        identity = contact.identity_json if isinstance(contact.identity_json, dict) else {}
        aliases = identity.get("aliases") if isinstance(identity.get("aliases"), list) else []
        return {
            "contact_id": contact.id,
            "display_name": contact.display_name,
            "contact_name": contact.contact_name,
            "push_name": contact.push_name,
            "whatsapp_id": contact.whatsapp_id,
            "phone": contact.normalized_phone or contact.whatsapp_phone,
            "chat_id": contact.chat_id,
            "waha_contact_id": contact.waha_contact_id,
            "waha_participant_id": contact.waha_participant_id,
            "aliases": aliases,
            "identity_source": contact.identity_source,
            "is_name_verified": contact.is_name_verified,
        }
