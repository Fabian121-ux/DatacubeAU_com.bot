from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.services.conversation_export_service import ConversationExportService


router = APIRouter(
    prefix="/admin/conversation-export",
    tags=["admin-conversation-export"],
    dependencies=[Depends(require_admin_session)],
)


@router.get("")
async def export_conversation(
    contact: str = Query(min_length=1, max_length=180),
    limit: int = Query(default=200, ge=1, le=200),
    after: datetime | None = Query(default=None),
    before: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        payload = await ConversationExportService(db).export(
            contact_reference=contact,
            limit=limit,
            after=after,
            before=before,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    return payload
