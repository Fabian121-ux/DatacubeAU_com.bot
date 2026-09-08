from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import (
    AuditLog,
    OutboundMessageSet,
    OutboundMessageVariant,
    OutboundVariantUsage,
)
from app.utils.time import utcnow

_TOKEN_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")
# Any "{{...}}"-shaped span, whether or not its contents are a valid identifier. Used
# only to detect a malformed placeholder (e.g. a typo'd hyphen) that _TOKEN_PATTERN
# would otherwise silently ignore rather than substitute.
_LOOSE_BRACE_PATTERN = re.compile(r"\{\{(.*?)\}\}")
_VALID_TOKEN_CONTENT = re.compile(r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*$")


@dataclass(slots=True)
class LibraryResult:
    ok: bool
    id: int | None = None
    error: str | None = None


@dataclass(slots=True)
class RenderResult:
    ok: bool
    text: str | None = None
    missing_variables: list[str] = field(default_factory=list)
    error: str | None = None


class OutboundMessageLibraryService:
    """Reusable outbound message library: "WHAT COULD ZINA SAY?" (roadmap Phase 17).

    This is the message-content layer only — `OutboundMessageSet` and
    `OutboundMessageVariant`, plus an `OutboundVariantUsage` analytics/audit trail.
    It answers "what could Zina say", never "may Zina send". Nothing in this service
    reads or writes `outbound_queue`, `contact_automation_policies`,
    `outbound_approvals`, or any Authority Engine primitive, and no producer or
    delivery path calls it yet — selecting a variant here has zero effect on outbound
    behavior until a future, separately reviewed Selection Engine / producer wires it
    into the existing per-recipient authorization flow
    (see docs/ZINA_IMPLEMENTATION_ROADMAP.md, Phase 17, "Authority separation").

    Every bounded field is length/shape-checked before the row ever reaches
    ``flush()``, matching the fail-closed validation pattern established by
    ``PrivateMediaArtifactService``. ``selection_strategy``/``status``/``send_result``
    are closed allowlists rather than arbitrary text, for the same reason
    ``PrivateMediaArtifactService.ALLOWED_RETENTION_POLICIES`` is closed: expanding the
    set is deliberately the trigger for the future work that would make the new value
    meaningful, not something to accept ahead of it.

    A variant's ``required_variables`` must equal, exactly, the set of ``{{token}}``
    placeholders that actually appear in its ``template_body`` — enforced at creation
    time. This makes rendering unambiguous: every token in the body has a declared
    name, and every declared name is used. ``render()`` never invents a value for a
    missing variable; a caller must source real values from an authoritative Zina
    domain (Identity Registry, Contact, conversation context) and pass them in. A
    variable missing from that input fails the render closed rather than falling back
    to guessed or blank text.
    """

    ALLOWED_SELECTION_STRATEGIES = frozenset({"deterministic_score"})
    ALLOWED_VARIANT_STATUSES = frozenset({"draft", "approved"})
    ALLOWED_SEND_RESULTS = frozenset({"pending", "sent", "failed", "blocked"})

    MAX_KEY_LENGTH = 120
    MAX_NAME_LENGTH = 180
    MAX_CATEGORY_LENGTH = 80
    MAX_CHANNEL_LENGTH = 40
    MAX_LANGUAGE_LENGTH = 20
    MAX_LABEL_LENGTH = 40
    MAX_TEMPLATE_BODY_LENGTH = 4000
    MAX_MEDIA_KIND_LENGTH = 40
    MAX_MEDIA_MIME_LENGTH = 160
    MAX_SOURCE_AUTOMATION_LENGTH = 120
    MAX_CREATED_BY_LENGTH = 120
    MIN_WEIGHT = 1
    MAX_WEIGHT = 100

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------------------
    # Message sets
    # ------------------------------------------------------------------------------

    async def create_message_set(
        self,
        *,
        set_key: str,
        name: str,
        description: str,
        category: str,
        purpose: str | None = None,
        channel: str = "whatsapp",
        primary_language: str | None = None,
        selection_strategy: str = "deterministic_score",
        created_by: str | None = None,
        request_id: str | None = None,
    ) -> LibraryResult:
        set_key = str(set_key or "").strip()
        name = str(name or "").strip()
        description = str(description or "").strip()
        category = str(category or "").strip()
        channel = str(channel or "").strip()
        created_by = str(created_by).strip() if created_by else None

        if not set_key or len(set_key) > self.MAX_KEY_LENGTH:
            return LibraryResult(False, error="invalid set_key")
        if not name or len(name) > self.MAX_NAME_LENGTH:
            return LibraryResult(False, error="invalid name")
        if not description:
            return LibraryResult(False, error="description is required")
        if not category or len(category) > self.MAX_CATEGORY_LENGTH:
            return LibraryResult(False, error="invalid category")
        if not channel or len(channel) > self.MAX_CHANNEL_LENGTH:
            return LibraryResult(False, error="invalid channel")
        if primary_language is not None and len(primary_language) > self.MAX_LANGUAGE_LENGTH:
            return LibraryResult(False, error="invalid primary_language")
        if created_by is not None and len(created_by) > self.MAX_CREATED_BY_LENGTH:
            return LibraryResult(False, error="invalid created_by")
        if selection_strategy not in self.ALLOWED_SELECTION_STRATEGIES:
            return LibraryResult(
                False,
                error=(
                    f"selection_strategy {selection_strategy!r} is not enabled yet; "
                    f"only {sorted(self.ALLOWED_SELECTION_STRATEGIES)} is accepted"
                ),
            )

        # set_key is a permanent identifier, the same convention Identity Registry uses
        # for registry_key: once used, never reused, even after delete()'s tombstone.
        # The column carries an unconditional (not partial) UNIQUE constraint, so a
        # deleted row must be rejected here too, rather than left to crash flush().
        existing = (
            await self.session.execute(
                select(OutboundMessageSet).where(OutboundMessageSet.set_key == set_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.deleted_at is not None:
                return LibraryResult(False, error=f"set_key {set_key!r} was deleted and cannot be reused")
            return LibraryResult(False, error=f"set_key {set_key!r} already exists")

        message_set = OutboundMessageSet(
            set_key=set_key,
            name=name,
            description=description,
            category=category,
            purpose=str(purpose).strip() if purpose else None,
            channel=channel,
            primary_language=primary_language,
            selection_strategy=selection_strategy,
            created_by=created_by,
        )
        self.session.add(message_set)
        await self.session.flush()

        self.session.add(
            AuditLog(
                action="outbound_message_set_created",
                entity_type="outbound_message_set",
                entity_id=str(message_set.id),
                details_json={"request_id": request_id, "set_key": set_key, "category": category},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=message_set.id)

    async def get_message_set(self, message_set_id: int) -> OutboundMessageSet | None:
        message_set = await self.session.get(OutboundMessageSet, message_set_id)
        if message_set is None or message_set.deleted_at is not None:
            return None
        return message_set

    async def list_message_sets(self, *, include_disabled: bool = False) -> list[OutboundMessageSet]:
        stmt = select(OutboundMessageSet).where(OutboundMessageSet.deleted_at.is_(None))
        if not include_disabled:
            stmt = stmt.where(OutboundMessageSet.is_enabled.is_(True))
        stmt = stmt.order_by(OutboundMessageSet.name.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def disable_message_set(self, message_set_id: int, *, request_id: str | None = None) -> LibraryResult:
        message_set = await self.get_message_set(message_set_id)
        if message_set is None:
            return LibraryResult(False, error="message set not found")
        if message_set.disabled_at is not None:
            return LibraryResult(True, id=message_set_id)

        message_set.disabled_at = utcnow()
        message_set.is_enabled = False
        self.session.add(
            AuditLog(
                action="outbound_message_set_disabled",
                entity_type="outbound_message_set",
                entity_id=str(message_set_id),
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=message_set_id)

    async def delete_message_set(self, message_set_id: int, *, request_id: str | None = None) -> LibraryResult:
        message_set = await self.session.get(OutboundMessageSet, message_set_id)
        if message_set is None:
            return LibraryResult(False, error="message set not found")
        if message_set.deleted_at is not None:
            return LibraryResult(True, id=message_set_id)

        now = utcnow()
        message_set.deleted_at = now
        message_set.disabled_at = message_set.disabled_at or now
        message_set.is_enabled = False

        # Cascade the tombstone to every active child variant. Without this, a
        # variant under a deleted set stays fetchable via get_variant()/
        # list_variants_for_set() and renderable, so deleting the set would not
        # actually retire its message content.
        child_variants = (
            await self.session.execute(
                select(OutboundMessageVariant).where(
                    OutboundMessageVariant.message_set_id == message_set_id,
                    OutboundMessageVariant.deleted_at.is_(None),
                )
            )
        ).scalars().all()
        for variant in child_variants:
            variant.deleted_at = now
            variant.disabled_at = variant.disabled_at or now
            variant.is_enabled = False

        self.session.add(
            AuditLog(
                action="outbound_message_set_deleted",
                entity_type="outbound_message_set",
                entity_id=str(message_set_id),
                details_json={"request_id": request_id, "cascaded_variant_count": len(child_variants)},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=message_set_id)

    # ------------------------------------------------------------------------------
    # Variants
    # ------------------------------------------------------------------------------

    async def create_variant(
        self,
        *,
        message_set_id: int,
        label: str,
        template_body: str,
        required_variables: list[str] | None = None,
        optional_variables: list[str] | None = None,
        media_locator: str | None = None,
        media_kind: str | None = None,
        media_mime: str | None = None,
        media_caption: str | None = None,
        language: str | None = None,
        tags: list[str] | None = None,
        weight: int = 1,
        status: str = "draft",
        request_id: str | None = None,
    ) -> LibraryResult:
        message_set = await self.get_message_set(message_set_id)
        if message_set is None:
            return LibraryResult(False, error="message set not found")

        label = str(label or "").strip()
        template_body = str(template_body or "").strip()
        required_variables = sorted({str(v).strip() for v in (required_variables or []) if str(v).strip()})
        optional_variables = sorted({str(v).strip() for v in (optional_variables or []) if str(v).strip()})

        if not label or len(label) > self.MAX_LABEL_LENGTH:
            return LibraryResult(False, error="invalid label")
        if not template_body or len(template_body) > self.MAX_TEMPLATE_BODY_LENGTH:
            return LibraryResult(False, error="invalid template_body")
        if status not in self.ALLOWED_VARIANT_STATUSES:
            return LibraryResult(
                False,
                error=f"status {status!r} is not valid; only {sorted(self.ALLOWED_VARIANT_STATUSES)} is accepted",
            )
        if not (self.MIN_WEIGHT <= int(weight) <= self.MAX_WEIGHT):
            return LibraryResult(False, error=f"weight must be between {self.MIN_WEIGHT} and {self.MAX_WEIGHT}")
        if media_kind is not None and len(media_kind) > self.MAX_MEDIA_KIND_LENGTH:
            return LibraryResult(False, error="invalid media_kind")
        if media_mime is not None and len(media_mime) > self.MAX_MEDIA_MIME_LENGTH:
            return LibraryResult(False, error="invalid media_mime")
        if language is not None and len(language) > self.MAX_LANGUAGE_LENGTH:
            return LibraryResult(False, error="invalid language")

        overlap = set(required_variables) & set(optional_variables)
        if overlap:
            return LibraryResult(False, error=f"variable(s) {sorted(overlap)} cannot be both required and optional")

        malformed = [
            span for span in _LOOSE_BRACE_PATTERN.findall(template_body) if not _VALID_TOKEN_CONTENT.match(span)
        ]
        if malformed:
            return LibraryResult(False, error=f"template contains malformed variable placeholder(s) {malformed!r}")

        tokens_in_body = set(_TOKEN_PATTERN.findall(template_body))
        if tokens_in_body != set(required_variables):
            missing_declared = tokens_in_body - set(required_variables)
            unused_declared = set(required_variables) - tokens_in_body
            detail = []
            if missing_declared:
                detail.append(f"template uses undeclared variable(s) {sorted(missing_declared)}")
            if unused_declared:
                detail.append(f"required_variables declares unused variable(s) {sorted(unused_declared)}")
            return LibraryResult(False, error="; ".join(detail))

        duplicate = (
            await self.session.execute(
                select(OutboundMessageVariant).where(
                    OutboundMessageVariant.message_set_id == message_set_id,
                    OutboundMessageVariant.label == label,
                    OutboundMessageVariant.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            return LibraryResult(False, error=f"label {label!r} already exists in this set")

        variant = OutboundMessageVariant(
            message_set_id=message_set_id,
            label=label,
            template_body=template_body,
            required_variables=required_variables or None,
            optional_variables=optional_variables or None,
            media_locator=str(media_locator).strip() if media_locator else None,
            media_kind=str(media_kind).strip() if media_kind else None,
            media_mime=str(media_mime).strip() if media_mime else None,
            media_caption=str(media_caption).strip() if media_caption else None,
            language=language,
            tags=list(tags) if tags else None,
            weight=int(weight),
            status=status,
        )
        self.session.add(variant)
        await self.session.flush()

        self.session.add(
            AuditLog(
                action="outbound_message_variant_created",
                entity_type="outbound_message_variant",
                entity_id=str(variant.id),
                details_json={"request_id": request_id, "message_set_id": message_set_id, "label": label},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=variant.id)

    async def get_variant(self, variant_id: int) -> OutboundMessageVariant | None:
        variant = await self.session.get(OutboundMessageVariant, variant_id)
        if variant is None or variant.deleted_at is not None:
            return None
        return variant

    async def list_variants_for_set(
        self,
        message_set_id: int,
        *,
        include_disabled: bool = False,
        only_approved: bool = False,
    ) -> list[OutboundMessageVariant]:
        stmt = select(OutboundMessageVariant).where(
            OutboundMessageVariant.message_set_id == message_set_id,
            OutboundMessageVariant.deleted_at.is_(None),
        )
        if not include_disabled:
            stmt = stmt.where(OutboundMessageVariant.is_enabled.is_(True))
        if only_approved:
            stmt = stmt.where(OutboundMessageVariant.status == "approved")
        stmt = stmt.order_by(OutboundMessageVariant.label.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def disable_variant(self, variant_id: int, *, request_id: str | None = None) -> LibraryResult:
        variant = await self.get_variant(variant_id)
        if variant is None:
            return LibraryResult(False, error="variant not found")
        if variant.disabled_at is not None:
            return LibraryResult(True, id=variant_id)

        variant.disabled_at = utcnow()
        variant.is_enabled = False
        self.session.add(
            AuditLog(
                action="outbound_message_variant_disabled",
                entity_type="outbound_message_variant",
                entity_id=str(variant_id),
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=variant_id)

    async def delete_variant(self, variant_id: int, *, request_id: str | None = None) -> LibraryResult:
        variant = await self.session.get(OutboundMessageVariant, variant_id)
        if variant is None:
            return LibraryResult(False, error="variant not found")
        if variant.deleted_at is not None:
            return LibraryResult(True, id=variant_id)

        now = utcnow()
        variant.deleted_at = now
        variant.disabled_at = variant.disabled_at or now
        variant.is_enabled = False
        self.session.add(
            AuditLog(
                action="outbound_message_variant_deleted",
                entity_type="outbound_message_variant",
                entity_id=str(variant_id),
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=variant_id)

    # ------------------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------------------

    def render(self, variant: OutboundMessageVariant, variables: dict[str, Any] | None = None) -> RenderResult:
        """Substitute a variant's declared variables. Never invents a missing value.

        ``variables`` must be sourced by the caller from an authoritative Zina domain
        (Identity Registry, Contact, conversation context). Any required variable
        absent (or empty) from ``variables`` fails the render closed rather than
        guessing, leaving a blank, or leaking the literal ``{{token}}`` text.
        """
        variables = variables or {}
        required = set(variant.required_variables or [])
        allowed = required | set(variant.optional_variables or [])

        tokens_in_body = set(_TOKEN_PATTERN.findall(variant.template_body))
        if not tokens_in_body <= allowed:
            # Defense in depth: creation already enforces this, but never render a
            # template whose placeholders drifted outside its declared contract.
            return RenderResult(False, error="template contains undeclared variable(s)")

        missing = sorted(
            name for name in required if name not in variables or variables[name] in (None, "")
        )
        if missing:
            return RenderResult(False, missing_variables=missing)

        def _substitute(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables[key])

        rendered_text = _TOKEN_PATTERN.sub(_substitute, variant.template_body)
        return RenderResult(True, text=rendered_text)

    # ------------------------------------------------------------------------------
    # Usage analytics
    # ------------------------------------------------------------------------------

    async def record_variant_usage(
        self,
        *,
        message_set_id: int,
        variant_id: int,
        contact_id: int | None = None,
        outbound_queue_id: int | None = None,
        selection_score: float | None = None,
        selection_reason: str | None = None,
        source_automation: str | None = None,
    ) -> LibraryResult:
        if source_automation is not None and len(source_automation) > self.MAX_SOURCE_AUTOMATION_LENGTH:
            return LibraryResult(False, error="invalid source_automation")

        variant = await self.session.get(OutboundMessageVariant, variant_id)
        if variant is None:
            return LibraryResult(False, error="variant not found")
        if variant.message_set_id != message_set_id:
            return LibraryResult(False, error="variant does not belong to message_set_id")

        usage = OutboundVariantUsage(
            contact_id=contact_id,
            message_set_id=message_set_id,
            variant_id=variant_id,
            outbound_queue_id=outbound_queue_id,
            selection_score=selection_score,
            selection_reason=selection_reason,
            source_automation=source_automation,
        )
        self.session.add(usage)
        await self.session.flush()
        return LibraryResult(True, id=usage.id)

    async def update_usage_send_result(self, usage_id: int, send_result: str) -> LibraryResult:
        if send_result not in self.ALLOWED_SEND_RESULTS:
            return LibraryResult(
                False, error=f"send_result {send_result!r} is not valid; only {sorted(self.ALLOWED_SEND_RESULTS)}"
            )
        usage = await self.session.get(OutboundVariantUsage, usage_id)
        if usage is None:
            return LibraryResult(False, error="usage record not found")

        usage.send_result = send_result
        usage.updated_at = utcnow()
        await self.session.flush()
        return LibraryResult(True, id=usage_id)
