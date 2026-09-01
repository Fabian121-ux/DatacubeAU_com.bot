from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    outbound_queue_id: int
    inbound_message_id: int
    contact_id: int
    target_chat_id: str
    content_sha256: str
    response_category: str


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    authority_type: str
    reason: str
    approval_id: int | None = None
    policy_id: int | None = None


class OutboundAuthorizationService:
    """Durable, fail-closed authority for ordinary external outbound replies.

    This service does not infer authority from display names or chat history. Callers
    must provide exact durable source/contact/queue identifiers stamped by the router.
    """

    _MEDIA_BINDING_DOMAIN = "zina.outbound.authority.v1.media:"

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def content_hash(text_value: str) -> str:
        """Hash exact text-only outbound content.

        Preserved byte-for-byte so already-stamped text-only authority stays valid.
        """
        return hashlib.sha256((text_value or "").encode("utf-8")).hexdigest()

    @classmethod
    def authority_content_hash(
        cls,
        text_value: str,
        *,
        media_url: str | None = None,
        media_type: str | None = None,
        media_caption: str | None = None,
    ) -> str:
        """Bind exact media identity into the authorized content hash.

        A text-only row keeps the original text digest, so existing durable approvals
        remain valid. When any media field is present the digest additionally commits
        to the exact media locator/kind/caption under a domain-separated preimage.
        Swapping an approved attachment for a different one therefore invalidates the
        authority instead of silently reusing it.

        Values are committed exactly as stored; no trimming or normalization is applied
        so WhatsApp formatting and locator identity stay preserved.
        """
        if not (media_url or media_type or media_caption):
            return cls.content_hash(text_value)
        preimage = json.dumps(
            {
                "text": text_value or "",
                "media_url": media_url or "",
                "media_type": media_type or "",
                "media_caption": media_caption or "",
            },
            separators=(",", ":"),
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(f"{cls._MEDIA_BINDING_DOMAIN}{preimage}".encode("utf-8")).hexdigest()

    @classmethod
    def content_hash_for_message(cls, message: Any) -> str:
        """Compute the media-aware authority digest for one concrete queue row."""
        return cls.authority_content_hash(
            str(getattr(message, "message_text", "") or ""),
            media_url=getattr(message, "media_url", None),
            media_type=getattr(message, "media_type", None),
            media_caption=getattr(message, "media_caption", None),
        )

    @classmethod
    def context_from_queue_message(cls, message: Any) -> AuthorizationContext | None:
        metadata = message.formatting_json if isinstance(getattr(message, "formatting_json", None), dict) else {}
        try:
            outbound_queue_id = int(message.id)
            inbound_message_id = int(metadata["inbound_message_id"])
            contact_id = int(metadata["contact_id"])
        except (KeyError, TypeError, ValueError):
            return None

        target_chat_id = str(getattr(message, "chat_id", "") or "").strip()
        response_category = str(metadata.get("response_category") or "normal_reply").strip().lower()
        expected_hash = str(metadata.get("content_sha256") or "").strip().lower()
        actual_hash = cls.content_hash_for_message(message)
        if not target_chat_id or expected_hash != actual_hash:
            return None

        return AuthorizationContext(
            outbound_queue_id=outbound_queue_id,
            inbound_message_id=inbound_message_id,
            contact_id=contact_id,
            target_chat_id=target_chat_id,
            content_sha256=actual_hash,
            response_category=response_category or "normal_reply",
        )

    async def authorize_queue_message(
        self,
        message: Any,
        *,
        now: datetime | None = None,
    ) -> tuple[AuthorizationContext | None, AuthorizationDecision]:
        """Authorize one concrete queue row without letting callers bypass context checks.

        This is the integration boundary for the delivery worker. Missing source/contact
        identifiers, a target mismatch, or content changed after the authority stamp all
        fail closed before any approval or contact-policy lookup can permit delivery.
        """
        context = self.context_from_queue_message(message)
        if context is None:
            return None, AuthorizationDecision(
                False,
                "none",
                "queue row missing exact durable authority context or content hash mismatch",
            )
        return context, await self.authorize(context, now=now)

    async def create_pending_approval(
        self,
        *,
        context: AuthorizationContext,
        ttl: timedelta = timedelta(minutes=30),
    ) -> int:
        expires_at = utcnow() + ttl
        result = await self.session.execute(
            text(
                """
                INSERT INTO outbound_approvals (
                    inbound_message_id, outbound_queue_id, target_chat_id,
                    content_sha256, status, expires_at, updated_at
                ) VALUES (
                    :inbound_message_id, :outbound_queue_id, :target_chat_id,
                    :content_sha256, 'pending', :expires_at, now()
                )
                ON CONFLICT (outbound_queue_id) DO UPDATE SET
                    target_chat_id = EXCLUDED.target_chat_id,
                    content_sha256 = EXCLUDED.content_sha256,
                    expires_at = EXCLUDED.expires_at,
                    updated_at = now()
                WHERE outbound_approvals.status = 'pending'
                RETURNING id
                """
            ),
            {
                "inbound_message_id": context.inbound_message_id,
                "outbound_queue_id": context.outbound_queue_id,
                "target_chat_id": context.target_chat_id,
                "content_sha256": context.content_sha256,
                "expires_at": expires_at,
            },
        )
        approval_id = result.scalar_one_or_none()
        if approval_id is None:
            raise ValueError("approval already finalized")
        return int(approval_id)

    async def approve_exact(
        self,
        *,
        approval_id: int,
        owner_identity: str,
        target_chat_id: str,
        content_sha256: str,
        now: datetime | None = None,
    ) -> bool:
        instant = now or utcnow()
        result = await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'approved', approved_by = :owner_identity,
                    approved_at = :instant, updated_at = :instant
                WHERE id = :approval_id
                  AND status = 'pending'
                  AND expires_at > :instant
                  AND target_chat_id = :target_chat_id
                  AND content_sha256 = :content_sha256
                RETURNING id
                """
            ),
            {
                "approval_id": approval_id,
                "owner_identity": owner_identity,
                "instant": instant,
                "target_chat_id": target_chat_id,
                "content_sha256": content_sha256,
            },
        )
        return result.scalar_one_or_none() is not None

    async def authorize(self, context: AuthorizationContext, *, now: datetime | None = None) -> AuthorizationDecision:
        instant = now or utcnow()

        approval = await self.session.execute(
            text(
                """
                SELECT id
                FROM outbound_approvals
                WHERE outbound_queue_id = :outbound_queue_id
                  AND inbound_message_id = :inbound_message_id
                  AND target_chat_id = :target_chat_id
                  AND content_sha256 = :content_sha256
                  AND status = 'approved'
                  AND expires_at > :instant
                LIMIT 1
                """
            ),
            {
                "outbound_queue_id": context.outbound_queue_id,
                "inbound_message_id": context.inbound_message_id,
                "target_chat_id": context.target_chat_id,
                "content_sha256": context.content_sha256,
                "instant": instant,
            },
        )
        approval_id = approval.scalar_one_or_none()
        if approval_id is not None:
            return AuthorizationDecision(True, "owner_approval", "exact active owner approval", approval_id=int(approval_id))

        policy = await self.session.execute(
            text(
                """
                SELECT id, allowed_categories, prohibited_categories,
                       approval_required_categories, quiet_hours_json
                FROM contact_automation_policies
                WHERE contact_id = :contact_id
                  AND exact_chat_id = :target_chat_id
                  AND enabled = true
                  AND disabled_at IS NULL
                  AND (expires_at IS NULL OR expires_at > :instant)
                LIMIT 1
                """
            ),
            {
                "contact_id": context.contact_id,
                "target_chat_id": context.target_chat_id,
                "instant": instant,
            },
        )
        row = policy.mappings().first()
        if row is None:
            return AuthorizationDecision(False, "none", "no exact active owner approval or contact automation policy")

        policy_id = int(row["id"])
        quiet_active = self._quiet_hours_active(row["quiet_hours_json"], instant)
        if quiet_active is None:
            return AuthorizationDecision(False, "contact_policy", "contact policy quiet-hours configuration invalid", policy_id=policy_id)
        if quiet_active:
            return AuthorizationDecision(False, "contact_policy", "contact policy quiet hours active", policy_id=policy_id)

        allowed = {str(value).strip().lower() for value in (row["allowed_categories"] or [])}
        prohibited = {str(value).strip().lower() for value in (row["prohibited_categories"] or [])}
        approval_required = {str(value).strip().lower() for value in (row["approval_required_categories"] or [])}
        category = context.response_category
        if category in prohibited:
            return AuthorizationDecision(False, "contact_policy", "response category prohibited by contact policy", policy_id=policy_id)
        if category in approval_required:
            return AuthorizationDecision(False, "contact_policy", "response category requires owner approval", policy_id=policy_id)
        if category not in allowed:
            return AuthorizationDecision(False, "contact_policy", "response category not explicitly allowed", policy_id=policy_id)
        return AuthorizationDecision(True, "contact_policy", "exact contact policy permits response category", policy_id=policy_id)

    @classmethod
    def _quiet_hours_active(cls, config: Any, instant: datetime) -> bool | None:
        if config is None:
            return False
        if not isinstance(config, dict) or instant.tzinfo is None or instant.utcoffset() is None:
            return None

        start = cls._clock_minutes(config.get("start"))
        end = cls._clock_minutes(config.get("end"))
        timezone_name = str(config.get("timezone") or "").strip()
        if start is None or end is None or not timezone_name:
            return None
        try:
            local = instant.astimezone(ZoneInfo(timezone_name))
        except ZoneInfoNotFoundError:
            return None

        current = local.hour * 60 + local.minute
        if start == end:
            return True
        if start < end:
            return start <= current < end
        return current >= start or current < end

    @staticmethod
    def _clock_minutes(value: Any) -> int | None:
        raw = str(value or "").strip()
        parts = raw.split(":")
        if len(parts) != 2 or len(parts[0]) != 2 or len(parts[1]) != 2:
            return None
        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return None
        if hour not in range(24) or minute not in range(60):
            return None
        return hour * 60 + minute

    async def consume_approval(self, approval_id: int, *, now: datetime | None = None) -> bool:
        instant = now or utcnow()
        result = await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'consumed', consumed_at = :instant, updated_at = :instant
                WHERE id = :approval_id AND status = 'approved' AND expires_at > :instant
                RETURNING id
                """
            ),
            {"approval_id": approval_id, "instant": instant},
        )
        return result.scalar_one_or_none() is not None
