from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.owner_contact_automation_policy_service import OwnerContactAutomationPolicyService


@dataclass(frozen=True, slots=True)
class OwnerContactAutomationPolicyCommandResult:
    consumed: bool
    action: str
    reply_text: str
    error: str | None = None
    policy_id: int | None = None


@dataclass(frozen=True, slots=True)
class ParsedContactAutomationPolicy:
    contact_id: int
    exact_chat_id: str
    allowed_categories: tuple[str, ...] = ()
    prohibited_categories: tuple[str, ...] = ()
    approval_required_categories: tuple[str, ...] = ()
    relationship_context: str | None = None
    tone_guidance: str | None = None
    quiet_hours: dict[str, str] | None = None
    expires_at: datetime | None = None


class OwnerContactAutomationPolicyCommandService:
    """OWNER-only adapter for exact-contact automation policy mutations.

    This adapter deliberately owns no command names or aliases and never resolves
    display names. Command Center must pass a normalized action and exact durable
    Identity Registry contact/chat identifiers. This prevents ambiguous-name grants.
    """

    ACTIONS = frozenset({"set", "disable"})
    OPTION_KEYS = frozenset({"allowed", "prohibited", "approval", "relationship", "tone", "quiet", "expires"})
    _QUIET_RE = re.compile(r"^(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})@(?P<timezone>[A-Za-z0-9_+\-/]+)$")

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
            parsed = self._parse_args(normalized_action, args)
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
                contact_id=parsed.contact_id,
                exact_chat_id=parsed.exact_chat_id,
            )
            verb = "disabled"
        else:
            result = await self.mutations.upsert_exact(
                permission=normalized_permission,
                owner_identity=self._bounded_owner_identity(owner_identity),
                contact_id=parsed.contact_id,
                exact_chat_id=parsed.exact_chat_id,
                enabled=True,
                allowed_categories=parsed.allowed_categories,
                prohibited_categories=parsed.prohibited_categories,
                approval_required_categories=parsed.approval_required_categories,
                relationship_context=parsed.relationship_context,
                tone_guidance=parsed.tone_guidance,
                quiet_hours=parsed.quiet_hours,
                expires_at=parsed.expires_at,
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
                f"Policy {verb} for exact contact `{parsed.contact_id}` / `{parsed.exact_chat_id}`."
            ),
            policy_id=result.policy_id,
        )

    @classmethod
    def _parse_args(cls, action: str, args: str) -> ParsedContactAutomationPolicy:
        raw = (args or "").strip()
        first, separator, remainder = raw.partition(" ")
        second, second_separator, policy_spec = remainder.strip().partition(" ") if separator else ("", "", "")

        try:
            contact_id = int(first)
        except (TypeError, ValueError) as exc:
            raise ValueError("Contact ID must be a positive integer from the Identity Registry.") from exc
        if contact_id <= 0:
            raise ValueError("Contact ID must be a positive integer from the Identity Registry.")

        exact_chat_id = second.strip()
        if not exact_chat_id or len(exact_chat_id) > 120 or "@" not in exact_chat_id:
            raise ValueError("Exact chat ID is required; display names and ambiguous names are not accepted.")

        if action == "disable":
            if second_separator and policy_spec.strip():
                raise ValueError("Usage: <contact-id> <exact-chat-id>")
            return ParsedContactAutomationPolicy(contact_id=contact_id, exact_chat_id=exact_chat_id)

        policy_spec = policy_spec.strip() if second_separator else ""
        if not policy_spec:
            raise ValueError("At least one allowed category is required.")

        if "=" not in policy_spec:
            allowed = cls._categories(policy_spec)
            if not allowed:
                raise ValueError("At least one allowed category is required.")
            return ParsedContactAutomationPolicy(
                contact_id=contact_id,
                exact_chat_id=exact_chat_id,
                allowed_categories=allowed,
            )

        options: dict[str, str] = {}
        for segment in policy_spec.split(";"):
            segment = segment.strip()
            if not segment:
                continue
            key, equals, value = segment.partition("=")
            normalized_key = key.strip().lower()
            if not equals or normalized_key not in cls.OPTION_KEYS:
                raise ValueError(f"Unsupported policy option: {key.strip() or segment}.")
            if normalized_key in options:
                raise ValueError(f"Duplicate policy option: {normalized_key}.")
            options[normalized_key] = value.strip()

        allowed = cls._categories(options.get("allowed", ""))
        if not allowed:
            raise ValueError("Option `allowed=` must include at least one category.")
        prohibited = cls._categories(options.get("prohibited", ""))
        approval = cls._categories(options.get("approval", ""))

        quiet_hours = cls._quiet_hours(options.get("quiet"))
        expires_at = cls._expires_at(options.get("expires"))

        relationship = cls._optional_text(options.get("relationship"), 2000)
        tone = cls._optional_text(options.get("tone"), 2000)

        return ParsedContactAutomationPolicy(
            contact_id=contact_id,
            exact_chat_id=exact_chat_id,
            allowed_categories=allowed,
            prohibited_categories=prohibited,
            approval_required_categories=approval,
            relationship_context=relationship,
            tone_guidance=tone,
            quiet_hours=quiet_hours,
            expires_at=expires_at,
        )

    @staticmethod
    def _categories(value: str) -> tuple[str, ...]:
        return tuple(item.strip().lower() for item in (value or "").split(",") if item.strip())

    @classmethod
    def _quiet_hours(cls, value: str | None) -> dict[str, str] | None:
        if value is None or not value.strip():
            return None
        match = cls._QUIET_RE.fullmatch(value.strip())
        if match is None:
            raise ValueError("Quiet hours must use HH:MM-HH:MM@Timezone, for example 22:00-07:00@Africa/Lagos.")
        start = cls._clock(match.group("start"))
        end = cls._clock(match.group("end"))
        timezone_name = match.group("timezone")
        try:
            ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Quiet-hours timezone is not recognized.") from exc
        return {"start": start, "end": end, "timezone": timezone_name}

    @staticmethod
    def _clock(value: str) -> str:
        try:
            hour_text, minute_text = value.split(":", 1)
            hour = int(hour_text)
            minute = int(minute_text)
        except (TypeError, ValueError) as exc:
            raise ValueError("Quiet-hours clock must use HH:MM.") from exc
        if hour not in range(24) or minute not in range(60):
            raise ValueError("Quiet-hours clock is outside the valid 00:00-23:59 range.")
        return f"{hour:02d}:{minute:02d}"

    @staticmethod
    def _expires_at(value: str | None) -> datetime | None:
        if value is None or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError("Expiry must be an ISO-8601 timestamp with timezone offset.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Expiry must include a timezone offset.")
        return parsed

    @staticmethod
    def _optional_text(value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if len(cleaned) > limit:
            raise ValueError(f"Policy text must be at most {limit} characters.")
        return cleaned or None

    @staticmethod
    def _bounded_owner_identity(value: str) -> str:
        normalized = (value or "").strip()
        return normalized[:160] if normalized else "owner"
