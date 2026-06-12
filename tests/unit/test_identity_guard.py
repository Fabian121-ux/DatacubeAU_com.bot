from __future__ import annotations

import pytest

from app.core.experience_formatter import WhatsAppExperienceFormatter
from app.core.reply_planner import PlannedReply, ReplyPlanner
from app.models.enums import DecisionType
from app.models.schema import BotConfig
from app.services.bot_config_service import BotConfigService


class FakeBotConfig:
    async def violates_identity_boundary(self, text_value: str) -> bool:
        service = BotConfigService.__new__(BotConfigService)
        service.get_identity_profile = self.get_identity_profile  # type: ignore[method-assign]
        return await service.violates_identity_boundary(text_value)

    async def escalation_reply(self) -> str:
        return "Fabian may need to answer this personally."

    async def get_bool(self, key: str, default: bool = False) -> bool:
        if key.startswith("experience_") or key in {"show_source_badges", "show_context_badges", "enable_signature_style"}:
            return False
        return default

    async def get_identity_profile(self) -> dict[str, str]:
        return {
            "assistant_name": "Zina",
            "assistant_role": "Fabian's Personal AI Assistant",
            "owner_name": "Fabian",
            "owner_bio": "",
            "projects": "",
            "services": "",
            "skills": "",
            "interests": "",
            "current_focus": "",
            "communication_style": "",
        }


def planner_with_identity_guard() -> ReplyPlanner:
    planner = ReplyPlanner.__new__(ReplyPlanner)
    planner.bot_config = FakeBotConfig()
    planner.formatter = WhatsAppExperienceFormatter()
    return planner


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_reply",
    [
        "I am Fabian.",
        "I'm Fabian, the founder of Datacube AU.",
        "I’m Fabian and I build automation systems.",
        "As Fabian I recommend this personally.",
        "As Fabian, I recommend this personally.",
        "Speaking as Fabian, this is my personal view.",
    ],
)
async def test_identity_guard_escalates_fabian_impersonation(bad_reply: str) -> None:
    planner = planner_with_identity_guard()
    reply = PlannedReply(
        decision_type=DecisionType.AI_REPLY_LIGHT,
        reason="test ai response",
        should_reply=True,
        reply_text=bad_reply,
        ai_used=True,
    )

    guarded = await planner._apply_identity_guard(reply)

    assert guarded.decision_type == DecisionType.ESCALATED
    assert guarded.reply_text == "Fabian may need to answer this personally."
    assert guarded.ai_used is False
    assert guarded.source_diagnostics["identity_guard"] == {"triggered": True}
    assert "identity boundary guard" in guarded.reason


@pytest.mark.asyncio
async def test_identity_guard_allows_legitimate_zina_response() -> None:
    planner = planner_with_identity_guard()
    reply = PlannedReply(
        decision_type=DecisionType.FAQ_REPLY,
        reason="faq match",
        should_reply=True,
        reply_text="I'm Zina, Fabian's AI assistant. I can help answer questions about Datacube AU.",
    )

    guarded = await planner._apply_identity_guard(reply)

    assert guarded.decision_type == DecisionType.FAQ_REPLY
    assert guarded.reply_text == reply.reply_text
    assert "identity_guard" not in guarded.source_diagnostics
    assert guarded.source_diagnostics["source"] == "FAQ"


@pytest.mark.asyncio
async def test_bot_config_identity_boundary_detection_uses_owner_name() -> None:
    service = BotConfigService.__new__(BotConfigService)

    async def fake_profile() -> dict[str, str]:
        return {"owner_name": "Fabian"}

    service.get_identity_profile = fake_profile  # type: ignore[method-assign]

    assert await service.violates_identity_boundary("My name is Fabian.")
    assert await service.violates_identity_boundary("As Fabian I would answer personally.")
    assert not await service.violates_identity_boundary("Fabian builds Datacube AU. I am Zina.")


class FakeScalarCollection:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return list(self.rows)


class FakeConfigResult:
    def __init__(self, scalar=None, rows=None):
        self.scalar = scalar
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return FakeScalarCollection(self.rows)


class FakeConfigSession:
    def __init__(self, scalar_results=None, rows=None):
        self.scalar_results = list(scalar_results or [])
        self.rows = list(rows or [])
        self.added = []
        self.flushed = False

    async def execute(self, _statement):
        if self.scalar_results:
            return FakeConfigResult(scalar=self.scalar_results.pop(0))
        return FakeConfigResult(rows=self.rows)

    def add(self, model):
        self.added.append(model)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_bot_config_get_bool_int_set_and_defaults() -> None:
    existing = BotConfig(config_key="ai_enabled", config_value="false")
    session = FakeConfigSession(scalar_results=["yes", "bad-int", existing, None])
    service = BotConfigService(session)  # type: ignore[arg-type]

    assert await service.get_bool("ai_enabled") is True
    assert await service.get_int("rate_limit_per_user_daily", 50) == 50

    await service.set("ai_enabled", "true")
    await service.set("new_key", "new_value")

    assert existing.config_value == "true"
    assert session.added[0].config_key == "new_key"
    assert session.added[0].config_value == "new_value"
    assert session.flushed is True


@pytest.mark.asyncio
async def test_bot_config_identity_prompt_intro_and_escalation() -> None:
    rows = [
        BotConfig(config_key="assistant_name", config_value="Zina"),
        BotConfig(config_key="assistant_role", config_value="Fabian's Personal AI Assistant"),
        BotConfig(config_key="owner_name", config_value="Fabian"),
        BotConfig(config_key="owner_bio", config_value="Fabian builds AI systems."),
        BotConfig(config_key="identity_projects", config_value="Datacube AU"),
        BotConfig(config_key="identity_services", config_value="Automation systems"),
        BotConfig(config_key="identity_skills", config_value="Python, FastAPI"),
        BotConfig(config_key="identity_interests", config_value="AI"),
        BotConfig(config_key="identity_focus", config_value="WhatsApp assistants"),
        BotConfig(config_key="identity_style", config_value="Concise"),
        BotConfig(config_key="personality_tone", config_value="professional"),
        BotConfig(config_key="personality_humor", config_value="low"),
        BotConfig(config_key="personality_reply_length", config_value="short"),
        BotConfig(config_key="personality_tech_depth", config_value="advanced"),
        BotConfig(config_key="personality_emoji", config_value="light"),
        BotConfig(config_key="ai_strictness", config_value="high"),
        BotConfig(config_key="ai_hallucination_protection", config_value="high"),
    ]
    service = BotConfigService(FakeConfigSession(rows=rows))  # type: ignore[arg-type]

    profile = await service.get_identity_profile()
    personality = await service.get_personality_settings()
    prompt = await service.build_system_prompt()
    intro = await service.introduction_reply()
    escalation = await service.escalation_reply()

    assert profile["assistant_name"] == "Zina"
    assert personality["strictness"] == "high"
    assert "You are Zina, Fabian's Personal AI Assistant." in prompt
    assert "Zina is not Fabian" in prompt
    assert "Never answer with \"I am Fabian\"" in prompt
    assert intro.startswith("Hi 👋 I'm Zina")
    assert escalation == "Fabian may need to answer this personally."
