from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.models.enums import ChatType, DecisionType, Direction, GroupReplyMode
from app.models.schema import DMConfig, GroupConfig, Message, ReplyRule
from app.utils.text import normalize_text
from app.utils.time import utcnow


@dataclass(slots=True)
class RulesResult:
    should_continue: bool
    decision_type: DecisionType | None
    reason: str
    reply_text: str | None


class RulesEngine:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def evaluate(self, message: NormalizedMessage, contact_id: int | None) -> RulesResult:
        if not message.message_text.strip():
            return RulesResult(False, DecisionType.IGNORE, "non-text or empty message", None)
        if not settings.enable_auto_reply:
            return RulesResult(False, DecisionType.IGNORE, "auto reply disabled", None)

        if message.chat_type == ChatType.GROUP:
            return await self._evaluate_group(message)
        return await self._evaluate_dm(message, contact_id)

    async def _evaluate_group(self, message: NormalizedMessage) -> RulesResult:
        cfg = await self._get_group_config(message.chat_id)
        if not cfg["is_enabled"]:
            return RulesResult(False, DecisionType.IGNORE, "group disabled by config", None)
        if cfg["reply_mode"] == GroupReplyMode.OFF.value:
            return RulesResult(False, DecisionType.IGNORE, "group mode off", None)
        if cfg["reply_mode"] == GroupReplyMode.MENTION_ONLY.value and not message.is_bot_mentioned:
            return RulesResult(False, DecisionType.IGNORE, "mention required", None)
        if await self._cooldown_active(message.chat_id, int(cfg["cooldown_seconds"])):
            return RulesResult(False, DecisionType.COOLDOWN_BLOCK, "group cooldown active", None)

        rule_reply = await self._resolve_reply_rule(message.message_text, ChatType.GROUP)
        if rule_reply:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched reply rule", rule_reply)

        return RulesResult(True, None, "group rules passed", None)

    async def _evaluate_dm(self, message: NormalizedMessage, contact_id: int | None) -> RulesResult:
        cfg = await self._get_dm_config(contact_id)
        if not cfg["is_enabled"]:
            return RulesResult(False, DecisionType.IGNORE, "dm disabled by config", None)
        if await self._cooldown_active(message.chat_id, int(cfg["cooldown_seconds"])):
            return RulesResult(False, DecisionType.COOLDOWN_BLOCK, "dm cooldown active", None)

        rule_reply = await self._resolve_reply_rule(message.message_text, ChatType.DM)
        if rule_reply:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched reply rule", rule_reply)

        return RulesResult(True, None, "dm rules passed", None)

    async def _cooldown_active(self, chat_id: str, cooldown_seconds: int) -> bool:
        if cooldown_seconds <= 0:
            return False
        cutoff = utcnow() - timedelta(seconds=cooldown_seconds)
        stmt = (
            select(Message.id)
            .where(Message.chat_id == chat_id)
            .where(Message.direction == Direction.OUTBOUND.value)
            .where(Message.created_at >= cutoff)
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def _get_group_config(self, chat_id: str) -> dict[str, object]:
        stmt = select(GroupConfig).where(GroupConfig.chat_id == chat_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if not model:
            return {
                "reply_mode": settings.group_default_reply_mode,
                "is_enabled": True,
                "cooldown_seconds": settings.group_default_cooldown_seconds,
            }
        return {
            "reply_mode": model.reply_mode,
            "is_enabled": model.is_enabled,
            "cooldown_seconds": model.cooldown_seconds,
        }

    async def _get_dm_config(self, contact_id: int | None) -> dict[str, object]:
        if not contact_id:
            return {"is_enabled": True, "cooldown_seconds": settings.dm_default_cooldown_seconds}
        stmt = select(DMConfig).where(DMConfig.contact_id == contact_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if not model:
            return {"is_enabled": True, "cooldown_seconds": settings.dm_default_cooldown_seconds}
        return {"is_enabled": model.is_enabled, "cooldown_seconds": model.cooldown_seconds}

    async def _resolve_reply_rule(self, message_text: str, chat_type: ChatType) -> str | None:
        """Query reply_rules table for a matching rule, ordered by priority."""
        normalized = normalize_text(message_text)
        stmt = (
            select(ReplyRule)
            .where(ReplyRule.is_enabled.is_(True))
            .where(
                (ReplyRule.chat_type_filter.is_(None)) | (ReplyRule.chat_type_filter == chat_type.value)
            )
            .order_by(ReplyRule.priority.desc())
        )
        rules = (await self.session.execute(stmt)).scalars().all()

        for rule in rules:
            rule_keyword = normalize_text(rule.keyword)
            if rule.match_mode == "exact" and normalized == rule_keyword:
                return rule.response_text
            if rule.match_mode == "contains" and rule_keyword in normalized:
                return rule.response_text
            if rule.match_mode == "startswith" and normalized.startswith(rule_keyword):
                return rule.response_text

        return None
