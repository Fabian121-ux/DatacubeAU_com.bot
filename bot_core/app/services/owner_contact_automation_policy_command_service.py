from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.owner_contact_automation_policy_service import OwnerContactAutomationPolicyService


@dataclass(frozen=True, slots=True)
class OwnerContactAutomationPolicyCommandResult:
    consumed: bool
    action: str
    reply_text: str
    error: str | None = None
    policy_id: int | None = None


class OwnerContactAutomationPolicyCommandService:
    """OWNER-only adapter for exact-contact automation policy mutations.

    This adapter deliberately owns no command names or aliases and never resolves
    display names. Command Center must pass a normalized action and exact durable
    Identity Registry contact/chat identifiers. This prevents ambiguous-name grants.
    """

    ACTIONS = frozenset({"set", "disable"})

    def __init__(
        self,
        session: AsyncSession,
        *,
        mutation_service: OwnerContactAutomationPolicyService | Any | None = None,
    ) -> None:
        self.session = session
        self.mutations = mutation_service or OwnerContactAutomationPolicyService(session)

    async def handle(
        self,
        action: str,
        args: str,
        *,
        permission: str,
        owner_identity: str,
    ) -> OwnerContactAutomationPolicyCommandResult:
        normalized_action = (action or "").strip().lower()
        normalized_permission = (permission or "").strip().lower()

        if normalized_action not in self.ACTIONS:
            return OwnerContactAutomationPolicyCommandResult(
                consumed=False,
                action=normalized_action,
                reply_text="",
                error="unsupported contact automation action",
            )

        if normalized_permission != "owner":
            return OwnerContactAutomationPolicyCommandResult(
                consumed=True,
                action=normalized_action,
                reply_text="Owner command. Access denied.",
                error="owner permission required",
            )

        try:
            contact_id, exact_chat_id, allowed_categories = self._parse_args(normalized_action, args)
        except ValueError as exc:
            return OwnerContactAutomationPolicyCommandResult(
                consumed=True,
                action=normalized_action,
                reply_text=f"*Command Error*\n\n{exc}",
                error="invalid contact automation command arguments",
            )

        if normalized_action == "disable":
            result = await self.mutations.disable_exact(
                permission=normalized_permission,
                owner_identity=self._bounded_owner_identity(owner_identity),
                contact_id=contact_id,
                exact_chat_id=exact_chat_id,
            )
            verb = "disabled"
        else:
            result = await self.mutations.upsert_exact(
                permission=normalized_permission,
                owner_identity=self._bounded_owner_identity(owner_identity),
                contact_id=contact_id,
                exact_chat_id=exact_chat_id,
                enabled=True,
                allowed_categories=allowed_categories,
            )
            verb = "enabled"

        if not result.ok:
            return OwnerContactAutomationPolicyCommandResult(
                consumed=True,
                action=normalized_action,
                reply_text=f"*Contact Automation*\n\nNot changed: {result.error or 'policy mutation failed'}.",
                error=result.error or "policy mutation failed",
                policy_id=result.policy_id,
            )

        return OwnerContactAutomationPolicyCommandResult(
            consumed=True,
            action=normalized_action,
            reply_text=(
                "*Contact Automation*\n\n"
                f"Policy {verb} for exact contact `{contact_id}` / `{exact_chat_id}`."
            ),
            policy_id=result.policy_id,
        )

    @staticmethod
    def _parse_args(action: str, args: str) -> tuple[int, str, tuple[str, ...]]:
        parts = (args or "").strip().split()
        required = 2 if action == "disable" else 3
        if len(parts) != required:
            if action == "disable":
                raise ValueError("Usage: <contact-id> <exact-chat-id>")
            raise ValueError("Usage: <contact-id> <exact-chat-id> <allowed-category[,category...]>")

        try:
            contact_id = int(parts[0])
        except (TypeError, ValueError) as exc:
            raise ValueError("Contact ID must be a positive integer from the Identity Registry.") from exc
        if contact_id <= 0:
            raise ValueError("Contact ID must be a positive integer from the Identity Registry.")

        exact_chat_id = parts[1].strip()
        if not exact_chat_id or len(exact_chat_id) > 120 or "@" not in exact_chat_id:
            raise ValueError("Exact chat ID is required; display names and ambiguous names are not accepted.")

        if action == "disable":
            return contact_id, exact_chat_id, ()

        allowed = tuple(
            value.strip().lower()
            for value in parts[2].split(",")
            if value.strip()
        )
        if not allowed:
            raise ValueError("At least one allowed category is required.")
        return contact_id, exact_chat_id, allowed

    @staticmethod
    def _bounded_owner_identity(value: str) -> str:
        normalized = (value or "").strip()
        return normalized[:160] if normalized else "owner"
