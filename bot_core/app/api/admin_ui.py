"""Serves authenticated owner/admin dashboard pages."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response

from app.api.deps import require_admin_session

router = APIRouter(tags=["admin-ui"], dependencies=[Depends(require_admin_session)])

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def _html_file(name: str) -> HTMLResponse:
    html_path = _STATIC_DIR / name
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI not found</h1>", status_code=404)
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


def _admin_html() -> HTMLResponse:
    """Serve the legacy admin page with small authenticated extension scripts."""
    html_path = _STATIC_DIR / "admin.html"
    if not html_path.exists():
        return HTMLResponse("<h1>Admin UI not found</h1>", status_code=404)
    html = html_path.read_text(encoding="utf-8")
    extension = '<script src="/admin/inspector-action-queue.js"></script>'
    if extension not in html:
        html = html.replace("</body>", f"{extension}\n</body>")
    return HTMLResponse(html)


@router.get("/admin/ui", response_class=HTMLResponse, response_model=None)
async def admin_ui() -> HTMLResponse:
    return _admin_html()


@router.get("/admin/action-queue", response_class=HTMLResponse, response_model=None)
async def admin_action_queue() -> HTMLResponse:
    """Render Fabian's private evidence-backed Conversation Engine action queue."""
    return _html_file("action_queue.html")


@router.get("/admin/inspector-action-queue.js", response_class=Response, response_model=None)
async def inspector_action_queue_script() -> Response:
    """Serve the authenticated Conversation Inspector Action Queue integration."""
    script_path = _STATIC_DIR / "inspector_action_queue.js"
    if not script_path.exists():
        return Response("// Admin UI extension not found\n", status_code=404, media_type="application/javascript")
    return Response(script_path.read_text(encoding="utf-8"), media_type="application/javascript")
