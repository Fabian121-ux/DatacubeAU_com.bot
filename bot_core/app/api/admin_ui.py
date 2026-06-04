"""Serves the admin dashboard UI as a single HTML page."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["admin-ui"])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/admin/ui", response_class=HTMLResponse)
async def admin_ui() -> HTMLResponse:
    html_path = _STATIC_DIR / "admin.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))
