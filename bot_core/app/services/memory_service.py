"""Per-user memory and onboarding service."""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import UserMemory, UserMemoryTimeline
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
        profession: str | None = None,
        interests: str | None = None,
        projects: str | None = None,
        goals: str | None = None,
        communication_style: str | None = None,
        relationship: str | None = None,
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
            if profession is not None:
                memory.profession = profession
            if interests is not None:
                memory.interests = interests
            if projects is not None:
                memory.projects = projects
            if goals is not None:
                memory.goals = goals
            if communication_style is not None:
                memory.communication_style = communication_style
            if relationship is not None:
                memory.relationship = relationship
            memory.updated_at = utcnow()
        else:
            memory = UserMemory(
                contact_id=contact_id,
                user_name=user_name,
                preferences=preferences,
                context_notes=context_notes,
                onboarding_complete=onboarding_complete or False,
                profession=profession,
                interests=interests,
                projects=projects,
                goals=goals,
                communication_style=communication_style,
                relationship=relationship,
                updated_at=utcnow(),
            )
            self.session.add(memory)
        await self.session.flush()
        return memory

    async def log_memory_fact(
        self,
        contact_id: int,
        *,
        memory_text: str,
        source: str = "chat_extraction",
        confidence: float = 0.7,
    ) -> UserMemoryTimeline:
        entry = UserMemoryTimeline(
            contact_id=contact_id,
            memory_text=memory_text[:1200],
            source=source[:40],
            confidence=max(0.0, min(confidence, 1.0)),
            updated_at=utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def extract_profile_from_message(
        self,
        contact_id: int,
        message_text: str,
        *,
        source: str = "chat_extraction",
    ) -> list[str]:
        """Extract obvious profile facts without forcing an onboarding flow."""
        extracted = self._extract_profile_fields(message_text)
        if not extracted:
            return []

        memory = await self.get_memory(contact_id)
        if not memory:
            memory = await self.upsert_memory(contact_id)

        changed: dict[str, str] = {}
        for field, value in extracted.items():
            current = getattr(memory, field, None)
            merged = self._merge_fact(current, value)
            if merged != current:
                setattr(memory, field, merged)
                changed[field] = value

        if not changed:
            return []

        memory.updated_at = utcnow()
        for field, value in changed.items():
            await self.log_memory_fact(
                contact_id,
                memory_text=f"{field}: {value}",
                source=source,
                confidence=0.72,
            )
        await self.session.flush()
        return [f"{field}: {value}" for field, value in changed.items()]

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
            name = self._extract_name(message_text)
            if name:
                await self.upsert_memory(contact_id, user_name=name)
                await self.log_memory_fact(
                    contact_id,
                    memory_text=f"user_name: {name}",
                    source="onboarding",
                    confidence=0.9,
                )
                return (
                    f"Nice to meet you, {name}! 😊 "
                    "Is there anything I should know about you? "
                    "(preferences, topics of interest, etc.) "
                    "Type 'skip' to skip.",
                    _STAGE_ASK_PREF,
                )
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
        if memory.profession:
            parts.append(f"Profession: {memory.profession}")
        if memory.interests:
            parts.append(f"Interests: {memory.interests}")
        if memory.projects:
            parts.append(f"Projects: {memory.projects}")
        if memory.goals:
            parts.append(f"Goals: {memory.goals}")
        if memory.communication_style:
            parts.append(f"Communication style: {memory.communication_style}")
        if memory.relationship:
            parts.append(f"Relationship to Fabian: {memory.relationship}")
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
                candidate = match.group(1).strip()
                lowered = candidate.lower()
                invalid_prefixes = ("a ", "an ", "the ", "into ", "interested ", "working ", "building ", "trying ")
                if lowered.startswith(invalid_prefixes):
                    continue
                name = candidate.title()
                if 1 < len(name) <= 40:
                    return name
        # Fallback: if it's short enough, treat entire input as name
        words = cleaned.split()
        stop_words = {"i", "am", "im", "i'm", "my", "name", "is", "a", "an", "the"}
        if (
            1 < len(cleaned) <= 30
            and 1 <= len(words) <= 2
            and cleaned.replace(" ", "").isalpha()
            and not any(word.lower() in stop_words for word in words)
        ):
            return cleaned.strip().title()
        return None

    @staticmethod
    def _extract_profile_fields(text: str) -> dict[str, str]:
        cleaned = " ".join(text.strip().split())
        if len(cleaned) < 8:
            return {}

        patterns: dict[str, list[str]] = {
            "profession": [
                r"\b(?:i am|i'm|im|i work as|my profession is|my job is)\s+(?:a|an)?\s*([^.!?;,]{3,80})",
                r"\b(?:i work in|my field is)\s+([^.!?;,]{3,80})",
            ],
            "interests": [
                r"\b(?:i am interested in|i'm interested in|im interested in|i like|i'm into|im into)\s+([^.!?;]{3,160})",
            ],
            "projects": [
                r"\b(?:i am working on|i'm working on|im working on|i am building|i'm building|im building|my project is)\s+([^.!?;]{3,180})",
            ],
            "goals": [
                r"\b(?:my goal is|my goals are|i want to|i'm trying to|im trying to)\s+([^.!?;]{3,180})",
            ],
            "communication_style": [
                r"\b(?:i prefer|please keep|talk to me in)\s+([^.!?;]{3,120})(?:\s+(?:replies|responses|style))?",
            ],
            "relationship": [
                r"\b(?:fabian is my|i know fabian as|i am fabian's|i'm fabian's|im fabian's)\s+([^.!?;]{3,120})",
            ],
        }

        values: dict[str, str] = {}
        for field, field_patterns in patterns.items():
            for pattern in field_patterns:
                match = re.search(pattern, cleaned, flags=re.IGNORECASE)
                if not match:
                    continue
                value = MemoryService._clean_profile_value(match.group(1))
                if value:
                    values[field] = value
                    break
        return values

    @staticmethod
    def _clean_profile_value(value: str) -> str:
        cleaned = value.strip(" -:,.").strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned or len(cleaned) < 3:
            return ""
        return cleaned[:240]

    @staticmethod
    def _merge_fact(current: str | None, new_value: str) -> str:
        if not current:
            return new_value
        current_norm = current.lower()
        new_norm = new_value.lower()
        if new_norm in current_norm:
            return current
        merged = f"{current}; {new_value}"
        return merged[:1000]
