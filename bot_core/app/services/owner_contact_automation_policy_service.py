from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class ContactAutomationPolicyResult:
    ok: bool
    policy_id: int | None
    error: str | None = None


class OwnerContactAutomationPolicyService:
    """OWNER-only mutations for one exact durable contact identity.

    This service never resolves display names and never sends messages. Callers must
    supply the Identity Registry's durable contact id together with its exact chat id.
    Command Center remains responsible for aliases/parsing and OWNER identity gates.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_exact(
        self,
        *,
        permission: str,
        owner_identity: str,
        contact_id: int,
        exact_chat_id: str,
        enabled: bool,
        allowed_categories: Iterable[str],
        prohibited_categories: Iterable[str] = (),
        approval_required_categories: Iterable[str] = (),
        relationship_context: str | None = None,
        tone_guidance: str | None = None,
        quiet_hours: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> ContactAutomationPolicyResult:
        if self._permission(permission) != "owner":
            return ContactAutomationPolicyResult(False, None, "owner permission required")

        normalized = self._exact_identity(contact_id, exact_chat_id)
        if normalized is None:
            return ContactAutomationPolicyResult(False, None, "exact contact identity required")
        durable_contact_id, durable_chat_id = normalized

        allowed = self._categories(allowed_categories)
        prohibited = self._categories(prohibited_categories)
        approval_required = self._categories(approval_required_categories)
        if not allowed:
            return ContactAutomationPolicyResult(False, None, "at least one allowed category required")
        if allowed & prohibited:
            return ContactAutomationPolicyResult(False, None, "allowed and prohibited categories overlap")
        if expires_at is not None and expires_at <= utcnow():
            return ContactAutomationPolicyResult(False, None, "policy expiry must be in the future")

        created_by = (owner_identity or "").strip()[:120]
        if not created_by:
            return ContactAutomationPolicyResult(False, None, "owner identity required")

        result = await self.session.execute(
            text(
                """
                INSERT INTO contact_automation_policies (
                    contact_id, exact_chat_id, enabled, relationship_context,
                    tone_guidance, allowed_categories, prohibited_categories,
                    approval_required_categories, quiet_hours_json, expires_at,
                    created_by, disabled_at, updated_at
                ) VALUES (
                    :contact_id, :exact_chat_id, :enabled, :relationship_context,
                    :tone_guidance, CAST(:allowed_categories AS jsonb),
                    CAST(:prohibited_categories AS jsonb),
                    CAST(:approval_required_categories AS jsonb),
                    CAST(:quiet_hours_json AS jsonb), :expires_at,
                    :created_by, CASE WHEN :enabled THEN NULL ELSE :instant END, :instant
                )
                ON CONFLICT (contact_id, exact_chat_id) DO UPDATE SET
                    enabled = EXCLUDED.enabled,
                    relationship_context = EXCLUDED.relationship_context,
                    tone_guidance = EXCLUDED.tone_guidance,
                    allowed_categories = EXCLUDED.allowed_categories,
                    prohibited_categories = EXCLUDED.prohibited_categories,
                    approval_required_categories = EXCLUDED.approval_required_categories,
                    quiet_hours_json = EXCLUDED.quiet_hours_json,
                    expires_at = EXCLUDED.expires_at,
                    created_by = EXCLUDED.created_by,
                    disabled_at = CASE WHEN EXCLUDED.enabled THEN NULL ELSE :instant END,
                    updated_at = :instant
                RETURNING id
                """
            ),
            {
                "contact_id": durable_contact_id,
                "exact_chat_id": durable_chat_id,
                "enabled": bool(enabled),
                "relationship_context": self._bounded_text(relationship_context, 2000),
                "tone_guidance": self._bounded_text(tone_guidance, 2000),
                "allowed_categories": json.dumps(sorted(allowed)),
                "prohibited_categories": json.dumps(sorted(prohibited)),
                "approval_required_categories": json.dumps(sorted(approval_required)),
                "quiet_hours_json": json.dumps(quiet_hours) if quiet_hours is not None else "null",
                "expires_at": expires_at,
                "created_by": created_by,
                "instant": utcnow(),
            },
        )
        policy_id = result.scalar_one_or_none()
        if policy_id is None:
            return ContactAutomationPolicyResult(False, None, "policy mutation failed")
        await self.session.flush()
        return ContactAutomationPolicyResult(True, int(policy_id), None)

    async def disable_exact(
        self,
        *,
        permission: str,
        owner_identity: str,
        contact_id: int,
        exact_chat_id: str,
    ) -> ContactAutomationPolicyResult:
        if self._permission(permission) != "owner":
            return ContactAutomationPolicyResult(False, None, "owner permission required")
        normalized = self._exact_identity(contact_id, exact_chat_id)
        if normalized is None:
            return ContactAutomationPolicyResult(False, None, "exact contact identity required")
        durable_contact_id, durable_chat_id = normalized
        if not (owner_identity or "").strip():
            return ContactAutomationPolicyResult(False, None, "owner identity required")

        instant = utcnow()
        result = await self.session.execute(
            text(
                """
                UPDATE contact_automation_policies
                SET enabled = false, disabled_at = :instant, updated_at = :instant
                WHERE contact_id = :contact_id AND exact_chat_id = :exact_chat_id
                  AND enabled = true
                RETURNING id
                """
            ),
            {
                "contact_id": durable_contact_id,
                "exact_chat_id": durable_chat_id,
                "instant": instant,
            },
        )
        policy_id = result.scalar_one_or_none()
        if policy_id is None:
            return ContactAutomationPolicyResult(False, None, "active exact-contact policy not found")
        await self.session.flush()
        return ContactAutomationPolicyResult(True, int(policy_id), None)

    @staticmethod
    def _permission(permission: str) -> str:
        return (permission or "").strip().lower()

    @staticmethod
    def _exact_identity(contact_id: int, exact_chat_id: str) -> tuple[int, str] | None:
        try:
            durable_contact_id = int(contact_id)
        except (TypeError, ValueError):
            return None
        durable_chat_id = (exact_chat_id or "").strip()
        if durable_contact_id <= 0 or not durable_chat_id or len(durable_chat_id) > 120:
            return None
        return durable_contact_id, durable_chat_id

    @staticmethod
    def _categories(values: Iterable[str]) -> set[str]:
        return {
            str(value).strip().lower()
            for value in (values or ())
            if str(value).strip()
        }

    @staticmethod
    def _bounded_text(value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned[:limit] if cleaned else None
