"""Shared API dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.config import settings
from app.services.admin_auth_service import AdminAuthService, AdminPrincipal, ADMIN_SESSION_COOKIE


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Raise 401 if the admin token is configured and the header doesn't match."""
    if settings.admin_api_token and x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


def require_admin_session(
    request: Request,
    x_admin_token: str | None = Header(default=None),
) -> AdminPrincipal:
    auth = AdminAuthService()
    token_principal = auth.token_principal(x_admin_token)
    if token_principal:
        return token_principal

    principal = auth.verify_session_cookie(request.cookies.get(ADMIN_SESSION_COOKIE))
    if principal:
        return principal

    raise HTTPException(
        status_code=303,
        detail="admin login required",
        headers={"Location": "/admin/login"},
    )
