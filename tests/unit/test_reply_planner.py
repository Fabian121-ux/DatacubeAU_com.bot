from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.config import settings
from app.core.experience_formatter import WhatsAppExperienceFormatter
from app.core.intent_classifier import IntentClassifier
from app.core.message_normalizer import NormalizedMessage
from app.core.reply_planner import PlannedReply, ReplyPlanner
from app.core.rules_engine import RulesResult
from app.models.enums import ChatType, DecisionType
from app.services.memory_service import MemoryContextPackage, MemoryService
from app.services.retrieval_service import RetrievedChunk, SearchResult
from app.utils.text import normalize_text


@dataclass
class RateResult:
    allowed: bool = True
    reason: str = "allowed"
    limit: int = 5
    used: int = 0
    reset_time: object | None = None


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
    def __init__(self, user_allowed: bool = True, global_allowed: bool = True, ai_quota_allowed: bool = True):
        self.user_allowed = user_allowed
        self.global_allowed = global_allowed
        self.ai_quota_allowed = ai_quota_allowed

    async def check_user_daily_limit(self, *_: Any) -> RateResult:
        return RateResult(allowed=self.user_allowed, reason="user limit")

    async def check_global_ai_limit(self) -> RateResult:
        return RateResult(allowed=self.global_allowed, reason="global limit")

    async def check_user_ai_quota(self, *_: Any) -> RateResult:
        return RateResult(allowed=self.ai_quota_allowed, reason="user AI quota", limit=5, used=5)


class FakeFAQ:
    def __init__(self, entry: FakeFAQEntry | None = None, score: float = 0.92):
        self.entry = entry
        self.score = score
        self.calls = 0

    async def search_faq(self, *_: Any, **__: Any) -> tuple[FakeFAQEntry | None, float]:
        self.calls += 1
        return self.entry, self.score


class FakeIdentityRegistry:
    async def resolve_references(self, text_value: str) -> str:
        return text_value


class FakeCommandCatalog:
    async def is_enabled(self, _: str) -> bool:
        return True


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
    def __init__(self, reply_text: str | None = None, context_package: MemoryContextPackage | None = None, continuation_reply: str | None = None):
        self.reply_text = reply_text
        self.context_package = context_package or MemoryContextPackage(contact_id=1)
        self.continuation_reply = continuation_reply
        self.calls = 0
        self.context_calls = 0
        self.global_chat_updates = []

    async def check_onboarding(self, *_: Any) -> tuple[str | None, str | None]:
        self.calls += 1
        if self.reply_text:
            return self.reply_text, "ask_name"
        return None, None

    async def get_context_package(self, contact_id: int, **_: Any) -> MemoryContextPackage:
        self.context_calls += 1
        self.context_package.contact_id = contact_id
        return self.context_package

    def build_continuation_reply(self, *_: Any) -> str | None:
        return self.continuation_reply

    def build_memory_answer(self, *_: Any) -> tuple[str, str] | None:
        if self.continuation_reply:
            return self.continuation_reply, "Memory + Timeline"
        return None

    @staticmethod
    def diagnostics_for_package(package: MemoryContextPackage | None) -> dict[str, Any]:
        if not package:
            return {"retrieved_items": 0, "used": []}
        return {
            "used": package.used_sections,
            "retrieved_items": package.retrieved_item_count,
            "relationship_profile": bool(package.profile),
            "timeline_entries": len(package.timeline_entries),
            "summary_entries": len(package.summaries),
            "context_indicators": MemoryService.context_indicators_for_package(package),
        }

    @staticmethod
    def source_label_for_package(package: MemoryContextPackage, *, timeline_required: bool = False) -> str:
        return MemoryService.source_label_for_package(package, timeline_required=timeline_required)

    async def get_memory(self, *_: Any) -> None:
        return None

    def get_memory_context(self, *_: Any) -> str:
        return ""

    async def set_global_chat(self, *_: Any) -> None:
        self.global_chat_updates.append(_)
        return None


class FakeInternet:
    @staticmethod
    def parse_user_command(_: str) -> tuple[None, str, str]:
        return None, "", ""

    async def run(self, *_: Any, **__: Any) -> None:
        return None

    async def maybe_live_lookup(self, *_: Any, **__: Any) -> None:
        return None

    @staticmethod
    def usage_for_command(command: str) -> str:
        return f"Usage: {command} <query>"


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

    async def introduction_reply(self) -> str:
        return "Hi. I'm Zina, Fabian's AI assistant."

    async def identity_reply(self, _: str) -> str:
        return "I am Zina, Fabian's AI assistant."

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
    memory_context: MemoryContextPackage | None = None,
    memory_continuation: str | None = None,
    ai_enabled: bool = False,
    user_allowed: bool = True,
    global_allowed: bool = True,
    ai_quota_allowed: bool = True,
    strictness: str = "medium",
    threshold: str = "0.0",
) -> ReplyPlanner:
    planner = ReplyPlanner.__new__(ReplyPlanner)
    planner.session = None
    planner.rules = FakeRules(rule_reply)
    planner.faq = FakeFAQ(faq_entry)
    planner.identity_registry = FakeIdentityRegistry()
    planner.retrieval = FakeRetrieval(cache_hit, search_result)
    planner.memory_service = FakeMemory(memory_reply, memory_context, memory_continuation)
    planner.internet_service = FakeInternet()
    planner.command_catalog = FakeCommandCatalog()
    planner.rate_limiter = FakeRateLimiter(user_allowed=user_allowed, global_allowed=global_allowed, ai_quota_allowed=ai_quota_allowed)
    planner.bot_config = FakeBotConfig(ai_enabled, strictness=strictness, threshold=threshold)
    planner.formatter = WhatsAppExperienceFormatter()
    planner.intent_classifier = IntentClassifier()
    planner._active_intent = None
    planner._active_question = ""

    async def conversation_summary(_: str) -> str:
        return ""

    planner._get_conversation_summary = conversation_summary
    return planner


@pytest.mark.asyncio
async def test_rule_source_preempts_everything() -> None:
    planner = make_planner(rule_reply="Rule answer.")

    reply = await planner.plan(make_message("help"), contact_id=1)

    assert reply.decision_type == DecisionType.REPLY_RULE
    assert reply.raw_reply_text == "Rule answer."
    assert reply.reply_text.startswith("*Zina*")
    assert "Rule answer." in reply.reply_text
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
async def test_identity_source_preempts_faq_cache_kb_memory_and_ai() -> None:
    planner = make_planner(
        faq_entry=FakeFAQEntry(),
        cache_hit=FakeCacheHit(),
        search_result=make_kb_result(),
        memory_reply="Memory onboarding.",
        ai_enabled=True,
    )

    reply = await planner.plan(make_message("Who are you?"), contact_id=1)

    assert reply.decision_type == DecisionType.STATIC_REPLY
    assert reply.raw_reply_text == "I am Zina, Fabian's AI assistant."
    assert reply.reply_text.startswith("*Zina*")
    assert reply.source_diagnostics["source"] == "Identity"
    assert planner.retrieval.cache_calls == 0
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_faq_source_preempts_cache_kb_and_ai_for_non_identity_question() -> None:
    planner = make_planner(
        faq_entry=FakeFAQEntry(question="What services are offered?", answer="Fabian builds automation systems."),
        cache_hit=FakeCacheHit(),
        search_result=make_kb_result(),
        ai_enabled=True,
    )

    reply = await planner.plan(make_message("What services are offered?"), contact_id=1)

    assert reply.decision_type == DecisionType.FAQ_REPLY
    assert reply.raw_reply_text == "Fabian builds automation systems."
    assert reply.reply_text.startswith("*Zina*")
    assert reply.source_diagnostics["source"] == "FAQ"
    assert planner.retrieval.cache_calls == 0


@pytest.mark.asyncio
async def test_cache_source_preempts_internet_and_ai_after_local_knowledge_misses() -> None:
    planner = make_planner(cache_hit=FakeCacheHit(), memory_reply="Memory.", ai_enabled=True)

    reply = await planner.plan(make_message("cached question"), contact_id=1)

    assert reply.decision_type == DecisionType.KB_REPLY
    assert reply.raw_reply_text == "Cached answer."
    assert reply.reply_text.startswith("*Zina*")
    assert "Cached answer." in reply.reply_text
    assert reply.source_diagnostics["source"] == "Cache"
    assert planner.retrieval.search_calls == 1
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_kb_source_preempts_memory_and_ai() -> None:
    planner = make_planner(search_result=make_kb_result(), memory_reply="Memory onboarding.", ai_enabled=True)

    reply = await planner.plan(make_message("datacube capabilities"), contact_id=1)

    assert reply.decision_type == DecisionType.KB_REPLY
    assert "Datacube AU is a WhatsApp assistant system" in reply.reply_text
    assert reply.source_diagnostics["source"] == "KB"
    assert planner.memory_service.calls == 0


@pytest.mark.asyncio
async def test_memory_source_preempts_ai() -> None:
    planner = make_planner(memory_reply="Welcome. What's your name?", ai_enabled=True)

    reply = await planner.plan(make_message("I am new here"), contact_id=1)

    assert reply.decision_type == DecisionType.MEMORY_ONBOARD
    assert reply.raw_reply_text == "Welcome. What's your name?"
    assert reply.reply_text.startswith("*Zina*")
    assert reply.source_diagnostics["source"] == "Memory"


@pytest.mark.asyncio
async def test_memory_continuation_preempts_ai() -> None:
    package = MemoryContextPackage(
        contact_id=1,
        profile={"display_name": "Kingsley", "relationship_type": "friend"},
        timeline_entries=[{"topic": "cybersecurity internships", "summary": "Asked about internships"}],
        context_text="User: Kingsley\nRecent Topics:\n- cybersecurity internships",
        retrieved_item_count=2,
        used_sections=["Relationship Profile", "Timeline Entry"],
    )
    planner = make_planner(
        memory_context=package,
        memory_continuation="Welcome back Kingsley. Last time we discussed cybersecurity internships. How is that going?",
        ai_enabled=True,
    )

    reply = await planner.plan(make_message("hi"), contact_id=1)

    assert reply.decision_type == DecisionType.MEMORY_REPLY
    assert "Welcome back Kingsley" in reply.reply_text
    assert "Last time we discussed cybersecurity internships." in reply.reply_text
    assert reply.source_diagnostics["source"] == "Memory + Timeline"
    assert reply.source_diagnostics["memory"]["retrieved_items"] == 2


@pytest.mark.asyncio
async def test_ai_used_only_after_earlier_sources_fail(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True)

    reply = await planner.plan(make_message("!ask novel strategic question"), contact_id=1)

    assert reply.decision_type == DecisionType.AI_REPLY_LIGHT
    assert reply.raw_reply_text == "AI answer from Zina."
    assert reply.reply_text.startswith("*Zina*")
    assert "AI answer from Zina." in reply.reply_text
    assert reply.ai_used is True
    assert reply.source_diagnostics["source"] == "AI"
    assert mock_openrouter.calls == 1


@pytest.mark.asyncio
async def test_global_chat_commands_toggle_contact_mode() -> None:
    planner = make_planner()

    enabled = await planner.plan(make_message("/global on"), contact_id=1)
    disabled = await planner.plan(make_message("/global off"), contact_id=1)

    assert enabled.decision_type == DecisionType.STATIC_REPLY
    assert enabled.source_diagnostics["global_chat"]["active"] is True
    assert enabled.reply_text.startswith("*Zina*")
    assert disabled.source_diagnostics["global_chat"]["active"] is False
    assert planner.memory_service.global_chat_updates == [(1, True), (1, False)]


@pytest.mark.asyncio
async def test_global_chat_enabled_profile_allows_ai_without_bang_ask(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    package = MemoryContextPackage(
        contact_id=1,
        profile={"display_name": "Kingsley", "global_chat_enabled": True},
        context_text="User: Kingsley",
        retrieved_item_count=1,
        used_sections=["Relationship Profile"],
    )
    planner = make_planner(memory_context=package, ai_enabled=True)

    reply = await planner.plan(make_message("novel strategic question"), contact_id=1)

    assert reply.decision_type == DecisionType.AI_REPLY_LIGHT
    assert reply.source_diagnostics["global_chat"]["active"] is True
    assert reply.reply_text.startswith("*Zina*")
    assert "Welcome back Kingsley." in reply.reply_text


@pytest.mark.asyncio
async def test_general_knowledge_routes_to_ai_after_local_sources_miss(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True)

    reply = await planner.plan(make_message("What is the psychology behind humanity?"), contact_id=1)

    assert reply.decision_type == DecisionType.AI_REPLY_LIGHT
    assert reply.source_diagnostics["source"] == "AI"
    assert "general knowledge requires synthesis" in reply.source_diagnostics["ai"]["invocation_reason"]
    assert mock_openrouter.calls == 1


@pytest.mark.asyncio
async def test_user_ai_quota_prevents_global_chat_call(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True, ai_quota_allowed=False)

    reply = await planner.plan(make_message("!ask novel strategic question"), contact_id=1)

    assert reply.decision_type == DecisionType.RATE_LIMITED
    assert "Global Chat limit reached" in reply.raw_reply_text
    assert reply.source_diagnostics["ai_quota"]["allowed"] is False
    assert mock_openrouter.calls == 0


@pytest.mark.asyncio
async def test_global_ai_limit_falls_back_without_calling_openrouter(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True, global_allowed=False)

    reply = await planner.plan(make_message("!ask novel strategic question"), contact_id=1)

    assert reply.decision_type == DecisionType.NO_MATCH
    assert reply.source_diagnostics["source"] == "Fallback"
    assert mock_openrouter.calls == 0


@pytest.mark.asyncio
async def test_high_strictness_escalates_before_ai_call(monkeypatch, mock_openrouter) -> None:
    monkeypatch.setattr("app.core.reply_planner.OpenRouterClient", mock_openrouter)
    monkeypatch.setattr(settings, "ai_enabled", True)
    planner = make_planner(ai_enabled=True, strictness="high", threshold="0.9")

    reply = await planner.plan(make_message("!ask low confidence question"), contact_id=1)

    assert reply.decision_type == DecisionType.ESCALATED
    assert reply.raw_reply_text == "Fabian may need to answer this personally."
    assert reply.source_diagnostics["source"] == "AI"
    assert reply.source_diagnostics["ai"]["escalated"] is True
    assert mock_openrouter.calls == 0


@pytest.mark.asyncio
async def test_fallback_used_when_ai_disabled_and_no_sources(monkeypatch) -> None:
    monkeypatch.setattr(settings, "ai_enabled", False)
    planner = make_planner(ai_enabled=False)

    reply = await planner.plan(make_message("unknown question"), contact_id=None)

    assert reply.decision_type == DecisionType.NO_MATCH
    assert reply.raw_reply_text == "Fabian may need to answer this personally."
    assert reply.reply_text.startswith("*Zina*")
    assert reply.source_diagnostics["source"] == "Fallback"


@pytest.mark.asyncio
async def test_cache_answer_if_reusable_writes_supported_sources() -> None:
    planner = make_planner()
    reply = PlannedReply(
        decision_type=DecisionType.FAQ_REPLY,
        reason="test",
        should_reply=True,
        reply_text="*Zina*\n\nSource: FAQ\n\nI'm Zina.",
        raw_reply_text="I'm Zina.",
        kb_confidence=0.8,
        source_diagnostics={"source": "FAQ"},
    )

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


@pytest.mark.asyncio
async def test_cache_answer_skips_replies_that_used_memory_context() -> None:
    planner = make_planner()
    reply = await planner._apply_identity_guard(
        type("Reply", (), {
            "decision_type": DecisionType.AI_REPLY_LIGHT,
            "reply_text": "Personalized answer for Kingsley.",
            "source_diagnostics": {"memory": {"retrieved_items": 2}},
            "matched_chunks": [],
            "kb_confidence": 0.0,
            "ai_used": True,
        })()
    )

    await planner.cache_answer_if_reusable("what next?", reply)

    assert planner.retrieval.cached_answers == []


def test_merge_summary_trims_long_history() -> None:
    assert ReplyPlanner._merge_summary("", "latest") == "latest"
    merged = ReplyPlanner._merge_summary("old", "latest")
    assert merged == "old\nlatest"
    long_previous = "x" * 2300
    trimmed = ReplyPlanner._merge_summary(long_previous, "latest")
    assert len(trimmed) == 2200
    assert trimmed.endswith("latest")
