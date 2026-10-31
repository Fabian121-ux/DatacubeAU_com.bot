from __future__ import annotations

from dataclasses import dataclass
import difflib
import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.enums import KnowledgeDocumentStatus
from app.models.schema import KnowledgeChunk, KnowledgeDocument, QACache
from app.services.chunking_service import ChunkingService
from app.services.logging_service import log_event
from app.utils.hashing import normalize_question_key
from app.utils.text import normalize_text
from app.utils.time import utcnow


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievedChunk:
    id: int
    document_id: int
    title: str
    source_type: str
    heading: str | None
    content: str
    score: float
    diagnostics: dict[str, float]


@dataclass(slots=True)
class SearchResult:
    chunks: list[RetrievedChunk]
    confidence: float


class RetrievalService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.chunker = ChunkingService()

    async def reindex_document(self, document_id: int) -> int:
        document = await self.session.get(KnowledgeDocument, document_id)
        if not document:
            raise ValueError(f"knowledge document {document_id} not found")
        return await self.index_document(document)

    async def index_document(self, document: KnowledgeDocument) -> int:
        await self.session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document.id))
        chunks = self.chunker.chunk_text(document.raw_text)

        for chunk in chunks:
            self.session.add(
                KnowledgeChunk(
                    document_id=document.id,
                    chunk_index=chunk.chunk_index,
                    heading=chunk.heading,
                    content=chunk.content,
                    normalized_content=normalize_text(chunk.content),
                    token_estimate=chunk.token_estimate,
                    metadata_json={"title": document.title, "source_type": document.source_type},
                )
            )

        document.status = KnowledgeDocumentStatus.ACTIVE.value
        document.updated_at = utcnow()
        await self.session.flush()
        log_event(logger, logging.INFO, "knowledge_document_indexed", document_id=document.id, chunks=len(chunks))
        return len(chunks)

    async def search(self, query: str, limit: int | None = None) -> SearchResult:
        query_norm = normalize_text(query)
        query_tokens = [token for token in query_norm.split() if token]
        # Skip search if query has no meaningful tokens
        if not query_tokens:
            return SearchResult(chunks=[], confidence=0.0)

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeDocument.is_enabled.is_(True))
            .where(KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE.value)
        )

        rows = (await self.session.execute(stmt)).all()
        chunks: list[RetrievedChunk] = []

        for chunk_model, document_model in rows:
            score, diagnostics = self._score_chunk(
                query_norm,
                query_tokens,
                chunk_model.normalized_content,
                normalize_text(chunk_model.heading or ""),
                document_model.source_type,
            )
            if score <= 0:
                continue
            chunks.append(
                RetrievedChunk(
                    id=chunk_model.id,
                    document_id=document_model.id,
                    title=document_model.title,
                    source_type=document_model.source_type,
                    heading=chunk_model.heading,
                    content=chunk_model.content,
                    score=score,
                    diagnostics=diagnostics,
                )
            )

        chunks.sort(key=lambda item: item.score, reverse=True)
        limited = chunks[: (limit or settings.kb_max_chunks)]
        confidence = limited[0].score if limited else 0.0
        return SearchResult(chunks=limited, confidence=confidence)

    async def lookup_cache(self, question: str) -> QACache | None:
        normalized = normalize_question_key(question)
        stmt = select(QACache).where(QACache.normalized_question == normalized).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.hit_count += 1
            await self.session.flush()
        return model

    async def upsert_cache_answer(
        self,
        *,
        question: str,
        answer_text: str,
        answer_mode: str,
        confidence: float,
        source_json: dict[str, object] | None,
    ) -> None:
        normalized = normalize_question_key(question)
        stmt = select(QACache).where(QACache.normalized_question == normalized).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            model.answer_text = answer_text
            model.answer_mode = answer_mode
            model.confidence = confidence
            model.source_json = source_json
            model.updated_at = utcnow()
            return

        self.session.add(
            QACache(
                normalized_question=normalized,
                answer_text=answer_text,
                answer_mode=answer_mode,
                confidence=confidence,
                source_json=source_json,
                hit_count=0,
            )
        )
        await self.session.flush()

    def build_kb_reply(self, result: SearchResult) -> str:
        if not result.chunks:
            return ""
        top = result.chunks[0]
        snippet = top.content.strip().replace("\n", " ")
        if len(snippet) > settings.kb_reply_max_chars:
            snippet = snippet[: settings.kb_reply_max_chars].rstrip() + "..."
        heading = (top.heading or "").strip()
        if heading and not heading.endswith("?") and not snippet.lower().startswith(heading.lower()):
            return f"{top.heading}: {snippet}"
        return snippet

    def prompt_context(self, result: SearchResult) -> list[dict[str, object]]:
        return [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "source_type": chunk.source_type,
                "heading": chunk.heading,
                "content": chunk.content[:700],
                "score": chunk.score,
                "retrieval_diagnostics": chunk.diagnostics,
            }
            for chunk in result.chunks[: settings.kb_max_chunks]
        ]

    @staticmethod
    def _score_chunk(
        query_norm: str,
        query_tokens: list[str],
        normalized_content: str,
        normalized_heading: str,
        source_type: str,
    ) -> tuple[float, dict[str, float]]:
        if not query_tokens or not normalized_content:
            return 0.0, {
                "keyword_score": 0.0,
                "fuzzy_score": 0.0,
                "phrase_score": 0.0,
                "source_boost": 0.0,
                "retrieval_score": 0.0,
            }

        content_tokens = list({token for token in normalized_content.split() if token})
        heading_tokens = list({token for token in normalized_heading.split() if token})
        searchable_tokens = content_tokens + heading_tokens
        query_set = set(query_tokens)
        content_set = set(searchable_tokens)

        overlap = len(query_set & content_set)
        keyword_overlap_score = overlap / max(1, len(query_set))

        fuzzy_matches = 0
        fuzzy_ratios: list[float] = []
        for token in query_set:
            best = max(
                (difflib.SequenceMatcher(None, token, content_token).ratio() for content_token in searchable_tokens),
                default=0.0,
            )
            fuzzy_ratios.append(best)
            if best >= 0.78:
                fuzzy_matches += 1
        fuzzy_match_score = fuzzy_matches / max(1, len(query_set))
        keyword_score = max(keyword_overlap_score, fuzzy_match_score * 0.85)
        fuzzy_score = sum(fuzzy_ratios) / max(1, len(fuzzy_ratios))

        phrase_targets = [
            normalized_heading,
            normalized_content[:500],
            normalized_content[:1200],
        ]
        phrase_score = max(
            (difflib.SequenceMatcher(None, query_norm, target).ratio() for target in phrase_targets if target),
            default=0.0,
        )
        if query_norm and query_norm in normalized_content:
            phrase_score = max(phrase_score, 1.0)
        if normalized_heading and query_norm and query_norm in normalized_heading:
            phrase_score = max(phrase_score, 1.0)

        source_boost = 0.05 if source_type == "faq" else 0.0
        retrieval_score = (keyword_score * fuzzy_score * max(phrase_score, 0.25)) + source_boost
        diagnostics = {
            "keyword_score": round(keyword_score, 4),
            "fuzzy_score": round(fuzzy_score, 4),
            "phrase_score": round(phrase_score, 4),
            "source_boost": round(source_boost, 4),
            "retrieval_score": round(min(retrieval_score, 0.99), 4),
        }
        return min(retrieval_score, 0.99), diagnostics
