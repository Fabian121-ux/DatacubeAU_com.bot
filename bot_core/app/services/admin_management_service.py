from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schema import AdminAccount
from app.utils.time import utcnow


class AdminManagementService:
    """Authoritative WhatsApp admin registry."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_from_config(self, configured_ids: str | None = None) -> None:
        configured = configured_ids if configured_ids is not None else settings.owner_whatsapp_ids
        existing = {row.normalized_whatsapp_id for row in await self.list_admins(include_disabled=True)}
        primary_exists = any(row.is_primary and row.is_enabled for row in await self.list_admins(include_disabled=True))
        for index, raw in enumerate(self._split_configured_ids(configured), start=1):
            normalized = self.normalize_whatsapp_id(raw)
            if not normalized or normalized in existing:
                continue
            self.session.add(
                AdminAccount(
                    name="Primary Admin" if index == 1 and not primary_exists else f"Admin {index}",
                    whatsapp_number=raw,
                    normalized_whatsapp_id=normalized,
                    role="primary_admin" if index == 1 and not primary_exists else "admin",
                    permission_level="owner",
                    is_primary=index == 1 and not primary_exists,
                    is_enabled=True,
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            existing.add(normalized)
        await self.session.flush()

    async def list_admins(self, *, include_disabled: bool = True, search: str | None = None) -> list[AdminAccount]:
        stmt = select(AdminAccount).order_by(AdminAccount.is_primary.desc(), AdminAccount.name)
        if not include_disabled:
            stmt = stmt.where(AdminAccount.is_enabled.is_(True))
        rows = (await self.session.execute(stmt)).scalars().all()
        if search:
            needle = search.strip().lower()
            rows = [
                row
                for row in rows
                if needle in row.name.lower()
                or needle in row.whatsapp_number.lower()
                or needle in row.normalized_whatsapp_id.lower()
                or needle in row.role.lower()
                or needle in row.permission_level.lower()
            ]
        return rows

    async def is_admin_message(self, message: Any) -> bool:
        await self.ensure_from_config()
        keys = self.identity_keys_for_message(message)
        rows = await self.list_admins(include_disabled=False)
        for row in rows:
            admin_keys = self.identity_keys(row.normalized_whatsapp_id) | self.identity_keys(row.whatsapp_number)
            if keys & admin_keys:
                row.last_active_at = utcnow()
                row.updated_at = utcnow()
                await self.session.flush()
                return True
        return False

    async def create_admin(
        self,
        *,
        name: str,
        whatsapp_number: str,
        role: str = "admin",
        permission_level: str = "owner",
        is_primary: bool = False,
    ) -> AdminAccount:
        normalized = self.normalize_whatsapp_id(whatsapp_number)
        if not normalized:
            raise ValueError("A valid WhatsApp number is required.")
        existing = await self._get_by_normalized(normalized)
        if existing:
            raise ValueError("An administrator with that WhatsApp number already exists.")
        row = AdminAccount(
            name=self._clean_name(name) or normalized,
            whatsapp_number=whatsapp_number.strip(),
            normalized_whatsapp_id=normalized,
            role=role.strip() or "admin",
            permission_level=permission_level.strip() or "owner",
            is_primary=False,
            is_enabled=True,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(row)
        await self.session.flush()
        if is_primary:
            await self.set_primary(row.id)
        return row

    async def update_admin(self, admin_id: int, updates: dict[str, Any]) -> AdminAccount:
        row = await self._get(admin_id)
        if "whatsapp_number" in updates and updates["whatsapp_number"] is not None:
            normalized = self.normalize_whatsapp_id(str(updates["whatsapp_number"]))
            if not normalized:
                raise ValueError("A valid WhatsApp number is required.")
            duplicate = await self._get_by_normalized(normalized)
            if duplicate and duplicate.id != row.id:
                raise ValueError("An administrator with that WhatsApp number already exists.")
            row.whatsapp_number = str(updates["whatsapp_number"]).strip()
            row.normalized_whatsapp_id = normalized
        for field in ("name", "role", "permission_level"):
            if field in updates and updates[field] is not None:
                value = str(updates[field]).strip()
                if field == "name":
                    value = self._clean_name(value) or row.name
                setattr(row, field, value)
        if "is_enabled" in updates and updates["is_enabled"] is not None:
            await self.set_enabled(row.id, bool(updates["is_enabled"]))
            row = await self._get(admin_id)
        if "is_primary" in updates and updates["is_primary"]:
            await self.set_primary(row.id)
            row = await self._get(admin_id)
        row.updated_at = utcnow()
        await self.session.flush()
        return row

    async def set_enabled(self, admin_id: int, enabled: bool) -> AdminAccount:
        row = await self._get(admin_id)
        if not enabled and row.is_primary:
            active_primary_count = len([item for item in await self.list_admins(include_disabled=False) if item.is_primary])
            if active_primary_count <= 1:
                raise ValueError("The final active primary administrator cannot be disabled.")
        row.is_enabled = enabled
        row.updated_at = utcnow()
        await self.session.flush()
        return row

    async def set_primary(self, admin_id: int) -> AdminAccount:
        row = await self._get(admin_id)
        if not row.is_enabled:
            raise ValueError("A disabled administrator cannot be primary.")
        rows = await self.list_admins(include_disabled=True)
        for item in rows:
            item.is_primary = item.id == row.id
            item.role = "primary_admin" if item.id == row.id else ("admin" if item.role == "primary_admin" else item.role)
            item.updated_at = utcnow()
        await self.session.flush()
        return row

    async def delete_admin(self, admin_id: int) -> AdminAccount:
        row = await self._get(admin_id)
        if row.is_primary and row.is_enabled:
            active_primary_count = len([item for item in await self.list_admins(include_disabled=False) if item.is_primary])
            if active_primary_count <= 1:
                raise ValueError("The final active primary administrator cannot be removed.")
        await self.session.delete(row)
        await self.session.flush()
        return row

    async def _get(self, admin_id: int) -> AdminAccount:
        row = await self.session.get(AdminAccount, admin_id)
        if not row:
            raise ValueError(f"administrator {admin_id} not found")
        return row

    async def _get_by_normalized(self, normalized: str) -> AdminAccount | None:
        return (
            await self.session.execute(
                select(AdminAccount).where(AdminAccount.normalized_whatsapp_id == normalized).limit(1)
            )
        ).scalar_one_or_none()

    @classmethod
    def serialize(cls, row: AdminAccount) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "whatsapp_number": row.whatsapp_number,
            "normalized_whatsapp_id": row.normalized_whatsapp_id,
            "role": row.role,
            "permission_level": row.permission_level,
            "is_primary": row.is_primary,
            "primary": row.is_primary,
            "is_enabled": row.is_enabled,
            "enabled": row.is_enabled,
            "last_active_at": row.last_active_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @classmethod
    def identity_keys_for_message(cls, message: Any) -> set[str]:
        values = [getattr(message, "sender_id", None)]
        values.extend(getattr(message, "sender_alternate_ids", []) or [])
        payload = getattr(message, "payload", None) or {}
        if isinstance(payload, dict):
            sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
            values.extend([payload.get("from"), payload.get("chatId"), sender.get("phone"), sender.get("id"), sender.get("lid")])
        keys: set[str] = set()
        for value in values:
            keys.update(cls.identity_keys(value))
        return keys

    @classmethod
    def identity_keys(cls, value: Any) -> set[str]:
        raw = cls.clean_identifier(value)
        if not raw:
            return set()
        keys = {raw.lower()}
        normalized = cls.normalize_whatsapp_id(raw)
        if normalized:
            keys.add(normalized)
            digits = cls.digits_only(normalized)
            if digits:
                keys.update({digits, f"{digits}@c.us", f"{digits}@s.whatsapp.net", f"{digits}@lid"})
        return keys

    @classmethod
    def normalize_whatsapp_id(cls, value: Any) -> str:
        raw = cls.clean_identifier(value)
        if not raw:
            return ""
        lowered = raw.lower()
        if "@" in lowered:
            left, _, domain = lowered.partition("@")
            digits = cls.digits_only(left)
            if domain in {"c.us", "s.whatsapp.net"} and digits:
                return f"{digits}@c.us"
            if domain == "lid":
                return f"{left}@lid"
            if left:
                return lowered
        digits = cls.digits_only(raw)
        return f"{digits}@c.us" if digits else ""

    @staticmethod
    def clean_identifier(value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        markdown = re.match(r"^\[([^\]]+)\]\([^)]*\)$", text)
        if markdown:
            text = markdown.group(1).strip()
        if text.startswith("mailto:"):
            text = text[7:]
        return text.strip()

    @staticmethod
    def digits_only(value: Any) -> str:
        return re.sub(r"\D+", "", str(value or ""))

    @staticmethod
    def _split_configured_ids(configured: str | None) -> list[str]:
        return [item.strip() for item in re.split(r"[\s,;]+", configured or "") if item.strip()]

    @staticmethod
    def _clean_name(value: str) -> str:
        return " ".join(value.strip().split())[:180]
