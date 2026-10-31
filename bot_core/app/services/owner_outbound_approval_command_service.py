from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.owner_outbound_approval_service import OwnerOutboundApprovalService


@dataclass(frozen=True, slots=True)
class OwnerOutboundApprovalCommandResult:
    consumed: bool
    action: str
    reply_text: str
    error: str | None = None
    approval_id: int | None = None
    outbound_queue_id: int | None = None


class OwnerOutboundApprovalCommandService:
    """OWNER-only adapter between Command Center and durable approval mutations.

    This class deliberately owns no command names or aliases. Command Center remains
    the sole parser/alias authority and passes only a normalized action plus arguments.
    ADMIN/USER permissions fail closed before OwnerOutboundApprovalService is invoked.
    """

    ACTIONS = frozenset({"info", "approve", "edit", "reject", "requeue"})

    def __init__(
        self,
        session: AsyncSession,
        *,
        mutation_service: OwnerOutboundApprovalService | Any | None = None,
    ) -> None:
        self.session = session
        self.mutations = mutation_service or OwnerOutboundApprovalService(session)

    async def handle(
        self,
        action: str,
        args: str,
        *,
        permission: str,
        owner_identity: str,
    ) -> OwnerOutboundApprovalCommandResult:
        normalized_action = (action or "").strip().lower()
        normalized_permission = (permission or "").strip().lower()

        if normalized_action not in self.ACTIONS:
            return OwnerOutboundApprovalCommandResult(
                consumed=False,
                action=normalized_action,
                reply_text="",
                error="unsupported approval action",
            )

        if normalized_permission != "owner":
            return OwnerOutboundApprovalCommandResult(
                consumed=True,
                action=normalized_action,
                reply_text="Owner command. Access denied.",
                error="owner permission required",
            )

        try:
            approval_id, payload = self._parse_args(normalized_action, args)
        except ValueError as exc:
            return OwnerOutboundApprovalCommandResult(
                consumed=True,
                action=normalized_action,
                reply_text=f"*Command Error*\n\n{exc}",
                error="invalid approval command arguments",
            )

        if normalized_action == "info":
            result = await self.mutations.inspect(approval_id)
        elif normalized_action == "approve":
            result = await self.mutations.approve(
                approval_id,
                owner_identity=self._bounded_owner_identity(owner_identity),
            )
        elif normalized_action == "edit":
            result = await self.mutations.edit(approval_id, payload)
        elif normalized_action == "reject":
            result = await self.mutations.reject(approval_id)
        else:
            result = await self.mutations.requeue(approval_id)

        return OwnerOutboundApprovalCommandResult(
            consumed=True,
            action=normalized_action,
            reply_text=result.reply_text,
            error=result.error,
            approval_id=approval_id,
            outbound_queue_id=result.outbound_queue_id,
        )

    @staticmethod
    def _parse_args(action: str, args: str) -> tuple[int, str]:
        raw = (args or "").strip()
        if not raw:
            raise ValueError(OwnerOutboundApprovalCommandService._usage(action))

        first, separator, remainder = raw.partition(" ")
        try:
            approval_id = int(first)
        except (TypeError, ValueError) as exc:
            raise ValueError("Approval ID must be a positive integer.") from exc
        if approval_id <= 0:
            raise ValueError("Approval ID must be a positive integer.")

        payload = remainder.strip() if separator else ""
        if action == "edit" and not payload:
            raise ValueError(OwnerOutboundApprovalCommandService._usage(action))
        if action != "edit" and payload:
            raise ValueError(OwnerOutboundApprovalCommandService._usage(action))
        return approval_id, payload

    @staticmethod
    def _usage(action: str) -> str:
        if action == "edit":
            return "Usage: <approval-id> <replacement text>"
        return "Usage: <approval-id>"

    @staticmethod
    def _bounded_owner_identity(value: str) -> str:
        """Keep durable attribution bounded and free of message/body content."""
        normalized = (value or "").strip()
        if not normalized:
            return "owner"
        return normalized[:160]
