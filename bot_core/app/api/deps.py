"""Shared API dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import settings


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Raise 401 if the admin token is configured and the header doesn't match."""
    if settings.admin_api_token and x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="invalid admin token")
