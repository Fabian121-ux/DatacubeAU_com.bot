from __future__ import annotations

from dataclasses import dataclass
import difflib
import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import FAQEntry, FAQImportCandidate
from app.utils.hashing import sha256_text
from app.utils.text import normalize_text
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

FAQ_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:#{1,6}\s*)?Q(?:uestion)?\s*:\s*(.*?)\n(?:\s*V(?:ariations?)?\s*:\s*(.*?)\n)?\s*A(?:nswer)?\s*:\s*(.*?)(?=\n\s*(?:#{1,6}\s*)?Q(?:uestion)?\s*:|$)",
    re.IGNORECASE | re.DOTALL,
)

QUESTION_LINE_RE = re.compile(
    r"^(who|what|when|where|why|how|can|could|should|do|does|did|is|are|tell|explain|describe)\b",
    re.IGNORECASE,
)

FAQ_CATEGORIES = {
    "Identity",
    "Projects",
    "Datacube AU",
    "Zina",
    "ZinaX",
    "Commands",
    "Owner",
    "Knowledge",
    "Services",
    "Contact",
    "General",
    "Custom",
}

KNOWN_ENTITIES = {
    "zina": "Zina",
    "fabian": "Fabian",
    "datacube": "Datacube AU",
    "datacube au": "Datacube AU",
    "zinax": "ZinaX",
    "moxiz": "Moxiz Gateway",
}

TOKEN_SYNONYMS = {
    "u": "you",
    "ur": "your",
    "ya": "your",
    "whats": "what",
    "whoami": "who",
    "created": "create",
    "creator": "create",
    "creates": "create",
    "creating": "create",
    "made": "create",
    "make": "create",
    "makes": "create",
    "built": "create",
    "build": "create",
    "builds": "create",
    "developed": "create",
    "developer": "create",
    "owner": "own",
    "owns": "own",
    "owned": "own",
    "founded": "own",
    "founder": "own",
    "commands": "command",
    "helps": "help",
    "assistant": "bot",
    "yourself": "you",
}

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "can",
    "do",
    "does",
    "for",
    "have",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "you",
    "your",
}


@dataclass(slots=True)
class FAQPayload:
    question: str
    normalized_question: str
    dedupe_key: str
    answer: str
    category: str = "General"
    intent: str = "custom"
    question_variations: list[str] | None = None
    keywords: list[str] | None = None
    entities: list[str] | None = None
    confidence_threshold: float = 0.72


class FAQService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def parse_faq_text(self, raw_text: str) -> list[dict[str, Any]]:
        pairs = self._parse_labeled_faq(raw_text)
        if pairs:
            return pairs
        return self._parse_plain_faq(raw_text)

    async def sync_faq_in_db(self, pairs: list[tuple[str, str]]) -> int:
        return await self.replace_source_entries(
            pairs,
            source_id="core_faq",
            source_name="core_faq.md",
            source_version="legacy-sync",
        )

    async def replace_source_entries(
        self,
        pairs: list[dict[str, Any]] | list[tuple[str, str]],
        *,
        source_id: str,
        source_name: str,
        source_version: str | None = None,
    ) -> int:
        report = await self.replace_source_entries_report(
            pairs,
            source_id=source_id,
            source_name=source_name,
            source_version=source_version,
        )
        return int(report["active_entries"])

    async def replace_source_entries_report(self, pairs, *, source_id, source_name, source_version=None) -> dict[str, int | str]:
        if not pairs:
            raise ValueError("FAQ source did not contain any parseable entries.")
        from sqlalchemy.exc import IntegrityError
        version = source_version or self.version_for_pairs(pairs)
        source_hash = sha256_text("\n\n".join(f"{q}\n{a}" for q, a in pairs))
        count = created = updated = unchanged = duplicates = superseded = conflicted = failed = 0
        seen: set[str] = set()
        seen_questions: set[str] = set()
        active_ids: set[int] = set()

        for item in pairs:
            if isinstance(item, dict):
                question = item.get("question", "")
                answer = item.get("answer", "")
                variations = item.get("variations", [])
            else:
                question, answer = item
                variations = []
            
            payload = self.build_payload(question=question, answer=answer, question_variations=variations)
            dedupe_key = self._dedupe_key(payload)
            if dedupe_key in seen or payload.normalized_question in seen_questions:
                duplicates += 1
                continue
            seen.add(dedupe_key)
            seen_questions.add(payload.normalized_question)

            stmt = select(FAQEntry).where(FAQEntry.normalized_question == payload.normalized_question)
            existing = (await self.session.execute(stmt)).scalars().first()

            if existing:
                if getattr(existing, "source_id", source_id) != source_id:
                    conflicted += 1
                    continue

                is_unchanged = (
                    existing.question == payload.question and
                    existing.answer == payload.answer and
                    existing.category == payload.category and
                    existing.intent == payload.intent and
                    set(self._coerce_list(existing.question_variations)) == set(payload.question_variations or []) and
                    set(self._coerce_list(existing.keywords)) == set(payload.keywords or []) and
                    set(self._coerce_list(existing.entities)) == set(payload.entities or []) and
                    abs(float(existing.confidence_threshold or 0) - payload.confidence_threshold) < 0.001
                )
                if is_unchanged:
                    unchanged += 1
                else:
                    updated += 1
                    existing.question = payload.question
                    existing.answer = payload.answer
                    existing.category = payload.category
                    existing.intent = payload.intent
                    existing.question_variations = payload.question_variations
                    existing.keywords = payload.keywords
                    existing.entities = payload.entities
                    existing.confidence_threshold = payload.confidence_threshold
                    existing.updated_at = utcnow()

                existing.source_name = source_name
                existing.source_version = version
                existing.source_hash = source_hash
                existing.sync_status = "synced"
                existing.is_enabled = True
                existing.last_synchronized_at = utcnow()
                active_ids.add(int(existing.id))
                count += 1
            else:
                try:
                    async with self.session.begin_nested():
                        entry = FAQEntry(
                            source_id=source_id, source_name=source_name, source_version=version,
                            source_hash=source_hash, sync_status="synced",
                            question=payload.question, normalized_question=payload.normalized_question,
                            dedupe_key=payload.dedupe_key, answer=payload.answer, category=payload.category,
                            intent=payload.intent, question_variations=payload.question_variations,
                            keywords=payload.keywords, entities=payload.entities,
                            confidence_threshold=payload.confidence_threshold, is_enabled=True,
                            last_synchronized_at=utcnow(), created_at=utcnow(), updated_at=utcnow()
                        )
                        self.session.add(entry)
                        await self.session.flush()
                        active_ids.add(int(entry.id))
                        created += 1
                        count += 1
                except IntegrityError:
                    conflicted += 1

        stmt = select(FAQEntry).where(FAQEntry.source_id == source_id).where(FAQEntry.is_enabled.is_(True))
        all_core_entries = (await self.session.execute(stmt)).scalars().all()
        for entry in all_core_entries:
            if int(entry.id) not in active_ids:
                entry.is_enabled = False
                entry.sync_status = "superseded"
                entry.updated_at = utcnow()
                superseded += 1

        await self.session.flush()
        logger.info("Synchronized %s FAQ entries in database.", count)
        return {
            "source_id": source_id,
            "source_version": version,
            "active_entries": count,
            "created": created,
            "inserted": created,
            "updated": updated,
            "unchanged": unchanged,
            "superseded": superseded,
            "disabled": superseded,
            "conflicted": conflicted,
            "duplicates": duplicates,
            "failed": failed,
        }


    async def upsert_faq(self, question: str, answer: str, *, category: str | None = None) -> tuple[FAQEntry, bool]:
        payload = self.build_payload(question=question, answer=answer, category=category)
        entries = await self._fetch_all_entries()
        existing = self._find_existing_entry(payload, entries)
        entry = await self._upsert_entry(payload, existing)
        await self.session.flush()
        return entry, existing is None

    async def load_faq_from_file(self, file_path: str) -> int:
        report = await self.load_faq_report_from_file(file_path)
        return int(report.get("active_entries", 0))

    async def load_faq_report_from_file(self, file_path: str) -> dict[str, int | str]:
        path = Path(file_path)
        if not path.exists():
            logger.warning("FAQ file %s not found.", file_path)
            return {}
        try:
            raw = path.read_text(encoding="utf-8")
            pairs = self.parse_faq_text(raw)
            return await self.replace_source_entries_report(
                pairs,
                source_id="core_faq",
                source_name=path.name,
                source_version=self.version_for_text(raw),
            )
        except Exception as exc:
            await self.session.rollback()
            logger.error("Failed to load FAQ from file %s: %s", file_path, exc, exc_info=True)
            return {}


    async def search_faq(
        self,
        query: str,
        threshold: float = 0.72,
        *,
        context_entities: list[str] | None = None,
        track_usage: bool = True,
    ) -> tuple[FAQEntry | None, float]:
        query_norm = self.semantic_normalize(query)
        if not query_norm.strip():
            return None, 0.0
        if self._is_greeting_or_too_short(query_norm):
            return None, 0.0

        entries = await self._fetch_enabled_entries()
        best_entry = None
        best_score = 0.0

        queries = [query]
        for entity in context_entities or []:
            expanded = self._replace_pronoun(query, entity)
            if expanded and expanded != query:
                queries.append(expanded)

        for entry in entries:
            score = max(self.score_entry(candidate, entry) for candidate in queries)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry:
            entry_threshold = float(getattr(best_entry, "confidence_threshold", None) or threshold)
            min_threshold = max(threshold, entry_threshold)
            if best_score >= min_threshold:
                if track_usage:
                    await self.record_match(best_entry, success=True)
                return best_entry, best_score
            if track_usage and best_score >= 0.35:
                await self.record_match(best_entry, success=False)

        return None, best_score

    async def import_candidates(
        self,
        raw_text: str,
        *,
        source_name: str | None = None,
        default_category: str = "General",
    ) -> dict[str, Any]:
        pairs = self.parse_faq_text(raw_text)
        if not pairs:
            return {"created": 0, "duplicates": 0, "skipped": 0, "candidates": []}

        existing_entries = await self._fetch_all_entries()
        existing_candidates = await self._fetch_candidates()
        created = 0
        duplicates = 0
        skipped = 0
        candidates: list[FAQImportCandidate] = []
        seen: set[str] = set()

        for question, answer in pairs:
            payload = self.build_payload(question=question, answer=answer, category=default_category)
            key = f"{self._dedupe_key(payload)}:{normalize_text(payload.answer)[:160]}"
            if key in seen:
                skipped += 1
                continue
            seen.add(key)
            if self._candidate_exists(payload, answer, existing_candidates):
                skipped += 1
                continue
            duplicate = self._find_existing_entry(payload, existing_entries, threshold=0.88)
            status = "duplicate" if duplicate else "pending"
            if duplicate:
                duplicates += 1

            candidate = FAQImportCandidate(
                source_name=source_name,
                source_text=raw_text[:4000],
                category=payload.category,
                intent=payload.intent,
                question=payload.question,
                normalized_question=payload.normalized_question,
                question_variations=payload.question_variations,
                keywords=payload.keywords,
                entities=payload.entities,
                answer=payload.answer,
                confidence_score=1.0 if not duplicate else self.score_entry(payload.question, duplicate),
                duplicate_of_faq_id=getattr(duplicate, "id", None) if duplicate else None,
                status=status,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.session.add(candidate)
            candidates.append(candidate)
            existing_candidates.append(candidate)
            created += 1

        await self.session.flush()
        return {
            "created": created,
            "duplicates": duplicates,
            "skipped": skipped,
            "candidates": [self.serialize_candidate(row) for row in candidates],
        }

    async def list_candidates(self, status: str | None = None, limit: int = 100) -> list[FAQImportCandidate]:
        stmt = select(FAQImportCandidate).order_by(FAQImportCandidate.created_at.desc()).limit(limit)
        if status:
            stmt = stmt.where(FAQImportCandidate.status == status)
        return (await self.session.execute(stmt)).scalars().all()

    async def approve_candidate(self, candidate_id: int) -> FAQEntry:
        candidate = await self.session.get(FAQImportCandidate, candidate_id)
        if not candidate:
            raise ValueError(f"FAQ candidate {candidate_id} not found")
        if candidate.status == "approved":
            existing = self._find_existing_entry(
                self.build_payload(question=candidate.question, answer=candidate.answer, category=candidate.category),
                await self._fetch_all_entries(),
            )
            if existing:
                return existing

        payload = FAQPayload(
            question=candidate.question,
            normalized_question=candidate.normalized_question,
            dedupe_key=self._dedupe_key_from_parts(
                candidate.normalized_question,
                candidate.intent,
                candidate.entities or [],
            ),
            answer=candidate.answer,
            category=candidate.category,
            intent=candidate.intent,
            question_variations=candidate.question_variations or [],
            keywords=candidate.keywords or [],
            entities=candidate.entities or [],
        )
        entries = await self._fetch_all_entries()
        existing = None
        if candidate.duplicate_of_faq_id:
            existing = next((entry for entry in entries if entry.id == candidate.duplicate_of_faq_id), None)
        existing = existing or self._find_existing_entry(payload, entries)
        entry = await self._upsert_entry(payload, existing)
        candidate.status = "approved"
        candidate.reviewed_at = utcnow()
        candidate.updated_at = utcnow()
        await self.session.flush()
        return entry

    async def reject_candidate(self, candidate_id: int) -> FAQImportCandidate:
        candidate = await self.session.get(FAQImportCandidate, candidate_id)
        if not candidate:
            raise ValueError(f"FAQ candidate {candidate_id} not found")
        candidate.status = "rejected"
        candidate.reviewed_at = utcnow()
        candidate.updated_at = utcnow()
        await self.session.flush()
        return candidate

    async def analytics(self) -> dict[str, Any]:
        entries = await self._fetch_all_entries()
        candidates = await self._fetch_candidates()
        enabled = [row for row in entries if getattr(row, "is_enabled", True)]

        def success_rate(row: FAQEntry) -> float:
            usage = int(getattr(row, "usage_count", 0) or 0)
            if usage <= 0:
                return 0.0
            return round(float(getattr(row, "success_count", 0) or 0) / usage, 4)

        top_used = sorted(enabled, key=lambda row: int(getattr(row, "usage_count", 0) or 0), reverse=True)[:10]
        most_missed = sorted(enabled, key=lambda row: int(getattr(row, "failed_count", 0) or 0), reverse=True)[:10]
        unused = [row for row in enabled if int(getattr(row, "usage_count", 0) or 0) == 0][:10]
        low_confidence = [
            row for row in enabled if float(getattr(row, "confidence_threshold", 0.72) or 0.72) < 0.65
        ][:10]
        duplicates = [row for row in candidates if getattr(row, "status", "") == "duplicate"][:10]
        total_usage = sum(int(getattr(row, "usage_count", 0) or 0) for row in enabled)
        total_success = sum(int(getattr(row, "success_count", 0) or 0) for row in enabled)

        return {
            "faq_count": len(entries),
            "enabled_count": len(enabled),
            "candidate_count": len(candidates),
            "pending_candidates": len([row for row in candidates if row.status == "pending"]),
            "duplicate_candidates": [self.serialize_candidate(row) for row in duplicates],
            "top_faq": [self.serialize_entry(row, success_rate(row)) for row in top_used],
            "most_used_faq": [self.serialize_entry(row, success_rate(row)) for row in top_used],
            "most_missed_faq": [self.serialize_entry(row, success_rate(row)) for row in most_missed],
            "unused_faqs": [self.serialize_entry(row, success_rate(row)) for row in unused],
            "low_confidence_faqs": [self.serialize_entry(row, success_rate(row)) for row in low_confidence],
            "overall_success_rate": round(total_success / total_usage, 4) if total_usage else 0.0,
        }

    async def preview_source(self, raw_text: str) -> dict[str, Any]:
        pairs = self.parse_faq_text(raw_text)
        entries = []
        duplicates = []
        seen: set[str] = set()
        for question, answer in pairs:
            payload = self.build_payload(question=question, answer=answer)
            key = self._dedupe_key(payload)
            item = {
                "question": payload.question,
                "answer": payload.answer,
                "category": payload.category,
                "intent": payload.intent,
                "normalized_question": payload.normalized_question,
                "dedupe_key": key,
                "keywords": payload.keywords or [],
                "entities": payload.entities or [],
            }
            if key in seen:
                duplicates.append(item)
                continue
            seen.add(key)
            entries.append(item)
        return {
            "source_id": "core_faq",
            "source_version": self.version_for_text(raw_text),
            "parse_status": "ok" if entries else "empty",
            "entry_count": len(entries),
            "duplicates": duplicates,
            "entries": entries,
        }

    async def record_match(self, entry: FAQEntry, *, success: bool) -> None:
        entry.usage_count = int(getattr(entry, "usage_count", 0) or 0) + 1
        if success:
            entry.success_count = int(getattr(entry, "success_count", 0) or 0) + 1
        else:
            entry.failed_count = int(getattr(entry, "failed_count", 0) or 0) + 1
        entry.last_used_at = utcnow()
        entry.updated_at = utcnow()
        await self.session.flush()

    def build_payload(self, *, question: str, answer: str, category: str | None = None) -> FAQPayload:
        normalized = self.semantic_normalize(question)
        inferred_category = self._valid_category(category) or self.infer_category(question, answer)
        intent = self.infer_intent(question, answer, inferred_category)
        entities = self.extract_entities(f"{question}\n{answer}")
        keywords = sorted(self._keywords(f"{question} {answer}") | set(self._keyword_synonyms(question, answer)))
        variations = sorted(self.default_variations(question, entities) | {question.strip()})
        return FAQPayload(
            question=question.strip(),
            normalized_question=normalized,
            dedupe_key=self._dedupe_key_from_parts(normalized, intent, entities),
            answer=answer.strip(),
            category=inferred_category,
            intent=intent,
            question_variations=variations,
            keywords=keywords,
            entities=entities,
            confidence_threshold=self.default_threshold(intent),
        )

    @classmethod
    def score_entry(cls, query: str, entry: FAQEntry) -> float:
        query_norm = cls.semantic_normalize(query)
        candidates = [getattr(entry, "question", "") or ""]
        candidates.extend(cls._coerce_list(getattr(entry, "question_variations", None)))
        candidates = [item for item in candidates if item]
        base_score = max((cls.score_match(query_norm, cls.semantic_normalize(item)) for item in candidates), default=0.0)
        if base_score >= 0.99:
            return 1.0

        query_tokens = cls._keywords(query_norm)
        keywords = {cls._canonical_token(item) for item in cls._coerce_list(getattr(entry, "keywords", None))}
        entities = {cls.semantic_normalize(item) for item in cls._coerce_list(getattr(entry, "entities", None))}
        keyword_hits = len(query_tokens & keywords)
        keyword_score = keyword_hits / max(1, min(len(query_tokens), len(keywords) or 1))
        entity_score = 0.0
        if entities:
            entity_score = 1.0 if any(entity and entity in query_norm for entity in entities) else 0.0

        intent_bonus = 0.0
        intent = str(getattr(entry, "intent", "") or "")
        if intent == "command_help" and query_norm in {"help", "command", "commands", "what command can you do"}:
            intent_bonus = 0.25
        if intent == "identity_question" and {"name", "bot", "create", "own"} & query_tokens:
            intent_bonus = 0.12

        score = (base_score * 0.72) + (keyword_score * 0.18) + (entity_score * 0.1) + intent_bonus
        return min(1.0, score)

    @classmethod
    def score_match(cls, query_norm: str, question_norm: str) -> float:
        query_norm = cls.semantic_normalize(query_norm)
        question_norm = cls.semantic_normalize(question_norm)
        if query_norm == question_norm:
            return 1.0
        if query_norm in question_norm or question_norm in query_norm:
            sequence_score = difflib.SequenceMatcher(None, query_norm, question_norm).ratio()
            if sequence_score >= 0.78:
                return min(1.0, sequence_score + 0.14)

        query_tokens = cls._keywords(query_norm)
        question_tokens = cls._keywords(question_norm)
        if not query_tokens or not question_tokens:
            return 0.0

        sequence_score = difflib.SequenceMatcher(None, query_norm, question_norm).ratio()
        overlap = query_tokens & question_tokens
        union = query_tokens | question_tokens
        jaccard_score = len(overlap) / len(union) if union else 0.0
        coverage_score = len(overlap) / min(len(query_tokens), len(question_tokens))
        fuzzy_score = cls._token_fuzzy_score(query_tokens, question_tokens)
        order_bonus = 0.12 if query_norm in question_norm or question_norm in query_norm else 0.0
        entity_bonus = 0.08 if overlap & {"fabian", "zina", "datacube", "zinax", "moxiz"} else 0.0

        score = (
            sequence_score * 0.24
            + jaccard_score * 0.22
            + coverage_score * 0.34
            + fuzzy_score * 0.2
        )
        return min(1.0, score + order_bonus + entity_bonus)

    @classmethod
    def semantic_normalize(cls, text_value: str) -> str:
        value = (text_value or "").lower()
        replacements = {
            "what's": "what is",
            "whats": "what is",
            "who's": "who is",
            "whos": "who is",
            "you're": "you are",
            "youre": "you are",
            "i'm": "i am",
            "i’m": "i am",
            "it's": "it is",
            "its": "it is",
        }
        for old, new in replacements.items():
            value = value.replace(old, new)
        normalized = normalize_text(value)
        tokens = [cls._canonical_token(token) for token in normalized.split()]
        return " ".join(tokens)

    @classmethod
    def infer_category(cls, question: str, answer: str) -> str:
        text_value = cls.semantic_normalize(f"{question} {answer}")
        if "datacube" in text_value:
            return "Datacube AU"
        if "zinax" in text_value:
            return "ZinaX"
        if "zina" in text_value:
            return "Zina"
        if "fabian" in text_value or "owner" in text_value:
            return "Owner"
        if "command" in text_value or text_value in {"help", "commands"}:
            return "Commands"
        if "service" in text_value:
            return "Services"
        if "contact" in text_value or "email" in text_value or "whatsapp" in text_value:
            return "Contact"
        if "project" in text_value:
            return "Projects"
        return "General"

    @classmethod
    def infer_intent(cls, question: str, answer: str, category: str) -> str:
        text_value = cls.semantic_normalize(f"{question} {answer}")
        if text_value in {"help", "command", "commands"} or "available command" in text_value:
            return "command_help"
        if category in {"Identity", "Owner", "Zina", "Datacube AU", "ZinaX", "Projects"}:
            if any(token in text_value for token in ("name", "who", "create", "own", "project", "datacube", "zina", "fabian")):
                return "identity_question"
        if "contact" in text_value or "email" in text_value or "whatsapp" in text_value:
            return "contact_question"
        if "service" in text_value:
            return "service_question"
        return "custom"

    @staticmethod
    def default_threshold(intent: str) -> float:
        if intent == "identity_question":
            return 0.68
        if intent == "command_help":
            return 0.64
        return 0.72

    @classmethod
    def extract_entities(cls, text_value: str) -> list[str]:
        normalized = cls.semantic_normalize(text_value)
        found = []
        for marker, entity in KNOWN_ENTITIES.items():
            if cls.semantic_normalize(marker) in normalized and entity not in found:
                found.append(entity)
        return found

    @classmethod
    def default_variations(cls, question: str, entities: list[str] | None = None) -> set[str]:
        normalized = cls.semantic_normalize(question)
        variations = {question.strip()}
        entity = (entities or ["Zina"])[0]
        if "your name" in normalized or "who are you" in normalized or "tell me about you" in normalized:
            variations.update({"What is your name?", "What's your name?", "What's ur name?", "Who are you?", "Tell me about yourself."})
        if "create" in normalized or "built" in normalized or "made" in normalized:
            variations.update({
                f"Who created {entity}?",
                f"Who made {entity}?",
                f"Who built {entity}?",
                f"Who owns {entity}?",
                f"Who is {entity}'s creator?",
            })
        if "own" in normalized or "founder" in normalized:
            variations.update({f"Who owns {entity}?", f"Who founded {entity}?", f"Who built {entity}?"})
        if "help" in normalized or "command" in normalized:
            variations.update({"help", "/help", "commands", "What commands can I use?", "Show commands"})
        return {item for item in variations if item}

    @classmethod
    def serialize_entry(cls, row: FAQEntry, success_rate: float | None = None) -> dict[str, Any]:
        usage = int(getattr(row, "usage_count", 0) or 0)
        success = int(getattr(row, "success_count", 0) or 0)
        rate = success_rate if success_rate is not None else (round(success / usage, 4) if usage else 0.0)
        return {
            "id": row.id,
            "source_id": getattr(row, "source_id", "core_faq"),
            "source_name": getattr(row, "source_name", None),
            "source_version": getattr(row, "source_version", "legacy"),
            "source_hash": getattr(row, "source_hash", None),
            "sync_status": getattr(row, "sync_status", "synced"),
            "category": getattr(row, "category", "General") or "General",
            "intent": getattr(row, "intent", "custom") or "custom",
            "question": row.question,
            "dedupe_key": getattr(row, "dedupe_key", "") or row.normalized_question,
            "question_variations": cls._coerce_list(getattr(row, "question_variations", None)),
            "keywords": cls._coerce_list(getattr(row, "keywords", None)),
            "entities": cls._coerce_list(getattr(row, "entities", None)),
            "answer": row.answer,
            "confidence_threshold": float(getattr(row, "confidence_threshold", 0.72) or 0.72),
            "usage_count": usage,
            "success_count": success,
            "failed_count": int(getattr(row, "failed_count", 0) or 0),
            "success_rate": rate,
            "last_used_at": getattr(row, "last_used_at", None),
            "last_synchronized_at": getattr(row, "last_synchronized_at", None),
            "enabled": bool(getattr(row, "is_enabled", True)),
            "is_enabled": bool(getattr(row, "is_enabled", True)),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def serialize_candidate(cls, row: FAQImportCandidate) -> dict[str, Any]:
        return {
            "id": row.id,
            "source_name": row.source_name,
            "category": row.category,
            "intent": row.intent,
            "question": row.question,
            "question_variations": cls._coerce_list(row.question_variations),
            "keywords": cls._coerce_list(row.keywords),
            "entities": cls._coerce_list(row.entities),
            "answer": row.answer,
            "confidence_score": float(row.confidence_score or 0.0),
            "duplicate_of_faq_id": row.duplicate_of_faq_id,
            "status": row.status,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "reviewed_at": row.reviewed_at,
        }

    @classmethod
    def _keywords(cls, text_value: str) -> set[str]:
        normalized = cls.semantic_normalize(text_value)
        return {word for word in re.findall(r"[a-z0-9]+", normalized) if word not in STOP_WORDS}

    @classmethod
    def _keyword_synonyms(cls, question: str, answer: str) -> set[str]:
        text_value = cls.semantic_normalize(f"{question} {answer}")
        values: set[str] = set()
        if any(token in text_value for token in ("create", "own")):
            values.update({"create", "own", "builder"})
        if "command" in text_value or "help" in text_value:
            values.update({"help", "command"})
        return values

    @classmethod
    def _canonical_token(cls, token: str) -> str:
        return TOKEN_SYNONYMS.get(token, token)

    @staticmethod
    def _parse_labeled_faq(raw_text: str) -> list[dict[str, Any]]:
        pairs = []
        for match in FAQ_PATTERN.finditer(raw_text):
            q = match.group(1).strip()
            v_text = match.group(2)
            a = match.group(3).strip()
            if q and a:
                variations = [v.strip() for v in v_text.split("\n")] if v_text else []
                variations = [v for v in variations if v]
                pairs.append({"question": q, "answer": a, "variations": variations})
        return pairs

    @staticmethod
    def _parse_plain_faq(raw_text: str) -> list[dict[str, Any]]:
        pairs: list[dict[str, Any]] = []
        question: str | None = None
        answer_lines: list[str] = []

        def flush() -> None:
            nonlocal question, answer_lines
            answer = "\n".join(line for line in answer_lines if line.strip()).strip()
            if question and answer:
                pairs.append({"question": question, "answer": answer, "variations": []})
            question = None
            answer_lines = []

        for raw_line in (raw_text or "").splitlines():
            line = re.sub(r"^[-*]\s*", "", raw_line.strip()).strip()
            if not line:
                continue
            is_question = line.endswith("?") or bool(QUESTION_LINE_RE.match(line))
            if is_question:
                flush()
                question = line
                answer_lines = []
                continue
            if question:
                answer_lines.append(line)

        flush()
        return pairs

    async def _fetch_all_entries(self) -> list[FAQEntry]:
        return (await self.session.execute(select(FAQEntry).order_by(FAQEntry.id))).scalars().all()

    async def _fetch_enabled_entries(self) -> list[FAQEntry]:
        stmt = select(FAQEntry).where(FAQEntry.is_enabled.is_(True)).order_by(FAQEntry.id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [row for row in rows if getattr(row, "is_enabled", True)]

    async def _fetch_candidates(self) -> list[FAQImportCandidate]:
        return (await self.session.execute(select(FAQImportCandidate).order_by(FAQImportCandidate.id))).scalars().all()

    async def _upsert_entry(self, payload: FAQPayload, existing: FAQEntry | None) -> FAQEntry:
        now = utcnow()
        if existing:
            existing.question = payload.question
            existing.normalized_question = payload.normalized_question
            existing.dedupe_key = payload.dedupe_key
            existing.answer = payload.answer
            existing.category = payload.category
            existing.intent = payload.intent
            existing.question_variations = self._merge_list(existing.question_variations, payload.question_variations)
            existing.keywords = self._merge_list(existing.keywords, payload.keywords)
            existing.entities = self._merge_list(existing.entities, payload.entities)
            existing.confidence_threshold = payload.confidence_threshold
            existing.is_enabled = True
            existing.updated_at = now
            return existing

        entry = FAQEntry(
            source_id="core_faq",
            source_name="core_faq.md",
            source_version="legacy",
            sync_status="synced",
            question=payload.question,
            normalized_question=payload.normalized_question,
            dedupe_key=payload.dedupe_key,
            answer=payload.answer,
            category=payload.category,
            intent=payload.intent,
            question_variations=payload.question_variations,
            keywords=payload.keywords,
            entities=payload.entities,
            confidence_threshold=payload.confidence_threshold,
            is_enabled=True,
            last_synchronized_at=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(entry)
        return entry

    def _find_existing_entry(
        self,
        payload: FAQPayload,
        entries: list[FAQEntry],
        *,
        threshold: float = 0.92,
    ) -> FAQEntry | None:
        exact = next((entry for entry in entries if entry.normalized_question == payload.normalized_question), None)
        if exact:
            return exact
        deduped = next((entry for entry in entries if getattr(entry, "dedupe_key", "") == payload.dedupe_key), None)
        if deduped:
            return deduped
        if payload.intent == "command_help":
            same_intent = [entry for entry in entries if getattr(entry, "intent", None) == "command_help"]
        else:
            payload_entities = set(payload.entities or [])
            same_intent = [
                entry
                for entry in entries
                if getattr(entry, "intent", None) == payload.intent
                and payload.intent in {"identity_question", "contact_question", "service_question"}
                and payload.dedupe_key.startswith("intent:identity_question:")
                and payload_entities
                and set(self._coerce_list(getattr(entry, "entities", None))) == payload_entities
            ]
        if same_intent:
            return same_intent[0]
        same_answer = next(
            (
                entry
                for entry in entries
                if self._looks_like_alias(payload.question, getattr(entry, "question", ""))
                and normalize_text(getattr(entry, "answer", "")) == normalize_text(payload.answer)
            ),
            None,
        )
        if same_answer:
            return same_answer
        best = None
        best_score = 0.0
        for entry in entries:
            score = self.score_entry(payload.question, entry)
            if score > best_score:
                best = entry
                best_score = score
        if best and best_score >= threshold:
            return best
        return None

    def _candidate_exists(
        self,
        payload: FAQPayload,
        answer: str,
        candidates: list[FAQImportCandidate],
    ) -> bool:
        normalized_answer = normalize_text(answer)
        for candidate in candidates:
            if candidate.normalized_question != payload.normalized_question:
                continue
            if normalize_text(candidate.answer) == normalized_answer and candidate.status in {"pending", "duplicate"}:
                return True
        return False

    @staticmethod
    def _looks_like_alias(question: str, existing_question: str) -> bool:
        def compact(value: str) -> str:
            return normalize_text(value).strip()

        left = compact(question)
        right = compact(existing_question)
        if not left or not right:
            return False
        if left == right:
            return True
        return len(left.split()) <= 3 and len(right.split()) <= 3

    @classmethod
    def _dedupe_key(cls, payload: FAQPayload) -> str:
        return payload.dedupe_key

    @staticmethod
    def version_for_text(raw_text: str) -> str:
        cleaned = raw_text.strip()
        return sha256_text(cleaned)[:16] if cleaned else "empty"

    @classmethod
    def version_for_pairs(cls, pairs: list[dict[str, Any]] | list[tuple[str, str]]) -> str:
        raw_parts = []
        for item in pairs:
            if isinstance(item, dict):
                raw_parts.append(f"{item.get('question', '').strip()}\n{item.get('answer', '').strip()}")
            else:
                raw_parts.append(f"{item[0].strip()}\n{item[1].strip()}")
        raw = "\n\n".join(raw_parts)
        return cls.version_for_text(raw)

    @classmethod
    def _dedupe_key_from_parts(cls, normalized_question: str, intent: str, entities: list[str] | None) -> str:
        if intent == "command_help":
            return "intent:command_help"
        entity_key = ",".join(sorted(entities or []))
        identity_markers = (
            "who is ",
            "what is ",
            "who are you",
            "your name",
            "who created",
            "who made",
            "who built",
            "who owns",
            "who founded",
        )
        if intent == "identity_question" and entity_key and any(marker in normalized_question for marker in identity_markers):
            return f"intent:identity_question:{entity_key}"
        return normalized_question

    @staticmethod
    def _valid_category(category: str | None) -> str | None:
        if not category:
            return None
        stripped = category.strip()
        return stripped if stripped in FAQ_CATEGORIES else None

    @staticmethod
    def _merge_list(existing: list[str] | None, incoming: list[str] | None) -> list[str]:
        result: list[str] = []
        for item in list(existing or []) + list(incoming or []):
            text = str(item).strip()
            if text and text not in result:
                result.append(text)
        return result

    @staticmethod
    def _coerce_list(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @staticmethod
    def _replace_pronoun(query: str, entity: str) -> str:
        return re.sub(r"\b(it|this|that|they|them|those)\b", entity, query, flags=re.IGNORECASE)

    @staticmethod
    def _is_greeting_or_too_short(query_norm: str) -> bool:
        if query_norm in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}:
            return True
        words = query_norm.split()
        if len(words) <= 4 and words and words[0] in {"hi", "hello", "hey"}:
            return True
        return len([word for word in words if len(word) > 2]) == 0

    @staticmethod
    def _token_fuzzy_score(query_tokens: set[str], question_tokens: set[str]) -> float:
        if not query_tokens or not question_tokens:
            return 0.0
        scores = []
        for token in query_tokens:
            scores.append(
                max(
                    (difflib.SequenceMatcher(None, token, candidate).ratio() for candidate in question_tokens),
                    default=0.0,
                )
            )
        return sum(scores) / len(scores)
