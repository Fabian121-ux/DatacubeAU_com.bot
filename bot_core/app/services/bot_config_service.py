"""Dynamic bot configuration from the bot_config DB table."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import BotConfig
from app.utils.time import utcnow


_DEFAULTS: dict[str, str] = {
    "system_instructions": (
        "You are the personal WhatsApp assistant for Fabian and his projects.\n"
        "Your role is to answer questions about Fabian, explain his projects clearly, "
        "guide users, reduce repetitive conversations, and keep responses short, intelligent, and natural.\n"
        "You are NOT a generic AI chatbot. Present yourself as Fabian's assistant.\n"
        "Never pretend to be Fabian directly, and never invent fake services or achievements."
    ),
    "ai_enabled": "false",
    "ai_model_light": "openai/gpt-4o-mini",
    "ai_model_deep": "openai/gpt-4o",
    "rate_limit_per_user_daily": "50",
    "rate_limit_cooldown_seconds": "6",
    "rate_limit_global_daily": "500",
    "personality_tone": "professional",
    "personality_humor": "low",
    "personality_reply_length": "short",
    "personality_tech_depth": "medium",
    "personality_emoji": "light",
    "ai_strictness": "medium",
    "ai_creativity": "0.7",
    "ai_escalation_threshold": "0.3",
    "ai_hallucination_protection": "high",
    "identity_bio": "I am Fabian, a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.",
    "identity_projects": "AI systems, automation tools, WhatsApp assistant systems, knowledge and productivity projects. Main active project: Datacube AU.",
    "identity_services": "I build AI-assisted systems, automation tools, and productivity-focused projects.",
    "identity_skills": "AI, Automation, Cybersecurity, Python, Node.js",
    "identity_interests": "Technology, Productivity, Automation",
    "identity_focus": "Building intelligent WhatsApp assistants",
    "identity_style": "Helpful, concise, and direct",
    "identity_faq": "Q: What is Datacube AU?\nA: An intelligent WhatsApp assistant system focused on automation, smart replies, and AI-powered interactions.",
}


class BotConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, key: str, default: str | None = None) -> str:
        stmt = select(BotConfig.config_value).where(BotConfig.config_key == key).limit(1)
        value = (await self.session.execute(stmt)).scalar_one_or_none()
        if value is not None:
            return value
        if default is not None:
            return default
        return _DEFAULTS.get(key, "")

    async def get_bool(self, key: str, default: bool = False) -> bool:
        raw = await self.get(key, str(default).lower())
        return raw.strip().lower() in {"true", "1", "yes"}

    async def get_int(self, key: str, default: int = 0) -> int:
        raw = await self.get(key, str(default))
        try:
            return int(raw)
        except (ValueError, TypeError):
            return default

    async def set(self, key: str, value: str) -> None:
        stmt = select(BotConfig).where(BotConfig.config_key == key).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.config_value = value
            model.updated_at = utcnow()
        else:
            self.session.add(BotConfig(config_key=key, config_value=value, updated_at=utcnow()))
        await self.session.flush()

    async def get_all(self) -> dict[str, str]:
        stmt = select(BotConfig)
        rows = (await self.session.execute(stmt)).scalars().all()
        result = dict(_DEFAULTS)
        for row in rows:
            result[row.config_key] = row.config_value
        return result
