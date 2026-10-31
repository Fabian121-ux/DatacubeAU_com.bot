from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from app.utils.text import normalize_text


class MessageIntent(StrEnum):
    GREETING = "greeting"
    QUESTION = "question"
    FOLLOW_UP = "follow_up"
    COMMAND = "command"
    OWNER_COMMAND = "owner_command"
    SEARCH_REQUEST = "search_request"
    IDENTITY_QUESTION = "identity_question"
    OPINION_REQUEST = "opinion_request"
    MEMORY_RECALL = "memory_recall"
    SMALL_TALK = "small_talk"
    GENERAL_KNOWLEDGE = "general_knowledge"
    STATEMENT = "statement"


@dataclass(slots=True)
class IntentResult:
    intent: MessageIntent
    confidence: float
    reason: str


class IntentClassifier:
    """Cheap deterministic intent pass that runs before retrieval routing."""

    OWNER_COMMANDS = {
        "/remember",
        "/forget",
        "/memory-search",
        "/recent-memory",
        "/teach",
        "/create-command",
        "/edit-command",
        "/delete-command",
        "/groups",
        "/communities",
        "/my-groups",
        "/my-communities",
        "/group-info",
        "/find-group",
        "/inventory",
        "/group-sync",
        "/tag-group",
        "/group-notes",
        "/group-update",
        "/user",
        "/timeline",
        "/summary",
        "/force",
        "/unforce",
        "/trigger",
        "/broadcast",
        "/broadcast-groups",
        "/broadcast-users",
        "/system",
        "/storage",
        "/logs",
        "/errors",
        "/queue",
        "/reviews",
        "/stopbot",
        "/startbot",
        "/maintenance",
        "/mentiononly",
        "/enable-ai",
        "/disable-ai",
        "/top-users",
        "/top-questions",
        "/ai-usage",
        "/memory-stats",
        "/internet",
        "/web",
        "/internet-status",
        "/internet-usage",
        "/whoami",
        "/owner-help",
    }
    SEARCH_COMMANDS = {"!search", "!google", "!news", "!weather", "!currency", "!youtube", "!image", "!sticker", "!gif"}

    @classmethod
    def classify(cls, text_value: str) -> IntentResult:
        stripped = (text_value or "").strip()
        normalized = normalize_text(stripped)
        if not normalized:
            return IntentResult(MessageIntent.STATEMENT, 0.2, "empty message")

        first = stripped.split(maxsplit=1)[0].lower()
        if first in cls.OWNER_COMMANDS:
            return IntentResult(MessageIntent.OWNER_COMMAND, 0.99, "known owner command")
        if first.startswith("/"):
            return IntentResult(MessageIntent.COMMAND, 0.95, "slash command")
        if first in cls.SEARCH_COMMANDS:
            return IntentResult(MessageIntent.SEARCH_REQUEST, 0.99, "explicit search command")
        if first.startswith("!"):
            return IntentResult(MessageIntent.COMMAND, 0.9, "bang command")

        if cls.is_greeting(normalized):
            return IntentResult(MessageIntent.GREETING, 0.96, "short greeting")
        if cls._is_memory_recall(normalized):
            return IntentResult(MessageIntent.MEMORY_RECALL, 0.94, "memory recall wording")
        if cls._is_identity_question(normalized):
            return IntentResult(MessageIntent.IDENTITY_QUESTION, 0.96, "identity wording")
        if cls._is_follow_up(normalized):
            return IntentResult(MessageIntent.FOLLOW_UP, 0.82, "continuation wording")
        if cls._is_opinion_request(normalized):
            return IntentResult(MessageIntent.OPINION_REQUEST, 0.84, "opinion wording")
        if cls._is_small_talk(normalized):
            return IntentResult(MessageIntent.SMALL_TALK, 0.84, "small talk wording")
        if cls._is_live_search_request(normalized):
            return IntentResult(MessageIntent.SEARCH_REQUEST, 0.78, "live information wording")
        if cls._is_general_knowledge(normalized):
            return IntentResult(MessageIntent.GENERAL_KNOWLEDGE, 0.76, "conceptual knowledge wording")
        if cls._is_question(normalized):
            return IntentResult(MessageIntent.QUESTION, 0.74, "question wording")
        return IntentResult(MessageIntent.STATEMENT, 0.5, "default statement")

    @staticmethod
    def is_greeting(normalized_text: str) -> bool:
        words = normalized_text.split()
        if normalized_text in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}:
            return True
        if len(words) <= 4 and words[0] in {"hi", "hello", "hey"}:
            return True
        return False

    @staticmethod
    def _is_identity_question(normalized: str) -> bool:
        phrases = (
            "what is your name",
            "whats your name",
            "who are you",
            "who created you",
            "who built you",
            "why were you created",
            "why do you exist",
            "what are you",
            "who is fabian",
            "who created zina",
            "what projects does fabian have",
            "fabian projects",
            "who owns datacube",
            "who owns datacube au",
            "who founded datacube",
            "who founded datacube au",
        )
        if any(phrase in normalized for phrase in phrases):
            return True
        return bool(re.search(r"\b(?:what|who)\s+(?:is|are)\s+(?:zina|datacube au|datacube|zinax|moxiz)\b", normalized))

    @staticmethod
    def _is_memory_recall(normalized: str) -> bool:
        phrases = (
            "what is my name",
            "whats my name",
            "do you know my name",
            "remember my name",
            "who am i",
            "what do you remember about me",
            "what do you know about me",
            "my profile",
            "my interests",
            "my goals",
            "my projects",
            "my preferences",
            "last discussion",
            "last conversation",
            "previous discussion",
            "previous conversation",
            "what did we discuss",
            "what were we talking",
            "summarize our",
        )
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _is_follow_up(normalized: str) -> bool:
        if normalized in {"why", "how", "when", "where", "which one", "compare them", "what about it"}:
            return True
        if re.match(r"^(what about|how about|and|but|also|then)\b", normalized):
            return True
        if re.search(r"\b(it|that|this|they|them|those|he|she|his|her)\b", normalized) and len(normalized.split()) <= 9:
            return True
        return bool(re.match(r"^(who owns it|who built it|how much|cost|price|ram|storage|performance)\b", normalized))

    @staticmethod
    def _is_opinion_request(normalized: str) -> bool:
        phrases = ("what do you think", "your opinion", "do you think", "should i", "would you recommend")
        return any(phrase in normalized for phrase in phrases)

    @staticmethod
    def _is_small_talk(normalized: str) -> bool:
        phrases = ("how are you", "thank you", "thanks", "nice", "okay", "ok", "cool")
        return normalized in phrases or any(normalized.startswith(f"{phrase} ") for phrase in phrases)

    @staticmethod
    def _is_live_search_request(normalized: str) -> bool:
        live_terms = ("latest", "today", "current", "right now", "news", "weather", "exchange rate", "price of")
        return any(term in normalized for term in live_terms)

    @staticmethod
    def _is_general_knowledge(normalized: str) -> bool:
        starters = ("what is", "what are", "why is", "why are", "how does", "how do", "explain", "define")
        conceptual_terms = (
            "psychology",
            "humanity",
            "science",
            "history",
            "philosophy",
            "economics",
            "biology",
            "technology",
            "internet",
            "server",
            "vps",
            "security",
            "cybersecurity",
        )
        return normalized.startswith(starters) and any(term in normalized for term in conceptual_terms)

    @staticmethod
    def _is_question(normalized: str) -> bool:
        starters = (
            "what",
            "who",
            "when",
            "where",
            "why",
            "how",
            "can",
            "could",
            "should",
            "do",
            "does",
            "did",
            "is",
            "are",
            "will",
            "tell",
            "explain",
            "describe",
            "show",
            "give",
        )
        return normalized.endswith("?") or normalized.split(maxsplit=1)[0] in starters
