from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.core.reply_planner import ReplyPlanner
from app.core.rules_engine import RulesResult
from app.models.enums import ChatType, DecisionType
from app.services.retrieval_service import RetrievedChunk, SearchResult
from app.utils.text import normalize_text


@dataclass
class RateResult:
    allowed: bool = True
    reason: str = "allowed"


@dataclass
class FakeFAQEntry:
    id: int = 1
    question: str = "Who are you?"
    answer: str = "I'm Zina, Fabian's AI assistant."


@dataclass
class FakeCacheHit:
    id: int = 1
    answer_text: str = "Cached answer."
    confidence: float = 0.82
    answer_mode: str = "kb_reply"


class FakeRules:
    def __init__(self, reply_text: str | None = None):
        self.reply_text = reply_text
        self.calls = 0

    async def evaluate(self, *_: Any) -> RulesResult:
        self.calls += 1
        if self.reply_text:
            return RulesResult(False, DecisionType.REPLY_RULE, "matched reply rule", self.reply_text)
        return RulesResult(True, None, "rules passed", None)


class FakeRateLimiter:
    def __init__(self, user_allowed: bool = True, global_allowed: bool = True):
        self.user_allowed = user_allowed
        self.global_allowed = global_allowed

    async def check_user_daily_limit(self, *_: Any) -> RateResult:
        return RateResult(allowed=self.user_allowed, reason="user limit")

    async def check_global_ai_limit(self) -> RateResult:
        return RateResult(allowed=self.global_allowed, reason="global limit")


class FakeFAQ:
    def __init__(self, entry: FakeFAQEntry | None = None, score: float = 0.92):
        self.entry = entry
        self.score = score
        self.calls = 0

    async def search_faq(self, *_: Any) -> tuple[FakeFAQEntry | None, float]:
        self.calls += 1
        return self.entry, self.score


class FakeRetrieval:
    def __init__(self, cache_hit: FakeCacheHit | None = None, search_result: SearchResult | None = None):
        self.cache_hit = cache_hit
        self.search_result = search_result or SearchResult(chunks=[], confidence=0.0)
        self.cache_calls = 0
        self.search_calls = 0
        self.cached_answers = []

    async def lookup_cache(self, *_: Any) -> FakeCacheHit | None:
        self.cache_calls += 1
        return self.cache_hit

    async def search(self, *_: Any) -> SearchResult:
        self.search_calls += 1
        return self.search_result

    def prompt_context(self, result: SearchResult) -> list[dict[str, object]]:
        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "content": chunk.content,
                "score": chunk.score,
            }
            for chunk in result.chunks
        ]

    def build_kb_reply(self, result: SearchResult) -> str:
        return f"{result.chunks[0].heading}: {result.chunks[0].content}"

    async def upsert_cache_answer(self, **kwargs: Any) -> None:
        self.cached_answers.append(kwargs)


class FakeMemory:
    def __init__(self, reply_text: str | None = None):
        self.reply_text = reply_text
        self.calls = 0

    async def check_onboarding(self, *_: Any) -> tuple[str | None, str | None]:
        self.calls += 1
        if self.reply_text:
            return self.reply_text, "ask_name"
        return None, None

    async def get_memory(self, *_: Any) -> None:
        return None

    def get_memory_context(self, *_: Any) -> str:
        return ""


class FakeBotConfig:
    def __init__(self, ai_enabled: bool = False, strictness: str = "medium", threshold: str = "0.0"):
        self.ai_enabled = ai_enabled
        self.strictness = strictness
        self.threshold = threshold

    async def get_bool(self, key: str, default: bool = False) -> bool:
        if key == "ai_enabled":
            return self.ai_enabled
        return default

    async def get(self, key: str, default: str = "") -> str:
        defaults = {
            "ai_strictness": self.strictness,
            "ai_escalation_threshold": self.threshold,
            "ai_hallucination_protection": "high",
        }
        return defaults.get(key, default)

    async def build_system_prompt(self) -> str:
        return "You are Zina, Fabian's AI assistant."

    async def escalation_reply(self) -> str:
        return "Fabian may need to answer this personally."

    async def violates_identity_boundary(self, _: str) -> bool:
        return False


def make_message(text: str = "test message") -> NormalizedMessage:
    return NormalizedMessage(
        chat_id="15550000001@c.us",
        sender_id="15550000001@c.us",
        sender_name="Test User",
        chat_type=ChatType.DM,
        message_text=text,
        normalized_text=normalize_text(text),
        message_type="text",
        is_bot_mentioned=False,
        payload={},
    )


def make_kb_result() -> SearchResult:
    return SearchResult(
        chunks=[
            RetrievedChunk(
                id=10,
                document_id=20,
                title="Datacube AU",
                source_type="product_docs",
                heading="Datacube AU",
                content="Datacube AU is a WhatsApp assistant system.",
                score=0.9,
                diagnostics={"keyword_score": 1.0, "fuzzy_score": 1.0, "phrase_score": 0.9},
            )
        ],
        confidence=0.9,
    )


def make_planner(
    *,
    rule_reply: str | None = None,
    faq_entry: FakeFAQEntry | None = None,
    cache_hit: FakeCacheHit | None = None,
    search_result: SearchResult | None = None,
    memory_reply: str | None = None,
    ai_enabled: bool = False,
    user_allowed: bool = True,
    global_allowed: bool = True,
    strictness: str = "medium",
    threshold: str = "0.0",
) -> ReplyPlanner:
    planner = ReplyPlanner.__new__(ReplyPlanner)
    planner.session = None
    planner.rules = FakeRules(rule_reply)
    planner.faq = FakeFAQ(faq_entry)
    planner.retrieval = FakeRetrieval(cache_hit, search_result)
    planner.memory_service = FakeMemory(memory_reply)
    planner.rate_limiter = FakeRateLimiter(user_allowed=user_allowed, global_allowed=global_allowed)
    planner.bot_config = FakeBotConfig(ai_enabled, strictness=strictness, threshold=threshold)

    async def conversation_summary(_: str) -> str:
        return ""

    planner._get_conversation_summary = conversation_summary
    return planner


@pytest.mark.asyncio
async def test_rule_source_preempts_everything() -> None:
    planner = make_planner(rule_reply="Rule answer.")

    reply = await planner.plan(make_message("help"), contact_id=1)

    assert reply.decision_type == DecisionType.REPLY_RULE
    assert reply.reply_text == "Rule answer."
    assert reply.source_diagnostics["source"] == "Rule"
    assert planner.faq.calls == 0
    assert planner.retrieval.cache_calls == 0


@pytest.mark.asyncio
async def test_user_rate_limit_preempts_retrieval_and_ai() -> None:
    planner = make_planner(user_allowed=False, ai_enabled=True)

    reply = await planner.plan(make_message("hello"), contact_id=1)

    assert reply.decision_type == DecisionType.RATE_LIMITED
    assert "daily message limit" in reply.reply_text
    assert reply.source_diagnostics["source"] == "Rule"
    assert planner.faq.calls == 0


@pytest.mark.asyncio
async def test_faq_source_preempts_cache_kb_memory_and_ai() -> None:
    planner = make_planner(
        faq_entry=FakeFAQEntry(),
        cache_hit=FakeCacheHit(),
        search_result=make_kb_result(),
        memory_reply="Memory onboarding.",
        ai_enabled=True,
    )

    reply = await planner.plan(make_message("Who are you?"), contact_id=1)

    assert reply.decision_type == DecisionType.FAQ_REPLY
    assert reply.reply_text == "I'm Zina, Fabian's AI assistant."
    assert reply.source_diagnostics["source"] == "FAQ"
    assert planner.retrieval.cache_calls == 0
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_cache_source_preempts_kb_memory_and_ai() -> None:
    planner = make_planner(cache_hit=FakeCacheHit(), search_result=make_kb_result(), memory_reply="Memory.", ai_enabled=True)

    reply = await planner.plan(make_message("cached question"), contact_id=1)

    assert reply.decision_type == DecisionType.KB_REPLY
    assert reply.reply_text == "Cached answer."
    assert reply.source_diagnostics["source"] == "Cache"
    assert planner.retrieval.search_calls == 0
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_kb_source_preempts_memory_and_ai() -> None:
    planner = make_planner(search_result=make_kb_result(), memory_reply="Memory onboarding.", ai_enabled=True)

    reply = await planner.plan(make_message("what is datacube"), contact_id=1)

    assert reply.decision_type == DecisionType.KB_REPLY
    assert "Datacube AU is a WhatsApp assistant system" in reply.reply_text
    assert reply.source_diagnostics["source"] == "KB"
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_memory_source_preempts_ai() -> None:
    planner = make_planner(memory_reply="Welcome! What's your name?", ai_enabled=True)

    reply = await planner.plan(make_message("hello"), contact_id=1)

    assert reply.decision_type == DecisionType.MEMORY_ONBOARD
    assert reply.reply_text == "Welcome! What's your name?"
    assert reply.source_diagnostics["source"] == "Memory"


@pytest.mark.asyncio
async def test_ai_used_only_after_earlier_sources_fail(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True)

    reply = await planner.plan(make_message("novel strategic question"), contact_id=None)

    assert reply.decision_type == DecisionType.AI_REPLY_LIGHT
    assert reply.reply_text == "AI answer from Zina."
    assert reply.ai_used is True
    assert reply.source_diagnostics["source"] == "AI"
    assert mock_openrouter.calls == 1


@pytest.mark.asyncio
async def test_global_ai_limit_falls_back_without_calling_openrouter(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True, global_allowed=False)

    reply = await planner.plan(make_message("novel strategic question"), contact_id=None)

    assert reply.decision_type == DecisionType.NO_MATCH
    assert reply.source_diagnostics["source"] == "Fallback"
    assert mock_openrouter.calls == 0


@pytest.mark.asyncio
async def test_high_strictness_escalates_before_ai_call(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True, strictness="high", threshold="0.9")

    reply = await planner.plan(make_message("low confidence question"), contact_id=None)

    assert reply.decision_type == DecisionType.ESCALATED
    assert reply.reply_text == "Fabian may need to answer this personally."
    assert reply.source_diagnostics["source"] == "AI"
    assert reply.source_diagnostics["ai"]["escalated"] is True
    assert mock_openrouter.calls == 0


@pytest.mark.asyncio
async def test_fallback_used_when_ai_disabled_and_no_sources(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)
    planner = make_planner(ai_enabled=False)

    reply = await planner.plan(make_message("unknown question"), contact_id=None)

    assert reply.decision_type == DecisionType.NO_MATCH
    assert reply.reply_text == "Fabian may need to answer this personally."
    assert reply.source_diagnostics["source"] == "Fallback"


@pytest.mark.asyncio
async def test_cache_answer_if_reusable_writes_supported_sources() -> None:
    planner = make_planner()
    reply = await planner.plan(make_message("Who are you?"), contact_id=None)
    reply.decision_type = DecisionType.FAQ_REPLY
    reply.reply_text = "I'm Zina."
    reply.kb_confidence = 0.8

    await planner.cache_answer_if_reusable("Who are you?", reply)

    assert planner.retrieval.cached_answers[0]["answer_text"] == "I'm Zina."
    assert planner.retrieval.cached_answers[0]["answer_mode"] == "faq_reply"


@pytest.mark.asyncio
async def test_cache_answer_ignores_unsupported_or_empty_replies() -> None:
    planner = make_planner()

    await planner.cache_answer_if_reusable(
        "unknown",
        await planner._apply_identity_guard(
            type("Reply", (), {
                "decision_type": DecisionType.NO_MATCH,
                "reply_text": "fallback",
                "source_diagnostics": {},
            })()
        ),
    )
    await planner.cache_answer_if_reusable(
        "empty",
        type("Reply", (), {
            "decision_type": DecisionType.FAQ_REPLY,
            "reply_text": None,
            "source_diagnostics": {},
        })(),
    )

    assert planner.retrieval.cached_answers == []


def test_merge_summary_trims_long_history() -> None:
    assert ReplyPlanner._merge_summary("", "latest") == "latest"
    merged = ReplyPlanner._merge_summary("old", "latest")
    assert merged == "old\nlatest"
    long_previous = "x" * 2300
    trimmed = ReplyPlanner._merge_summary(long_previous, "latest")
    assert len(trimmed) == 2200
    assert trimmed.endswith("latest")
