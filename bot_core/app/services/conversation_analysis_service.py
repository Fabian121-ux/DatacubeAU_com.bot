from __future__ import annotations

from collections import Counter
from datetime import datetime
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation_export_service import ConversationExportService


class ConversationAnalysisService:
    """Derive conservative, evidence-linked conversation analysis from `zina.chat.v1`.

    This slice intentionally does not call an LLM. It only derives conclusions that can
    be traced to explicit export evidence: open loops, direct first-person commitments,
    summary-topic labels corroborated by delivered DM history, and scheduled actions.
    A later LLM layer may enrich this projection, but it must preserve source references
    and deterministic authority boundaries.
    """

    SCHEMA_VERSION = "zina.chat.analysis.v1"
    MAX_COMMITMENTS = 25
    MAX_TOPICS = 12
    MAX_FOLLOW_UPS = 25
    MAX_IMPORTANT_DATES = 25
    ACTIVE_ACTION_STATUSES = frozenset(ConversationExportService.ACTIVE_ACTION_STATUSES)

    _COMMITMENT_START = re.compile(
        r"\b(?:i will\b|i(?:'|’)ll\b|i can(?!['’]t\b)(?!\s+not\b)\b|i shall\b|"
        r"i promise(?:\s+to)?\b|let me\s+(?!(?:know|see)\b)(?:send|check|call|share|"
        r"handle|review|prepare|forward|bring|pay|book|arrange|fix|update|confirm|look|"
        r"follow\s+up|take\s+care\s+of|sort\s+out)\b)",
        re.IGNORECASE,
    )
    _TRAILING_CONJUNCTION = re.compile(r"(?:,?\s+(?:and|then))\s*$", re.IGNORECASE)
    _WORD_RE = re.compile(r"(?<!\w)(?:\.[A-Za-z]\w*|\w+(?:\+\+|#)?)", re.UNICODE)
    _DOTTED_ABBREVIATION = re.compile(r"(?:\b[A-Za-z]\.)+[A-Za-z]$")
    _QUEUE_DELIVERY_ID = re.compile(r"^outbound_queue:(\d+)(?::delivery:\d+)?$")

    def __init__(self, session: AsyncSession):
        self.session = session
        self.exporter = ConversationExportService(session)

    async def analyze(
        self,
        *,
        contact_reference: str,
        limit: int = 200,
        after: datetime | None = None,
        before: datetime | None = None,
        requested_by_contact_id: int | None = None,
    ) -> dict[str, Any]:
        export = await self.exporter.export(
            contact_reference=contact_reference,
            limit=limit,
            after=after,
            before=before,
            requested_by_contact_id=requested_by_contact_id,
        )
        analysis = self.derive(export)
        conversation = export["conversation"]
        observed_window = conversation["window"]
        return {
            "schema_version": self.SCHEMA_VERSION,
            "conversation_schema_version": export["schema_version"],
            "contact": export["contact"],
            "window": {
                "limit": conversation.get("limit"),
                "after": conversation.get("after"),
                "before": conversation.get("before"),
                "oldest_at": observed_window.get("oldest_at"),
                "newest_at": observed_window.get("newest_at"),
            },
            "message_count": conversation["message_count"],
            "analysis": analysis,
            "provenance": {
                "conversation_export": export["schema_version"],
                "analysis_method": "deterministic_evidence_projection",
                "llm_used": False,
                "source_ids_are_required": True,
            },
        }

    @classmethod
    def derive(cls, export: dict[str, Any]) -> dict[str, Any]:
        messages = export.get("conversation", {}).get("messages") or []
        open_loops = export.get("open_loops") or []
        summaries = export.get("memory", {}).get("summaries") or []
        scheduled_actions = export.get("zina_activity", {}).get("scheduled_actions") or []

        unresolved = [
            {
                "open_loop_id": row.get("id"),
                "type": row.get("type"),
                "text": row.get("text"),
                "source_message_id": row.get("source_message_id"),
                "last_message_id": row.get("last_message_id"),
                "updated_at": row.get("updated_at"),
            }
            for row in open_loops[: cls.MAX_FOLLOW_UPS]
        ]

        commitments = cls._commitments(messages)
        topics = cls._recurring_topics(summaries, messages)
        important_dates = cls._important_dates(scheduled_actions)
        follow_ups = cls._recommended_follow_ups(open_loops, scheduled_actions)

        return {
            "status": "generated",
            "method": "deterministic_evidence_projection",
            "unresolved_matters": unresolved,
            "explicit_commitments": commitments,
            "recurring_topics": topics,
            "important_dates": important_dates,
            "recommended_follow_ups": follow_ups,
            "limitations": [
                "Commitments are reported only when Fabian's delivered outbound text contains a bounded explicit first-person commitment clause outside quoted speech.",
                "Recurring topics use existing Memory Engine summary labels only when at least two distinct delivered DM messages independently corroborate the label.",
                "Recommended follow-ups are projections of unresolved open loops and active scheduled actions, not autonomous advice.",
                "No LLM is used in this analysis version.",
            ],
        }

    @classmethod
    def _commitments(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # A resend is another delivery event, not another authored promise. Keep the
        # newest delivery evidence for each logical outbound queue row so one promise
        # cannot occupy multiple commitment slots.
        logical_messages: dict[str, tuple[tuple[str, int], dict[str, Any]]] = {}
        for index, message in enumerate(messages):
            if message.get("direction") != "outbound":
                continue
            text = str(message.get("text") or "").strip()
            if not text:
                continue
            message_id = message.get("id")
            logical_key = cls._logical_message_key(message_id) if message_id is not None else f"anonymous:{index}"
            sort_key = (cls._datetime_sort_key(message.get("created_at")), index)
            existing = logical_messages.get(logical_key)
            if existing is None or sort_key >= existing[0]:
                logical_messages[logical_key] = (sort_key, message)

        ordered_messages = [
            row[1]
            for row in sorted(
                logical_messages.values(),
                key=lambda row: row[0],
            )
        ]

        items: list[dict[str, Any]] = []
        for message in ordered_messages:
            normalized = " ".join(str(message.get("text") or "").split())
            for statement, start, end in cls._commitment_clause_spans(normalized):
                items.append(
                    {
                        "text": statement[:300],
                        "source_message_id": message.get("id"),
                        "created_at": message.get("created_at"),
                        "evidence_text": cls._evidence_text(normalized, start=start, end=end),
                    }
                )

        # Keep the most current promises when the bounded evidence window contains more
        # than MAX_COMMITMENTS clauses, but preserve chronological presentation.
        return items[-cls.MAX_COMMITMENTS :]

    @classmethod
    def _commitment_clauses(cls, text: str) -> list[str]:
        return [statement for statement, _, _ in cls._commitment_clause_spans(text)]

    @classmethod
    def _commitment_clause_spans(cls, text: str) -> list[tuple[str, int, int]]:
        quoted_spans = cls._quoted_spans(text)
        starts = [match for match in cls._COMMITMENT_START.finditer(text) if not cls._in_spans(match.start(), quoted_spans)]
        clauses: list[tuple[str, int, int]] = []
        for index, match in enumerate(starts):
            start = match.start()
            candidate_ends = [starts[index + 1].start()] if index + 1 < len(starts) else []
            sentence_end = cls._find_sentence_end(text, match.end())
            if sentence_end is not None:
                candidate_ends.append(sentence_end)
            end = min(candidate_ends) if candidate_ends else len(text)
            statement = text[start:end].strip(" \t\r\n,.:;!?")
            statement = cls._TRAILING_CONJUNCTION.sub("", statement).strip(" \t\r\n,.:;!?")
            if statement:
                statement_end = start + len(text[start:end].rstrip(" \t\r\n,.:;!?"))
                clauses.append((statement, start, statement_end))
        return clauses

    @classmethod
    def _find_sentence_end(cls, text: str, start: int) -> int | None:
        for index in range(start, len(text)):
            char = text[index]
            if char in "!?;":
                return index
            if char != ".":
                continue
            previous = text[index - 1] if index > 0 else ""
            following = text[index + 1] if index + 1 < len(text) else ""
            if previous.isalnum() and following.isalnum():
                continue
            prefix = text[:index]
            if cls._DOTTED_ABBREVIATION.search(prefix):
                next_nonspace = next((c for c in text[index + 1 :] if not c.isspace()), "")
                if next_nonspace and next_nonspace.islower():
                    continue
            return index
        return None

    @staticmethod
    def _quoted_spans(text: str) -> list[tuple[int, int]]:
        spans: list[tuple[int, int]] = []
        for opener, closer in (("“", "”"), ('"', '"'), ("«", "»")):
            cursor = 0
            while cursor < len(text):
                start = text.find(opener, cursor)
                if start < 0:
                    break
                end = text.find(closer, start + len(opener))
                if end < 0:
                    spans.append((start, len(text)))
                    break
                spans.append((start, end + len(closer)))
                cursor = end + len(closer)
        return spans

    @staticmethod
    def _in_spans(index: int, spans: list[tuple[int, int]]) -> bool:
        return any(start <= index < end for start, end in spans)

    @staticmethod
    def _evidence_text(text: str, *, start: int, end: int, limit: int = 400) -> str:
        if len(text) <= limit:
            return text
        required_end = min(len(text), max(end, start + 300))
        required_length = min(limit, max(0, required_end - start))
        prefix_budget = max(0, limit - required_length)
        window_start = max(0, start - min(80, prefix_budget))
        window_end = min(len(text), window_start + limit)
        if window_end < required_end:
            window_end = required_end
            window_start = max(0, window_end - limit)
        return text[window_start:window_end]

    @classmethod
    def _recurring_topics(
        cls,
        summaries: list[dict[str, Any]],
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        counts: Counter[str] = Counter()
        evidence: dict[str, list[int | str]] = {}
        labels: dict[str, str] = {}
        for summary in summaries:
            summary_id = summary.get("id")
            unique_topics: dict[str, str] = {}
            for raw_topic in summary.get("topics") or []:
                topic = " ".join(str(raw_topic).split()).strip()
                key = topic.casefold()
                if key:
                    unique_topics.setdefault(key, topic)
            for key, topic in unique_topics.items():
                counts[key] += 1
                labels.setdefault(key, topic)
                if summary_id is not None:
                    evidence.setdefault(key, []).append(summary_id)

        dm_evidence: dict[str, list[int | str]] = {}
        for key, label in labels.items():
            matched_by_logical_message: dict[str, int | str] = {}
            for message in messages:
                message_id = message.get("id")
                text = str(message.get("text") or "")
                if message_id is None or not text:
                    continue
                if cls._topic_matches_text(label, text):
                    logical_key = cls._logical_message_key(message_id)
                    matched_by_logical_message.setdefault(logical_key, message_id)
            dm_evidence[key] = list(matched_by_logical_message.values())

        ranked = sorted(
            (
                key
                for key in counts
                if counts[key] > 1 and len(dm_evidence.get(key, [])) > 1
            ),
            key=lambda key: (-counts[key], -len(dm_evidence[key]), labels[key].casefold()),
        )
        return [
            {
                "topic": labels[key],
                "summary_count": counts[key],
                "dm_message_count": len(dm_evidence[key]),
                "source_summary_ids": evidence.get(key, []),
                "source_message_ids": dm_evidence[key],
            }
            for key in ranked[: cls.MAX_TOPICS]
        ]

    @classmethod
    def _logical_message_key(cls, message_id: int | str) -> str:
        value = str(message_id)
        match = cls._QUEUE_DELIVERY_ID.fullmatch(value)
        if match:
            return f"outbound_queue:{match.group(1)}"
        return f"message:{value}"

    @classmethod
    def _topic_matches_text(cls, topic: str, text: str) -> bool:
        topic_tokens = [token.casefold() for token in cls._WORD_RE.findall(topic) if token]
        text_tokens = [token.casefold() for token in cls._WORD_RE.findall(text) if token]
        if not topic_tokens or not text_tokens:
            return False
        if len(topic_tokens) == 1:
            return topic_tokens[0] in set(text_tokens)
        width = len(topic_tokens)
        return any(text_tokens[index : index + width] == topic_tokens for index in range(len(text_tokens) - width + 1))

    @classmethod
    def _important_dates(cls, scheduled_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        eligible = [
            action
            for action in scheduled_actions
            if action.get("scheduled_for") is not None
            and str(action.get("status") or "").lower() in cls.ACTIVE_ACTION_STATUSES
        ]
        eligible.sort(
            key=lambda action: (
                cls._datetime_sort_key(action.get("scheduled_for")),
                str(action.get("id") or ""),
            )
        )
        return [
            {
                "scheduled_action_id": action.get("id"),
                "action_type": action.get("action_type"),
                "status": action.get("status"),
                "scheduled_for": action.get("scheduled_for"),
                "timezone": action.get("timezone"),
                "source_message_id": action.get("source_message_id"),
            }
            for action in eligible[: cls.MAX_IMPORTANT_DATES]
        ]

    @staticmethod
    def _datetime_sort_key(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value or "")

    @classmethod
    def _recommended_follow_ups(
        cls,
        open_loops: list[dict[str, Any]],
        scheduled_actions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in open_loops:
            items.append(
                {
                    "kind": "open_loop",
                    "text": row.get("text"),
                    "source_open_loop_id": row.get("id"),
                    "source_message_id": row.get("source_message_id"),
                }
            )
            if len(items) >= cls.MAX_FOLLOW_UPS:
                return items

        for action in scheduled_actions:
            if str(action.get("status") or "").lower() not in cls.ACTIVE_ACTION_STATUSES:
                continue
            items.append(
                {
                    "kind": "scheduled_action",
                    "text": f"Review scheduled {action.get('action_type') or 'action'}.",
                    "source_scheduled_action_id": action.get("id"),
                    "source_message_id": action.get("source_message_id"),
                    "scheduled_for": action.get("scheduled_for"),
                    "status": action.get("status"),
                }
            )
            if len(items) >= cls.MAX_FOLLOW_UPS:
                break
        return items
