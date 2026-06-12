from __future__ import annotations

from dataclasses import dataclass, field
from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.experience_formatter import WhatsAppExperienceFormatter, memory_context_indicators
from app.core.message_normalizer import NormalizedMessage
from app.core.rules_engine import RulesEngine
from app.models.enums import AIMode, ChatType, DecisionType
from app.models.schema import AICall, ConversationSession
from app.services.bot_config_service import BotConfigService
from app.services.faq_service import FAQService
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


class ReplyPlanner:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules = RulesEngine(session)
        self.faq = FAQService(session)
        self.retrieval = RetrievalService(session)
        self.memory_service = MemoryService(session)
        self.internet_service = InternetService(session)
        self.rate_limiter = RateLimiter(session)
        self.bot_config = BotConfigService(session)
        self.formatter = WhatsAppExperienceFormatter()

    async def plan(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
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
                    source_diagnostics={"source": "Rule", "global_chat": {"one_shot": True, "valid": False}},
                ))
            global_chat_one_shot = True
            message = replace(
                message,
                message_text=ask_text.strip(),
                normalized_text=normalize_text(ask_text),
            )

        internet_request: tuple[str, str, str] | None = None
        service, command, query = self.internet_service.parse_user_command(message.message_text)
        if service:
            if not query:
                return await self._apply_identity_guard(PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason="internet command missing query",
                    should_reply=True,
                    reply_text=self.internet_service.usage_for_command(command),
                    source_diagnostics={"source": "Internet", "internet": {"command": command, "valid": False}},
                ))
            internet_request = (service, command, query)
            message = replace(
                message,
                message_text=query,
                normalized_text=normalize_text(query),
            )

        # Operational and custom rules stay ahead of knowledge routing.
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
                    reply_text="You've reached the daily message limit. Please try again tomorrow. 🕐",
                    source_diagnostics={"rate_limit": {"allowed": False, "reason": rate_check.reason}},
                ))

        # 1-3. Contact-scoped relationship memory, timeline, and summaries.
        memory_package: MemoryContextPackage | None = None
        if contact_id:
            memory_package = await self.memory_service.get_context_package(
                contact_id,
                query=message.message_text,
            )
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
                        "memory": self.memory_service.diagnostics_for_package(memory_package),
                        "global_chat": {"one_shot": global_chat_one_shot, "active": False},
                    },
                ))

        # 4. Core FAQ layer.
        faq_entry, faq_score = await self.faq.search_faq(message.message_text)
        if faq_entry:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.FAQ_REPLY,
                reason="core FAQ match above threshold",
                should_reply=True,
                reply_text=faq_entry.answer,
                kb_confidence=faq_score,
                source_diagnostics={
                    "faq": {
                        "matched": True,
                        "score": faq_score,
                        "entry_id": faq_entry.id,
                        "question": faq_entry.question,
                    }
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
                    "memory": self.memory_service.diagnostics_for_package(memory_package),
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
        ai_needed = self._requires_openrouter(message.message_text) or global_chat_one_shot
        ai_enabled = (
            global_chat_active
            and global_chat_system_enabled
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
                            "🤖 Global Chat limit reached.\n\n"
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
                )
                if ai_plan:
                    return ai_plan

        # 8. Escalating fallback.
        no_match_text = await self._no_match_reply(message.chat_type)
        return await self._apply_identity_guard(PlannedReply(
            decision_type=DecisionType.NO_MATCH,
            reason="no rule, faq, cache, knowledge, memory, or ai match",
            should_reply=no_match_text is not None,
            reply_text=no_match_text,
            kb_confidence=search_result.confidence,
            matched_chunks=retrieval_context,
            source_diagnostics={
                "faq": {"matched": False, "score": faq_score},
                "cache": {"hit": False},
                "kb": {"matched": False, "confidence": search_result.confidence, "chunks": retrieval_context},
                "memory": self.memory_service.diagnostics_for_package(memory_package),
                "ai": {"used": False, "enabled": ai_enabled},
                "global_chat": {
                    "one_shot": global_chat_one_shot,
                    "active": global_chat_active,
                    "system_enabled": global_chat_system_enabled,
                },
            },
        ))

    async def _try_ai(
        self,
        message: NormalizedMessage,
        search_result: SearchResult,
        contact_id: int | None,
        *,
        memory_package: MemoryContextPackage | None = None,
        global_chat: dict[str, object] | None = None,
    ) -> PlannedReply | None:
        client = OpenRouterClient()
        mode = AIMode.DEEP if looks_complex(message.message_text) else AIMode.LIGHT

        # Load dynamic config
        model_override_light = await self.bot_config.get("ai_model_light")
        model_override_deep = await self.bot_config.get("ai_model_deep")
        
        # Load AI behavior settings
        strictness = await self.bot_config.get("ai_strictness", "medium")
        try:
            escalation_threshold = float(await self.bot_config.get("ai_escalation_threshold", "0.3"))
        except ValueError:
            escalation_threshold = 0.3
        hallucination_protection = await self.bot_config.get("ai_hallucination_protection", "high")
        
        # Check escalation based on KB confidence vs threshold
        force_escalation = False
        if search_result.confidence < escalation_threshold and strictness == "high":
            force_escalation = True
        
        dynamic_system_instructions = await self.bot_config.build_system_prompt()
        
        if force_escalation:
            return await self._apply_identity_guard(PlannedReply(
                decision_type=DecisionType.ESCALATED,
                reason="kb confidence below escalation threshold",
                should_reply=True,
                reply_text=await self.bot_config.escalation_reply(),
                kb_confidence=search_result.confidence,
                matched_chunks=self.retrieval.prompt_context(search_result),
                ai_used=False,
                source_diagnostics={
                    "kb": {"matched": False, "confidence": search_result.confidence},
                    "memory": self.memory_service.diagnostics_for_package(memory_package),
                    "ai": {"used": False, "escalated": True, "strictness": strictness},
                    "global_chat": global_chat or {},
                },
            ))

        # Load user memory context
        user_context = ""
        if contact_id and memory_package is None:
            memory_package = await self.memory_service.get_context_package(contact_id, query=message.message_text)
        if memory_package and memory_package.context_text:
            user_context = memory_package.context_text
        elif contact_id:
            memory = await self.memory_service.get_memory(contact_id)
            user_context = self.memory_service.get_memory_context(memory)

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
                    "kb": {
                        "matched": bool(search_result.chunks),
                        "confidence": search_result.confidence,
                        "chunks": self.retrieval.prompt_context(search_result),
                    },
                    "memory": self.memory_service.diagnostics_for_package(memory_package),
                    "ai": {
                        "used": True,
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
        compact = f"decision:{decision} | user:{user_text[:140]} | assistant:{bot_text[:220]}"
        stmt = select(ConversationSession).where(ConversationSession.chat_id == chat_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.chat_type = chat_type
            previous = model.summary or ""
            model.summary = self._merge_summary(previous, compact)
            model.last_intent = decision
            model.last_message_at = utcnow()
            model.updated_at = utcnow()
            return

        self.session.add(
            ConversationSession(
                chat_id=chat_id,
                chat_type=chat_type,
                summary=compact,
                last_intent=decision,
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
        show_source = await self.bot_config.get_bool("show_source_badges", settings.show_source_badges)
        show_context = await self.bot_config.get_bool("show_context_badges", settings.show_context_badges)
        signature_style = await self.bot_config.get_bool("enable_signature_style", settings.enable_signature_style)
        memory_info = reply.source_diagnostics.get("memory")
        indicators = memory_context_indicators(memory_info if isinstance(memory_info, dict) else None)
        reply_mode = str(reply.source_diagnostics.get("reply_mode") or "normal")
        reply.reply_text = self.formatter.format_reply(
            reply.raw_reply_text or "",
            source=source,
            context_indicators=indicators,
            show_source=show_source,
            show_context=show_context,
            enable_signature_style=signature_style,
            mode=reply_mode,
        )
        if isinstance(experience_info, dict):
            experience_info["formatted"] = True
            experience_info["source_badge"] = self.formatter.source_badge(source)
            experience_info["context_indicators"] = indicators
            experience_info["signature_style"] = signature_style
            experience_info["reply_mode"] = reply_mode
        return reply

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
                source_diagnostics={"source": "Rule"},
            )
        enabled = normalized == "global on"
        await self.memory_service.set_global_chat(contact_id, enabled)
        if enabled:
            text = "Global Chat is on. Use `!ask` for one-off AI questions, or send a normal message while Global Chat is on."
        else:
            text = "Global Chat is off. I’ll use rules, FAQ, cache, knowledge, and memory before stopping."
        return PlannedReply(
            decision_type=DecisionType.STATIC_REPLY,
            reason=f"global chat {'enabled' if enabled else 'disabled'}",
            should_reply=True,
            reply_text=text,
            source_diagnostics={"source": "Rule", "global_chat": {"active": enabled, "command": normalized}},
        )

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

    async def _no_match_reply(self, chat_type: ChatType) -> str | None:
        if chat_type == ChatType.DM:
            return await self.bot_config.escalation_reply()
        return await self.bot_config.escalation_reply()

    @staticmethod
    def _merge_summary(previous: str, latest: str) -> str:
        if not previous:
            return latest
        merged = f"{previous}\n{latest}"
        if len(merged) <= 2200:
            return merged
        return merged[-2200:].lstrip()
