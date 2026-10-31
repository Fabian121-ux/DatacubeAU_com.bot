from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.intent_classifier import IntentClassifier, MessageIntent
from app.core.message_normalizer import NormalizedMessage
from app.models.enums import ChatType, DecisionType, Direction, GroupReplyMode
from app.models.schema import DMConfig, ForcedReplyTarget, GroupConfig, Message, ReplyRule, UserTrigger
from app.services.bot_config_service import BotConfigService
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
        self.bot_config = BotConfigService(session)

    async def evaluate(self, message: NormalizedMessage, contact_id: int | None) -> RulesResult:
        if not message.message_text.strip():
            return RulesResult(False, DecisionType.IGNORE, "non-text or empty message", None)
        if not settings.enable_auto_reply:
            return RulesResult(False, DecisionType.IGNORE, "auto reply disabled", None)
        if not await self.bot_config.get_bool("bot_enabled", True):
            return RulesResult(False, DecisionType.IGNORE, "bot stopped by owner command", None)
        if await self.bot_config.get_bool("maintenance_mode", False):
            return RulesResult(False, DecisionType.IGNORE, "maintenance mode active", None)

        if message.chat_type == ChatType.GROUP:
            return await self._evaluate_group(message, contact_id)
        return await self._evaluate_dm(message, contact_id)

    async def _evaluate_group(self, message: NormalizedMessage, contact_id: int | None) -> RulesResult:
        cfg = await self._get_group_config(message.chat_id)
        if not cfg["is_enabled"]:
            return RulesResult(False, DecisionType.IGNORE, "group disabled by config", None)
        if cfg["reply_mode"] == GroupReplyMode.OFF.value:
            return RulesResult(False, DecisionType.IGNORE, "group mode off", None)

        trigger_reply = await self._resolve_user_trigger(message, contact_id)
        if trigger_reply:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched user trigger", trigger_reply)

        forced_reply = await self._is_forced_reply_target(message.sender_id, contact_id)
        if cfg["reply_mode"] == GroupReplyMode.MENTION_ONLY.value and not message.is_bot_mentioned and not forced_reply:
            return RulesResult(False, DecisionType.IGNORE, "mention required", None)
        if not forced_reply and await self._cooldown_active(message.chat_id, int(cfg["cooldown_seconds"])):
            return RulesResult(False, DecisionType.COOLDOWN_BLOCK, "group cooldown active", None)

        rule_reply = await self._resolve_reply_rule(message.message_text, ChatType.GROUP)
        if rule_reply:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched reply rule", rule_reply)

        return RulesResult(True, None, "group rules passed", None)

    async def _evaluate_dm(self, message: NormalizedMessage, contact_id: int | None) -> RulesResult:
        cfg = await self._get_dm_config(contact_id)
        if not cfg["is_enabled"]:
            return RulesResult(False, DecisionType.IGNORE, "dm disabled by config", None)
        trigger_reply = await self._resolve_user_trigger(message, contact_id)
        if trigger_reply:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched user trigger", trigger_reply)
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
            default_mode = await self.bot_config.get("group_default_reply_mode", settings.group_default_reply_mode)
            return {
                "reply_mode": default_mode,
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
        intent = IntentClassifier.classify(message_text).intent
        if intent in {
            MessageIntent.GREETING,
            MessageIntent.IDENTITY_QUESTION,
            MessageIntent.MEMORY_RECALL,
            MessageIntent.FOLLOW_UP,
            MessageIntent.GENERAL_KNOWLEDGE,
        }:
            return None
        if self._is_identity_question(normalized):
            return await self.bot_config.introduction_reply()

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

    async def _is_forced_reply_target(self, sender_id: str, contact_id: int | None) -> bool:
        conditions = [ForcedReplyTarget.target_whatsapp_id == sender_id]
        if contact_id:
            conditions.append(ForcedReplyTarget.target_contact_id == contact_id)
        stmt = (
            select(ForcedReplyTarget.id)
            .where(ForcedReplyTarget.is_enabled.is_(True))
            .where(or_(*conditions))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None

    async def _resolve_user_trigger(self, message: NormalizedMessage, contact_id: int | None) -> str | None:
        conditions = [UserTrigger.target_whatsapp_id == message.sender_id]
        if contact_id:
            conditions.append(UserTrigger.target_contact_id == contact_id)
        stmt = (
            select(UserTrigger)
            .where(UserTrigger.is_enabled.is_(True))
            .where(or_(*conditions))
            .order_by(UserTrigger.created_at.desc())
        )
        triggers = (await self.session.execute(stmt)).scalars().all()
        normalized_message = normalize_text(message.message_text)
        for trigger in triggers:
            if trigger.normalized_trigger_text and trigger.normalized_trigger_text in normalized_message:
                return trigger.response_text
        return None

    @staticmethod
    def _is_identity_question(normalized_text: str) -> bool:
        identity_questions = {
            "who are you",
            "what is your name",
            "whats your name",
            "your name",
            "tell me your name",
            "introduce yourself",
            "who is this",
        }
        return normalized_text in identity_questions
