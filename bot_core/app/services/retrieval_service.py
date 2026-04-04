from __future__ import annotations

from dataclasses import dataclass
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
        stmt = (
            select(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .where(KnowledgeDocument.is_enabled.is_(True))
            .where(KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE.value)
        )
        rows = (await self.session.execute(stmt)).all()
        query_norm = normalize_text(query)
        query_tokens = [token for token in query_norm.split() if token]
        chunks: list[RetrievedChunk] = []

        for chunk_model, document_model in rows:
            score = self._score_chunk(query_norm, query_tokens, chunk_model.normalized_content, document_model.source_type)
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
        if top.heading:
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
            }
            for chunk in result.chunks[: settings.kb_max_chunks]
        ]

    @staticmethod
    def _score_chunk(query_norm: str, query_tokens: list[str], normalized_content: str, source_type: str) -> float:
        if not query_tokens or not normalized_content:
            return 0.0

        content_tokens = set(normalized_content.split())
        overlap = len(set(query_tokens) & content_tokens)
        score = overlap / max(1, len(set(query_tokens)))

        if query_norm and query_norm in normalized_content:
            score += 0.3
        if source_type == "faq":
            score += 0.05

        return min(score, 0.99)
