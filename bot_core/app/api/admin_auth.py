from __future__ import annotations

from html import escape
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.config import settings
from app.db import get_db_session
from app.services.admin_auth_service import ADMIN_SESSION_COOKIE, AdminAuthService, AdminPrincipal


router = APIRouter(tags=["admin-auth"])


@router.get("/admin", include_in_schema=False)
async def admin_root(principal: AdminPrincipal = Depends(require_admin_session)) -> RedirectResponse:
    return RedirectResponse("/admin/ui", status_code=303)


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    auth = AdminAuthService()
    principal = auth.verify_session_cookie(request.cookies.get(ADMIN_SESSION_COOKIE))
    if principal:
        return RedirectResponse("/admin/ui", status_code=303)
    return _render_login_page()


@router.post("/admin/login", response_class=HTMLResponse, response_model=None)
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    auth = AdminAuthService()
    submitted_username = username.strip()
    ip_address = auth.client_ip(request)

    if await auth.is_locked_out(db, username=submitted_username, ip_address=ip_address):
        await auth.record_login_event(
            db,
            action="admin_login_locked",
            username=submitted_username,
            request=request,
            details={"reason": "temporary lockout"},
        )
        return _render_login_page(
            error=f"Too many failed attempts. Try again in {settings.admin_login_lockout_seconds // 60} minutes.",
            username=submitted_username,
            status_code=429,
        )

    principal = auth.authenticate(submitted_username, password)
    if not principal:
        await auth.record_login_event(
            db,
            action="admin_login_failed",
            username=submitted_username,
            request=request,
            details={"reason": "invalid credentials"},
        )
        locked = await auth.is_locked_out(db, username=submitted_username, ip_address=ip_address)
        error = "Invalid username or password."
        if locked:
            error = f"Too many failed attempts. Try again in {settings.admin_login_lockout_seconds // 60} minutes."
        return _render_login_page(error=error, username=submitted_username, status_code=401)

    await auth.record_login_event(db, action="admin_login_success", username=principal.username, request=request)
    response = RedirectResponse("/admin/ui", status_code=303)
    response.set_cookie(
        ADMIN_SESSION_COOKIE,
        auth.create_session_cookie(principal),
        max_age=settings.admin_session_ttl_seconds,
        httponly=True,
        secure=auth.cookie_secure_for_request(request),
        samesite="lax",
        path="/admin",
    )
    return response


@router.get("/admin/logout", include_in_schema=False)
async def logout(request: Request, db: AsyncSession = Depends(get_db_session)) -> RedirectResponse:
    auth = AdminAuthService()
    principal = auth.verify_session_cookie(request.cookies.get(ADMIN_SESSION_COOKIE))
    if principal:
        await auth.record_login_event(db, action="admin_logout", username=principal.username, request=request)
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/admin")
    return response


@router.get("/admin/session")
async def admin_session(principal: AdminPrincipal = Depends(require_admin_session)) -> dict[str, object]:
    return {
        "username": principal.username,
        "auth_method": principal.auth_method,
        "last_login": principal.login_at.isoformat() if principal.login_at else None,
        "expires_at": principal.expires_at.isoformat() if principal.expires_at else None,
    }


def _render_login_page(error: str = "", username: str = "", status_code: int = 200) -> HTMLResponse:
    error_html = f'<div class="error">{escape(error)}</div>' if error else ""
    username_value = escape(username or settings.admin_username)
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zina Admin Login</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{min-height:100vh;display:grid;place-items:center;background:#0b0e14;color:#e2e8f0;font-family:Inter,system-ui,-apple-system,sans-serif}}
.login{{width:min(420px,calc(100vw - 32px));background:#131720;border:1px solid #2a3040;border-radius:10px;padding:28px;box-shadow:0 20px 60px rgba(0,0,0,.35)}}
h1{{font-size:1.35rem;margin-bottom:6px;color:#a29bfe}}
p{{color:#8892a8;margin-bottom:22px;line-height:1.45}}
label{{display:block;font-size:.78rem;color:#8892a8;margin:14px 0 6px}}
input{{width:100%;background:#1a1f2e;border:1px solid #2a3040;color:#e2e8f0;border-radius:6px;padding:12px;font-size:1rem}}
input:focus{{outline:none;border-color:#6c5ce7}}
button{{width:100%;margin-top:20px;background:#6c5ce7;color:white;border:0;border-radius:6px;padding:12px;font-weight:700;cursor:pointer}}
button:hover{{background:#4834d4}}
.error{{background:rgba(255,107,107,.12);border:1px solid rgba(255,107,107,.45);color:#ffb4b4;border-radius:6px;padding:10px;margin-bottom:12px}}
.meta{{margin-top:18px;font-size:.76rem;color:#5a6478}}
</style>
</head>
<body>
  <form class="login" method="post" action="/admin/login">
    <h1>Zina Admin</h1>
    <p>Sign in to manage memory, identity, rules, queue, AI controls, and knowledge sources.</p>
    {error_html}
    <label for="username">Username</label>
    <input id="username" name="username" value="{username_value}" autocomplete="username" required autofocus>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required>
    <button type="submit">Sign In</button>
    <div class="meta">Session expires after {settings.admin_session_ttl_seconds // 60} minutes.</div>
  </form>
</body>
</html>""",
        status_code=status_code,
    )
