from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
from typing import Any

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

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def content_hash(text_value: str) -> str:
        return hashlib.sha256((text_value or "").encode("utf-8")).hexdigest()

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
        actual_hash = cls.content_hash(str(getattr(message, "message_text", "") or ""))
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
                SELECT id, allowed_categories, prohibited_categories, approval_required_categories
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

        allowed = {str(value).strip().lower() for value in (row["allowed_categories"] or [])}
        prohibited = {str(value).strip().lower() for value in (row["prohibited_categories"] or [])}
        approval_required = {str(value).strip().lower() for value in (row["approval_required_categories"] or [])}
        category = context.response_category
        if category in prohibited:
            return AuthorizationDecision(False, "contact_policy", "response category prohibited by contact policy", policy_id=int(row["id"]))
        if category in approval_required:
            return AuthorizationDecision(False, "contact_policy", "response category requires owner approval", policy_id=int(row["id"]))
        if category not in allowed:
            return AuthorizationDecision(False, "contact_policy", "response category not explicitly allowed", policy_id=int(row["id"]))
        return AuthorizationDecision(True, "contact_policy", "exact contact policy permits response category", policy_id=int(row["id"]))

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
