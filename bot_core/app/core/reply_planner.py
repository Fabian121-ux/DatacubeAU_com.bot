from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.core.rules_engine import RulesEngine
from app.models.enums import AIMode, ChatType, DecisionType
from app.models.schema import AICall, ConversationSession
from app.services.bot_config_service import BotConfigService
from app.services.faq_service import FAQService
from app.services.memory_service import MemoryService
from app.services.openrouter_client import OpenRouterClient, OpenRouterClientError
from app.services.rate_limiter import RateLimiter
from app.services.retrieval_service import RetrievalService, SearchResult
from app.utils.hashing import sha256_text
from app.utils.text import looks_complex
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


class ReplyPlanner:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules = RulesEngine(session)
        self.faq = FAQService(session)
        self.retrieval = RetrievalService(session)
        self.memory_service = MemoryService(session)
        self.rate_limiter = RateLimiter(session)
        self.bot_config = BotConfigService(session)

    async def plan(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
        # 1. Rules check (includes DB-driven reply rules)
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

        # 2. Core FAQ layer.
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

        # Cached answer lookup sits below FAQ so edited core FAQ answers win immediately.
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
                    "cache": {"hit": True, "cache_id": cache_hit.id, "answer_mode": cache_hit.answer_mode},
                },
            ))

        # 3. Knowledge search.
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

        # 4. Memory onboarding check (DM only), after FAQ/KB so useful answers are not blocked.
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
                        "memory": {"onboarding_stage": stage},
                    },
                ))

        # 5. AI fallback (if enabled).
        ai_enabled_config = await self.bot_config.get_bool("ai_enabled", False)
        ai_enabled = settings.ai_enabled or ai_enabled_config
        if ai_enabled:
            # Check global AI rate limit first
            global_check = await self.rate_limiter.check_global_ai_limit()
            if global_check.allowed:
                ai_plan = await self._try_ai(message, search_result, contact_id)
                if ai_plan:
                    return ai_plan

        # 6. Escalating fallback.
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
                "ai": {"used": False, "enabled": ai_enabled},
            },
        ))

    async def _try_ai(
        self,
        message: NormalizedMessage,
        search_result: SearchResult,
        contact_id: int | None,
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
                    "ai": {"used": False, "escalated": True, "strictness": strictness},
                },
            ))

        # Load user memory context
        user_context = ""
        if contact_id:
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
                    "ai": {
                        "used": True,
                        "mode": mode.value,
                        "model": result.model,
                        "prompt_hash": result.prompt_hash,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "latency_ms": result.latency_ms,
                    },
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
        await self.retrieval.upsert_cache_answer(
            question=question,
            answer_text=reply.reply_text,
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
            return reply

        reply.decision_type = DecisionType.ESCALATED
        reply.reason = f"{reply.reason}; identity boundary guard"
        reply.reply_text = await self.bot_config.escalation_reply()
        reply.source_diagnostics["identity_guard"] = {"triggered": True}
        reply.ai_used = False
        reply.ai_call = None
        return reply

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
