from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import Contact
from app.services.waha_client import WAHAClient
from app.utils.time import utcnow


@dataclass(slots=True)
class ContactSyncResult:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0


class ContactSyncService:
    """Synchronize WAHA's saved contacts into Zina's existing Contact source of truth."""

    PAGE_SIZE = 500
    MAX_CONTACTS = 10_000

    def __init__(self, session: AsyncSession, *, waha: WAHAClient | None = None):
        self.session = session
        self.waha = waha or WAHAClient()
        self._owns_waha = waha is None

    async def sync(self, *, session_name: str | None = None) -> dict[str, int]:
        result = ContactSyncResult()
        offset = 0
        try:
            while result.fetched < self.MAX_CONTACTS:
                page_limit = min(self.PAGE_SIZE, self.MAX_CONTACTS - result.fetched)
                contacts = await self.waha.get_contacts(
                    session_name=session_name,
                    limit=page_limit,
                    offset=offset,
                )
                if not contacts:
                    break

                for payload in contacts:
                    result.fetched += 1
                    outcome = await self._sync_one(payload)
                    if outcome == "created":
                        result.created += 1
                    elif outcome == "updated":
                        result.updated += 1
                    else:
                        result.skipped += 1

                if len(contacts) < page_limit:
                    break
                offset += len(contacts)

            await self.session.flush()
            return {
                "fetched": result.fetched,
                "created": result.created,
                "updated": result.updated,
                "skipped": result.skipped,
            }
        finally:
            if self._owns_waha:
                await self.waha.close()

    async def _sync_one(self, payload: dict[str, Any]) -> str:
        if not isinstance(payload, dict):
            return "skipped"

        raw_id = self._first_text(
            payload.get("id"),
            payload.get("jid"),
            payload.get("contactId"),
            self._nested(payload, "_data", "id", "_serialized"),
            self._nested(payload, "_data", "id"),
        )
        if not raw_id or self._is_non_person_chat(raw_id):
            return "skipped"

        whatsapp_id = self._canonical_whatsapp_id(raw_id)
        lid = raw_id if raw_id.endswith("@lid") else self._first_text(payload.get("lid"), payload.get("LID"))
        phone = self._first_text(
            payload.get("phone"),
            payload.get("number"),
            payload.get("phoneNumber"),
            self._phone_from_jid(whatsapp_id),
        )
        normalized_phone = self._digits(phone or whatsapp_id) or None
        contact_name = self._first_text(payload.get("name"), payload.get("contactName"))
        push_name = self._first_text(payload.get("pushName"), payload.get("pushname"), payload.get("notify"))

        row = await self._find_existing(
            whatsapp_id=whatsapp_id,
            raw_id=raw_id,
            lid=lid,
            normalized_phone=normalized_phone,
        )
        created = row is None
        if row is None:
            row = Contact(whatsapp_id=whatsapp_id, updated_at=utcnow())
            self.session.add(row)

        if contact_name:
            row.contact_name = contact_name[:180]
        if push_name:
            row.push_name = push_name[:180]
        if not getattr(row, "is_name_verified", False):
            preferred_name = contact_name or push_name
            if preferred_name:
                row.display_name = preferred_name[:180]

        row.chat_id = row.chat_id or whatsapp_id
        row.waha_contact_id = raw_id[:120]
        if lid:
            row.waha_participant_id = lid[:120]
        if phone:
            row.whatsapp_phone = phone[:80]
        if normalized_phone:
            row.normalized_phone = normalized_phone[:80]
        row.identity_source = "waha_contact_sync"
        row.identity_json = self._merged_identity_json(
            row.identity_json,
            raw_id=raw_id,
            whatsapp_id=whatsapp_id,
            lid=lid,
            contact_name=contact_name,
            push_name=push_name,
            normalized_phone=normalized_phone,
        )
        row.updated_at = utcnow()
        await self.session.flush()
        return "created" if created else "updated"

    async def _find_existing(
        self,
        *,
        whatsapp_id: str,
        raw_id: str,
        lid: str | None,
        normalized_phone: str | None,
    ) -> Contact | None:
        conditions = [Contact.whatsapp_id == whatsapp_id, Contact.waha_contact_id == raw_id]
        if lid:
            conditions.extend([Contact.whatsapp_id == lid, Contact.waha_participant_id == lid])
        if normalized_phone:
            conditions.append(Contact.normalized_phone == normalized_phone)
        return (
            await self.session.execute(
                select(Contact).where(or_(*conditions)).order_by(Contact.updated_at.desc(), Contact.id.desc()).limit(1)
            )
        ).scalar_one_or_none()

    @classmethod
    def _merged_identity_json(
        cls,
        current: dict[str, Any] | None,
        *,
        raw_id: str,
        whatsapp_id: str,
        lid: str | None,
        contact_name: str | None,
        push_name: str | None,
        normalized_phone: str | None,
    ) -> dict[str, Any]:
        identity = dict(current) if isinstance(current, dict) else {}
        aliases = [str(item).strip() for item in identity.get("aliases", []) if str(item).strip()] if isinstance(identity.get("aliases"), list) else []
        for value in (contact_name, push_name):
            if value and value not in aliases:
                aliases.append(value)
        identity.update(
            {
                "source": "waha_contact_sync",
                "waha_contact_id": raw_id,
                "whatsapp_id": whatsapp_id,
                "normalized_phone": normalized_phone,
                "contact_name": contact_name,
                "push_name": push_name,
            }
        )
        if lid:
            identity["waha_participant_id"] = lid
        identity["aliases"] = aliases[:20]
        return identity

    @staticmethod
    def _canonical_whatsapp_id(value: str) -> str:
        cleaned = str(value).strip().lower()
        if cleaned.endswith("@s.whatsapp.net"):
            return cleaned.removesuffix("@s.whatsapp.net") + "@c.us"
        return cleaned

    @staticmethod
    def _phone_from_jid(value: str) -> str | None:
        local = str(value).split("@", 1)[0]
        digits = re.sub(r"\D+", "", local)
        return digits or None

    @staticmethod
    def _digits(value: str) -> str:
        return re.sub(r"\D+", "", value or "")

    @staticmethod
    def _is_non_person_chat(value: str) -> bool:
        lowered = value.lower()
        return lowered.endswith("@g.us") or lowered in {"status@broadcast"} or lowered.endswith("@newsletter") or lowered.endswith("@broadcast")

    @staticmethod
    def _nested(payload: dict[str, Any], *path: str) -> Any:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _first_text(*values: Any) -> str | None:
        for value in values:
            if isinstance(value, dict):
                value = value.get("_serialized") or value.get("id")
            text = " ".join(str(value or "").strip().split())
            if text:
                return text
        return None
