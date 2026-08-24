from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Contact
from app.utils.text import normalize_text


@dataclass(frozen=True, slots=True)
class ContactCandidate:
    contact_id: int
    whatsapp_id: str
    display_name: str | None
    contact_name: str | None
    push_name: str | None
    normalized_phone: str | None
    score: float
    matched_field: str
    matched_value: str


class ContactIntelligenceService:
    """Resolve owner-facing contact references against the existing contacts source of truth.

    This service deliberately does not create another address book. It ranks the identity
    evidence already persisted on ``Contact`` and returns provenance so callers can decide
    whether to execute an action or ask for disambiguation.
    """

    RESOLVE_THRESHOLD = 0.82
    AMBIGUITY_MARGIN = 0.08

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve(self, query: str, *, limit: int = 5) -> dict[str, Any]:
        cleaned = self._clean_query(query)
        if not cleaned:
            return {"query": query, "status": "not_found", "confidence": 0.0, "match": None, "candidates": []}

        rows = (
            await self.session.execute(
                select(Contact)
                .order_by(Contact.updated_at.desc(), Contact.id.desc())
                .limit(5000)
            )
        ).scalars().all()

        candidates = [candidate for row in rows if (candidate := self._score_contact(row, cleaned)) is not None]
        candidates.sort(key=lambda item: (-item.score, item.contact_id))
        candidates = candidates[: max(1, min(limit, 20))]

        if not candidates:
            return {"query": query, "status": "not_found", "confidence": 0.0, "match": None, "candidates": []}

        best = candidates[0]
        runner_up = candidates[1].score if len(candidates) > 1 else 0.0
        margin = best.score - runner_up
        resolved = best.score >= self.RESOLVE_THRESHOLD and (len(candidates) == 1 or margin >= self.AMBIGUITY_MARGIN)

        return {
            "query": query,
            "status": "resolved" if resolved else "ambiguous",
            "confidence": round(best.score, 3),
            "margin": round(margin, 3),
            "match": self._serialize(best) if resolved else None,
            "candidates": [self._serialize(item) for item in candidates],
        }

    @classmethod
    def _score_contact(cls, contact: Contact, query: str) -> ContactCandidate | None:
        query_text = normalize_text(query)
        query_digits = cls._digits(query)
        evidence: list[tuple[float, str, str]] = []

        exact_identity_fields = (
            ("whatsapp_id", contact.whatsapp_id),
            ("chat_id", contact.chat_id),
            ("waha_contact_id", contact.waha_contact_id),
            ("waha_participant_id", contact.waha_participant_id),
        )
        for field, value in exact_identity_fields:
            if not value:
                continue
            normalized_value = normalize_text(str(value))
            if query_text == normalized_value:
                evidence.append((1.0, field, str(value)))
            elif query_digits and query_digits == cls._digits(str(value)):
                evidence.append((0.995, field, str(value)))

        phone_fields = (
            ("normalized_phone", contact.normalized_phone),
            ("whatsapp_phone", contact.whatsapp_phone),
        )
        for field, value in phone_fields:
            if value and query_digits and query_digits == cls._digits(str(value)):
                evidence.append((0.99, field, str(value)))

        name_fields = (
            ("contact_name", contact.contact_name, 0.97),
            ("display_name", contact.display_name, 0.95),
            ("push_name", contact.push_name, 0.90),
        )
        for field, value, exact_score in name_fields:
            if value:
                score = cls._name_score(query_text, normalize_text(str(value)), exact_score)
                if score:
                    evidence.append((score, field, str(value)))

        identity = contact.identity_json if isinstance(contact.identity_json, dict) else {}
        aliases = identity.get("aliases") if isinstance(identity, dict) else None
        if isinstance(aliases, list):
            for alias in aliases:
                if not isinstance(alias, str) or not alias.strip():
                    continue
                score = cls._name_score(query_text, normalize_text(alias), 0.93)
                if score:
                    evidence.append((score, "identity_json.aliases", alias))

        if not evidence:
            return None

        score, matched_field, matched_value = max(evidence, key=lambda item: item[0])
        return ContactCandidate(
            contact_id=contact.id,
            whatsapp_id=contact.whatsapp_id,
            display_name=contact.display_name,
            contact_name=contact.contact_name,
            push_name=contact.push_name,
            normalized_phone=contact.normalized_phone,
            score=score,
            matched_field=matched_field,
            matched_value=matched_value,
        )

    @staticmethod
    def _name_score(query: str, candidate: str, exact_score: float) -> float | None:
        if not query or not candidate:
            return None
        if query == candidate:
            return exact_score
        if len(query) >= 4 and (candidate.startswith(query + " ") or query.startswith(candidate + " ")):
            return min(exact_score - 0.10, 0.86)
        if len(query) >= 4 and query in candidate:
            return min(exact_score - 0.13, 0.84)

        query_tokens = {token for token in query.split() if len(token) >= 3}
        candidate_tokens = {token for token in candidate.split() if len(token) >= 3}
        if query_tokens and candidate_tokens:
            overlap = len(query_tokens & candidate_tokens) / len(query_tokens | candidate_tokens)
            if overlap >= 0.75:
                return 0.80
        return None

    @staticmethod
    def _clean_query(value: str) -> str:
        cleaned = (value or "").strip()
        if cleaned.startswith("@"): 
            cleaned = cleaned[1:]
        return cleaned.strip()

    @staticmethod
    def _digits(value: str) -> str:
        return re.sub(r"\D+", "", value or "")

    @staticmethod
    def _serialize(candidate: ContactCandidate) -> dict[str, Any]:
        return {
            "contact_id": candidate.contact_id,
            "whatsapp_id": candidate.whatsapp_id,
            "display_name": candidate.display_name,
            "contact_name": candidate.contact_name,
            "push_name": candidate.push_name,
            "normalized_phone": candidate.normalized_phone,
            "confidence": round(candidate.score, 3),
            "matched_field": candidate.matched_field,
            "matched_value": candidate.matched_value,
        }
