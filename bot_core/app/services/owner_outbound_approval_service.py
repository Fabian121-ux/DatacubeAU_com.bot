from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class OwnerApprovalMutationResult:
    ok: bool
    action: str
    approval_id: int
    reply_text: str
    outbound_queue_id: int | None = None
    error: str | None = None


class OwnerOutboundApprovalService:
    """Exact-ID OWNER mutations for deferred outbound approvals.

    This service owns no command aliases and never calls WAHA. It mutates only the
    existing durable approval + Outbound Queue rows inside the caller transaction.
    Command Center remains the only place that may expose these operations to OWNER.
    """

    MAX_EDIT_CHARS = 4096

    def __init__(self, session: AsyncSession):
        self.session = session

    async def inspect(self, approval_id: int, *, now: datetime | None = None) -> OwnerApprovalMutationResult:
        instant = now or utcnow()
        row = await self._load_exact(approval_id, lock=False)
        if row is None:
            return self._deny("info", approval_id, "Approval not found.", "approval not found")
        if row["status"] == "pending" and row["expires_at"] <= instant:
            await self._expire(approval_id, instant)
            row = {**row, "status": "expired"}
        return OwnerApprovalMutationResult(
            True,
            "info",
            approval_id,
            (
                f"Approval #{approval_id}\n"
                f"Status: {row['status']}\n"
                f"Queue: {row['outbound_queue_id']}\n"
                f"Target: {row['target_chat_id']}\n"
                f"Queue status: {row['queue_status']}"
            ),
            outbound_queue_id=int(row["outbound_queue_id"]),
        )

    async def approve(
        self,
        approval_id: int,
        *,
        owner_identity: str,
        now: datetime | None = None,
    ) -> OwnerApprovalMutationResult:
        instant = now or utcnow()
        await self._lock(approval_id)
        row = await self._load_exact(approval_id, lock=True)
        validation = await self._validate_pending(row, approval_id, instant, action="approve")
        if validation is not None:
            return validation

        result = await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'approved', approved_by = :owner_identity,
                    approved_at = :instant, updated_at = :instant
                WHERE id = :approval_id AND status = 'pending'
                RETURNING outbound_queue_id
                """
            ),
            {"approval_id": approval_id, "owner_identity": owner_identity, "instant": instant},
        )
        queue_id = result.scalar_one_or_none()
        if queue_id is None:
            return self._deny("approve", approval_id, "Approval changed before it could be approved.", "approval state changed")

        await self.session.execute(
            text(
                """
                UPDATE outbound_queue
                SET status = 'pending', next_attempt_at = :instant,
                    error_message = NULL, updated_at = :instant
                WHERE id = :queue_id
                  AND status = 'deferred'
                """
            ),
            {"queue_id": int(queue_id), "instant": instant},
        )
        await self._audit(
            row,
            decision="approve",
            reason="exact single-use owner approval granted and exact deferred row requeued",
        )
        return OwnerApprovalMutationResult(
            True,
            "approve",
            approval_id,
            f"Approved #{approval_id}. Exact queue row {int(queue_id)} is eligible for one authorized delivery.",
            outbound_queue_id=int(queue_id),
        )

    async def reject(self, approval_id: int, *, now: datetime | None = None) -> OwnerApprovalMutationResult:
        instant = now or utcnow()
        await self._lock(approval_id)
        row = await self._load_exact(approval_id, lock=True)
        validation = await self._validate_pending(row, approval_id, instant, action="reject")
        if validation is not None:
            return validation

        result = await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'rejected', rejected_at = :instant, updated_at = :instant
                WHERE id = :approval_id AND status = 'pending'
                RETURNING outbound_queue_id
                """
            ),
            {"approval_id": approval_id, "instant": instant},
        )
        queue_id = result.scalar_one_or_none()
        if queue_id is None:
            return self._deny("reject", approval_id, "Approval changed before it could be rejected.", "approval state changed")
        await self.session.execute(
            text(
                """
                UPDATE outbound_queue
                SET status = 'deferred', error_message = 'owner rejected outbound approval', updated_at = :instant
                WHERE id = :queue_id AND status <> 'sent'
                """
            ),
            {"queue_id": int(queue_id), "instant": instant},
        )
        await self._audit(row, decision="reject", reason="exact owner approval rejected")
        return OwnerApprovalMutationResult(
            True,
            "reject",
            approval_id,
            f"Rejected #{approval_id}. No send authority remains for queue row {int(queue_id)}.",
            outbound_queue_id=int(queue_id),
        )

    async def edit(
        self,
        approval_id: int,
        new_text: str,
        *,
        now: datetime | None = None,
    ) -> OwnerApprovalMutationResult:
        instant = now or utcnow()
        new_text = (new_text or "").strip()
        if not new_text:
            return self._deny("edit", approval_id, "Replacement text is required.", "empty replacement text")
        if len(new_text) > self.MAX_EDIT_CHARS:
            return self._deny(
                "edit",
                approval_id,
                f"Replacement text is too long. Maximum is {self.MAX_EDIT_CHARS} characters.",
                "replacement text too long",
            )

        await self._lock(approval_id)
        row = await self._load_exact(approval_id, lock=True)
        validation = await self._validate_pending(row, approval_id, instant, action="edit")
        if validation is not None:
            return validation

        digest = OutboundAuthorizationService.authority_content_hash(
            new_text,
            media_url=row.get("media_url"),
            media_type=row.get("media_type"),
            media_caption=row.get("media_caption"),
        )
        formatting = dict(row["formatting_json"] or {})
        formatting["content_sha256"] = digest

        await self.session.execute(
            text(
                """
                UPDATE outbound_queue
                SET message_text = :message_text,
                    formatting_json = CAST(:formatting_json AS jsonb),
                    status = 'deferred', error_message = NULL, updated_at = :instant
                WHERE id = :queue_id AND status = 'deferred'
                """
            ),
            {
                "queue_id": int(row["outbound_queue_id"]),
                "message_text": new_text,
                "formatting_json": self._json_dumps(formatting),
                "instant": instant,
            },
        )
        await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET content_sha256 = :content_sha256, updated_at = :instant
                WHERE id = :approval_id AND status = 'pending'
                """
            ),
            {"approval_id": approval_id, "content_sha256": digest, "instant": instant},
        )
        await self._audit(row, decision="allow", reason="owner edited exact deferred draft; approval remains pending")
        return OwnerApprovalMutationResult(
            True,
            "edit",
            approval_id,
            f"Edited #{approval_id}. The draft remains deferred and still requires OWNER approval.",
            outbound_queue_id=int(row["outbound_queue_id"]),
        )

    async def requeue(self, approval_id: int, *, now: datetime | None = None) -> OwnerApprovalMutationResult:
        instant = now or utcnow()
        await self._lock(approval_id)
        row = await self._load_exact(approval_id, lock=True)
        if row is None:
            return self._deny("requeue", approval_id, "Approval not found.", "approval not found")
        mismatch = self._authority_mismatch(row)
        if mismatch:
            await self._audit(row, decision="deny", reason=mismatch)
            return self._deny("requeue", approval_id, "Requeue denied: durable authority no longer matches the exact queue row.", mismatch)
        if row["status"] != "approved":
            return self._deny("requeue", approval_id, "Requeue requires an already-approved, unconsumed approval.", "approval not active")
        if row["expires_at"] <= instant:
            await self._expire(approval_id, instant)
            return self._deny("requeue", approval_id, "Approval expired. Requeue denied.", "approval expired")
        if row["queue_status"] not in {"deferred", "failed"}:
            return self._deny(
                "requeue",
                approval_id,
                f"Queue row is {row['queue_status']}; requeue is allowed only from deferred/failed.",
                "queue row not safely requeueable",
            )

        await self.session.execute(
            text(
                """
                UPDATE outbound_queue
                SET status = 'pending', next_attempt_at = :instant,
                    error_message = NULL, updated_at = :instant
                WHERE id = :queue_id AND status IN ('deferred', 'failed')
                """
            ),
            {"queue_id": int(row["outbound_queue_id"]), "instant": instant},
        )
        await self._audit(row, decision="allow", reason="exact approved unconsumed row explicitly requeued by owner")
        return OwnerApprovalMutationResult(
            True,
            "requeue",
            approval_id,
            f"Requeued approved row {int(row['outbound_queue_id'])}. Existing exact approval remains single-use.",
            outbound_queue_id=int(row["outbound_queue_id"]),
        )

    async def _validate_pending(
        self,
        row: dict[str, Any] | None,
        approval_id: int,
        instant: datetime,
        *,
        action: str,
    ) -> OwnerApprovalMutationResult | None:
        if row is None:
            return self._deny(action, approval_id, "Approval not found.", "approval not found")
        mismatch = self._authority_mismatch(row)
        if mismatch:
            await self._audit(row, decision="deny", reason=mismatch)
            return self._deny(action, approval_id, "Approval denied: durable authority no longer matches the exact queue row.", mismatch)
        if row["status"] != "pending":
            return self._deny(action, approval_id, f"Approval is already {row['status']}.", "approval not pending")
        if row["expires_at"] <= instant:
            await self._expire(approval_id, instant)
            return self._deny(action, approval_id, "Approval expired.", "approval expired")
        if row["queue_status"] != "deferred":
            return self._deny(action, approval_id, f"Queue row is {row['queue_status']}; expected deferred.", "queue row not deferred")
        return None

    @staticmethod
    def _authority_mismatch(row: dict[str, Any]) -> str | None:
        formatting = row.get("formatting_json") if isinstance(row.get("formatting_json"), dict) else {}
        try:
            inbound_id = int(formatting["inbound_message_id"])
            contact_id = int(formatting["contact_id"])
        except (KeyError, TypeError, ValueError):
            return "queue row missing durable inbound/contact authority metadata"
        if inbound_id != int(row["inbound_message_id"]):
            return "approval inbound identity does not match queue authority"
        if contact_id <= 0:
            return "queue contact identity is invalid"
        if str(row["target_chat_id"] or "").strip() != str(row["queue_chat_id"] or "").strip():
            return "approval target does not match queue target"
        actual_hash = OutboundAuthorizationService.authority_content_hash(
            str(row["message_text"] or ""),
            media_url=row.get("media_url"),
            media_type=row.get("media_type"),
            media_caption=row.get("media_caption"),
        )
        if str(row["content_sha256"] or "").lower() != actual_hash:
            return "approval content hash does not match queue content"
        if str(formatting.get("content_sha256") or "").lower() != actual_hash:
            return "queue authority content hash does not match queue content"
        if str(formatting.get("delivery_policy") or "").strip().lower() not in {"approval_required", "authorized_external"}:
            return "queue row is not on an external authorization-controlled delivery policy"
        return None

    async def _load_exact(self, approval_id: int, *, lock: bool) -> dict[str, Any] | None:
        suffix = " FOR UPDATE OF a, q" if lock else ""
        result = await self.session.execute(
            text(
                """
                SELECT a.id, a.inbound_message_id, a.outbound_queue_id,
                       a.target_chat_id, a.content_sha256, a.status, a.expires_at,
                       q.chat_id AS queue_chat_id, q.message_text, q.status AS queue_status,
                       q.media_url, q.media_type, q.media_caption,
                       q.formatting_json
                FROM outbound_approvals a
                JOIN outbound_queue q ON q.id = a.outbound_queue_id
                WHERE a.id = :approval_id
                """ + suffix
            ),
            {"approval_id": approval_id},
        )
        row = result.mappings().first()
        return dict(row) if row is not None else None

    async def _lock(self, approval_id: int) -> None:
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": 930000000 + int(approval_id)},
        )

    async def _expire(self, approval_id: int, instant: datetime) -> None:
        await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'expired', updated_at = :instant
                WHERE id = :approval_id AND status IN ('pending', 'approved')
                """
            ),
            {"approval_id": approval_id, "instant": instant},
        )

    async def _audit(self, row: dict[str, Any], *, decision: str, reason: str) -> None:
        formatting = row.get("formatting_json") if isinstance(row.get("formatting_json"), dict) else {}
        contact_id = formatting.get("contact_id")
        try:
            contact_id = int(contact_id) if contact_id is not None else None
        except (TypeError, ValueError):
            contact_id = None
        await self.session.execute(
            text(
                """
                INSERT INTO outbound_authorization_audit (
                    outbound_queue_id, inbound_message_id, contact_id, target_chat_id,
                    authority_type, decision, reason, details_json
                ) VALUES (
                    :outbound_queue_id, :inbound_message_id, :contact_id, :target_chat_id,
                    'owner_command', :decision, :reason, NULL
                )
                """
            ),
            {
                "outbound_queue_id": int(row["outbound_queue_id"]),
                "inbound_message_id": int(row["inbound_message_id"]),
                "contact_id": contact_id,
                "target_chat_id": str(row["target_chat_id"]),
                "decision": decision,
                "reason": reason[:240],
            },
        )

    @staticmethod
    def _deny(action: str, approval_id: int, text_value: str, error: str) -> OwnerApprovalMutationResult:
        return OwnerApprovalMutationResult(False, action, approval_id, text_value, error=error)

    @staticmethod
    def _json_dumps(value: dict[str, Any]) -> str:
        import json

        return json.dumps(value, separators=(",", ":"), sort_keys=True)
