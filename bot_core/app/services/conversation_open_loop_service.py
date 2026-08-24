from __future__ import annotations

import re
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_open_loop import ConversationOpenLoop
from app.models.schema import AuditLog, BotConfig, ConversationSummary, Message
from app.utils.text import normalize_text
from app.utils.time import utcnow


SCAN_CURSOR_KEY = "memory_open_loop_scanner_last_message_id"
OPEN_LOOP_PROJECTION_SOURCE = "open_loop_projection"

_REQUEST_PREFIXES = (
    "please ",
    "can you ",
    "could you ",
    "would you ",
    "will you ",
    "kindly ",
    "let me know ",
    "remind me ",
    "send me ",
    "help me ",
)
_RESOLUTION_MESSAGES = {
    "all sorted",
    "done now",
    "forget it",
    "it is resolved",
    "it is sorted",
    "never mind",
    "nevermind",
    "problem solved",
    "resolved",
    "sorted",
    "that is resolved",
    "that is sorted",
    "that solves it",
}
_IGNORED_SHORT_MESSAGES = {
    "hello",
    "hey",
    "hi",
    "how are you",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "yo",
}


class ConversationOpenLoopService:
    """Maintain durable unresolved questions/requests and a Memory Engine projection.

    `conversation_open_loops` is authoritative mutable state. A derived
    `ConversationSummary` row is rebuilt only when that state changes so the
    existing Memory -> AI context path can consume unresolved items without a
    second prompt or retrieval system.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def scan_once(self, *, limit: int = 100) -> dict[str, int]:
        cursor = await self._get_cursor()
        rows = list(
            (
                await self.session.execute(
                    select(Message)
                    .where(Message.id > cursor)
                    .order_by(Message.id)
                    .limit(max(1, min(limit, 500)))
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return {"processed": 0, "created": 0, "repeated": 0, "resolved": 0}

        created = 0
        repeated = 0
        resolved = 0
        changed_contacts: set[int] = set()

        for message in rows:
            if message.direction != "inbound" or not message.contact_id:
                continue
            text_value = (message.message_text or "").strip()
            normalized = normalize_text(text_value)
            if not normalized:
                continue

            if normalized in _RESOLUTION_MESSAGES:
                closed = await self._resolve_single_active_loop(message)
                if closed:
                    resolved += 1
                    changed_contacts.add(message.contact_id)
                continue

            loop_type = self.classify_open_loop(text_value)
            if not loop_type:
                continue
            outcome = await self._upsert_open_loop(message, loop_type, normalized)
            if outcome == "created":
                created += 1
                changed_contacts.add(message.contact_id)
            elif outcome == "repeated":
                repeated += 1
                changed_contacts.add(message.contact_id)

        for contact_id in changed_contacts:
            await self._refresh_memory_projection(contact_id)

        await self._set_cursor(int(rows[-1].id))
        await self.session.flush()
        return {
            "processed": len(rows),
            "created": created,
            "repeated": repeated,
            "resolved": resolved,
        }

    @staticmethod
    def classify_open_loop(message_text: str) -> str | None:
        text_value = (message_text or "").strip()
        normalized = normalize_text(text_value)
        if not normalized or normalized in _IGNORED_SHORT_MESSAGES or normalized in _RESOLUTION_MESSAGES:
            return None
        if len(normalized) < 4:
            return None
        if "?" in text_value:
            return "question"
        if any(normalized.startswith(prefix.strip()) or normalized.startswith(prefix) for prefix in _REQUEST_PREFIXES):
            return "request"
        if re.match(r"^(please|kindly)\b", normalized):
            return "request"
        return None

    async def list_active(self, contact_id: int, *, limit: int = 8) -> list[ConversationOpenLoop]:
        stmt = (
            select(ConversationOpenLoop)
            .where(ConversationOpenLoop.contact_id == contact_id)
            .where(ConversationOpenLoop.status == "open")
            .order_by(ConversationOpenLoop.updated_at.desc(), ConversationOpenLoop.id.desc())
            .limit(max(1, min(limit, 20)))
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def _upsert_open_loop(self, message: Message, loop_type: str, normalized: str) -> str:
        active = await self.list_active(int(message.contact_id), limit=20)
        duplicate = next(
            (
                row
                for row in active
                if row.chat_id == message.chat_id and row.normalized_text == normalized
            ),
            None,
        )
        if duplicate:
            duplicate.last_message_id = message.id
            duplicate.updated_at = utcnow()
            metadata = dict(duplicate.metadata_json or {})
            metadata["repeat_count"] = int(metadata.get("repeat_count") or 1) + 1
            metadata["last_seen_message_id"] = message.id
            duplicate.metadata_json = metadata
            self.session.add(
                AuditLog(
                    action="conversation_open_loop_repeated",
                    entity_type="conversation_open_loop",
                    entity_id=str(duplicate.id),
                    details_json={"contact_id": message.contact_id, "chat_id": message.chat_id, "message_id": message.id},
                )
            )
            return "repeated"

        loop = ConversationOpenLoop(
            contact_id=int(message.contact_id),
            chat_id=message.chat_id,
            source_message_id=message.id,
            last_message_id=message.id,
            loop_type=loop_type,
            loop_text=(message.message_text or "").strip()[:1600],
            normalized_text=normalized[:1600],
            status="open",
            metadata_json={"repeat_count": 1, "last_seen_message_id": message.id},
            updated_at=utcnow(),
        )
        self.session.add(loop)
        await self.session.flush()
        self.session.add(
            AuditLog(
                action="conversation_open_loop_created",
                entity_type="conversation_open_loop",
                entity_id=str(loop.id),
                details_json={
                    "contact_id": message.contact_id,
                    "chat_id": message.chat_id,
                    "message_id": message.id,
                    "loop_type": loop_type,
                },
            )
        )
        return "created"

    async def _resolve_single_active_loop(self, message: Message) -> bool:
        active = [row for row in await self.list_active(int(message.contact_id), limit=20) if row.chat_id == message.chat_id]
        if len(active) != 1:
            return False
        loop = active[0]
        loop.status = "resolved"
        loop.resolution_message_id = message.id
        loop.resolution_reason = "contact_explicit_resolution"
        loop.resolved_at = utcnow()
        loop.updated_at = utcnow()
        self.session.add(
            AuditLog(
                action="conversation_open_loop_resolved",
                entity_type="conversation_open_loop",
                entity_id=str(loop.id),
                details_json={
                    "contact_id": message.contact_id,
                    "chat_id": message.chat_id,
                    "resolution_message_id": message.id,
                    "resolution_reason": loop.resolution_reason,
                },
            )
        )
        return True

    async def _refresh_memory_projection(self, contact_id: int) -> None:
        await self.session.execute(
            delete(ConversationSummary)
            .where(ConversationSummary.contact_id == contact_id)
            .where(ConversationSummary.source == OPEN_LOOP_PROJECTION_SOURCE)
        )
        active = await self.list_active(contact_id, limit=8)
        if not active:
            return

        message_count = (
            await self.session.execute(select(func.count(Message.id)).where(Message.contact_id == contact_id))
        ).scalar_one()
        lines = ["Unresolved conversation items:"]
        for row in reversed(active[:8]):
            lines.append(f"- [{row.loop_type}] {row.loop_text[:500]}")
        projection = ConversationSummary(
            contact_id=contact_id,
            summary="\n".join(lines)[:1800],
            topics=["Unresolved questions and requests"],
            message_count=int(message_count or 0),
            threshold=None,
            source=OPEN_LOOP_PROJECTION_SOURCE,
            updated_at=utcnow(),
        )
        self.session.add(projection)
        await self.session.flush()
        self.session.add(
            AuditLog(
                action="conversation_open_loop_projection_refreshed",
                entity_type="conversation_summary",
                entity_id=str(projection.id),
                details_json={
                    "contact_id": contact_id,
                    "active_loop_ids": [row.id for row in active],
                    "active_loop_count": len(active),
                    "source": OPEN_LOOP_PROJECTION_SOURCE,
                },
            )
        )

    async def _get_cursor(self) -> int:
        row = (
            await self.session.execute(select(BotConfig).where(BotConfig.config_key == SCAN_CURSOR_KEY).limit(1))
        ).scalar_one_or_none()
        if not row:
            return 0
        try:
            return max(0, int(row.config_value or 0))
        except (TypeError, ValueError):
            return 0

    async def _set_cursor(self, message_id: int) -> None:
        row = (
            await self.session.execute(select(BotConfig).where(BotConfig.config_key == SCAN_CURSOR_KEY).limit(1))
        ).scalar_one_or_none()
        if row:
            row.config_value = str(message_id)
            row.updated_at = utcnow()
            return
        self.session.add(BotConfig(config_key=SCAN_CURSOR_KEY, config_value=str(message_id), updated_at=utcnow()))
