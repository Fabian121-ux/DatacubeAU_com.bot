from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schema import AuditLog
from app.utils.time import utcnow


ADMIN_SESSION_COOKIE = "zina_admin_session"


@dataclass(frozen=True)
class AdminUser:
    username: str
    password: str


@dataclass(frozen=True)
class AdminPrincipal:
    username: str
    issued_at: datetime | None = None
    expires_at: datetime | None = None
    login_at: datetime | None = None
    auth_method: str = "session"


class AdminAuthService:
    """Authentication boundary for admin users.

    The current provider reads one user from env. The shape is intentionally
    list-based so a DB-backed provider can replace it without changing route
    dependencies.
    """

    def configured_users(self) -> tuple[AdminUser, ...]:
        return (AdminUser(username=settings.admin_username, password=settings.admin_password),)

    def authenticate(self, username: str, password: str) -> AdminPrincipal | None:
        username = username.strip()
        for user in self.configured_users():
            username_ok = secrets.compare_digest(username, user.username)
            password_ok = secrets.compare_digest(password, user.password)
            if username_ok and password_ok:
                now = utcnow()
                return AdminPrincipal(
                    username=user.username,
                    issued_at=now,
                    expires_at=now + timedelta(seconds=settings.admin_session_ttl_seconds),
                    login_at=now,
                )
        return None

    def create_session_cookie(self, principal: AdminPrincipal) -> str:
        issued_at = principal.issued_at or utcnow()
        expires_at = principal.expires_at or issued_at + timedelta(seconds=settings.admin_session_ttl_seconds)
        login_at = principal.login_at or issued_at
        payload = {
            "username": principal.username,
            "iat": int(issued_at.timestamp()),
            "exp": int(expires_at.timestamp()),
            "login_at": login_at.isoformat(),
            "nonce": secrets.token_urlsafe(12),
        }
        encoded_payload = self._encode_json(payload)
        signature = self._sign(encoded_payload)
        return f"{encoded_payload}.{signature}"

    def verify_session_cookie(self, cookie_value: str | None) -> AdminPrincipal | None:
        if not cookie_value or "." not in cookie_value:
            return None
        encoded_payload, signature = cookie_value.rsplit(".", 1)
        expected = self._sign(encoded_payload)
        if not secrets.compare_digest(signature, expected):
            return None
        try:
            payload = self._decode_json(encoded_payload)
            username = str(payload["username"])
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=utcnow().tzinfo)
            issued_at = datetime.fromtimestamp(int(payload["iat"]), tz=utcnow().tzinfo)
            login_at = datetime.fromisoformat(str(payload["login_at"]))
        except (KeyError, TypeError, ValueError):
            return None
        if expires_at <= utcnow():
            return None
        if username not in {user.username for user in self.configured_users()}:
            return None
        return AdminPrincipal(username=username, issued_at=issued_at, expires_at=expires_at, login_at=login_at)

    def get_soft_session(self, request: Request) -> AdminPrincipal | None:
        try:
            return self.verify_session_cookie(request.cookies.get(ADMIN_SESSION_COOKIE))
        except Exception:
            return None

    def token_principal(self, token: str | None) -> AdminPrincipal | None:
        if not settings.admin_api_token:
            return None
        if token and secrets.compare_digest(token, settings.admin_api_token):
            return AdminPrincipal(username=settings.admin_username, auth_method="token")
        return None

    def cookie_secure_for_request(self, request: Request) -> bool:
        forwarded_proto = request.headers.get("x-forwarded-proto", "").split(",", 1)[0].strip().lower()
        return settings.admin_cookie_secure or request.url.scheme == "https" or forwarded_proto == "https"

    async def failed_attempt_count(self, db: AsyncSession, *, username: str, ip_address: str) -> int:
        since = utcnow() - timedelta(seconds=settings.admin_login_lockout_seconds)
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == "admin_login_failed")
            .where(AuditLog.entity_id == username)
            .where(AuditLog.created_at >= since)
            .order_by(AuditLog.created_at.desc())
            .limit(settings.admin_login_max_failures * 4)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return sum(1 for row in rows if (row.details_json or {}).get("ip_address") == ip_address)

    async def is_locked_out(self, db: AsyncSession, *, username: str, ip_address: str) -> bool:
        count = await self.failed_attempt_count(db, username=username, ip_address=ip_address)
        return count >= settings.admin_login_max_failures

    async def record_login_event(
        self,
        db: AsyncSession,
        *,
        action: str,
        username: str,
        request: Request,
        details: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "username": username,
            "ip_address": self.client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            **(details or {}),
        }
        db.add(AuditLog(action=action, entity_type="admin_user", entity_id=username, details_json=payload))
        await db.commit()

    @staticmethod
    def client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for", "")
        if forwarded_for:
            return forwarded_for.split(",", 1)[0].strip()
        return request.client.host if request.client else "unknown"

    def _sign(self, encoded_payload: str) -> str:
        return hmac.new(self._secret(), encoded_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _encode_json(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def _decode_json(encoded_payload: str) -> dict[str, Any]:
        raw = base64.urlsafe_b64decode(encoded_payload.encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("invalid session payload")
        return value

    @staticmethod
    def _secret() -> bytes:
        secret = settings.admin_session_secret or settings.admin_password or settings.admin_api_token
        return secret.encode("utf-8")
