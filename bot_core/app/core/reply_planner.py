from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.experience_formatter import (
    WhatsAppExperienceFormatter,
    WhatsAppMessageFormat,
    memory_context_indicators,
)
from app.core.intent_classifier import IntentClassifier, IntentResult, MessageIntent
from app.core.message_normalizer import NormalizedMessage
from app.core.rules_engine import RulesEngine
from app.models.enums import AIMode, ChatType, DecisionType
from app.models.schema import AICall, ConversationSession, Message
from app.services.bot_config_service import BotConfigService
from app.services.command_catalog_service import CommandCatalogService
from app.services.faq_service import FAQService
from app.services.identity_registry_service import IdentityRegistryService
from app.services.internet_service import InternetService
from app.services.memory_service import MemoryContextPackage, MemoryService
from app.services.openrouter_client import OpenRouterClient, OpenRouterClientError
from app.services.rate_limiter import RateLimiter
from app.services.retrieval_service import RetrievalService, SearchResult
from app.utils.hashing import sha256_text
from app.utils.text import looks_complex
from app.utils.text import normalize_text
from app.utils.time import utcnow


@dataclass(slots=True)
class PlannedReply:
    decision_type: DecisionType
    reason: str
    should_reply: bool
    reply_text: str | None
    kb_confidence: float = 0.0
    matched_chunks: list[dict[str, object]] = field(default_factory=list)
    source_diagnostics: dict[str, object] = field(default_factory=dict)
    ai_used: bool = False
    ai_call: AICall | None = None
    raw_reply_text: str | None = None
    media_url: str | None = None
    media_type: str | None = None
    media_caption: str | None = None
    intent: str = MessageIntent.STATEMENT.value


class ReplyPlanner:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules = RulesEngine(session)
        self.faq = FAQService(session)
        self.identity_registry = IdentityRegistryService(session)
        self.retrieval = RetrievalService(session)
        self.memory_service = MemoryService(session)
        self.internet_service = InternetService(session)
        self.command_catalog = CommandCatalogService(session)
        self.rate_limiter = RateLimiter(session)
        self.bot_config = BotConfigService(session)
        self.formatter = WhatsAppExperienceFormatter()
        self.intent_classifier = IntentClassifier()
        self._active_intent: IntentResult | None = None
        self._active_question: str = ""

    async def plan(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
        original_text = message.message_text
        intent_result = self.intent_classifier.classify(original_text)
        self._active_intent = intent_result
        self._active_question = original_text

        command_reply = await self._handle_global_chat_command(message, contact_id)
        if command_reply:
            return await self._apply_identity_guard(command_reply)

        global_chat_one_shot = False
        ask_text = self._extract_ask_text(message.message_text)
        if ask_text is not None:
            if not ask_text.strip():
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason="empty global chat command",
                    should_reply=True,
                    reply_text="Use `!ask` followed by your question.",
                    source_diagnostics={"source": "Command", "global_chat": {"one_shot": True, "valid": False}},
                ))
            global_chat_one_shot = True
            await self._record_command_usage("!ask")
            message = replace(
                message,
                message_text=ask_text.strip(),
                normalized_text=normalize_text(ask_text),
            )
            self._active_question = message.message_text

        internet_request: tuple[str, str, str] | None = None
        service, command, query = self.internet_service.parse_user_command(message.message_text)
        if service:
            if not await self.command_catalog.is_enabled(command):
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason=f"command disabled: {command}",
                    should_reply=True,
                    reply_text="This command is currently disabled.",
                    source_diagnostics={"source": "Command", "internet": {"command": command, "enabled": False}},
                ))
            if not query:
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason="internet command missing query",
                    should_reply=True,
                    reply_text=self.internet_service.usage_for_command(command),
                    source_diagnostics={"source": "Internet", "internet": {"command": command, "valid": False}},
                ))
            await self._record_command_usage(command)
            internet_request = (service, command, query)
            message = replace(
                message,
                message_text=query,
                normalized_text=normalize_text(query),
            )
            self._active_question = message.message_text

        # Operational controls, mention gates, cooldowns, triggers, and safe custom rules.
        rules_result = await self.rules.evaluate(message, contact_id)
        if not rules_result.should_continue:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=rules_result.decision_type or DecisionType.IGNORE,
                reason=rules_result.reason,
                should_reply=rules_result.reply_text is not None,
                reply_text=rules_result.reply_text,
                source_diagnostics={"rules": {"matched": bool(rules_result.reply_text), "reason": rules_result.reason}},
            ))

        # Guardrail: rate limit before spending retrieval/AI work.
        if contact_id:
            rate_check = await self.rate_limiter.check_user_daily_limit(contact_id)
            if not rate_check.allowed:
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.RATE_LIMITED,
                    reason=rate_check.reason,
                    should_reply=True,
                    reply_text="You've reached the daily message limit. Please try again tomorrow.",
                    source_diagnostics={"rate_limit": {"allowed": False, "reason": rate_check.reason}},
                ))

        if intent_result.intent == MessageIntent.GREETING and not internet_request and not global_chat_one_shot:
            return await self._greeting_reply(message, contact_id)

        if intent_result.intent == MessageIntent.IDENTITY_QUESTION and not internet_request and not global_chat_one_shot:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.STATIC_REPLY,
                reason="identity engine answered identity question",
                should_reply=True,
                reply_text=await self.bot_config.identity_reply(message.message_text),
                source_diagnostics={"source": "Identity", "identity": {"authoritative": True}},
            ))

        # 1-3. Contact-scoped relationship memory, timeline, and summaries.
        memory_package: MemoryContextPackage | None = None
        context_diagnostics: dict[str, object] = {"used": False}
        if contact_id:
            memory_package = await self.memory_service.get_context_package(
                contact_id,
                query=message.message_text,
            )
            expanded_message, context_diagnostics = await self._resolve_follow_up(message, memory_package)
            if expanded_message:
                message = expanded_message
                if intent_result.intent == MessageIntent.FOLLOW_UP:
                    identity_reply = await self._identity_reply_if_known_project(message.message_text)
                    if identity_reply:
                        return await self._apply_identity_guard(PlannedReply(
                            decision_type=DecisionType.STATIC_REPLY,
                            reason="follow-up resolved to identity/project context",
                            should_reply=True,
                            reply_text=identity_reply,
                            source_diagnostics={
                                "source": "Identity",
                                "context": context_diagnostics,
                                "memory": {
                                    **self.memory_service.diagnostics_for_package(memory_package),
                                    "context_used": True,
                                },
                            },
                        ))
            memory_answer = self.memory_service.build_memory_answer(message.message_text, memory_package)
            if memory_answer:
                answer_text, memory_source = memory_answer
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.MEMORY_REPLY,
                    reason="relationship memory answered request",
                    should_reply=True,
                    reply_text=answer_text,
                    source_diagnostics={
                        "source": memory_source,
                        "context": context_diagnostics,
                        "memory": {
                            **self.memory_service.diagnostics_for_package(memory_package),
                            "context_used": True,
                        },
                        "global_chat": {"one_shot": global_chat_one_shot, "active": False},
                    },
                ))
        elif intent_result.intent == MessageIntent.MEMORY_RECALL:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.MEMORY_REPLY,
                reason="memory recall requested without contact profile",
                should_reply=True,
                reply_text="I do not have your profile saved yet.",
                source_diagnostics={"source": "Memory", "memory": {"retrieved_items": 0, "context_used": True}},
            ))

        # 4. Core FAQ layer.
        context_entities = []
        active_topic = context_diagnostics.get("active_topic") if isinstance(context_diagnostics, dict) else None
        if isinstance(active_topic, str) and active_topic:
            context_entities.append(active_topic)
        faq_entry, faq_score = await self.faq.search_faq(message.message_text, context_entities=context_entities)
        if faq_entry:
            faq_answer = await self.identity_registry.resolve_references(faq_entry.answer)
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.FAQ_REPLY,
                reason="core FAQ match above threshold",
                should_reply=True,
                reply_text=faq_answer,
                kb_confidence=faq_score,
                source_diagnostics={
                    "source": "FAQ",
                    "faq": {
                        "matched": True,
                        "score": faq_score,
                        "entry_id": faq_entry.id,
                        "question": faq_entry.question,
                        "intent": getattr(faq_entry, "intent", ""),
                        "category": getattr(faq_entry, "category", ""),
                        "entities": getattr(faq_entry, "entities", None) or [],
                        "keywords": getattr(faq_entry, "keywords", None) or [],
                    },
                    "context": context_diagnostics,
                },
            ))

        # 5. Knowledge search.
        search_result = await self.retrieval.search(message.message_text)
        retrieval_context = self.retrieval.prompt_context(search_result)
        if search_result.chunks and search_result.confidence >= settings.kb_min_score:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.KB_REPLY,
                reason="knowledge match above threshold",
                should_reply=True,
                reply_text=self.retrieval.build_kb_reply(search_result),
                kb_confidence=search_result.confidence,
                matched_chunks=retrieval_context,
                source_diagnostics={
                    "faq": {"matched": False, "score": faq_score},
                    "cache": {"hit": False},
                    "kb": {"matched": True, "confidence": search_result.confidence, "chunks": retrieval_context},
                    "context": context_diagnostics,
                },
            ))

        # Reusable local answer cache sits below live FAQ/KB so edited local knowledge wins.
        cache_hit = await self.retrieval.lookup_cache(message.message_text)
        if cache_hit:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.KB_REPLY,
                reason="cached faq/knowledge match",
                should_reply=True,
                reply_text=cache_hit.answer_text,
                kb_confidence=float(cache_hit.confidence),
                matched_chunks=[],
                source_diagnostics={
                    "faq": {"matched": False, "score": faq_score},
                    "kb": {"matched": False, "confidence": search_result.confidence, "chunks": retrieval_context},
                    "cache": {"hit": True, "cache_id": cache_hit.id, "answer_mode": cache_hit.answer_mode},
                    "memory": {
                        **self.memory_service.diagnostics_for_package(memory_package),
                        "context_used": bool(context_diagnostics.get("used")),
                    },
                    "context": context_diagnostics,
                },
            ))

        # Memory onboarding check (DM only), after local answer layers so useful answers are not blocked.
        if contact_id and message.chat_type == ChatType.DM:
            onboard_reply, stage = await self.memory_service.check_onboarding(
                contact_id, message.message_text
            )
            if onboard_reply:
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.MEMORY_ONBOARD,
                    reason=f"onboarding: {stage}" if stage else "onboarding complete",
                    should_reply=True,
                    reply_text=onboard_reply,
                    kb_confidence=search_result.confidence,
                    matched_chunks=retrieval_context,
                    source_diagnostics={
                        "faq": {"matched": False, "score": faq_score},
                        "cache": {"hit": False},
                        "kb": {"matched": False, "confidence": search_result.confidence, "chunks": retrieval_context},
                        "memory": {
                            **self.memory_service.diagnostics_for_package(memory_package),
                            "onboarding_stage": stage,
                        },
                        "context": context_diagnostics,
                        "global_chat": {"one_shot": global_chat_one_shot, "active": False},
                    },
                ))

        # 6-7. Internet cache first, then SearXNG/provider lookup. Explicit commands use their target service.
        if internet_request:
            internet_reply = await self._run_internet_request(
                service=internet_request[0],
                command=internet_request[1],
                query=internet_request[2],
                contact_id=contact_id,
                reason=f"internet command: {internet_request[1]}",
            )
            return await self._apply_identity_guard(internet_reply)

        internet_live_reply = await self._maybe_live_internet_reply(message, contact_id)
        if internet_live_reply:
            return await self._apply_identity_guard(internet_live_reply)

        # 8. OpenRouter fallback, only after local and internet layers fail.
        global_chat_active = global_chat_one_shot or self._memory_global_chat_enabled(memory_package)
        global_chat_system_enabled = await self.bot_config.get_bool("global_chat_enabled", True)
        ai_enabled_config = await self.bot_config.get_bool("ai_enabled", False)
        ai_needed = (
            self._requires_openrouter(message.message_text)
            or global_chat_one_shot
            or intent_result.intent in {MessageIntent.GENERAL_KNOWLEDGE, MessageIntent.OPINION_REQUEST}
        )
        direct_ai_allowed = intent_result.intent in {MessageIntent.GENERAL_KNOWLEDGE, MessageIntent.OPINION_REQUEST}
        ai_enabled = (
            (global_chat_active or direct_ai_allowed)
            and (global_chat_system_enabled or direct_ai_allowed)
            and ai_needed
            and (settings.ai_enabled or ai_enabled_config or bool(settings.openrouter_api_key))
        )
        if ai_enabled:
            if contact_id:
                user_ai_check = await self.rate_limiter.check_user_ai_quota(contact_id)
                if not user_ai_check.allowed:
                    return await self._apply_identity_guard(PlannedReply(
                        decision_type=DecisionType.RATE_LIMITED,
                        reason=user_ai_check.reason,
                        should_reply=True,
                        reply_text=(
                            "Global Chat limit reached.\n\n"
                            "Please try again tomorrow.\n\n"
                            "For live information, try:\n"
                            "• !search <query>\n"
                            "• !news <topic>\n"
                            "• !weather <city>\n"
                            "• !currency 100 USD to NGN"
                        ),
                        kb_confidence=search_result.confidence,
                        matched_chunks=retrieval_context,
                        source_diagnostics={
                            "source": "AI",
                            "faq": {"matched": False, "score": faq_score},
                            "cache": {"hit": False},
                            "kb": {"matched": False, "confidence": search_result.confidence, "chunks": retrieval_context},
                            "memory": self.memory_service.diagnostics_for_package(memory_package),
                            "context": context_diagnostics,
                            "ai_quota": {
                                "allowed": False,
                                "reason": user_ai_check.reason,
                                "limit": user_ai_check.limit,
                                "used": user_ai_check.used,
                                "reset_time": user_ai_check.reset_time,
                            },
                            "global_chat": {"one_shot": global_chat_one_shot, "active": global_chat_active},
                        },
                    ))

            global_check = await self.rate_limiter.check_global_ai_limit()
            if global_check.allowed:
                ai_plan = await self._try_ai(
                    message,
                    search_result,
                    contact_id,
                    memory_package=memory_package,
                    global_chat={"one_shot": global_chat_one_shot, "active": global_chat_active},
                    invocation_reason=self._ai_invocation_reason(message.message_text, intent_result, search_result.confidence),
                    faq_score=faq_score,
                    context_diagnostics=context_diagnostics,
                )
                if ai_plan:
                    return ai_plan

        # 8. Final fallback. Human escalation is reserved for private decisions.
        human_escalation = self._requires_human_escalation(message.message_text)
        no_match_text = await self._no_match_reply(message.chat_type, message.message_text)
        if intent_result.intent == MessageIntent.GENERAL_KNOWLEDGE:
            no_match_text = (
                "I do not have enough approved local information to answer that fully right now.\n\n"
                "If internet or AI reasoning is enabled, I can use those routes. Otherwise, try `!search <topic>` "
                "for live research."
            )
        return await self._apply_identity_guard(PlannedReply(
            decision_type=DecisionType.ESCALATED if human_escalation else DecisionType.NO_MATCH,
            reason=(
                "human escalation required for private owner decision"
                if human_escalation
                else "no identity, memory, faq, cache, knowledge, internet, or ai answer available"
            ),
            should_reply=no_match_text is not None,
            reply_text=no_match_text,
            kb_confidence=search_result.confidence,
            matched_chunks=retrieval_context,
            source_diagnostics={
                "faq": {"matched": False, "score": faq_score},
                "cache": {"hit": False},
                "kb": {"matched": False, "confidence": search_result.confidence, "chunks": retrieval_context},
                "memory": self.memory_service.diagnostics_for_package(memory_package),
                "context": context_diagnostics,
                "ai": {"used": False, "enabled": ai_enabled},
                "fallback": {
                    "human_escalation": human_escalation,
                    "reason": (
                        "private_owner_decision_or_personal_opinion"
                        if human_escalation
                        else "approved_sources_missing_and_ai_unavailable_or_failed"
                    ),
                },
                "global_chat": {
                    "one_shot": global_chat_one_shot,
                    "active": global_chat_active,
                    "system_enabled": global_chat_system_enabled,
                },
            },
        ))

    async def _greeting_reply(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
        memory_package: MemoryContextPackage | None = None
        if contact_id:
            memory_package = await self.memory_service.get_context_package(contact_id, query=message.message_text)
            continuation = self.memory_service.build_continuation_reply(message.message_text, memory_package)
            if continuation:
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.MEMORY_REPLY,
                    reason="greeting answered with meaningful memory context",
                    should_reply=True,
                    reply_text=continuation,
                    source_diagnostics={
                        "source": self.memory_service.source_label_for_package(memory_package, timeline_required=True),
                        "memory": {
                            **self.memory_service.diagnostics_for_package(memory_package),
                            "context_used": True,
                        },
                    },
                ))

            name = memory_package.profile.get("display_name") or memory_package.profile.get("user_name")
            has_prior_context = bool(memory_package.timeline_entries or memory_package.summaries)
            conversation_count = int(memory_package.profile.get("conversation_count") or 0)
            if name and (has_prior_context or conversation_count > 1):
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason="greeting recognized returning user",
                    should_reply=True,
                    reply_text=f"Welcome back {name}.",
                    source_diagnostics={
                        "source": "Memory",
                        "memory": {
                            **self.memory_service.diagnostics_for_package(memory_package),
                            "context_used": True,
                        },
                    },
                ))

        return await self._apply_identity_guard(PlannedReply(
            decision_type=DecisionType.STATIC_REPLY,
            reason="greeting handled before FAQ routing",
            should_reply=True,
            reply_text=await self.bot_config.introduction_reply(),
            source_diagnostics={"source": "Identity", "memory": self.memory_service.diagnostics_for_package(memory_package)},
        ))

    async def _resolve_follow_up(
        self,
        message: NormalizedMessage,
        memory_package: MemoryContextPackage,
    ) -> tuple[NormalizedMessage | None, dict[str, object]]:
        if not self._active_intent or self._active_intent.intent != MessageIntent.FOLLOW_UP:
            return None, {"used": False}
        active_topic = await self._active_topic(message.chat_id, memory_package, exclude_text=message.message_text)
        if not active_topic:
            return None, {"used": False, "reason": "no active topic"}
        expanded = self._expand_followup_text(message.message_text, active_topic)
        if not expanded or normalize_text(expanded) == normalize_text(message.message_text):
            return None, {"used": False, "active_topic": active_topic}
        return (
            replace(message, message_text=expanded, normalized_text=normalize_text(expanded)),
            {
                "used": True,
                "original_question": message.message_text,
                "expanded_question": expanded,
                "active_topic": active_topic,
                "entities": [active_topic],
            },
        )

    async def _active_topic(
        self,
        chat_id: str,
        memory_package: MemoryContextPackage,
        *,
        exclude_text: str,
    ) -> str | None:
        for entry in memory_package.timeline_entries:
            topic = str(entry.get("topic") or "").strip()
            if topic and normalize_text(topic) not in {"general conversation"}:
                return topic

        session_summary = await self._get_conversation_summary(chat_id)
        topic = self._topic_from_text(session_summary)
        if topic:
            return topic

        rows = (
            await self.session.execute(
                select(Message.message_text)
                .where(Message.chat_id == chat_id)
                .where(Message.message_text != exclude_text)
                .order_by(Message.created_at.desc())
                .limit(6)
            )
        ).scalars().all()
        for text_value in rows:
            topic = self._topic_from_text(text_value)
            if topic:
                return topic
        return None

    @staticmethod
    def _topic_from_text(text_value: str | None) -> str | None:
        if not text_value:
            return None
        normalized = normalize_text(text_value)
        for marker, topic in (
            ("datacube", "Datacube AU"),
            ("zinax", "ZinaX"),
            ("moxiz", "Moxiz Gateway"),
            ("zina", "Zina"),
            ("vps", "VPS deployment"),
            ("server", "VPS deployment"),
            ("internship", "cybersecurity internships"),
        ):
            if marker in normalized:
                return topic
        return None

    @staticmethod
    def _expand_followup_text(text_value: str, active_topic: str) -> str:
        stripped = text_value.strip()
        normalized = normalize_text(stripped)
        if normalized in {"ram", "storage", "cost", "price", "performance"}:
            return f"What about {normalized} for {active_topic}?"
        if normalized.startswith("what about "):
            return f"{stripped} for {active_topic}?"
        if normalized.startswith("how about "):
            return f"{stripped} for {active_topic}?"
        if normalized in {"which one", "compare them"}:
            return f"{stripped} for {active_topic}?"
        if normalized in {"who owns it", "who built it"}:
            return re.sub(r"\bit\b", active_topic, stripped, flags=re.IGNORECASE)
        if re.search(r"\b(it|that|this|they|them|those)\b", normalized):
            return re.sub(r"\b(it|that|this|they|them|those)\b", active_topic, stripped, flags=re.IGNORECASE)
        return f"{stripped} about {active_topic}"

    async def _identity_reply_if_known_project(self, message_text: str) -> str | None:
        normalized = normalize_text(message_text)
        if any(marker in normalized for marker in ("datacube", "zina", "zinax", "moxiz", "fabian")):
            return await self.bot_config.identity_reply(message_text)
        return None

    async def _try_ai(
        self,
        message: NormalizedMessage,
        search_result: SearchResult,
        contact_id: int | None,
        *,
        memory_package: MemoryContextPackage | None = None,
        global_chat: dict[str, object] | None = None,
        invocation_reason: str = "local knowledge insufficient",
        faq_score: float = 0.0,
        context_diagnostics: dict[str, object] | None = None,
    ) -> PlannedReply | None:
        client = OpenRouterClient()
        mode = AIMode.DEEP if looks_complex(message.message_text) else AIMode.LIGHT

        # Load dynamic config
        model_override_light = await self.bot_config.get("ai_model_light")
        model_override_deep = await self.bot_config.get("ai_model_deep")
        
        # Load AI behavior settings
        strictness = await self.bot_config.get("ai_strictness", "medium")
        hallucination_protection = await self.bot_config.get("ai_hallucination_protection", "high")
        
        # Load user memory context
        user_context = ""
        if contact_id and memory_package is None:
            memory_package = await self.memory_service.get_context_package(contact_id, query=message.message_text)
        if memory_package and memory_package.context_text:
            user_context = memory_package.context_text
        elif contact_id:
            memory = await self.memory_service.get_memory(contact_id)
            user_context = self.memory_service.get_memory_context(memory)

        dynamic_system_instructions = await self.bot_config.build_system_prompt()
        
        ai_decision = DecisionType.AI_REPLY_DEEP if mode == AIMode.DEEP else DecisionType.AI_REPLY_LIGHT
        try:
            result = await client.generate(
                user_message=message.message_text,
                knowledge_context=self.retrieval.prompt_context(search_result),
                conversation_summary=await self._get_conversation_summary(message.chat_id),
                mode=mode,
                system_instructions=dynamic_system_instructions,
                user_context=user_context,
                model_override=model_override_deep if mode == AIMode.DEEP else model_override_light,
            )
            ai_call = AICall(
                message_id=None,
                prompt_hash=result.prompt_hash,
                mode=mode.value,
                model=result.model,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                latency_ms=result.latency_ms,
                success=True,
                request_json=result.request_json,
                response_json=result.response_json,
            )
            return await self._apply_identity_guard(PlannedReply(
                decision_type=ai_decision,
                reason="ai fallback used",
                should_reply=True,
                reply_text=result.text,
                kb_confidence=search_result.confidence,
                matched_chunks=self.retrieval.prompt_context(search_result),
                source_diagnostics={
                    "faq": {"matched": False, "score": faq_score},
                    "cache": {"hit": False},
                    "kb": {
                        "matched": bool(search_result.chunks),
                        "confidence": search_result.confidence,
                        "chunks": self.retrieval.prompt_context(search_result),
                    },
                    "memory": {
                        **self.memory_service.diagnostics_for_package(memory_package),
                        "context_used": bool(user_context),
                    },
                    "context": context_diagnostics or {"used": False},
                    "ai": {
                        "used": True,
                        "invocation_reason": invocation_reason,
                        "mode": mode.value,
                        "model": result.model,
                        "prompt_hash": result.prompt_hash,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "latency_ms": result.latency_ms,
                    },
                    "global_chat": global_chat or {},
                    "hallucination_protection": hallucination_protection,
                },
                ai_used=True,
                ai_call=ai_call,
            ))
        except OpenRouterClientError:
            return None
        finally:
            await client.close()

    async def _get_conversation_summary(self, chat_id: str) -> str:
        stmt = select(ConversationSession.summary).where(ConversationSession.chat_id == chat_id).limit(1)
        summary = (await self.session.execute(stmt)).scalar_one_or_none()
        return summary or ""

    async def upsert_conversation_summary(self, *, chat_id: str, chat_type: str, user_text: str, bot_text: str, decision: str) -> None:
        topic = self.memory_service.infer_topic_label(user_text)
        compact = f"topic:{topic} | decision:{decision} | user:{user_text[:140]} | assistant:{bot_text[:220]}"
        stmt = select(ConversationSession).where(ConversationSession.chat_id == chat_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.chat_type = chat_type
            previous = model.summary or ""
            model.summary = self._merge_summary(previous, compact)
            model.last_intent = topic
            model.last_message_at = utcnow()
            model.updated_at = utcnow()
            return

        self.session.add(
            ConversationSession(
                chat_id=chat_id,
                chat_type=chat_type,
                summary=compact,
                last_intent=topic,
                last_message_at=utcnow(),
                updated_at=utcnow(),
            )
        )
        await self.session.flush()

    async def cache_answer_if_reusable(self, question: str, reply: PlannedReply) -> None:
        if reply.decision_type not in {DecisionType.FAQ_REPLY, DecisionType.KB_REPLY, DecisionType.AI_REPLY_LIGHT, DecisionType.AI_REPLY_DEEP}:
            return
        if not reply.reply_text:
            return
        memory_info = reply.source_diagnostics.get("memory")
        if isinstance(memory_info, dict) and memory_info.get("retrieved_items", 0):
            return
        answer_text = getattr(reply, "raw_reply_text", None) or reply.reply_text
        if not answer_text:
            return
        await self.retrieval.upsert_cache_answer(
            question=question,
            answer_text=answer_text,
            answer_mode=reply.decision_type.value,
            confidence=reply.kb_confidence or (0.6 if reply.ai_used else 0.5),
            source_json={
                "matched_chunks": reply.matched_chunks,
                "source_diagnostics": reply.source_diagnostics,
                "hash": sha256_text(question),
            },
        )

    async def _apply_identity_guard(self, reply: PlannedReply) -> PlannedReply:
        self._attach_router_analytics(reply)
        reply.source_diagnostics.setdefault("source", self._diagnostic_source(reply))
        if not reply.reply_text:
            return reply
        if not await self.bot_config.violates_identity_boundary(reply.reply_text):
            return await self._format_experience(reply)

        reply.decision_type = DecisionType.ESCALATED
        reply.reason = f"{reply.reason}; identity boundary guard"
        reply.reply_text = await self.bot_config.escalation_reply()
        reply.raw_reply_text = reply.reply_text
        reply.source_diagnostics["identity_guard"] = {"triggered": True}
        reply.ai_used = False
        reply.ai_call = None
        return await self._format_experience(reply)

    async def _format_experience(self, reply: PlannedReply) -> PlannedReply:
        experience_info = reply.source_diagnostics.setdefault("experience", {})
        if isinstance(experience_info, dict) and experience_info.get("formatted"):
            return reply
        if getattr(reply, "raw_reply_text", None) is None:
            setattr(reply, "raw_reply_text", reply.reply_text)
        source = str(reply.source_diagnostics.get("source") or self._diagnostic_source(reply))
        configured_show_source = await self.bot_config.get_bool("show_source_badges", settings.show_source_badges)
        show_source = configured_show_source and self._should_show_source(reply, source)
        configured_show_context = await self.bot_config.get_bool("show_context_badges", settings.show_context_badges)
        show_context = configured_show_context and self._context_was_used(reply)
        signature_style = await self.bot_config.get_bool("enable_signature_style", settings.enable_signature_style)
        memory_info = reply.source_diagnostics.get("memory")
        indicators = memory_context_indicators(memory_info if isinstance(memory_info, dict) else None)
        reply_mode = str(reply.source_diagnostics.get("reply_mode") or "normal")
        message_format = self._normalize_whatsapp_message_format(
            await self.bot_config.get("whatsapp_message_format", settings.whatsapp_message_format)
        )
        
        from app.core.whatsapp_formatter import get_applied_format_mode
        applied_mode = get_applied_format_mode(reply.raw_reply_text or "", message_format.value)
        
        reply.reply_text = self.formatter.format_reply(
            reply.raw_reply_text or "",
            source=source,
            context_indicators=indicators,
            show_source=show_source,
            show_context=show_context,
            enable_signature_style=signature_style,
            mode=reply_mode,
            whatsapp_format_mode=message_format.value,
        )
        if isinstance(experience_info, dict):
            experience_info["formatted"] = True
            experience_info["source_badge"] = self.formatter.source_badge(source)
            experience_info["context_indicators"] = indicators
            experience_info["signature_style"] = signature_style
            experience_info["reply_mode"] = reply_mode
            experience_info["whatsapp_message_format"] = message_format.value
            experience_info["applied_formatting_mode"] = applied_mode
            experience_info["formatter_version"] = "2.0"
            experience_info["raw_reply_text_stored"] = bool(reply.raw_reply_text)
        return reply

    def _attach_router_analytics(self, reply: PlannedReply) -> None:
        classifier = getattr(self, "intent_classifier", IntentClassifier())
        active_question = getattr(self, "_active_question", "") or ""
        intent = getattr(self, "_active_intent", None) or classifier.classify(active_question)
        reply.intent = intent.intent.value
        source = str(reply.source_diagnostics.get("source") or self._diagnostic_source(reply))
        memory_info = reply.source_diagnostics.get("memory")
        faq_info = reply.source_diagnostics.get("faq")
        kb_info = reply.source_diagnostics.get("kb")
        internet_info = reply.source_diagnostics.get("internet")
        ai_info = reply.source_diagnostics.get("ai")
        context_info = reply.source_diagnostics.get("context")

        memory_score = 0.0
        if isinstance(memory_info, dict):
            memory_score = min(1.0, float(memory_info.get("retrieved_items") or 0) / 4)
            if memory_info.get("context_used"):
                memory_score = max(memory_score, 0.85)
        reply_confidence = float(getattr(reply, "kb_confidence", 0.0) or 0.0)
        faq_score = float(faq_info.get("score") or 0.0) if isinstance(faq_info, dict) else 0.0
        knowledge_score = float(kb_info.get("confidence") or reply_confidence or 0.0) if isinstance(kb_info, dict) else reply_confidence
        internet_score = 1.0 if isinstance(internet_info, dict) and internet_info.get("success", True) and source in {"Internet", "Giphy", "Cache"} else 0.0
        ai_score = 1.0 if getattr(reply, "ai_used", False) or (isinstance(ai_info, dict) and ai_info.get("used")) else 0.0

        rejected: list[dict[str, object]] = []
        if isinstance(faq_info, dict) and not faq_info.get("matched", False):
            rejected.append({"source": "FAQ", "score": faq_score, "reason": "below confidence threshold"})
        if isinstance(kb_info, dict) and not kb_info.get("matched", False):
            rejected.append({"source": "Knowledge", "score": knowledge_score, "reason": "below confidence threshold"})
        if isinstance(internet_info, dict) and internet_info.get("success") is False:
            rejected.append({"source": "Internet", "score": internet_score, "reason": internet_info.get("error") or "provider unavailable"})
        if isinstance(ai_info, dict) and ai_info.get("used") is False:
            rejected.append({"source": "AI", "score": ai_score, "reason": "not needed or disabled"})

        reply.source_diagnostics["intent"] = {
            "name": intent.intent.value,
            "confidence": intent.confidence,
            "reason": intent.reason,
        }
        reply.source_diagnostics["router_analytics"] = {
            "question": active_question,
            "expanded_query": context_info.get("expanded_question") if isinstance(context_info, dict) else active_question,
            "topic": context_info.get("active_topic") if isinstance(context_info, dict) else None,
            "entities": self._analytics_entities(faq_info, kb_info, context_info),
            "intent": intent.intent.value,
            "intent_confidence": intent.confidence,
            "scores": {
                "memory": round(memory_score, 2),
                "timeline": round(memory_score if isinstance(memory_info, dict) and memory_info.get("timeline_entries") else 0.0, 2),
                "knowledge": round(knowledge_score, 2),
                "faq": round(faq_score, 2),
                "internet": round(internet_score, 2),
                "ai": round(ai_score, 2),
            },
            "hits": {
                "memory": int(memory_info.get("retrieved_items") or 0) if isinstance(memory_info, dict) else 0,
                "faq": 1 if isinstance(faq_info, dict) and faq_info.get("matched") else 0,
                "knowledge": len(kb_info.get("chunks") or []) if isinstance(kb_info, dict) else len(getattr(reply, "matched_chunks", []) or []),
                "internet": 1 if isinstance(internet_info, dict) and internet_info.get("success") else 0,
                "ai": 1 if ai_score else 0,
            },
            "selected_source": source,
            "selected_route": source,
            "rejected_sources": rejected,
            "rejected_routes": rejected,
            "reason": getattr(reply, "reason", ""),
            "decision_reason": getattr(reply, "reason", ""),
        }

    @staticmethod
    def _analytics_entities(*items: object) -> list[str]:
        values: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("entities", "active_topic", "topic"):
                raw = item.get(key)
                if isinstance(raw, list):
                    for value in raw:
                        text = str(value).strip()
                        if text and text not in values:
                            values.append(text)
                elif raw:
                    text = str(raw).strip()
                    if text and text not in values:
                        values.append(text)
        return values

    @staticmethod
    def _should_show_source(reply: PlannedReply, source: str) -> bool:
        if source in {"Internet", "Giphy", "AI", "Global Chat"}:
            return True
        memory_info = reply.source_diagnostics.get("memory")
        if source in {"Memory", "Memory + Timeline", "Timeline"} and isinstance(memory_info, dict):
            return bool(memory_info.get("context_used"))
        return False

    @staticmethod
    def _context_was_used(reply: PlannedReply) -> bool:
        context_info = reply.source_diagnostics.get("context")
        if isinstance(context_info, dict) and context_info.get("used"):
            return True
        memory_info = reply.source_diagnostics.get("memory")
        return isinstance(memory_info, dict) and bool(memory_info.get("context_used"))

    @staticmethod
    def _normalize_whatsapp_message_format(value: str | None) -> WhatsAppMessageFormat:
        try:
            return WhatsAppMessageFormat(str(value or "").strip().lower())
        except ValueError:
            return WhatsAppMessageFormat.AUTOMATIC

    async def _handle_global_chat_command(
        self,
        message: NormalizedMessage,
        contact_id: int | None,
    ) -> PlannedReply | None:
        normalized = normalize_text(message.message_text).strip()
        if normalized not in {"global on", "global off"}:
            return None
        if not contact_id:
            return PlannedReply(
                decision_type=DecisionType.STATIC_REPLY,
                reason="global chat command missing contact",
                should_reply=True,
                reply_text="Global Chat needs a contact profile first.",
                source_diagnostics={"source": "Command"},
            )
        enabled = normalized == "global on"
        await self.memory_service.set_global_chat(contact_id, enabled)
        await self._record_command_usage("/global")
        if enabled:
            text = "Global Chat is on. Use `!ask` for one-off AI questions, or send a normal message while Global Chat is on."
        else:
            text = "Global Chat is off. I’ll use rules, FAQ, cache, knowledge, and memory before stopping."
        return PlannedReply(
            decision_type=DecisionType.STATIC_REPLY,
            reason=f"global chat {'enabled' if enabled else 'disabled'}",
            should_reply=True,
            reply_text=text,
            source_diagnostics={"source": "Command", "global_chat": {"active": enabled, "command": normalized}},
        )

    async def _record_command_usage(self, command: str) -> None:
        try:
            await self.command_catalog.record_usage(command)
        except Exception:
            return None

    async def _handle_internet_command(
        self,
        message: NormalizedMessage,
        contact_id: int | None,
    ) -> PlannedReply | None:
        service, command, query = self.internet_service.parse_user_command(message.message_text)
        if not service:
            return None
        if not query:
            return PlannedReply(
                decision_type=DecisionType.STATIC_REPLY,
                reason="internet command missing query",
                should_reply=True,
                reply_text=self.internet_service.usage_for_command(command),
                source_diagnostics={"source": "Internet", "internet": {"command": command, "valid": False}},
            )
        return await self._run_internet_request(
            service=service,
            command=command,
            query=query,
            contact_id=contact_id,
            reason=f"internet command: {command}",
        )

    async def _run_internet_request(
        self,
        *,
        service: str,
        command: str,
        query: str,
        contact_id: int | None,
        reason: str,
    ) -> PlannedReply:
        result = await self.internet_service.run(service, query, contact_id=contact_id, explicit_command=command)
        return PlannedReply(
            decision_type=DecisionType.STATIC_REPLY,
            reason=reason,
            should_reply=True,
            reply_text=result.reply_text,
            media_url=result.media_url,
            media_type=result.media_type,
            media_caption=result.media_caption,
            source_diagnostics={
                "source": self._source_for_internet_result(result),
                **(result.diagnostics or {}),
                "internet": {
                    **((result.diagnostics or {}).get("internet", {}) if isinstance((result.diagnostics or {}).get("internet"), dict) else {}),
                    "service": result.service,
                    "provider": result.provider,
                    "cache_hit": result.cache_hit,
                    "success": result.success,
                    "command": command,
                },
            },
        )

    async def _maybe_live_internet_reply(
        self,
        message: NormalizedMessage,
        contact_id: int | None,
    ) -> PlannedReply | None:
        result = await self.internet_service.maybe_live_lookup(message.message_text, contact_id)
        if not result:
            return None
        return PlannedReply(
            decision_type=DecisionType.STATIC_REPLY,
            reason="smart internet detection",
            should_reply=True,
            reply_text=result.reply_text,
            media_url=result.media_url,
            media_type=result.media_type,
            media_caption=result.media_caption,
            source_diagnostics={
                "source": self._source_for_internet_result(result),
                **(result.diagnostics or {}),
                "internet": {
                    **((result.diagnostics or {}).get("internet", {}) if isinstance((result.diagnostics or {}).get("internet"), dict) else {}),
                    "service": result.service,
                    "provider": result.provider,
                    "cache_hit": result.cache_hit,
                    "success": result.success,
                    "smart_detected": True,
                },
            },
        )

    @staticmethod
    def _extract_ask_text(message_text: str) -> str | None:
        stripped = message_text.strip()
        if not stripped.lower().startswith("!ask"):
            return None
        if len(stripped) == 4:
            return ""
        if stripped[4].isspace():
            return stripped[5:]
        return None

    @staticmethod
    def _source_for_internet_result(result) -> str:
        if getattr(result, "cache_hit", False):
            return "Cache"
        if getattr(result, "provider", "") == "giphy":
            return "Giphy"
        return "Internet"

    @staticmethod
    def _requires_openrouter(text_value: str) -> bool:
        normalized = normalize_text(text_value)
        if looks_complex(text_value):
            return True
        markers = (
            "analyze",
            "analysis",
            "compare",
            "comparison",
            "design",
            "strategy",
            "strategic",
            "summarize",
            "summary",
            "synthesize",
            "recommend",
            "recommendation",
            "reason",
            "tradeoff",
            "plan",
            "roadmap",
            "debug",
            "architecture",
        )
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _ai_invocation_reason(text_value: str, intent_result: IntentResult, kb_confidence: float) -> str:
        if intent_result.intent == MessageIntent.GENERAL_KNOWLEDGE:
            return f"general knowledge requires synthesis after local confidence {kb_confidence:.2f}"
        if intent_result.intent == MessageIntent.OPINION_REQUEST:
            return f"opinion or recommendation requires reasoning after local confidence {kb_confidence:.2f}"
        if looks_complex(text_value):
            return f"complex question requires reasoning after local confidence {kb_confidence:.2f}"
        return f"local knowledge insufficient at confidence {kb_confidence:.2f}"

    @staticmethod
    def _memory_global_chat_enabled(memory_package: MemoryContextPackage | None) -> bool:
        if not memory_package or not memory_package.profile:
            return False
        return bool(memory_package.profile.get("global_chat_enabled"))

    @staticmethod
    def _diagnostic_source(reply: PlannedReply) -> str:
        if reply.decision_type in {
            DecisionType.REPLY_RULE,
            DecisionType.STATIC_REPLY,
            DecisionType.IGNORE,
            DecisionType.COOLDOWN_BLOCK,
            DecisionType.RATE_LIMITED,
        }:
            return "Rule"
        if reply.decision_type == DecisionType.FAQ_REPLY:
            return "FAQ"
        if reply.decision_type == DecisionType.KB_REPLY:
            cache_info = reply.source_diagnostics.get("cache")
            if isinstance(cache_info, dict) and cache_info.get("hit"):
                return "Cache"
            return "KB"
        if reply.decision_type == DecisionType.MEMORY_ONBOARD:
            return "Memory"
        if reply.decision_type == DecisionType.MEMORY_REPLY:
            return "Memory"
        if reply.decision_type in {DecisionType.AI_REPLY_LIGHT, DecisionType.AI_REPLY_DEEP, DecisionType.ESCALATED}:
            return "AI"
        return "Fallback"

    async def _no_match_reply(self, chat_type: ChatType, message_text: str) -> str | None:
        if self._requires_human_escalation(message_text):
            return await self.bot_config.escalation_reply()
        if chat_type == ChatType.DM:
            return (
                "I do not have enough approved information to answer that reliably yet.\n\n"
                "I checked identity, memory, FAQ, knowledge, internet availability, and AI reasoning before stopping."
            )
        return None

    @staticmethod
    def _requires_human_escalation(message_text: str) -> bool:
        normalized = normalize_text(message_text)
        private_markers = {
            "should fabian",
            "will fabian",
            "can fabian approve",
            "can fabian decide",
            "does fabian want",
            "fabian opinion",
            "fabian private",
            "personal decision",
            "private decision",
            "approve this",
            "hire me",
            "give me permission",
        }
        return any(marker in normalized for marker in private_markers)

    @staticmethod
    def _merge_summary(previous: str, latest: str) -> str:
        if not previous:
            return latest
        merged = f"{previous}\n{latest}"
        if len(merged) <= 2200:
            return merged
        return merged[-2200:].lstrip()
