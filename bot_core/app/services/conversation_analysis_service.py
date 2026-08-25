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
    summary topics and scheduled actions. A later LLM layer may enrich this projection,
    but it must preserve these source references and deterministic authority boundaries.
    """

    SCHEMA_VERSION = "zina.chat.analysis.v1"
    MAX_COMMITMENTS = 25
    MAX_TOPICS = 12
    MAX_FOLLOW_UPS = 25

    _COMMITMENT_PATTERNS = (
        re.compile(r"\b(?:i will|i'll|i can|i shall|i promise(?: to)?)\s+(.+)", re.IGNORECASE),
        re.compile(r"\blet me\s+(.+)", re.IGNORECASE),
    )

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
        topics = cls._recurring_topics(summaries)
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
                "Commitments are reported only when Fabian's delivered outbound text contains an explicit first-person commitment phrase.",
                "Recurring topics come from existing Memory Engine summary topic labels; this slice does not infer new semantic topics.",
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
            for pattern in cls._COMMITMENT_PATTERNS:
                match = pattern.search(normalized)
                if not match:
                    continue
                statement = match.group(0).strip().rstrip(" .")
                items.append(
                    {
                        "text": statement[:300],
                        "source_message_id": message.get("id"),
                        "created_at": message.get("created_at"),
                        "evidence_text": normalized[:400],
                    }
                )
                break
            if len(items) >= cls.MAX_COMMITMENTS:
                break
        return items

    @classmethod
    def _recurring_topics(cls, summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        ranked = sorted(counts, key=lambda key: (-counts[key], labels[key].casefold()))
        return [
            {
                "topic": labels[key],
                "summary_count": counts[key],
                "source_summary_ids": evidence.get(key, [])[:10],
            }
            for key in ranked[: cls.MAX_TOPICS]
        ]

    @staticmethod
    def _important_dates(scheduled_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for action in scheduled_actions:
            scheduled_for = action.get("scheduled_for")
            if scheduled_for is None:
                continue
            items.append(
                {
                    "scheduled_action_id": action.get("id"),
                    "action_type": action.get("action_type"),
                    "status": action.get("status"),
                    "scheduled_for": scheduled_for,
                    "timezone": action.get("timezone"),
                    "source_message_id": action.get("source_message_id"),
                }
            )
        return items[:25]

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
