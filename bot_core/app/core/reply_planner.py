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
    ai_used: bool = False
    ai_call: AICall | None = None


class ReplyPlanner:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.rules = RulesEngine(session)
        self.retrieval = RetrievalService(session)
        self.memory_service = MemoryService(session)
        self.rate_limiter = RateLimiter(session)
        self.bot_config = BotConfigService(session)

    async def plan(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
        # 1. Rules check (includes DB-driven reply rules)
        rules_result = await self.rules.evaluate(message, contact_id)
        if not rules_result.should_continue:
            return PlannedReply(
                decision_type=rules_result.decision_type or DecisionType.IGNORE,
                reason=rules_result.reason,
                should_reply=rules_result.reply_text is not None,
                reply_text=rules_result.reply_text,
            )

        # 2. Rate limit check (per-user daily)
        if contact_id:
            rate_check = await self.rate_limiter.check_user_daily_limit(contact_id)
            if not rate_check.allowed:
                return PlannedReply(
                    decision_type=DecisionType.RATE_LIMITED,
                    reason=rate_check.reason,
                    should_reply=True,
                    reply_text="You've reached the daily message limit. Please try again tomorrow. 🕐",
                )

        # 3. Memory onboarding check (DM only)
        if contact_id and message.chat_type == ChatType.DM:
            onboard_reply, stage = await self.memory_service.check_onboarding(
                contact_id, message.message_text
            )
            if onboard_reply:
                return PlannedReply(
                    decision_type=DecisionType.MEMORY_ONBOARD,
                    reason=f"onboarding: {stage}" if stage else "onboarding complete",
                    should_reply=True,
                    reply_text=onboard_reply,
                )

        # 4. Cached answer lookup
        cache_hit = await self.retrieval.lookup_cache(message.message_text)
        if cache_hit:
            return PlannedReply(
                decision_type=DecisionType.KB_REPLY,
                reason="cached faq/knowledge match",
                should_reply=True,
                reply_text=cache_hit.answer_text,
                kb_confidence=float(cache_hit.confidence),
                matched_chunks=[],
            )

        # 5. Knowledge search
        search_result = await self.retrieval.search(message.message_text)
        if search_result.chunks and search_result.confidence >= settings.kb_min_score:
            return PlannedReply(
                decision_type=DecisionType.KB_REPLY,
                reason="knowledge match above threshold",
                should_reply=True,
                reply_text=self.retrieval.build_kb_reply(search_result),
                kb_confidence=search_result.confidence,
                matched_chunks=self.retrieval.prompt_context(search_result),
            )

        # 6. AI fallback (if enabled)
        ai_enabled_config = await self.bot_config.get_bool("ai_enabled", False)
        ai_enabled = settings.ai_enabled or ai_enabled_config
        if ai_enabled:
            # Check global AI rate limit first
            global_check = await self.rate_limiter.check_global_ai_limit()
            if global_check.allowed:
                ai_plan = await self._try_ai(message, search_result, contact_id)
                if ai_plan:
                    return ai_plan

        # 7. Fallback
        no_match_text = self._no_match_reply(message.chat_type)
        return PlannedReply(
            decision_type=DecisionType.NO_MATCH,
            reason="no rule, cache, knowledge, or ai match",
            should_reply=no_match_text is not None,
            reply_text=no_match_text,
            kb_confidence=search_result.confidence,
            matched_chunks=self.retrieval.prompt_context(search_result),
        )

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
        
        # Load identity settings
        identity_bio = await self.bot_config.get("identity_bio")
        identity_projects = await self.bot_config.get("identity_projects")
        identity_services = await self.bot_config.get("identity_services")
        identity_skills = await self.bot_config.get("identity_skills")
        identity_interests = await self.bot_config.get("identity_interests")
        identity_focus = await self.bot_config.get("identity_focus")
        identity_style = await self.bot_config.get("identity_style")
        identity_faq = await self.bot_config.get("identity_faq")

        # Load personality settings
        tone = await self.bot_config.get("personality_tone", "professional")
        humor = await self.bot_config.get("personality_humor", "low")
        reply_length = await self.bot_config.get("personality_reply_length", "short")
        tech_depth = await self.bot_config.get("personality_tech_depth", "medium")
        emoji = await self.bot_config.get("personality_emoji", "light")
        
        # Load AI behavior settings
        strictness = await self.bot_config.get("ai_strictness", "medium")
        escalation_threshold = float(await self.bot_config.get("ai_escalation_threshold", "0.3"))
        hallucination_protection = await self.bot_config.get("ai_hallucination_protection", "high")
        
        # Check escalation based on KB confidence vs threshold
        force_escalation = False
        if search_result.confidence < escalation_threshold and strictness == "high":
             force_escalation = True
        
        # Inject personality dynamically into the instructions
        dynamic_system_instructions = (
            f"You are the personal WhatsApp assistant for Fabian and his projects.\n"
            f"Your role is to answer questions about Fabian, explain his projects clearly, guide users, and keep responses {identity_style}.\n"
            f"You are NOT a generic AI chatbot. Present yourself as Fabian's assistant.\n\n"
            f"--- IDENTITY LAYER ---\n"
            f"Bio: {identity_bio}\n"
            f"Projects: {identity_projects}\n"
            f"Services: {identity_services}\n"
            f"Skills: {identity_skills}\n"
            f"Interests: {identity_interests}\n"
            f"Focus: {identity_focus}\n\n"
            f"--- FAQS ---\n{identity_faq}\n\n"
            f"--- PERSONALITY SETTINGS ---\n"
            f"Tone: {tone}\n"
            f"Humor level: {humor}\n"
            f"Reply length: {reply_length}\n"
            f"Technical depth: {tech_depth}\n"
            f"Emoji usage: {emoji}\n\n"
            f"--- BEHAVIOR RULES ---\n"
            f"Strictness: {strictness}\n"
            f"Hallucination Protection: {hallucination_protection}\n"
            f"If asked about something not in your knowledge base or identity layer, do NOT guess. "
            f"If hallucination protection is 'high' or you are unsure, you MUST reply exactly with: 'Fabian may need to answer this personally.'\n"
        )
        
        if force_escalation:
             return PlannedReply(
                decision_type=DecisionType.ESCALATED,
                reason="kb confidence below escalation threshold",
                should_reply=True,
                reply_text="Fabian may need to answer this personally.",
                kb_confidence=search_result.confidence,
                matched_chunks=self.retrieval.prompt_context(search_result),
                ai_used=False,
            )

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
            return PlannedReply(
                decision_type=ai_decision,
                reason="ai fallback used",
                should_reply=True,
                reply_text=result.text,
                kb_confidence=search_result.confidence,
                matched_chunks=self.retrieval.prompt_context(search_result),
                ai_used=True,
                ai_call=ai_call,
            )
        except OpenRouterClientError:
            return None
        finally:
            await client.close()

    async def _get_conversation_summary(self, chat_id: str) -> str:
        stmt = select(ConversationSession.summary).where(ConversationSession.chat_id == chat_id).limit(1)
        summary = (await self.session.execute(stmt)).scalar_one_or_none()
        return summary or ""

    async def upsert_conversation_summary(self, *, chat_id: str, chat_type: str, user_text: str, bot_text: str, decision: str) -> None:
        compact = f"user:{user_text[:100]} | bot:{bot_text[:180]}"
        stmt = select(ConversationSession).where(ConversationSession.chat_id == chat_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.chat_type = chat_type
            model.summary = compact
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
        if reply.decision_type not in {DecisionType.KB_REPLY, DecisionType.AI_REPLY_LIGHT, DecisionType.AI_REPLY_DEEP}:
            return
        if not reply.reply_text:
            return
        await self.retrieval.upsert_cache_answer(
            question=question,
            answer_text=reply.reply_text,
            answer_mode=reply.decision_type.value,
            confidence=reply.kb_confidence or (0.6 if reply.ai_used else 0.5),
            source_json={"matched_chunks": reply.matched_chunks, "hash": sha256_text(question)},
        )

    @staticmethod
    def _no_match_reply(chat_type: ChatType) -> str | None:
        if chat_type == ChatType.DM:
            return "I don't have an answer for that yet. Try rephrasing or type /help. 💡"
        return "I don't have an answer for that yet."
