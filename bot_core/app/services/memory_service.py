"""Per-user memory and onboarding service."""
from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RelationshipType
from app.models.schema import (
    ConversationSession,
    ConversationSummary,
    ConversationTimeline,
    Message,
    UserMemory,
    UserMemoryTimeline,
)
from app.utils.text import escape_like, normalize_text
from app.utils.time import utcnow


# Onboarding stages
_STAGE_ASK_NAME = "ask_name"
_STAGE_ASK_PREF = "ask_preferences"
DEFAULT_SUMMARY_THRESHOLDS = (25, 50, 100)
RELATIONSHIP_TYPES = {item.value for item in RelationshipType}
ACKNOWLEDGEMENT_NAMES = {
    "ah",
    "fine",
    "good",
    "great",
    "hmm",
    "kk",
    "k",
    "lol",
    "nah",
    "nice",
    "no",
    "okay",
    "ok",
    "sure",
    "thanks",
    "thank you",
    "wow",
    "ya",
    "yeah",
    "yes",
    "yup",
}


@dataclass(slots=True)
class MemoryContextPackage:
    contact_id: int
    profile: dict[str, Any] = field(default_factory=dict)
    timeline_entries: list[dict[str, Any]] = field(default_factory=list)
    summaries: list[dict[str, Any]] = field(default_factory=list)
    context_text: str = ""
    retrieved_item_count: int = 0
    used_sections: list[str] = field(default_factory=list)


class MemoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_memory(self, contact_id: int, *, include_disabled: bool = False, for_update: bool = False) -> UserMemory | None:
        stmt = select(UserMemory).where(UserMemory.contact_id == contact_id).limit(1)
        if not include_disabled:
            stmt = stmt.where(UserMemory.is_enabled.is_(True))
        if for_update:
            stmt = stmt.with_for_update()
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def upsert_memory(
        self,
        contact_id: int,
        *,
        display_name: str | None = None,
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
        relationship_type: str | None = None,
        personality_notes: str | None = None,
        global_chat_enabled: bool | None = None,
        last_interaction_at=None,
    ) -> UserMemory:
        normalized_relationship_type = (
            self.normalize_relationship_type(relationship_type) if relationship_type is not None else None
        )
        memory = await self.get_memory(contact_id, include_disabled=True, for_update=True)
        if memory:
            if display_name is not None:
                memory.display_name = display_name
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
                derived_type = self._relationship_type_from_text(relationship)
                if derived_type and getattr(memory, "relationship_type", "unknown") == RelationshipType.UNKNOWN.value:
                    memory.relationship_type = derived_type
            if normalized_relationship_type is not None:
                memory.relationship_type = normalized_relationship_type
            if personality_notes is not None:
                memory.personality_notes = personality_notes
            if global_chat_enabled is not None:
                memory.global_chat_enabled = global_chat_enabled
            if last_interaction_at is not None:
                memory.last_interaction_at = last_interaction_at
            memory.updated_at = utcnow()
        else:
            memory = UserMemory(
                contact_id=contact_id,
                display_name=display_name,
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
                relationship_type=normalized_relationship_type
                or self._relationship_type_from_text(relationship)
                or RelationshipType.UNKNOWN.value,
                personality_notes=personality_notes,
                global_chat_enabled=global_chat_enabled or False,
                is_enabled=True,
                first_seen_at=utcnow(),
                last_interaction_at=last_interaction_at,
                updated_at=utcnow(),
            )
            self.session.add(memory)
        await self.session.flush()
        return memory

    async def ensure_relationship_profile(self, contact_id: int, display_name: str | None = None) -> UserMemory:
        """Create or touch the contact-scoped relationship profile."""
        return await self.upsert_memory(
            contact_id,
            display_name=display_name,
            last_interaction_at=utcnow(),
        )

    async def set_global_chat(self, contact_id: int, enabled: bool) -> UserMemory:
        memory = await self.upsert_memory(contact_id, global_chat_enabled=enabled)
        await self.log_memory_fact(
            contact_id,
            memory_text=f"global_chat_enabled: {enabled}",
            source="user_command",
            confidence=1.0,
        )
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
            memory_type="profile_fact",
            importance=max(0.0, min(confidence, 1.0)),
            confidence=max(0.0, min(confidence, 1.0)),
            is_enabled=True,
            updated_at=utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def log_timeline_event(
        self,
        contact_id: int,
        *,
        topic: str,
        summary: str,
        importance_score: float = 0.5,
        source: str = "conversation",
    ) -> ConversationTimeline:
        entry = ConversationTimeline(
            contact_id=contact_id,
            timestamp=utcnow(),
            topic=self._clean_profile_value(topic)[:220] or "General conversation",
            summary=summary.strip()[:1200],
            importance_score=max(0.0, min(importance_score, 1.0)),
            source=source[:40],
            updated_at=utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def log_conversation_event(
        self,
        contact_id: int,
        *,
        user_text: str,
        decision: str,
        source: str = "router_trace",
    ) -> ConversationTimeline | None:
        payload = self._build_timeline_payload(user_text, decision)
        if not payload:
            return None
        return await self.log_timeline_event(
            contact_id,
            topic=payload["topic"],
            summary=payload["summary"],
            importance_score=payload["importance_score"],
            source=source,
        )

    async def search_timeline(
        self,
        contact_id: int,
        *,
        query: str | None = None,
        limit: int = 5,
    ) -> list[ConversationTimeline]:
        stmt = select(ConversationTimeline).where(ConversationTimeline.contact_id == contact_id)
        if query and normalize_text(query) not in {"", "hi", "hello", "hey", "yo"}:
            like = f"%{query.strip()}%"
            stmt = stmt.where(or_(ConversationTimeline.topic.ilike(like, escape="\\"), ConversationTimeline.summary.ilike(like, escape="\\")))
        stmt = stmt.order_by(ConversationTimeline.timestamp.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_timeline_entry(self, contact_id: int, timeline_id: int) -> bool:
        result = await self.session.execute(
            delete(ConversationTimeline)
            .where(ConversationTimeline.id == timeline_id)
            .where(ConversationTimeline.contact_id == contact_id)
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def create_summary(
        self,
        contact_id: int,
        *,
        summary: str,
        topics: Sequence[str] | None = None,
        message_count: int = 0,
        threshold: int | None = None,
        source: str = "threshold_summary",
    ) -> ConversationSummary:
        model = ConversationSummary(
            contact_id=contact_id,
            summary=summary.strip()[:1800],
            topics=list(topics or [])[:12],
            message_count=message_count,
            threshold=threshold,
            source=source[:40],
            updated_at=utcnow(),
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def get_recent_summaries(self, contact_id: int, *, limit: int = 3) -> list[ConversationSummary]:
        stmt = (
            select(ConversationSummary)
            .where(ConversationSummary.contact_id == contact_id)
            .order_by(ConversationSummary.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_summary(self, contact_id: int, summary_id: int) -> bool:
        result = await self.session.execute(
            delete(ConversationSummary)
            .where(ConversationSummary.id == summary_id)
            .where(ConversationSummary.contact_id == contact_id)
        )
        await self.session.flush()
        return bool(result.rowcount)

    async def generate_due_summaries(
        self,
        contact_id: int,
        *,
        chat_id: str,
        thresholds: Sequence[int] | None = None,
    ) -> list[ConversationSummary]:
        configured_thresholds = sorted({int(item) for item in (thresholds or DEFAULT_SUMMARY_THRESHOLDS) if int(item) > 0})
        if not configured_thresholds:
            return []

        message_count = (
            await self.session.execute(select(func.count(Message.id)).where(Message.contact_id == contact_id))
        ).scalar_one()
        due_thresholds = [threshold for threshold in configured_thresholds if message_count >= threshold]
        if not due_thresholds:
            return []

        existing_rows = (
            await self.session.execute(
                select(ConversationSummary.threshold)
                .where(ConversationSummary.contact_id == contact_id)
                .where(ConversationSummary.threshold.in_(due_thresholds))
            )
        ).scalars().all()
        existing = {item for item in existing_rows if item is not None}
        missing = [threshold for threshold in due_thresholds if threshold not in existing]
        if not missing:
            return []

        compact_summary, topics = await self._build_compact_summary(contact_id, chat_id, message_count)
        created: list[ConversationSummary] = []
        for threshold in missing:
            created.append(
                await self.create_summary(
                    contact_id,
                    summary=compact_summary,
                    topics=topics,
                    message_count=message_count,
                    threshold=threshold,
                )
            )
        return created

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
                if field == "relationship":
                    relationship_type = self._relationship_type_from_text(value)
                    if relationship_type and getattr(memory, "relationship_type", RelationshipType.UNKNOWN.value) == RelationshipType.UNKNOWN.value:
                        memory.relationship_type = relationship_type
                        changed["relationship_type"] = relationship_type

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
            await self.session.execute(delete(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == contact_id))
            await self.session.execute(delete(ConversationTimeline).where(ConversationTimeline.contact_id == contact_id))
            await self.session.execute(delete(ConversationSummary).where(ConversationSummary.contact_id == contact_id))
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
            name, confidence, source = self._extract_name_candidate(message_text)
            if name:
                await self.upsert_memory(contact_id, user_name=name)
                await self.log_memory_fact(
                    contact_id,
                    memory_text=f"user_name: {name} (source={source}, confidence={confidence:.2f})",
                    source="onboarding",
                    confidence=confidence,
                )
                return (
                    f"Nice to meet you, {name}. "
                    "Is there anything I should know about you? "
                    "(preferences, topics of interest, etc.) "
                    "Type 'skip' to skip.",
                    _STAGE_ASK_PREF,
                )
            await self.upsert_memory(contact_id)
            return "Welcome. What's your name?", _STAGE_ASK_NAME

        # Already completed
        if memory.onboarding_complete:
            return None, None

        # Waiting for name
        if not memory.user_name:
            name, confidence, source = self._name_from_memory_or_text(memory, message_text)
            if name:
                await self.upsert_memory(contact_id, user_name=name)
                await self.log_memory_fact(
                    contact_id,
                    memory_text=f"user_name: {name} (source={source}, confidence={confidence:.2f})",
                    source="onboarding",
                    confidence=confidence,
                )
                return (
                    f"Nice to meet you, {name}. "
                    "Is there anything I should know about you? "
                    "(preferences, topics of interest, etc.) "
                    "Type 'skip' to skip.",
                    _STAGE_ASK_PREF,
                )
            # Could not extract a name, ask again
            if self._is_greeting(message_text):
                return "Welcome. What's your name?", _STAGE_ASK_NAME
            return "I didn't catch that. What's your name?", _STAGE_ASK_NAME

        # Waiting for preferences
        if not memory.onboarding_complete:
            text_lower = message_text.strip().lower()
            if text_lower in {"skip", "no", "none", "n/a", "nothing", "nah"}:
                await self.upsert_memory(contact_id, onboarding_complete=True)
                return (
                    f"All set, {memory.user_name}. Ask me anything or type /help.",
                    None,
                )
            await self.upsert_memory(
                contact_id,
                preferences=message_text.strip()[:500],
                onboarding_complete=True,
            )
            return (
                f"Got it, {memory.user_name}. I'll remember that. Ask me anything or type /help.",
                None,
            )

        return None, None

    def get_memory_context(self, memory: UserMemory | None) -> str:
        """Build context string for AI prompt injection."""
        if not memory:
            return ""
        parts: list[str] = []
        if getattr(memory, "display_name", None):
            parts.append(f"Display name: {memory.display_name}")
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
        if getattr(memory, "relationship_type", None):
            parts.append(f"Relationship type: {memory.relationship_type}")
        if getattr(memory, "personality_notes", None):
            parts.append(f"Personality notes: {memory.personality_notes}")
        return " | ".join(parts) if parts else ""

    async def get_context_package(
        self,
        contact_id: int,
        *,
        query: str | None = None,
        timeline_limit: int = 3,
        summary_limit: int = 2,
    ) -> MemoryContextPackage:
        memory = await self.get_memory(contact_id)
        timeline = await self.search_timeline(contact_id, query=query, limit=timeline_limit)
        if query and not timeline:
            timeline = await self.search_timeline(contact_id, limit=timeline_limit)
        summaries = await self.get_recent_summaries(contact_id, limit=summary_limit)

        profile = self._profile_dict(memory, contact_id)
        timeline_payload = [self._timeline_dict(row) for row in timeline]
        summary_payload = [self._summary_dict(row) for row in summaries]
        if profile:
            profile.update(await self.relationship_intelligence(contact_id, memory, timeline_payload, summary_payload))
        context_text = self._build_context_text(profile, timeline_payload, summary_payload)
        used_sections: list[str] = []
        if profile:
            used_sections.append("Relationship Profile")
        if timeline_payload:
            used_sections.append("Timeline Entry")
        if summary_payload:
            used_sections.append("Summary Entry")

        return MemoryContextPackage(
            contact_id=contact_id,
            profile=profile,
            timeline_entries=timeline_payload,
            summaries=summary_payload,
            context_text=context_text,
            retrieved_item_count=(1 if profile else 0) + len(timeline_payload) + len(summary_payload),
            used_sections=used_sections,
        )

    async def relationship_intelligence(
        self,
        contact_id: int,
        memory: UserMemory | None,
        timeline_entries: list[dict[str, Any]] | None = None,
        summaries: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        message_count = (
            await self.session.execute(select(func.count(Message.id)).where(Message.contact_id == contact_id))
        ).scalar_one()
        timeline_payload = timeline_entries or [self._timeline_dict(row) for row in await self.search_timeline(contact_id, limit=8)]
        summary_payload = summaries or [self._summary_dict(row) for row in await self.get_recent_summaries(contact_id, limit=3)]
        topics = self._unique_strings(
            [str(row.get("topic") or "") for row in timeline_payload]
            + [topic for summary in summary_payload for topic in (summary.get("topics") or [])]
        )
        last_seen = getattr(memory, "last_interaction_at", None) or getattr(memory, "updated_at", None) if memory else None
        topic_factor = min(len(topics) / 8, 1.0)
        conversation_factor = min(int(message_count or 0) / 40, 1.0)
        trust_score = round(min(1.0, 0.2 + (conversation_factor * 0.45) + (topic_factor * 0.25)), 2)
        engagement_score = round(min(1.0, (conversation_factor * 0.65) + (topic_factor * 0.35)), 2)
        if message_count >= 30:
            frequency = "high"
        elif message_count >= 10:
            frequency = "medium"
        elif message_count > 0:
            frequency = "low"
        else:
            frequency = "none"
        if trust_score >= 0.75:
            importance = "high"
        elif trust_score >= 0.45:
            importance = "medium"
        else:
            importance = "normal"
        return {
            "conversation_count": int(message_count or 0),
            "topics_discussed": topics[:12],
            "last_seen": last_seen,
            "interaction_frequency": frequency,
            "trust_score": trust_score,
            "importance_level": importance,
            "engagement_score": engagement_score,
        }

    def build_continuation_reply(self, message_text: str, package: MemoryContextPackage) -> str | None:
        if not package.context_text:
            return None
        if not self._is_continuation_prompt(message_text):
            return None

        name = package.profile.get("display_name") or package.profile.get("user_name")
        opener = f"Welcome back {name}." if name else "Welcome back."
        last_discussion = self._latest_discussion_label(package)
        if not last_discussion:
            return None

        if self._asks_for_last_discussion(message_text):
            return f"Last time we discussed {last_discussion}."
        return f"{opener} Last time we discussed {last_discussion}. How is that going?"

    def build_memory_answer(self, message_text: str, package: MemoryContextPackage) -> tuple[str, str] | None:
        """Answer only when the user explicitly asks about remembered context."""
        if not package.context_text:
            return None

        continuation = self.build_continuation_reply(message_text, package)
        if continuation:
            return continuation, self.source_label_for_package(package, timeline_required=True)

        normalized = normalize_text(message_text)
        if self._asks_for_profile_memory(normalized):
            answer = self._profile_answer(package, normalized)
            if answer:
                return answer, "Memory"

        if self._asks_for_timeline_memory(normalized):
            answer = self._timeline_answer(package)
            if answer:
                return answer, self.source_label_for_package(package, timeline_required=True)

        if self._asks_for_summary_memory(normalized):
            answer = self._summary_answer(package)
            if answer:
                return answer, "Timeline"

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
            "global_chat_enabled": bool(package.profile.get("global_chat_enabled")) if package.profile else False,
        }

    @staticmethod
    def context_indicators_for_package(package: MemoryContextPackage | None) -> list[str]:
        if not package or not package.retrieved_item_count:
            return []
        indicators: list[str] = []
        name = package.profile.get("display_name") or package.profile.get("user_name")
        if name:
            indicators.append(f"Welcome back {name}.")
        last_discussion = MemoryService._latest_discussion_label(package)
        if last_discussion:
            indicators.append(f"Last time we discussed {last_discussion}.")
            indicators.append("Continuing our previous discussion.")
        return indicators[:3]

    @staticmethod
    def source_label_for_package(package: MemoryContextPackage, *, timeline_required: bool = False) -> str:
        has_profile = bool(package.profile)
        has_timeline = bool(package.timeline_entries or package.summaries)
        if has_profile and has_timeline:
            return "Memory + Timeline"
        if has_timeline or timeline_required:
            return "Timeline"
        return "Memory"

    @staticmethod
    def _asks_for_profile_memory(normalized: str) -> bool:
        phrases = (
            "what is my name",
            "whats my name",
            "do you know my name",
            "remember my name",
            "what do you remember about me",
            "what do you know about me",
            "my profile",
            "who am i",
            "my interests",
            "my goals",
            "my projects",
            "my preferences",
            "my relationship",
            "relationship to fabian",
        )
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _asks_for_timeline_memory(normalized: str) -> bool:
        phrases = (
            "timeline",
            "last discussion",
            "last conversation",
            "previous discussion",
            "previous conversation",
            "what did we discuss",
            "what were we talking",
        )
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _asks_for_summary_memory(normalized: str) -> bool:
        return any(phrase in normalized for phrase in ("summary", "summaries", "summarize our"))

    @staticmethod
    def _profile_answer(package: MemoryContextPackage, normalized: str = "") -> str:
        profile = package.profile
        if not profile:
            return ""
        name = profile.get("display_name") or profile.get("user_name")
        if any(phrase in normalized for phrase in ("what is my name", "whats my name", "do you know my name", "remember my name")):
            return f"Your name is {name}." if name else "I do not have your name saved yet."
        lines = ["Here is what I currently remember:"]
        fields = [
            ("Name", name),
            ("Relationship", profile.get("relationship") or profile.get("relationship_type")),
            ("Interests", profile.get("interests")),
            ("Goals", profile.get("goals")),
            ("Projects", profile.get("projects")),
            ("Preferences", profile.get("preferences")),
            ("Personality notes", profile.get("personality_notes")),
            ("Topics discussed", ", ".join(profile.get("topics_discussed") or [])),
            ("Conversation count", str(profile.get("conversation_count") or "")),
            ("Interaction frequency", profile.get("interaction_frequency")),
        ]
        for label, value in fields:
            if value:
                lines.append(f"• {label}: {value}")
        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _timeline_answer(package: MemoryContextPackage) -> str:
        entries = package.timeline_entries
        if not entries:
            return ""
        lines = ["Recent discussion history:"]
        for entry in entries[:5]:
            topic = str(entry.get("topic") or "General conversation")
            summary = str(entry.get("summary") or "").strip()
            lines.append(f"• {topic}: {summary[:180]}")
        return "\n".join(lines)

    @staticmethod
    def _summary_answer(package: MemoryContextPackage) -> str:
        summaries = package.summaries
        if not summaries:
            return ""
        lines = ["Stored conversation summaries:"]
        for summary in summaries[:3]:
            text_value = str(summary.get("summary") or "").strip()
            topics = summary.get("topics") or []
            suffix = f" ({', '.join(topics[:4])})" if topics else ""
            lines.append(f"• {text_value[:220]}{suffix}")
        return "\n".join(lines)

    @staticmethod
    def _extract_name(text: str) -> str | None:
        name, _, _ = MemoryService._extract_name_candidate(text)
        return name

    @staticmethod
    def _extract_name_candidate(text: str) -> tuple[str | None, float, str]:
        """Try to extract a name from freeform text."""
        cleaned = text.strip()
        if MemoryService._is_invalid_name_candidate(cleaned):
            return None, 0.0, "invalid"
        # Common patterns: "My name is X", "I'm X", "I am X", "Call me X", or just the name
        patterns = [
            r"(?:my name is|i'm|i am|call me|it's|its)\s+(.+)",
            r"^([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20})?)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, cleaned, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                if MemoryService._is_invalid_name_candidate(candidate):
                    continue
                name = candidate.title()
                if 1 < len(name) <= 40:
                    return name, 0.9, "explicit_message"
        # Fallback: if it's short enough, treat entire input as name
        words = cleaned.split()
        stop_words = {"i", "am", "im", "i'm", "my", "name", "is", "a", "an", "the"}
        greeting_words = {"hello", "hi", "hey", "yo"}
        if (
            1 < len(cleaned) <= 30
            and 1 <= len(words) <= 2
            and cleaned.replace(" ", "").isalpha()
            and not any(word.lower() in stop_words for word in words)
            and not any(word.lower() in greeting_words for word in words)
            and not MemoryService._is_invalid_name_candidate(cleaned)
        ):
            return cleaned.strip().title(), 0.55, "freeform_guess"
        return None, 0.0, "none"

    @staticmethod
    def _name_from_memory_or_text(memory: UserMemory, message_text: str) -> tuple[str | None, float, str]:
        display_name = MemoryService._trusted_display_name(getattr(memory, "display_name", None))
        if display_name:
            return display_name, 0.86, "whatsapp_metadata"
        return MemoryService._extract_name_candidate(message_text)

    @staticmethod
    def _trusted_display_name(display_name: str | None) -> str | None:
        cleaned = " ".join(str(display_name or "").strip().split())
        if not cleaned or MemoryService._is_invalid_name_candidate(cleaned):
            return None
        if "@" in cleaned or re.fullmatch(r"\+?\d[\d\s().-]{6,}", cleaned):
            return None
        if len(cleaned) > 50:
            return None
        return cleaned.title()

    @staticmethod
    def _is_invalid_name_candidate(candidate: str) -> bool:
        lowered = " ".join(str(candidate or "").strip().lower().split())
        if not lowered:
            return True
        invalid_prefixes = ("a ", "an ", "the ", "into ", "interested ", "working ", "building ", "trying ")
        invalid_terms = {
            "automation",
            "backend",
            "bot",
            "developer",
            "engineer",
            "frontend",
            "project",
            "software",
            "student",
            "system",
            "testing",
        }
        if lowered in ACKNOWLEDGEMENT_NAMES or lowered in {"hello", "hi", "hey", "yo"}:
            return True
        words = lowered.split()
        if any(word in ACKNOWLEDGEMENT_NAMES for word in words):
            return True
        if lowered.startswith(invalid_prefixes):
            return True
        return any(word in invalid_terms for word in words)

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
                if field == "profession" and value.lower().startswith(
                    ("building ", "working ", "interested ", "trying ", "into ")
                ):
                    continue
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

    async def _build_compact_summary(self, contact_id: int, chat_id: str, message_count: int) -> tuple[str, list[str]]:
        session_row = (
            await self.session.execute(
                select(ConversationSession.summary, ConversationSession.last_intent)
                .where(ConversationSession.chat_id == chat_id)
                .limit(1)
            )
        ).one_or_none()
        session_summary = session_row[0] if session_row else ""
        last_intent = session_row[1] if session_row else None
        timeline = await self.search_timeline(contact_id, limit=5)
        topics = self._unique_strings([row.topic for row in timeline] + ([last_intent] if last_intent else []))

        parts = [f"Conversation reached {message_count} messages."]
        if topics:
            parts.append("Recent topics: " + "; ".join(topics[:6]) + ".")
        if timeline:
            compact_timeline = " | ".join(
                f"{row.topic}: {row.summary[:140].rstrip()}" for row in timeline[:4]
            )
            parts.append("Timeline: " + compact_timeline)
        if session_summary:
            parts.append("Session notes: " + session_summary[-900:].lstrip())
        return " ".join(parts)[:1800], topics

    @staticmethod
    def normalize_relationship_type(value: str | None) -> str:
        if not value:
            return RelationshipType.UNKNOWN.value
        normalized = normalize_text(value).replace(" ", "_")
        if normalized in RELATIONSHIP_TYPES:
            return normalized
        return MemoryService._relationship_type_from_text(value) or RelationshipType.UNKNOWN.value

    @staticmethod
    def parse_summary_thresholds(value: str | Sequence[int] | None) -> tuple[int, ...]:
        if value is None:
            return DEFAULT_SUMMARY_THRESHOLDS
        if isinstance(value, str):
            raw_items: Sequence[str | int] = [item.strip() for item in value.split(",")]
        else:
            raw_items = value
        thresholds: set[int] = set()
        for item in raw_items:
            try:
                threshold = int(item)
            except (TypeError, ValueError):
                continue
            if threshold > 0:
                thresholds.add(threshold)
        return tuple(sorted(thresholds)) or DEFAULT_SUMMARY_THRESHOLDS

    @staticmethod
    def _relationship_type_from_text(value: str | None) -> str | None:
        if not value:
            return None
        text = normalize_text(value)
        if any(word in text for word in ("friend", "buddy", "pal")):
            return RelationshipType.FRIEND.value
        if any(word in text for word in ("brother", "sister", "cousin", "parent", "father", "mother", "family")):
            return RelationshipType.FAMILY.value
        if any(word in text for word in ("colleague", "coworker", "co-worker", "teammate", "partner")):
            return RelationshipType.COLLEAGUE.value
        if any(word in text for word in ("customer", "client", "buyer", "subscriber")):
            return RelationshipType.CUSTOMER.value
        if any(word in text for word in ("community", "member", "follower", "student")):
            return RelationshipType.COMMUNITY_MEMBER.value
        return None

    @staticmethod
    def _build_timeline_payload(user_text: str, decision: str) -> dict[str, Any] | None:
        cleaned = " ".join(user_text.strip().split())
        normalized = normalize_text(cleaned)
        if not cleaned or cleaned.startswith("/") or MemoryService._is_greeting(cleaned):
            return None
        if len(cleaned) < 18 and "?" not in cleaned:
            return None

        topic = MemoryService._infer_topic(cleaned)
        score = 0.45
        if "?" in cleaned or normalized.startswith(("how ", "what ", "why ", "can ", "could ", "should ")):
            score += 0.2
        if any(word in normalized for word in ("datacube", "zina", "zinax", "moxiz", "vps", "deploy", "server", "internship")):
            score += 0.2
        if len(cleaned) > 120:
            score += 0.1
        score = min(score, 1.0)
        if score < 0.5:
            return None

        if "?" in cleaned:
            summary = f"Asked about {topic}."
        elif normalized.startswith(("please ", "can you ", "could you ", "help me ")):
            summary = f"Requested help with {topic}."
        else:
            summary = f"Discussed {topic}."
        return {
            "topic": topic,
            "summary": f"{summary} User message: {cleaned[:220]}",
            "importance_score": score,
            "decision": decision,
        }

    @staticmethod
    def _infer_topic(text: str) -> str:
        normalized = normalize_text(text)
        if "datacube" in normalized:
            return "Datacube AU"
        if "zinax" in normalized:
            return "ZinaX"
        if "zina" in normalized:
            return "Zina"
        if "moxiz" in normalized:
            return "Moxiz Gateway"
        if "internship" in normalized and "cyber" in normalized:
            return "cybersecurity internships"
        if "internship" in normalized:
            return "internships"
        if "vps" in normalized or "deploy" in normalized:
            return "VPS deployment"
        if "linux" in normalized and "server" in normalized:
            return "Linux server setup"
        if "cyber" in normalized:
            return "cybersecurity"
        words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+'-]*", text)
        return " ".join(words[:6]).strip() or "general conversation"

    @staticmethod
    def infer_topic_label(text: str) -> str:
        return MemoryService._infer_topic(text)

    @staticmethod
    def _is_greeting(text: str) -> bool:
        normalized = normalize_text(text)
        return normalized in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}

    @staticmethod
    def _is_continuation_prompt(text: str) -> bool:
        normalized = normalize_text(text)
        if MemoryService._is_greeting(text):
            return True
        phrases = (
            "continue",
            "last time",
            "previous conversation",
            "where were we",
            "what were we talking",
            "what did we discuss",
            "remind me",
            "pick up",
        )
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _asks_for_last_discussion(text: str) -> bool:
        normalized = normalize_text(text)
        return any(
            phrase in normalized
            for phrase in ("last time", "previous conversation", "what were we", "what did we", "remind me")
        )

    @staticmethod
    def _latest_discussion_label(package: MemoryContextPackage) -> str | None:
        if package.timeline_entries:
            entry = package.timeline_entries[0]
            return str(entry.get("topic") or entry.get("summary") or "").strip()
        if package.summaries:
            topics = package.summaries[0].get("topics") or []
            if topics:
                return str(topics[0])
            return str(package.summaries[0].get("summary") or "")[:120].strip()
        return None

    @staticmethod
    def _profile_dict(memory: UserMemory | None, contact_id: int) -> dict[str, Any]:
        if not memory:
            return {}
        display_name = getattr(memory, "display_name", None) or memory.user_name
        return {
            "contact_id": contact_id,
            "display_name": display_name,
            "user_name": memory.user_name,
            "relationship_type": getattr(memory, "relationship_type", RelationshipType.UNKNOWN.value)
            or RelationshipType.UNKNOWN.value,
            "relationship": memory.relationship,
            "interests": memory.interests,
            "goals": memory.goals,
            "projects": memory.projects,
            "preferences": memory.preferences,
            "personality_notes": getattr(memory, "personality_notes", None),
            "global_chat_enabled": getattr(memory, "global_chat_enabled", False),
            "last_interaction_at": getattr(memory, "last_interaction_at", None),
            "first_seen_at": getattr(memory, "first_seen_at", None),
        }

    @staticmethod
    def _timeline_dict(row: ConversationTimeline) -> dict[str, Any]:
        return {
            "id": row.id,
            "contact_id": row.contact_id,
            "timestamp": row.timestamp,
            "topic": row.topic,
            "summary": row.summary,
            "importance_score": row.importance_score,
            "source": row.source,
        }

    @staticmethod
    def _summary_dict(row: ConversationSummary) -> dict[str, Any]:
        return {
            "id": row.id,
            "contact_id": row.contact_id,
            "summary": row.summary,
            "topics": row.topics or [],
            "message_count": row.message_count,
            "threshold": row.threshold,
            "source": row.source,
            "created_at": row.created_at,
        }

    @staticmethod
    def _build_context_text(
        profile: dict[str, Any],
        timeline_entries: list[dict[str, Any]],
        summaries: list[dict[str, Any]],
    ) -> str:
        lines: list[str] = []
        display_name = profile.get("display_name") or profile.get("user_name")
        if display_name:
            lines.append(f"User: {display_name}")
        if profile.get("relationship_type"):
            lines.append(f"Relationship: {profile['relationship_type']}")
        if profile.get("relationship"):
            lines.append(f"Relationship note: {profile['relationship']}")
        for label, key in (
            ("Interests", "interests"),
            ("Goals", "goals"),
            ("Projects", "projects"),
            ("Preferences", "preferences"),
            ("Personality notes", "personality_notes"),
        ):
            values = MemoryService._split_memory_values(profile.get(key))
            if values:
                lines.append(f"{label}:")
                lines.extend(f"- {value}" for value in values[:6])
        if timeline_entries:
            lines.append("Recent Topics:")
            for entry in timeline_entries[:4]:
                lines.append(f"- {entry['topic']}: {entry['summary'][:180]}")
        if summaries:
            lines.append("Conversation Summaries:")
            for summary in summaries[:2]:
                topics = summary.get("topics") or []
                topic_text = f" ({', '.join(topics[:4])})" if topics else ""
                lines.append(f"- {summary['summary'][:220]}{topic_text}")
        return "\n".join(lines)[:2400]

    @staticmethod
    def _split_memory_values(value: str | None) -> list[str]:
        if not value:
            return []
        parts = re.split(r";|\n|,\s+(?=[A-Za-z])", value)
        return [part.strip(" -") for part in parts if part.strip(" -")]

    @staticmethod
    def _unique_strings(values: Sequence[str | None]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for value in values:
            if not value:
                continue
            cleaned = str(value).strip()
            key = normalize_text(cleaned)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(cleaned)
        return unique
