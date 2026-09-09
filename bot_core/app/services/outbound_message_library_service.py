from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import (
    AuditLog,
    Contact,
    OutboundMessage,
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
    # Locked reads
    # ------------------------------------------------------------------------------
    #
    # Every method below that checks a lifecycle flag (is_enabled/disabled_at/
    # deleted_at) before deciding whether to mutate or reject must read through
    # here, not session.get()/a plain select(): this project's sessions use
    # expire_on_commit=False, so a plain read returns whatever object this
    # session's identity map already cached for that primary key without
    # applying another session's committed change. FOR UPDATE additionally
    # serializes against a *concurrent* mutation (not just a stale cache), and
    # populate_existing=True is required alongside it -- FOR UPDATE alone
    # re-runs the query, but the identity map still wins over its fresh result
    # unless populate_existing forces the cached object's attributes to be
    # overwritten. Missing populate_existing here was itself a bug (round 12):
    # it silently defeated the FOR UPDATE lock round 11 added to create_variant()
    # and record_variant_usage() for exactly the same reason.

    async def _locked_message_set(self, message_set_id: int) -> OutboundMessageSet | None:
        return (
            await self.session.execute(
                select(OutboundMessageSet)
                .where(OutboundMessageSet.id == message_set_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

    async def _locked_variant(self, variant_id: int) -> OutboundMessageVariant | None:
        return (
            await self.session.execute(
                select(OutboundMessageVariant)
                .where(OutboundMessageVariant.id == variant_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()

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
        created_by = str(created_by).strip() if created_by is not None else None
        primary_language = str(primary_language).strip() if primary_language is not None else None

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
        if not isinstance(selection_strategy, str) or selection_strategy not in self.ALLOWED_SELECTION_STRATEGIES:
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
        # The existence check above has a TOCTOU window: two concurrent callers can
        # both pass it before either INSERT commits. A SAVEPOINT (begin_nested)
        # contains the resulting IntegrityError to just this insert, so the loser
        # gets the documented fail-closed result instead of an unhandled exception
        # that leaves the whole session requiring rollback.
        try:
            async with self.session.begin_nested():
                self.session.add(message_set)
                await self.session.flush()
        except IntegrityError:
            return LibraryResult(False, error=f"set_key {set_key!r} already exists")

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
        message_set = await self._locked_message_set(message_set_id)
        if message_set is None or message_set.deleted_at is not None:
            return LibraryResult(False, error="message set not found")
        if message_set.disabled_at is not None:
            return LibraryResult(True, id=message_set_id)

        now = utcnow()
        message_set.disabled_at = now
        message_set.is_enabled = False
        message_set.updated_at = now

        # Cascade to every active child variant, same reasoning as delete_message_set:
        # without this, get_variant()/list_variants_for_set() and render() would still
        # treat the variant as usable even though its parent set is disabled. Locked +
        # populate_existing for the same reason as _locked_message_set()/
        # _locked_variant(): without it, a child this session already had cached
        # (stale, e.g. disabled_at=None) could be returned as-is even though another
        # session concurrently disabled that specific child and committed first --
        # `variant.disabled_at or now` would then see the stale None and overwrite the
        # child's real timestamp with this cascade's.
        child_variants = (
            await self.session.execute(
                select(OutboundMessageVariant)
                .where(
                    OutboundMessageVariant.message_set_id == message_set_id,
                    OutboundMessageVariant.deleted_at.is_(None),
                    OutboundMessageVariant.disabled_at.is_(None),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        for variant in child_variants:
            variant.disabled_at = now
            variant.is_enabled = False
            variant.updated_at = now

        self.session.add(
            AuditLog(
                action="outbound_message_set_disabled",
                entity_type="outbound_message_set",
                entity_id=str(message_set_id),
                details_json={"request_id": request_id, "cascaded_variant_count": len(child_variants)},
            )
        )
        await self.session.flush()
        return LibraryResult(True, id=message_set_id)

    async def delete_message_set(self, message_set_id: int, *, request_id: str | None = None) -> LibraryResult:
        message_set = await self._locked_message_set(message_set_id)
        if message_set is None:
            return LibraryResult(False, error="message set not found")
        if message_set.deleted_at is not None:
            return LibraryResult(True, id=message_set_id)

        now = utcnow()
        message_set.deleted_at = now
        message_set.disabled_at = message_set.disabled_at or now
        message_set.is_enabled = False
        message_set.updated_at = now

        # Cascade the tombstone to every active child variant. Without this, a
        # variant under a deleted set stays fetchable via get_variant()/
        # list_variants_for_set() and renderable, so deleting the set would not
        # actually retire its message content. Locked + populate_existing: same
        # staleness risk as disable_message_set()'s cascade above -- a concurrently
        # disabled/deleted child this session had already cached would otherwise have
        # its real timestamp overwritten by this cascade's.
        child_variants = (
            await self.session.execute(
                select(OutboundMessageVariant)
                .where(
                    OutboundMessageVariant.message_set_id == message_set_id,
                    OutboundMessageVariant.deleted_at.is_(None),
                )
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        for variant in child_variants:
            variant.deleted_at = now
            variant.disabled_at = variant.disabled_at or now
            variant.is_enabled = False
            variant.updated_at = now

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
        # A str is technically iterable (so "vip" would silently become
        # ['v','i','p']) and a non-iterable like an int raises TypeError the moment
        # a comprehension below tries to loop over it -- both must be rejected
        # before any iteration is attempted, not discovered by crashing.
        for field_name, field_value in (
            ("required_variables", required_variables),
            ("optional_variables", optional_variables),
            ("tags", tags),
        ):
            if field_value is not None and not isinstance(field_value, list):
                return LibraryResult(False, error=f"{field_name} must be a list")

        # required_variables/optional_variables tolerate any element (str() below
        # coerces it, and a garbage value just fails the token-match invariant that
        # follows). tags has no such downstream check, and the model column is
        # JSONB list[str]: a non-string element (e.g. an object, or a JSON-serializable
        # dict like {"tier": "vip"}) would either crash flush() or silently persist
        # a shape the model never declared, so it's rejected here explicitly.
        if tags is not None and not all(isinstance(t, str) for t in tags):
            return LibraryResult(False, error="tags must be a list of strings")

        label = str(label or "").strip()
        template_body = str(template_body or "").strip()
        required_variables = sorted({str(v).strip() for v in (required_variables or []) if str(v).strip()})
        optional_variables = sorted({str(v).strip() for v in (optional_variables or []) if str(v).strip()})

        # required_variables is validated implicitly below by the exact-match
        # comparison against the tokens actually found in template_body ("first-name"
        # could never equal a real {{token}}, so a bogus entry always fails that
        # check). optional_variables has no such downstream check -- nothing compares
        # it against template_body -- so a value that can never represent a real
        # {{token}} would otherwise pass silently and persist as malformed metadata
        # for the future personalization resolver and selection engine.
        invalid_optional = [v for v in optional_variables if not _VALID_TOKEN_CONTENT.match(v)]
        if invalid_optional:
            return LibraryResult(
                False, error=f"optional_variables contains invalid token name(s) {invalid_optional!r}"
            )

        media_kind = str(media_kind).strip() if media_kind is not None else None
        media_mime = str(media_mime).strip() if media_mime is not None else None
        language = str(language).strip() if language is not None else None

        if not label or len(label) > self.MAX_LABEL_LENGTH:
            return LibraryResult(False, error="invalid label")
        if not template_body or len(template_body) > self.MAX_TEMPLATE_BODY_LENGTH:
            return LibraryResult(False, error="invalid template_body")
        if not isinstance(status, str) or status not in self.ALLOWED_VARIANT_STATUSES:
            return LibraryResult(
                False,
                error=f"status {status!r} is not valid; only {sorted(self.ALLOWED_VARIANT_STATUSES)} is accepted",
            )
        if not isinstance(weight, int) or isinstance(weight, bool):
            return LibraryResult(False, error="weight must be an integer")
        if not (self.MIN_WEIGHT <= weight <= self.MAX_WEIGHT):
            return LibraryResult(False, error=f"weight must be between {self.MIN_WEIGHT} and {self.MAX_WEIGHT}")
        if media_kind is not None and len(media_kind) > self.MAX_MEDIA_KIND_LENGTH:
            return LibraryResult(False, error="invalid media_kind")
        if media_mime is not None and len(media_mime) > self.MAX_MEDIA_MIME_LENGTH:
            return LibraryResult(False, error="invalid media_mime")
        if language is not None and len(language) > self.MAX_LANGUAGE_LENGTH:
            return LibraryResult(False, error="invalid language")

        # Locked read (SELECT ... FOR UPDATE), not the plain get_message_set() used
        # elsewhere: a concurrent disable_message_set() UPDATEs this exact row inside
        # its own transaction, so this lock serializes the two rather than merely
        # checking a value that could go stale the instant after it's read. Without
        # this, transaction A could read "enabled" here, transaction B could disable
        # the set and finish cascading its *existing* children, and only then would
        # A's insert land -- a new, never-cascaded, fully enabled variant under a
        # disabled set.
        message_set = await self._locked_message_set(message_set_id)
        if message_set is None or message_set.deleted_at is not None:
            return LibraryResult(False, error="message set not found")
        if message_set.disabled_at is not None:
            return LibraryResult(False, error="message set is disabled")

        overlap = set(required_variables) & set(optional_variables)
        if overlap:
            return LibraryResult(False, error=f"variable(s) {sorted(overlap)} cannot be both required and optional")

        # Delimiters that never paired up at all (e.g. "Hi {{first_name" with no
        # closing "}}", or a "{{...}}" split across a newline, which "." does not
        # cross): strip every span _LOOSE_BRACE_PATTERN *did* match, and if a literal
        # "{{" or "}}" remains, something didn't close.
        unmatched_remainder = _LOOSE_BRACE_PATTERN.sub("", template_body)
        if "{{" in unmatched_remainder or "}}" in unmatched_remainder:
            return LibraryResult(False, error="template contains unmatched variable delimiter(s)")

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
            media_kind=media_kind or None,
            media_mime=media_mime or None,
            media_caption=str(media_caption).strip() if media_caption else None,
            language=language or None,
            tags=list(tags) if tags else None,
            weight=weight,
            status=status,
        )
        # Same TOCTOU window as create_message_set's set_key check: two concurrent
        # callers can both pass the duplicate-label query above before either INSERT
        # commits. The partial unique index (message_set_id, label WHERE deleted_at
        # IS NULL) then makes the loser's flush() raise IntegrityError; the SAVEPOINT
        # contains that to just this insert.
        try:
            async with self.session.begin_nested():
                self.session.add(variant)
                await self.session.flush()
        except IntegrityError:
            return LibraryResult(False, error=f"label {label!r} already exists in this set")

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
        variant = await self._locked_variant(variant_id)
        if variant is None or variant.deleted_at is not None:
            return LibraryResult(False, error="variant not found")
        if variant.disabled_at is not None:
            return LibraryResult(True, id=variant_id)

        now = utcnow()
        variant.disabled_at = now
        variant.is_enabled = False
        variant.updated_at = now
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
        variant = await self._locked_variant(variant_id)
        if variant is None:
            return LibraryResult(False, error="variant not found")
        if variant.deleted_at is not None:
            return LibraryResult(True, id=variant_id)

        now = utcnow()
        variant.deleted_at = now
        variant.disabled_at = variant.disabled_at or now
        variant.is_enabled = False
        variant.updated_at = now
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

    async def render(self, variant: OutboundMessageVariant, variables: dict[str, Any] | None = None) -> RenderResult:
        """Substitute a variant's declared variables. Never invents a missing value.

        ``variables`` must be sourced by the caller from an authoritative Zina domain
        (Identity Registry, Contact, conversation context). Any required variable
        absent (or empty) from ``variables`` fails the render closed rather than
        guessing, leaving a blank, or leaking the literal ``{{token}}`` text.
        """
        # Refresh from the database before trusting lifecycle fields: a caller may
        # have fetched this exact object earlier in a long-lived session (this
        # project's sessions use expire_on_commit=False), and another
        # session/worker could have disabled or deleted it since. Checking cached
        # Python attributes would silently render retired content.
        try:
            await self.session.refresh(variant)
        except InvalidRequestError:
            # A concurrent hard delete (maintenance/retention cleanup) removed the
            # row entirely -- refresh() raises InvalidRequestError ("Could not
            # refresh instance") in this case, not a plain empty result. Same
            # fail-closed outcome as any other retired variant, not an unhandled
            # exception.
            return RenderResult(False, error="variant is not active")
        if variant.deleted_at is not None or variant.disabled_at is not None or not variant.is_enabled:
            # get_variant() deliberately still returns a disabled variant (so an
            # owner can inspect it), but a caller holding a stale id must never be
            # able to render content from it — cascading disable/delete onto
            # children only matters if render() itself also refuses them.
            return RenderResult(False, error="variant is not active")

        # A JSON-facing caller could pass a truthy non-mapping (an int, a bare
        # string, a list) instead of a dict. "or {}" only rescues a falsy value
        # (None, {}), so a non-mapping would reach the membership/indexing checks
        # below and raise a plain TypeError instead of the documented fail-closed
        # RenderResult.
        if variables is not None and not isinstance(variables, dict):
            return RenderResult(False, error="variables must be a mapping")
        variables = variables or {}
        required = set(variant.required_variables or [])

        # Defense in depth, same order as create_variant(): a maintenance script or
        # direct ORM edit could change template_body after creation without going
        # through this service's validation at all. The undeclared-token subset check
        # below only catches a *recognized* {{token}}; it silently ignores a
        # malformed or unmatched delimiter (e.g. "{{first-name}}" or a dangling
        # "{{first_name" with no closing brace), so both must be re-checked here too,
        # not just at creation time.
        unmatched_remainder = _LOOSE_BRACE_PATTERN.sub("", variant.template_body)
        if "{{" in unmatched_remainder or "}}" in unmatched_remainder:
            return RenderResult(False, error="template contains unmatched variable delimiter(s)")
        malformed = [
            span
            for span in _LOOSE_BRACE_PATTERN.findall(variant.template_body)
            if not _VALID_TOKEN_CONTENT.match(span)
        ]
        if malformed:
            return RenderResult(False, error=f"template contains malformed variable placeholder(s) {malformed!r}")

        # create_variant() enforces tokens_in_body == required_variables exactly, so
        # an optional variable is *metadata only* and can never legitimately appear
        # as a literal {{token}} in the body -- a subset check against
        # required | optional would therefore let a tampered body reference a
        # declared-optional name that _is_blank()/missing (below) never requires,
        # and _substitute() would then raise a plain KeyError on it instead of
        # returning a fail-closed RenderResult. Re-enforce the exact match here too.
        tokens_in_body = set(_TOKEN_PATTERN.findall(variant.template_body))
        if tokens_in_body != required:
            # Defense in depth: creation already enforces this, but never render a
            # template whose placeholders drifted outside its declared contract.
            return RenderResult(False, error="template contains undeclared or missing variable(s)")

        def _is_blank(value: Any) -> bool:
            if value is None:
                return True
            if isinstance(value, str) and not value.strip():
                return True
            return False

        missing = sorted(name for name in required if name not in variables or _is_blank(variables[name]))
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
        source_automation = str(source_automation).strip() if source_automation is not None else None
        if source_automation is not None and len(source_automation) > self.MAX_SOURCE_AUTOMATION_LENGTH:
            return LibraryResult(False, error="invalid source_automation")
        if selection_reason is not None and not isinstance(selection_reason, str):
            return LibraryResult(False, error="invalid selection_reason")

        # A locked read (SELECT ... FOR UPDATE), not session.get()/refresh(): this
        # eligibility check and the usage insert below are not atomic on their own,
        # so a concurrent disable_variant()/delete_variant() could commit between the
        # two -- an UPDATE against this same row -- and this call would still record
        # the now-retired variant as an eligible selection. Postgres blocks that
        # concurrent UPDATE against a FOR-UPDATE-locked row until this transaction
        # commits or rolls back, serializing the check with the write instead of
        # merely reading a value that could go stale the instant after it's read.
        # This also reads directly from the database rather than the session's
        # identity map, so a concurrently hard-deleted row is a plain None here, not
        # the InvalidRequestError session.refresh() would raise.
        variant = await self._locked_variant(variant_id)
        if variant is None:
            return LibraryResult(False, error="variant not found")
        if variant.message_set_id != message_set_id:
            return LibraryResult(False, error="variant does not belong to message_set_id")
        # Only an approved, active variant was ever eligible to be selected. A
        # draft/disabled/deleted variant reaching this point (a stale id, a caller
        # bypassing the selection engine) must not be recorded as a real selection --
        # these rows drive per-variant send-result/reply-rate analytics.
        if variant.status != "approved" or not variant.is_enabled or variant.disabled_at is not None:
            return LibraryResult(False, error="variant is not an eligible (approved, active) selection")

        contact = await self.session.get(Contact, contact_id) if contact_id is not None else None
        if contact_id is not None and contact is None:
            return LibraryResult(False, error="contact not found")
        outbound_message = (
            await self.session.get(OutboundMessage, outbound_queue_id) if outbound_queue_id is not None else None
        )
        if outbound_queue_id is not None and outbound_message is None:
            return LibraryResult(False, error="outbound_queue_id not found")
        if (
            contact is not None
            and outbound_message is not None
            and outbound_message.chat_id not in (contact.whatsapp_id, contact.chat_id)
        ):
            # Both ids exist independently but don't refer to the same delivery --
            # e.g. a real contact paired with an OutboundMessage addressed to someone
            # else. Recording it would permanently misattribute that send/variant
            # selection in per-contact analytics. A contact is identified by either
            # whatsapp_id or chat_id (same convention as
            # PushCommandService._contact_for_chat()'s or_(Contact.chat_id == ...,
            # Contact.whatsapp_id == ...) lookup) -- Contact.chat_id is nullable and
            # never equals a real chat_id string when unset, so this stays safe.
            return LibraryResult(False, error="outbound_queue_id does not belong to contact_id")
        if selection_score is not None:
            is_real_number = isinstance(selection_score, (int, float)) and not isinstance(selection_score, bool)
            if not is_real_number:
                return LibraryResult(False, error="invalid selection_score")
            try:
                # A Python int far outside float range (e.g. 10**10000) is still an
                # "is_real_number", but converting it for math.isfinite() raises
                # OverflowError rather than returning False -- guard the conversion
                # itself, not just the finiteness check.
                score_is_finite = math.isfinite(selection_score)
            except OverflowError:
                score_is_finite = False
            if not score_is_finite:
                return LibraryResult(False, error="invalid selection_score")

        usage = OutboundVariantUsage(
            contact_id=contact_id,
            message_set_id=message_set_id,
            variant_id=variant_id,
            outbound_queue_id=outbound_queue_id,
            selection_score=selection_score,
            selection_reason=selection_reason,
            source_automation=source_automation,
        )
        # A retried call for the same outbound_queue_id (a producer retry after a
        # transient failure, or a duplicate selection-engine call) must not double-
        # count the selection: the partial unique index on outbound_queue_id makes
        # the second insert raise IntegrityError, contained to just this insert by a
        # SAVEPOINT so it doesn't poison the whole session. Return the existing
        # row's id as a successful, idempotent no-op rather than a fail-closed error
        # -- the selection genuinely was already recorded.
        try:
            async with self.session.begin_nested():
                self.session.add(usage)
                await self.session.flush()
        except IntegrityError:
            if outbound_queue_id is None:
                raise
            existing = (
                await self.session.execute(
                    select(OutboundVariantUsage).where(
                        OutboundVariantUsage.outbound_queue_id == outbound_queue_id
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                return LibraryResult(False, error="outbound_queue_id usage conflict")
            # The conflict alone only proves *some* row already claims this
            # outbound_queue_id -- not that it's a retry of *this* selection. If a
            # caller first recorded variant A against this queue row and later,
            # separately, recorded variant B against the same row (a bug elsewhere,
            # or two different selection attempts racing), treating B's call as a
            # successful idempotent no-op would silently attribute B's delivery to
            # A in the analytics this table exists to keep accurate. Only an exact
            # match on the row's immutable selection identity is a genuine retry.
            if (
                existing.message_set_id != message_set_id
                or existing.variant_id != variant_id
                or existing.contact_id != contact_id
            ):
                return LibraryResult(
                    False,
                    error=(
                        f"outbound_queue_id {outbound_queue_id!r} is already recorded against a "
                        "different selection"
                    ),
                )
            return LibraryResult(True, id=existing.id)
        return LibraryResult(True, id=usage.id)

    async def update_usage_send_result(self, usage_id: int, send_result: str) -> LibraryResult:
        if not isinstance(send_result, str) or send_result not in self.ALLOWED_SEND_RESULTS:
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
