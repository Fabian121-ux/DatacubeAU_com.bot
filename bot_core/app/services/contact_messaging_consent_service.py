from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import re

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scheduled_action import ScheduledAction
from app.models.schema import (
    AuditLog,
    Contact,
    ContactMessagingConsent,
    ContactMessagingConsentEvent,
    Message,
)
from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class ConsentDecision:
    allowed: bool
    reason: str
    contact_id: int | None = None
    consent_id: int | None = None


class ContactMessagingConsentService:
    """Single authority for exact-contact/chat consent and opt-out serialization.

    Missing state is materialized as UNKNOWN and denied. The row lock is intentionally
    held by the caller's transaction until the single outbound transport attempt ends.
    OWNER automation policies and one-use approvals never override an opt-out.
    """

    CONSENT_TTL = timedelta(days=90)
    _OWNER_EVIDENCE = re.compile(r"^[A-Za-z0-9._:/-]{1,120}$")
    _OPT_OUT_EXACT = frozenset({
        "stop", "please stop", "unsubscribe", "opt out", "opt-out", "optout",
        "remove me", "stop messaging me", "stop texting me", "stop contacting me",
        "stop sending me messages", "no more messages", "no more texts",
        "do not contact me", "don't contact me", "dont contact me",
        "do not message me", "don't message me", "dont message me",
    })
    _OPT_OUT_PATTERNS = (
        re.compile(r"\b(?:do not|don't|dont)\s+(?:send|message|text|contact)\s+(?:me|us)\b"),
        re.compile(r"\b(?:stop|unsubscribe)\s+(?:messaging|texting|contacting|sending)\s+(?:me|us)\b"),
        re.compile(r"\b(?:no more|enough)\s+(?:messages|texts|calls)\b"),
        re.compile(r"\b(?:i do not|i don't|i dont)\s+want\s+(?:any\s+)?(?:more\s+)?(?:messages|texts|contact)\b"),
    )

    def __init__(self, session: AsyncSession):
        self.session = session

    @classmethod
    def is_explicit_opt_out_message(cls, value: str | None) -> bool:
        raw = (value or "").casefold().replace("’", "'").strip()
        raw = re.sub(r"\s+", " ", raw)
        raw = re.sub(r"[.!?,;:]+$", "", raw).strip()
        if raw in cls._OPT_OUT_EXACT:
            return True
        return any(pattern.search(raw) for pattern in cls._OPT_OUT_PATTERNS)

    @staticmethod
    def _is_direct_chat(exact_chat_id: str | None) -> bool:
        chat = (exact_chat_id or "").strip().lower()
        if not chat or any(char.isspace() for char in chat):
            return False
        return not (
            chat.endswith("@g.us")
            or chat == "status@broadcast"
            or chat.endswith("@broadcast")
            or chat.endswith("@newsletter")
        )

    @classmethod
    def _validate_owner_evidence(cls, exact_chat_id: str, evidence_ref: str, owner_identity: str) -> None:
        if not cls._is_direct_chat(exact_chat_id):
            raise ValueError("consent requires one exact direct-message chat ID")
        if not cls._OWNER_EVIDENCE.fullmatch((evidence_ref or "").strip()):
            raise ValueError("evidence-ref must be a short opaque token; do not store message text")
        if not (owner_identity or "").strip():
            raise ValueError("owner identity is required")

    async def _lock_or_create(self, contact_id: int, exact_chat_id: str, instant: datetime) -> ContactMessagingConsent:
        # INSERT .. ON CONFLICT first is essential: SELECT FOR UPDATE cannot lock a
        # row that does not exist. Concurrent first dispatch and opt-out therefore
        # serialize on the unique (contact_id, exact_chat_id) key.
        await self.session.execute(
            pg_insert(ContactMessagingConsent)
            .values(
                contact_id=contact_id,
                exact_chat_id=exact_chat_id,
                status="unknown",
                created_at=instant,
                updated_at=instant,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    ContactMessagingConsent.contact_id,
                    ContactMessagingConsent.exact_chat_id,
                ]
            )
        )
        row = (
            await self.session.execute(
                select(ContactMessagingConsent)
                .where(ContactMessagingConsent.contact_id == contact_id)
                .where(ContactMessagingConsent.exact_chat_id == exact_chat_id)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            raise RuntimeError("contact consent row could not be locked")
        return row

    async def _resolve_contact_id(self, message) -> int | None:
        metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
        scheduled_raw = metadata.get("scheduled_action_id")
        if scheduled_raw is not None:
            try:
                scheduled_id = int(scheduled_raw)
                queue_id = int(message.id)
            except (TypeError, ValueError):
                return None
            if scheduled_id <= 0 or queue_id <= 0:
                return None
            return (
                await self.session.execute(
                    select(ScheduledAction.target_contact_id)
                    .where(ScheduledAction.id == scheduled_id)
                    .where(ScheduledAction.outbound_queue_id == queue_id)
                    .where(ScheduledAction.target_chat_id == message.chat_id)
                    .where(ScheduledAction.action_type == "whatsapp.send_message")
                    .limit(1)
                )
            ).scalar_one_or_none()

        try:
            inbound_id = int(metadata.get("inbound_message_id"))
            declared_contact_id = int(metadata.get("contact_id"))
        except (TypeError, ValueError):
            return None
        if inbound_id <= 0 or declared_contact_id <= 0:
            return None
        # Resolve from the durable inbound row, not only queue JSON. The queue must
        # target the same exact chat and carry the same contact identity as its source.
        contact_id = (
            await self.session.execute(
                select(Message.contact_id)
                .where(Message.id == inbound_id)
                .where(Message.chat_id == message.chat_id)
                .where(Message.contact_id == declared_contact_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        return int(contact_id) if contact_id is not None else None

    async def authorize_outbound_queue_message(
        self,
        message,
        *,
        now: datetime | None = None,
    ) -> ConsentDecision:
        instant = now or utcnow()
        exact_chat_id = str(getattr(message, "chat_id", "") or "")
        if not self._is_direct_chat(exact_chat_id):
            return ConsentDecision(False, "recipient is not an exact direct-message chat")
        contact_id = await self._resolve_contact_id(message)
        if contact_id is None:
            return ConsentDecision(False, "exact durable contact/chat mapping is missing")
        row = await self._lock_or_create(contact_id, exact_chat_id, instant)
        if row.status == "opted_out":
            return ConsentDecision(False, "contact has opted out", contact_id, int(row.id))
        if row.status == "revoked":
            return ConsentDecision(False, "contact consent has been revoked", contact_id, int(row.id))
        if row.status != "consented":
            return ConsentDecision(False, "contact consent is unknown", contact_id, int(row.id))
        if (
            row.provenance not in {"owner_attested", "owner_reconsent"}
            or not row.evidence_ref
            or row.granted_at is None
            or row.expires_at is None
        ):
            return ConsentDecision(False, "contact consent lacks required provenance or expiry", contact_id, int(row.id))
        if row.expires_at <= instant:
            return ConsentDecision(False, "contact consent has expired", contact_id, int(row.id))
        return ConsentDecision(True, "exact contact/chat consent is current", contact_id, int(row.id))

    async def _resolve_owner_chat(self, exact_chat_id: str) -> Contact:
        if not self._is_direct_chat(exact_chat_id):
            raise ValueError("consent requires one exact direct-message chat ID")
        rows = (
            await self.session.execute(
                select(Contact)
                .where(or_(Contact.whatsapp_id == exact_chat_id, Contact.chat_id == exact_chat_id))
                .limit(2)
            )
        ).scalars().all()
        if len(rows) != 1:
            raise ValueError("exact chat ID must resolve to exactly one known contact")
        return rows[0]

    async def grant_for_chat(self, *, exact_chat_id: str, evidence_ref: str, owner_identity: str) -> int:
        self._validate_owner_evidence(exact_chat_id, evidence_ref, owner_identity)
        contact = await self._resolve_owner_chat(exact_chat_id)
        instant = utcnow()
        row = await self._lock_or_create(int(contact.id), exact_chat_id, instant)
        if row.status == "opted_out":
            raise ValueError("contact opted out; explicit contact re-consent is required before .contact consent reconsent")
        row.status = "consented"
        row.provenance = "owner_attested"
        row.evidence_ref = evidence_ref.strip()
        row.granted_by = owner_identity.strip()
        row.granted_at = instant
        row.expires_at = instant + self.CONSENT_TTL
        row.opted_out_at = None
        row.revoked_at = None
        row.updated_at = instant
        await self._record_event(row, "granted", "owner", owner_identity.strip(), evidence_ref.strip(), instant)
        await self.session.flush()
        return int(contact.id)

    async def reconsent_for_chat(self, *, exact_chat_id: str, evidence_ref: str, owner_identity: str) -> int:
        self._validate_owner_evidence(exact_chat_id, evidence_ref, owner_identity)
        contact = await self._resolve_owner_chat(exact_chat_id)
        instant = utcnow()
        row = await self._lock_or_create(int(contact.id), exact_chat_id, instant)
        if row.status != "opted_out":
            raise ValueError("reconsent is only valid after an explicit contact opt-out")
        row.status = "consented"
        row.provenance = "owner_reconsent"
        row.evidence_ref = evidence_ref.strip()
        row.granted_by = owner_identity.strip()
        row.granted_at = instant
        row.expires_at = instant + self.CONSENT_TTL
        row.opted_out_at = None
        row.revoked_at = None
        row.updated_at = instant
        await self._record_event(row, "reconsented", "owner", owner_identity.strip(), evidence_ref.strip(), instant)
        await self.session.flush()
        return int(contact.id)

    async def revoke_for_chat(self, *, exact_chat_id: str, evidence_ref: str, owner_identity: str) -> int:
        self._validate_owner_evidence(exact_chat_id, evidence_ref, owner_identity)
        contact = await self._resolve_owner_chat(exact_chat_id)
        instant = utcnow()
        row = await self._lock_or_create(int(contact.id), exact_chat_id, instant)
        row.status = "revoked"
        row.provenance = "owner_revocation"
        row.evidence_ref = evidence_ref.strip()
        row.granted_by = owner_identity.strip()
        row.expires_at = None
        row.revoked_at = instant
        row.updated_at = instant
        await self._record_event(row, "revoked", "owner", owner_identity.strip(), evidence_ref.strip(), instant)
        await self.session.flush()
        return int(contact.id)

    async def record_inbound_opt_out(
        self,
        *,
        contact_id: int,
        exact_chat_id: str,
        evidence_ref: str,
    ) -> None:
        if not self._is_direct_chat(exact_chat_id):
            raise ValueError("contact opt-out must be tied to an exact direct-message chat")
        if contact_id <= 0 or not str(evidence_ref or "").strip():
            raise ValueError("contact ID and inbound evidence reference are required")
        instant = utcnow()
        row = await self._lock_or_create(contact_id, exact_chat_id, instant)
        row.status = "opted_out"
        row.provenance = "inbound_opt_out"
        row.evidence_ref = str(evidence_ref).strip()[:240]
        row.expires_at = None
        row.opted_out_at = instant
        row.updated_at = instant
        await self._record_event(row, "opted_out", "contact", None, row.evidence_ref, instant)
        await self.session.flush()

    async def _record_event(
        self,
        row: ContactMessagingConsent,
        event_type: str,
        actor_type: str,
        actor_identity: str | None,
        evidence_ref: str | None,
        instant: datetime,
    ) -> None:
        self.session.add(
            ContactMessagingConsentEvent(
                consent_id=row.id,
                contact_id=row.contact_id,
                exact_chat_id=row.exact_chat_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_identity=actor_identity,
                evidence_ref=evidence_ref,
                created_at=instant,
            )
        )
        self.session.add(
            AuditLog(
                action="contact_messaging_consent_changed",
                entity_type="contact_messaging_consent",
                entity_id=str(row.id),
                details_json={
                    "contact_id": row.contact_id,
                    "exact_chat_id": row.exact_chat_id,
                    "status": row.status,
                    "provenance": row.provenance,
                    "evidence_ref": evidence_ref,
                },
                created_at=instant,
            )
        )
