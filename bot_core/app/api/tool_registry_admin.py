from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.models.schema import AuditLog
from app.services.tool_registry_service import ToolRegistryService


router = APIRouter(prefix="/admin/tools", tags=["admin-tools"], dependencies=[Depends(require_admin_session)])


class ToolToggleIn(BaseModel):
    enabled: bool


@router.get("")
async def list_tools(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    service = ToolRegistryService(db)
    items = await service.list_tools()
    return {"count": len(items), "items": items}


@router.get("/catalog/planner")
async def planner_catalog(
    permission: str = Query(default="owner", pattern="^(user|admin|owner)$"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    items = await ToolRegistryService(db).planner_catalog(permission=permission)
    return {"count": len(items), "permission": permission, "items": items}


@router.get("/{tool_name:path}")
async def get_tool(tool_name: str, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    item = await ToolRegistryService(db).get_tool(tool_name)
    if not item:
        raise HTTPException(status_code=404, detail="tool not found")
    return item


@router.post("/{tool_name:path}/toggle")
async def toggle_tool(
    tool_name: str,
    payload: ToolToggleIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ToolRegistryService(db)
    try:
        item = await service.set_enabled(tool_name, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    db.add(
        AuditLog(
            action="tool_registry_updated",
            entity_type="tool_registry",
            entity_id=item["name"],
            details_json={
                "enabled": item["enabled"],
                "risk": item["risk"],
                "permission": item["permission"],
            },
        )
    )
    await db.commit()
    return {"ok": True, "item": item}
