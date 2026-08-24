"""Serves authenticated owner/admin dashboard pages."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.api.deps import require_admin_session

router = APIRouter(tags=["admin-ui"], dependencies=[Depends(require_admin_session)])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


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
