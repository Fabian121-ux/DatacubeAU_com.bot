from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db_session
from app.models.enums import KnowledgeDocumentStatus, SourceType
from app.models.schema import AuditLog, KnowledgeDocument
from app.services.retrieval_service import RetrievalService


router = APIRouter(prefix="/admin/knowledge", tags=["knowledge"])


def require_admin_token(x_admin_token: str | None) -> None:
    if settings.admin_api_token and x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


class KnowledgeTextIn(BaseModel):
    title: str
    source_type: SourceType
    raw_text: str
    metadata_json: dict[str, Any] | None = None


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    source_type: SourceType = Form(...),
    title: str | None = Form(default=None),
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    if not file.filename or not file.filename.lower().endswith((".txt", ".md")):
        raise HTTPException(status_code=400, detail="only .txt and .md files are supported")
    raw_text = (await file.read()).decode("utf-8", errors="ignore").strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="empty document")

    document = KnowledgeDocument(
        title=title or file.filename,
        source_type=source_type.value,
        raw_text=raw_text,
        status=KnowledgeDocumentStatus.INDEXING.value,
        metadata_json={"filename": file.filename},
    )
    db.add(document)
    await db.flush()
    retrieval = RetrievalService(db)
    try:
        chunks = await retrieval.index_document(document)
        db.add(
            AuditLog(
                action="knowledge_upload",
                entity_type="knowledge_document",
                entity_id=str(document.id),
                details_json={"title": document.title, "chunks": chunks, "source_type": document.source_type},
            )
        )
        await db.commit()
        return {"document_id": document.id, "chunks": chunks}
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"knowledge upload failed: {exc}") from exc


@router.post("/text")
async def create_document_from_text(
    payload: KnowledgeTextIn,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="raw_text is empty")

    document = KnowledgeDocument(
        title=payload.title,
        source_type=payload.source_type.value,
        raw_text=payload.raw_text.strip(),
        status=KnowledgeDocumentStatus.INDEXING.value,
        metadata_json=payload.metadata_json,
    )
    db.add(document)
    await db.flush()
    retrieval = RetrievalService(db)
    try:
        chunks = await retrieval.index_document(document)
        db.add(
            AuditLog(
                action="knowledge_text_ingest",
                entity_type="knowledge_document",
                entity_id=str(document.id),
                details_json={"title": document.title, "chunks": chunks, "source_type": document.source_type},
            )
        )
        await db.commit()
        return {"document_id": document.id, "chunks": chunks}
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"knowledge text ingest failed: {exc}") from exc


@router.post("/reindex/{document_id}")
async def reindex_document(
    document_id: int,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    retrieval = RetrievalService(db)
    try:
        chunks = await retrieval.reindex_document(document_id)
        db.add(
            AuditLog(
                action="knowledge_reindex",
                entity_type="knowledge_document",
                entity_id=str(document_id),
                details_json={"chunks": chunks},
            )
        )
        await db.commit()
        return {"document_id": document_id, "chunks": chunks}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"knowledge reindex failed: {exc}") from exc


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=2),
    limit: int = Query(default=5, ge=1, le=20),
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    retrieval = RetrievalService(db)
    result = await retrieval.search(q, limit=limit)
    return {
        "query": q,
        "confidence": result.confidence,
        "results": [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "title": chunk.title,
                "source_type": chunk.source_type,
                "heading": chunk.heading,
                "score": chunk.score,
                "content_preview": chunk.content[:300],
            }
            for chunk in result.chunks
        ],
    }


@router.get("/documents")
async def list_documents(
    x_admin_token: str | None = Header(default=None),
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    stmt = select(KnowledgeDocument).order_by(KnowledgeDocument.updated_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "title": row.title,
                "source_type": row.source_type,
                "status": row.status,
                "is_enabled": row.is_enabled,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }
