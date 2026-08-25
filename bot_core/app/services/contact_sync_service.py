from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any

from sqlalchemy import or_, select, text
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
    """Synchronize WAHA contact evidence into Zina's existing Contact source of truth."""

    PAGE_SIZE = 500
    MAX_CONTACTS = 10_000
    # One transaction-scoped lock serializes authoritative address-book scans. Contact
    # sync is an admin/owner operation, so correctness is more important than allowing
    # overlapping scans to race and make saved-state depend on commit order.
    SYNC_ADVISORY_LOCK_KEY = 902_026_082_601

    def __init__(self, session: AsyncSession, *, waha: WAHAClient | None = None):
        self.session = session
        self.waha = waha or WAHAClient()
        self._owns_waha = waha is None

    async def sync(self, *, session_name: str | None = None) -> dict[str, int]:
        await self._acquire_sync_lock()
        result = ContactSyncResult()
        offset = 0
        sync_at = utcnow()
        seen_person_ids: set[str] = set()
        complete_scan = False
        identity_coverage_complete = True
        try:
            while result.fetched < self.MAX_CONTACTS:
                page_limit = min(self.PAGE_SIZE, self.MAX_CONTACTS - result.fetched)
                contacts = await self.waha.get_contacts(
                    session_name=session_name,
                    limit=page_limit,
                    offset=offset,
                )
                if not contacts:
                    complete_scan = True
                    break

                for payload in contacts:
                    result.fetched += 1
                    outcome, seen_ids = await self._sync_one(payload, sync_at=sync_at)
                    seen_person_ids.update(seen_ids)
                    if outcome == "created":
                        result.created += 1
                    elif outcome == "updated":
                        result.updated += 1
                    else:
                        result.skipped += 1

                    # A bare LID with no known PN/person mapping is valid WAHA data but
                    # cannot prove which existing Contact it represents. Treating the
                    # scan as identity-complete would make absence reconciliation unsafe
                    # if an older inbound refresh had temporarily lost that LID alias.
                    if not seen_ids and self._payload_is_bare_lid(payload):
                        identity_coverage_complete = False

                if len(contacts) < page_limit:
                    complete_scan = True
                    break
                offset += len(contacts)

            # Only reconcile contacts missing from WAHA after a complete, validated,
            # identity-covered scan. WAHAClient rejects malformed/unrecognized pages,
            # and an unmapped bare LID conservatively suppresses absence reconciliation
            # instead of guessing that a saved contact was removed.
            if complete_scan and identity_coverage_complete:
                result.updated += await self._reconcile_absent_saved_contacts(
                    seen_person_ids,
                    sync_at=sync_at,
                )

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

    async def _sync_one(self, payload: dict[str, Any], *, sync_at: datetime) -> tuple[str, set[str]]:
        if not isinstance(payload, dict):
            return "skipped", set()

        raw_id = self._first_text(
            payload.get("id"),
            payload.get("contactId"),
            self._nested(payload, "_data", "id", "_serialized"),
            self._nested(payload, "_data", "id"),
            payload.get("jid"),
        )
        if not raw_id or self._is_non_person_chat(raw_id):
            return "skipped", set()

        lid = raw_id if raw_id.endswith("@lid") else self._first_text(payload.get("lid"), payload.get("LID"))
        pn_id = self._first_person_jid(
            payload.get("pn"),
            payload.get("phoneJid"),
            payload.get("phoneNumberJid"),
            payload.get("jid"),
            raw_id,
        )
        whatsapp_id = self._canonical_whatsapp_id(pn_id or raw_id)
        phone = self._first_text(
            payload.get("phone"),
            payload.get("number"),
            payload.get("phoneNumber"),
            self._phone_from_jid(whatsapp_id),
        )
        normalized_phone = self._digits(phone) or None if phone else None
        contact_name = self._first_text(payload.get("name"), payload.get("contactName"))
        push_name = self._first_text(payload.get("pushName"), payload.get("pushname"), payload.get("notify"))
        explicit_saved = self._first_bool(
            payload.get("isMyContact"),
            payload.get("is_my_contact"),
            self._nested(payload, "_data", "isMyContact"),
        )

        row = await self._find_existing(
            whatsapp_id=whatsapp_id,
            raw_id=raw_id,
            lid=lid,
            normalized_phone=normalized_phone,
        )

        # The advisory transaction lock serializes full sync() calls. Keep this
        # timestamp guard too because focused unit/service calls to _sync_one remain
        # safe when presented with explicitly older evidence.
        if row is not None:
            newer_evidence_at = self._saved_evidence_at(row.identity_json)
            if newer_evidence_at is not None and newer_evidence_at > sync_at:
                return "skipped", self._row_identity_keys(row, whatsapp_id, raw_id, lid)

        # A bare LID is not a phone number. It may still identify an existing person,
        # so preserve that row as seen during a complete scan, but never create a
        # second person row until WAHA supplies a PN mapping.
        if raw_id.endswith("@lid") and not pn_id and row is None:
            return "skipped", set()

        prior_saved = self._saved_marker_value(row.identity_json if row else None)
        if explicit_saved is not None:
            is_saved_contact = explicit_saved
        elif contact_name:
            # Compatibility path for older WAHA payloads that expose the address-book
            # name but omit the explicit saved-contact boolean.
            is_saved_contact = True
        elif prior_saved is not None:
            # Unknown is not evidence of removal. Preserve the last authoritative
            # marker until an explicit false value or complete-scan absence says otherwise.
            is_saved_contact = prior_saved
        else:
            is_saved_contact = False

        created = row is None
        if row is None:
            # Do not grow Zina's address book from WAHA-only unsaved contacts. Those
            # people are learned through the normal inbound Contact pipeline instead.
            if not is_saved_contact:
                return "skipped", self._identity_keys_from_values(whatsapp_id, raw_id, lid)
            row = Contact(whatsapp_id=whatsapp_id, updated_at=sync_at)
            self.session.add(row)

        if is_saved_contact is False:
            # contact_name is dedicated address-book evidence. An explicit false marker
            # must clear it even if WAHA also supplies a generic name field, otherwise a
            # later inbound refresh could lose the marker and resurrect stale saved state.
            row.contact_name = None
        elif contact_name:
            row.contact_name = contact_name[:180]
        if push_name:
            row.push_name = push_name[:180]
        if not getattr(row, "is_name_verified", False):
            preferred_name = contact_name or push_name
            if preferred_name:
                row.display_name = preferred_name[:180]

        row.chat_id = row.chat_id or (whatsapp_id if not whatsapp_id.endswith("@lid") else row.chat_id)
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
            contact_name=contact_name if is_saved_contact else None,
            push_name=push_name,
            normalized_phone=normalized_phone,
            is_saved_contact=is_saved_contact,
            saved_contact_synced_at=sync_at,
        )
        row.updated_at = sync_at
        await self.session.flush()
        return ("created" if created else "updated"), self._row_identity_keys(row, whatsapp_id, raw_id, lid)

    async def _reconcile_absent_saved_contacts(self, seen_person_ids: set[str], *, sync_at: datetime) -> int:
        # Lock the rows used for reconciliation. sync() additionally holds the
        # transaction-scoped advisory lock, while this row lock protects direct calls
        # and makes the evidence check occur against the row version we will mutate.
        rows = (await self.session.execute(select(Contact).order_by(Contact.id).with_for_update())).scalars().all()
        updated = 0
        for row in rows:
            if not self._has_saved_evidence(row):
                continue
            if self._row_identity_keys(row) & seen_person_ids:
                continue
            newer_evidence_at = self._saved_evidence_at(row.identity_json)
            if newer_evidence_at is not None and newer_evidence_at > sync_at:
                continue
            identity = dict(row.identity_json) if isinstance(row.identity_json, dict) else {}
            identity["is_saved_contact"] = False
            identity["saved_contact_synced_at"] = sync_at.isoformat()
            identity["saved_contact_reconciled_reason"] = "absent_from_full_waha_contact_scan"
            identity["contact_name"] = None
            row.identity_json = identity
            row.contact_name = None
            row.updated_at = sync_at
            updated += 1
        return updated

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
                select(Contact)
                .where(or_(*conditions))
                .order_by(Contact.updated_at.desc(), Contact.id.desc())
                .limit(1)
                .with_for_update()
            )
        ).scalar_one_or_none()

    async def _acquire_sync_lock(self) -> None:
        bind = self.session.get_bind()
        if getattr(getattr(bind, "dialect", None), "name", None) == "postgresql":
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(:key)"),
                {"key": self.SYNC_ADVISORY_LOCK_KEY},
            )

    @classmethod
    def _payload_is_bare_lid(cls, payload: dict[str, Any]) -> bool:
        raw_id = cls._first_text(
            payload.get("id"),
            payload.get("contactId"),
            cls._nested(payload, "_data", "id", "_serialized"),
            cls._nested(payload, "_data", "id"),
            payload.get("jid"),
        )
        if not raw_id or not raw_id.lower().endswith("@lid"):
            return False
        return cls._first_person_jid(
            payload.get("pn"),
            payload.get("phoneJid"),
            payload.get("phoneNumberJid"),
            payload.get("jid"),
            raw_id,
        ) is None

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
        is_saved_contact: bool,
        saved_contact_synced_at: datetime,
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
                "is_saved_contact": is_saved_contact,
                "saved_contact_synced_at": saved_contact_synced_at.isoformat(),
            }
        )
        identity.pop("saved_contact_reconciled_reason", None)
        if lid:
            identity["waha_participant_id"] = lid
        identity["aliases"] = aliases[:20]
        return identity

    @staticmethod
    def _saved_marker_value(identity_json: dict[str, Any] | None) -> bool | None:
        if not isinstance(identity_json, dict) or "is_saved_contact" not in identity_json:
            return None
        value = identity_json.get("is_saved_contact")
        return value if isinstance(value, bool) else None

    @staticmethod
    def _saved_evidence_at(identity_json: dict[str, Any] | None) -> datetime | None:
        if not isinstance(identity_json, dict):
            return None
        raw = identity_json.get("saved_contact_synced_at")
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @classmethod
    def _has_saved_evidence(cls, row: Contact) -> bool:
        marker = cls._saved_marker_value(row.identity_json)
        if marker is not None:
            return marker
        return bool((row.contact_name or "").strip())

    @classmethod
    def _row_identity_keys(cls, row: Contact, *extra: str | None) -> set[str]:
        identity = row.identity_json if isinstance(row.identity_json, dict) else {}
        return cls._identity_keys_from_values(
            row.whatsapp_id,
            row.waha_contact_id,
            row.waha_participant_id,
            row.chat_id,
            identity.get("whatsapp_id"),
            identity.get("waha_contact_id"),
            identity.get("waha_participant_id"),
            *extra,
        )

    @classmethod
    def _identity_keys_from_values(cls, *values: Any) -> set[str]:
        keys: set[str] = set()
        for value in values:
            text_value = cls._first_text(value)
            if not text_value:
                continue
            lowered = text_value.lower()
            if lowered.endswith("@s.whatsapp.net") or lowered.endswith("@c.us"):
                keys.add(cls._canonical_whatsapp_id(lowered))
            elif lowered.endswith("@lid"):
                keys.add(lowered)
        return keys

    @staticmethod
    def _canonical_whatsapp_id(value: str) -> str:
        cleaned = str(value).strip().lower()
        if cleaned.endswith("@s.whatsapp.net"):
            return cleaned.removesuffix("@s.whatsapp.net") + "@c.us"
        return cleaned

    @staticmethod
    def _phone_from_jid(value: str) -> str | None:
        lowered = str(value).strip().lower()
        if not (lowered.endswith("@c.us") or lowered.endswith("@s.whatsapp.net")):
            return None
        local = lowered.split("@", 1)[0]
        digits = re.sub(r"\D+", "", local)
        return digits or None

    @classmethod
    def _first_person_jid(cls, *values: Any) -> str | None:
        for value in values:
            text_value = cls._first_text(value)
            if not text_value:
                continue
            lowered = text_value.lower()
            if lowered.endswith("@c.us") or lowered.endswith("@s.whatsapp.net"):
                return text_value
        return None

    @staticmethod
    def _first_bool(*values: Any) -> bool | None:
        for value in values:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in {"true", "1", "yes"}:
                    return True
                if lowered in {"false", "0", "no"}:
                    return False
        return None

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
            text_value = " ".join(str(value or "").strip().split())
            if text_value:
                return text_value
        return None
