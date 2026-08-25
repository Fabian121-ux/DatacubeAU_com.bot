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

    _COMMITMENT_START = re.compile(
        r"\b(?:i will|i(?:'|’)ll|i can|i shall|i promise(?: to)?|"
        r"let me\s+(?!(?:know|see)\b)(?:send|check|call|share|handle|review|prepare|forward|"
        r"bring|pay|book|arrange|fix|update|confirm|look|follow\s+up|take\s+care\s+of|sort\s+out)\b)",
        re.IGNORECASE,
    )
    _SENTENCE_END = re.compile(r"[.!?;]+")
    _TRAILING_CONJUNCTION = re.compile(r"(?:,?\s+(?:and|then))\s*$", re.IGNORECASE)
    _WORD_RE = re.compile(r"[\w']+", re.UNICODE)

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
        return {
            "schema_version": self.SCHEMA_VERSION,
            "conversation_schema_version": export["schema_version"],
            "contact": export["contact"],
            "window": export["conversation"]["window"],
            "message_count": export["conversation"]["message_count"],
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
                "Commitments are reported only when Fabian's delivered outbound text contains a bounded explicit first-person commitment clause.",
                "Recurring topics use existing Memory Engine summary labels only when at least two delivered DM messages independently corroborate the label.",
                "Recommended follow-ups are projections of unresolved open loops and active scheduled actions, not autonomous advice.",
                "No LLM is used in this analysis version.",
            ],
        }

    @classmethod
    def _commitments(cls, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for message in messages:
            if message.get("direction") != "outbound":
                continue
            text = str(message.get("text") or "").strip()
            if not text:
                continue
            normalized = " ".join(text.split())
            for statement in cls._commitment_clauses(normalized):
                items.append(
                    {
                        "text": statement[:300],
                        "source_message_id": message.get("id"),
                        "created_at": message.get("created_at"),
                        "evidence_text": normalized[:400],
                    }
                )
                if len(items) >= cls.MAX_COMMITMENTS:
                    return items
        return items

    @classmethod
    def _commitment_clauses(cls, text: str) -> list[str]:
        starts = list(cls._COMMITMENT_START.finditer(text))
        clauses: list[str] = []
        for index, match in enumerate(starts):
            start = match.start()
            candidate_ends = [starts[index + 1].start()] if index + 1 < len(starts) else []
            sentence_end = cls._SENTENCE_END.search(text, match.end())
            if sentence_end:
                candidate_ends.append(sentence_end.start())
            end = min(candidate_ends) if candidate_ends else len(text)
            statement = text[start:end].strip(" \t\r\n,.:;!?")
            statement = cls._TRAILING_CONJUNCTION.sub("", statement).strip(" \t\r\n,.:;!?")
            if statement:
                clauses.append(statement)
        return clauses

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
            for raw_topic in summary.get("topics") or []:
                topic = " ".join(str(raw_topic).split()).strip()
                key = topic.casefold()
                if not key:
                    continue
                counts[key] += 1
                labels.setdefault(key, topic)
                if summary_id is not None:
                    evidence.setdefault(key, []).append(summary_id)

        dm_evidence: dict[str, list[int | str]] = {}
        for key, label in labels.items():
            matched_ids: list[int | str] = []
            for message in messages:
                message_id = message.get("id")
                text = str(message.get("text") or "")
                if message_id is None or not text:
                    continue
                if cls._topic_matches_text(label, text):
                    matched_ids.append(message_id)
            dm_evidence[key] = matched_ids

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
        active_statuses = {"scheduled", "pending", "queued", "retrying", "paused"}
        eligible = [
            action
            for action in scheduled_actions
            if action.get("scheduled_for") is not None
            and str(action.get("status") or "").lower() in active_statuses
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

        active_statuses = {"scheduled", "pending", "queued", "retrying", "paused"}
        for action in scheduled_actions:
            if str(action.get("status") or "").lower() not in active_statuses:
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
