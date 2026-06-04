"""Per-user memory and onboarding service."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import UserMemory
from app.utils.time import utcnow


# Onboarding stages
_STAGE_ASK_NAME = "ask_name"
_STAGE_ASK_PREF = "ask_preferences"


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_memory(self, contact_id: int) -> UserMemory | None:
        stmt = select(UserMemory).where(UserMemory.contact_id == contact_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert_memory(
        self,
        contact_id: int,
        *,
        user_name: str | None = None,
        preferences: str | None = None,
        context_notes: str | None = None,
        onboarding_complete: bool | None = None,
    ) -> UserMemory:
        memory = await self.get_memory(contact_id)
        if memory:
            if user_name is not None:
                memory.user_name = user_name
            if preferences is not None:
                memory.preferences = preferences
            if context_notes is not None:
                memory.context_notes = context_notes
            if onboarding_complete is not None:
                memory.onboarding_complete = onboarding_complete
            memory.updated_at = utcnow()
        else:
            memory = UserMemory(
                contact_id=contact_id,
                user_name=user_name,
                preferences=preferences,
                context_notes=context_notes,
                onboarding_complete=onboarding_complete or False,
                updated_at=utcnow(),
            )
            self.session.add(memory)
        await self.session.flush()
        return memory

    async def delete_memory(self, contact_id: int) -> bool:
        memory = await self.get_memory(contact_id)
        if memory:
            await self.session.delete(memory)
            await self.session.flush()
            return True
        return False

    async def check_onboarding(self, contact_id: int, message_text: str) -> tuple[str | None, str | None]:
        """Check if user is in onboarding flow.

        Returns (reply_text, stage) where reply_text is the bot response
        to send, or (None, None) if onboarding is complete / not needed.
        """
        memory = await self.get_memory(contact_id)

        # New user — start onboarding
        if memory is None:
            await self.upsert_memory(contact_id)
            return "Welcome! 👋 What's your name?", _STAGE_ASK_NAME

        # Already completed
        if memory.onboarding_complete:
            return None, None

        # Waiting for name
        if not memory.user_name:
            name = self._extract_name(message_text)
            if name:
                await self.upsert_memory(contact_id, user_name=name)
                return (
                    f"Nice to meet you, {name}! 😊 "
                    "Is there anything I should know about you? "
                    "(preferences, topics of interest, etc.) "
                    "Type 'skip' to skip.",
                    _STAGE_ASK_PREF,
                )
            # Could not extract a name, ask again
            return "I didn't catch that. What's your name?", _STAGE_ASK_NAME

        # Waiting for preferences
        if not memory.onboarding_complete:
            text_lower = message_text.strip().lower()
            if text_lower in {"skip", "no", "none", "n/a", "nothing", "nah"}:
                await self.upsert_memory(contact_id, onboarding_complete=True)
                return (
                    f"All set, {memory.user_name}! Ask me anything or type /help. 🚀",
                    None,
                )
            await self.upsert_memory(
                contact_id,
                preferences=message_text.strip()[:500],
                onboarding_complete=True,
            )
            return (
                f"Got it, {memory.user_name}! I'll remember that. Ask me anything or type /help. 🚀",
                None,
            )

        return None, None

    def get_memory_context(self, memory: UserMemory | None) -> str:
        """Build context string for AI prompt injection."""
        if not memory:
            return ""
        parts: list[str] = []
        if memory.user_name:
            parts.append(f"User name: {memory.user_name}")
        if memory.preferences:
            parts.append(f"Preferences: {memory.preferences}")
        if memory.context_notes:
            parts.append(f"Notes: {memory.context_notes}")
        return " | ".join(parts) if parts else ""

    @staticmethod
    def _extract_name(text: str) -> str | None:
        """Try to extract a name from freeform text."""
        cleaned = text.strip()
        # Common patterns: "My name is X", "I'm X", "I am X", "Call me X", or just the name
        patterns = [
            r"(?:my name is|i'm|i am|call me|it's|its)\s+(.+)",
            r"^([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20})?)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                name = match.group(1).strip().title()
                if 1 < len(name) <= 40:
                    return name
        # Fallback: if it's short enough, treat entire input as name
        if 1 < len(cleaned) <= 30 and cleaned.replace(" ", "").isalpha():
            return cleaned.strip().title()
        return None
