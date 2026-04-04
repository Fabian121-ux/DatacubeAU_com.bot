from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.core.rules_engine import RulesEngine
from app.models.enums import AIMode, ChatType, DecisionType
from app.models.schema import AICall, ConversationSession
from app.services.openrouter_client import OpenRouterClient, OpenRouterClientError
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

    async def plan(self, message: NormalizedMessage, contact_id: int | None) -> PlannedReply:
        rules_result = await self.rules.evaluate(message, contact_id)
        if not rules_result.should_continue:
            return PlannedReply(
                decision_type=rules_result.decision_type or DecisionType.IGNORE,
                reason=rules_result.reason,
                should_reply=rules_result.reply_text is not None,
                reply_text=rules_result.reply_text,
            )

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

        if settings.ai_enabled:
            ai_plan = await self._try_ai(message, search_result)
            if ai_plan:
                return ai_plan

        no_match_text = self._no_match_reply(message.chat_type)
        return PlannedReply(
            decision_type=DecisionType.NO_MATCH,
            reason="no static, cache, knowledge, or ai match",
            should_reply=no_match_text is not None,
            reply_text=no_match_text,
            kb_confidence=search_result.confidence,
            matched_chunks=self.retrieval.prompt_context(search_result),
        )

    async def _try_ai(self, message: NormalizedMessage, search_result: SearchResult) -> PlannedReply | None:
        client = OpenRouterClient()
        mode = AIMode.DEEP if looks_complex(message.message_text) else AIMode.LIGHT
        ai_decision = DecisionType.AI_REPLY_DEEP if mode == AIMode.DEEP else DecisionType.AI_REPLY_LIGHT
        try:
            result = await client.generate(
                user_message=message.message_text,
                knowledge_context=self.retrieval.prompt_context(search_result),
                conversation_summary=await self._get_conversation_summary(message.chat_id),
                mode=mode,
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
            return "I do not have a documented answer for that yet. Add knowledge or enable AI fallback later."
        return "I do not have a documented answer for that yet."
