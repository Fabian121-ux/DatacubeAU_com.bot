"""Serves authenticated owner/admin dashboard pages."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import require_admin_session

router = APIRouter(tags=["admin-ui"], dependencies=[Depends(require_admin_session)])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_ALLOWED_ACTIONS = {"reply_now", "review_today", "informational"}


def _html_file(name: str) -> HTMLResponse:
    html_path = _STATIC_DIR / name
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@router.get("/admin/ui", response_class=HTMLResponse, response_model=None)
async def admin_ui() -> HTMLResponse:
    return _html_file("admin.html")


@router.get("/admin/action-queue", response_class=HTMLResponse, response_model=None)
async def admin_action_queue() -> HTMLResponse:
    """Render Fabian's private evidence-backed Conversation Engine action queue."""
    return _html_file("action_queue.html")


@router.get("/admin/action-queue/open/{chat_id}", response_model=None)
async def open_admin_action_queue(
    chat_id: str,
    action: str | None = Query(default=None),
) -> RedirectResponse:
    """Open one persisted conversation's owner action queue through a safe canonical deep link."""
    target = f"/admin/action-queue?chat_id={quote(chat_id, safe='')}"
    if action in _ALLOWED_ACTIONS:
        target += f"&action={action}"
    return RedirectResponse(target, status_code=303)
