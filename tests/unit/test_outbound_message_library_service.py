"""Foundational data-model layer for the Intelligent Outbound Message Library.

Roadmap Phase 17 (docs/ZINA_IMPLEMENTATION_ROADMAP.md): reusable message sets and
their approved template variants, plus an analytics/audit trail of which variant was
selected for which contact and why. This service answers "WHAT COULD ZINA SAY?" only
-- it has zero outbound authority, is not wired into any producer or delivery path,
and selecting/rendering a variant never sends anything or implies send authority.
These tests cover CRUD lifecycle, fail-closed validation, and template rendering.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.schema import (
    AuditLog,
    Contact,
    OutboundMessage,
    OutboundMessageSet,
    OutboundMessageVariant,
    OutboundVariantUsage,
)
from app.services.outbound_message_library_service import OutboundMessageLibraryService


async def _make_set(service: OutboundMessageLibraryService, **overrides):
    defaults = dict(
        set_key="lead_follow_up",
        name="Lead Follow-up",
        description="Follow up with a lead after initial contact.",
        category="lead_follow_up",
    )
    defaults.update(overrides)
    result = await service.create_message_set(**defaults)
    assert result.ok, result.error
    return result.id


@pytest.mark.asyncio
async def test_create_message_set_persists_and_stamps_audit(db_session):
    service = OutboundMessageLibraryService(db_session)
    result = await service.create_message_set(
        set_key="lead_follow_up",
        name="Lead Follow-up",
        description="Follow up with a lead after initial contact.",
        category="lead_follow_up",
        purpose="Re-engage a lead who has gone quiet.",
        primary_language="en",
    )

    assert result.ok is True
    assert result.id

    message_set = await service.get_message_set(result.id)
    assert message_set is not None
    assert message_set.set_key == "lead_follow_up"
    assert message_set.selection_strategy == "deterministic_score"
    assert message_set.is_enabled is True

    audit = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "outbound_message_set_created")
        )
    ).mappings().first()
    assert audit is not None
    assert audit["entity_id"] == str(result.id)


@pytest.mark.asyncio
async def test_create_message_set_rejects_unknown_selection_strategy(db_session):
    service = OutboundMessageLibraryService(db_session)
    result = await service.create_message_set(
        set_key="lead_follow_up",
        name="Lead Follow-up",
        description="d",
        category="lead_follow_up",
        selection_strategy="ai_only_random",
    )
    assert result.ok is False
    assert "not enabled yet" in (result.error or "")


@pytest.mark.asyncio
async def test_create_message_set_rejects_duplicate_set_key(db_session):
    service = OutboundMessageLibraryService(db_session)
    await _make_set(service)
    duplicate = await service.create_message_set(
        set_key="lead_follow_up",
        name="Another Name",
        description="d",
        category="lead_follow_up",
    )
    assert duplicate.ok is False
    assert "already exists" in (duplicate.error or "")


@pytest.mark.asyncio
async def test_create_message_set_rejects_invalid_inputs(db_session):
    service = OutboundMessageLibraryService(db_session)
    missing_key = await service.create_message_set(set_key="", name="n", description="d", category="c")
    assert missing_key.ok is False

    missing_description = await service.create_message_set(set_key="k", name="n", description="", category="c")
    assert missing_description.ok is False

    oversized_name = await service.create_message_set(
        set_key="k2", name="x" * 181, description="d", category="c"
    )
    assert oversized_name.ok is False


@pytest.mark.asyncio
async def test_create_variant_requires_exact_match_between_template_tokens_and_required_variables(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    undeclared_token = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}, following up on {{project}}.",
        required_variables=["first_name"],
    )
    assert undeclared_token.ok is False
    assert "undeclared variable" in (undeclared_token.error or "")

    unused_declared = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name", "project"],
    )
    assert unused_declared.ok is False
    assert "unused variable" in (unused_declared.error or "")

    correct = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}, following up on {{project}}.",
        required_variables=["first_name", "project"],
        status="approved",
    )
    assert correct.ok is True


@pytest.mark.asyncio
async def test_create_variant_rejects_unknown_parent_set(db_session):
    service = OutboundMessageLibraryService(db_session)
    result = await service.create_variant(message_set_id=999999, label="A", template_body="Hi there.")
    assert result.ok is False
    assert "message set not found" in (result.error or "")


@pytest.mark.asyncio
async def test_create_variant_rejects_duplicate_label_in_same_set(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    first = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    assert first.ok is True

    duplicate = await service.create_variant(message_set_id=set_id, label="A", template_body="Hello there.")
    assert duplicate.ok is False
    assert "already exists" in (duplicate.error or "")


@pytest.mark.asyncio
async def test_create_variant_rejects_invalid_status_and_weight(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    bad_status = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="published"
    )
    assert bad_status.ok is False

    bad_weight = await service.create_variant(message_set_id=set_id, label="B", template_body="Hi.", weight=0)
    assert bad_weight.ok is False

    too_heavy = await service.create_variant(message_set_id=set_id, label="C", template_body="Hi.", weight=101)
    assert too_heavy.ok is False


@pytest.mark.asyncio
async def test_create_variant_rejects_variable_declared_as_both_required_and_optional(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    result = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        optional_variables=["first_name"],
    )
    assert result.ok is False
    assert "both required and optional" in (result.error or "")


@pytest.mark.asyncio
async def test_render_substitutes_provided_variables(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}, following up on {{project}}.",
        required_variables=["first_name", "project"],
        status="approved",
    )
    variant = await service.get_variant(created.id)

    result = await service.render(variant, {"first_name": "Ada", "project": "ZinaX"})
    assert result.ok is True
    assert result.text == "Hi Ada, following up on ZinaX."


@pytest.mark.asyncio
async def test_render_fails_closed_on_missing_required_variable_and_never_invents_one(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}, following up on {{project}}.",
        required_variables=["first_name", "project"],
        status="approved",
    )
    variant = await service.get_variant(created.id)

    missing_entirely = await service.render(variant, {"first_name": "Ada"})
    assert missing_entirely.ok is False
    assert missing_entirely.missing_variables == ["project"]
    assert missing_entirely.text is None

    empty_value = await service.render(variant, {"first_name": "Ada", "project": ""})
    assert empty_value.ok is False
    assert empty_value.missing_variables == ["project"]

    no_variables_at_all = await service.render(variant, None)
    assert no_variables_at_all.ok is False
    assert set(no_variables_at_all.missing_variables) == {"first_name", "project"}


@pytest.mark.asyncio
async def test_render_ignores_optional_variables_not_used_in_body(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        optional_variables=["appointment_time"],
        status="approved",
    )
    variant = await service.get_variant(created.id)

    result = await service.render(variant, {"first_name": "Ada"})
    assert result.ok is True
    assert result.text == "Hi Ada."


@pytest.mark.asyncio
async def test_list_variants_for_set_only_approved_excludes_draft(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    await service.create_variant(message_set_id=set_id, label="A", template_body="Draft copy.", status="draft")
    await service.create_variant(message_set_id=set_id, label="B", template_body="Approved copy.", status="approved")

    all_variants = await service.list_variants_for_set(set_id)
    assert {v.label for v in all_variants} == {"A", "B"}

    approved_only = await service.list_variants_for_set(set_id, only_approved=True)
    assert {v.label for v in approved_only} == {"B"}


@pytest.mark.asyncio
async def test_disable_then_delete_lifecycle_for_message_set_is_monotonic(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    disable_result = await service.disable_message_set(set_id)
    assert disable_result.ok is True

    fetched = await service.get_message_set(set_id)
    assert fetched is not None
    assert fetched.disabled_at is not None
    assert fetched.is_enabled is False

    # Disabling twice is idempotent, not an error.
    second_disable = await service.disable_message_set(set_id)
    assert second_disable.ok is True

    assert set_id not in {s.id for s in await service.list_message_sets()}
    assert set_id in {s.id for s in await service.list_message_sets(include_disabled=True)}

    delete_result = await service.delete_message_set(set_id)
    assert delete_result.ok is True
    assert await service.get_message_set(set_id) is None
    assert set_id not in {s.id for s in await service.list_message_sets(include_disabled=True)}

    # Deletion is idempotent.
    repeat_delete = await service.delete_message_set(set_id)
    assert repeat_delete.ok is True


@pytest.mark.asyncio
async def test_disable_then_delete_lifecycle_for_variant_is_monotonic(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    variant_id = created.id

    disable_result = await service.disable_variant(variant_id)
    assert disable_result.ok is True
    assert variant_id not in {v.id for v in await service.list_variants_for_set(set_id)}

    delete_result = await service.delete_variant(variant_id)
    assert delete_result.ok is True
    assert await service.get_variant(variant_id) is None

    repeat_delete = await service.delete_variant(variant_id)
    assert repeat_delete.ok is True


@pytest.mark.asyncio
async def test_disable_and_delete_on_unknown_ids_fail_closed(db_session):
    service = OutboundMessageLibraryService(db_session)
    assert (await service.disable_message_set(999999)).ok is False
    assert (await service.delete_message_set(999999)).ok is False
    assert (await service.disable_variant(999999)).ok is False
    assert (await service.delete_variant(999999)).ok is False


@pytest.mark.asyncio
async def test_a_deleted_label_can_be_reused_by_a_new_variant(db_session):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    first = await service.create_variant(message_set_id=set_id, label="A", template_body="Old copy.")
    await service.delete_variant(first.id)

    second = await service.create_variant(message_set_id=set_id, label="A", template_body="New copy.")
    assert second.ok is True
    assert second.id != first.id


@pytest.mark.asyncio
async def test_record_variant_usage_and_update_send_result(db_session, test_contact):
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )

    usage = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=test_contact.id,
        selection_score=0.87,
        selection_reason="highest deterministic score among eligible approved variants",
        source_automation="scheduled_action",
    )
    assert usage.ok is True
    assert usage.id

    row = await db_session.get(OutboundVariantUsage, usage.id)
    assert row is not None
    assert row.send_result == "pending"
    assert row.selection_reason.startswith("highest deterministic score")

    updated = await service.update_usage_send_result(usage.id, "sent")
    assert updated.ok is True
    row_after = await db_session.get(OutboundVariantUsage, usage.id)
    assert row_after.send_result == "sent"

    invalid = await service.update_usage_send_result(usage.id, "definitely_delivered")
    assert invalid.ok is False


@pytest.mark.asyncio
async def test_update_usage_send_result_on_unknown_id_fails_closed(db_session):
    service = OutboundMessageLibraryService(db_session)
    result = await service.update_usage_send_result(999999, "sent")
    assert result.ok is False


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review findings on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_message_set_rejects_oversized_created_by_cleanly(db_session):
    """Regression: created_by reached flush() unbounded and crashed instead of
    returning the service's documented fail-closed result."""
    service = OutboundMessageLibraryService(db_session)
    result = await service.create_message_set(
        set_key="lead_follow_up",
        name="Lead Follow-up",
        description="d",
        category="lead_follow_up",
        created_by="x" * 121,
    )
    assert result.ok is False
    assert "created_by" in (result.error or "")


@pytest.mark.asyncio
async def test_create_message_set_rejects_reuse_of_a_deleted_set_key(db_session):
    """Regression: set_key carries an unconditional UNIQUE constraint (unlike a
    variant's per-set label), so recreating a deleted set_key must be rejected
    cleanly rather than reaching flush() and raising an IntegrityError."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    await service.delete_message_set(set_id)

    recreate = await service.create_message_set(
        set_key="lead_follow_up",
        name="New Name",
        description="d",
        category="lead_follow_up",
    )
    assert recreate.ok is False
    assert "deleted" in (recreate.error or "")


@pytest.mark.asyncio
async def test_create_variant_rejects_malformed_placeholder(db_session):
    """Regression: a placeholder like {{first-name}} (hyphen, not underscore) doesn't
    match the strict token pattern, so it silently passed validation and would later
    render as literal, broken template syntax instead of being substituted."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    result = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first-name}}.",
    )
    assert result.ok is False
    assert "malformed" in (result.error or "")


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_variant_from_a_different_set(db_session, test_contact):
    """Regression: independent foreign keys let a variant from set B be recorded
    against set A's id, corrupting the per-set analytics trail."""
    service = OutboundMessageLibraryService(db_session)
    set_a = await _make_set(service, set_key="set_a")
    set_b = await _make_set(service, set_key="set_b")
    variant_in_b = await service.create_variant(message_set_id=set_b, label="A", template_body="Hi there.")

    result = await service.record_variant_usage(
        message_set_id=set_a,
        variant_id=variant_in_b.id,
        contact_id=test_contact.id,
    )
    assert result.ok is False
    assert "does not belong" in (result.error or "")

    rows = (await db_session.execute(OutboundVariantUsage.__table__.select())).mappings().all()
    assert rows == []


@pytest.mark.asyncio
async def test_delete_message_set_cascades_tombstone_to_its_variants(db_session):
    """Regression: deleting a set only tombstoned the parent row, leaving every
    child variant enabled and independently fetchable/renderable, so deleting the
    set did not actually retire its message content."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant_a = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    variant_b = await service.create_variant(message_set_id=set_id, label="B", template_body="Hello there.")

    await service.delete_message_set(set_id)

    assert await service.get_variant(variant_a.id) is None
    assert await service.get_variant(variant_b.id) is None
    assert await service.list_variants_for_set(set_id, include_disabled=True) == []


@pytest.mark.asyncio
async def test_create_variant_rejects_non_integer_weight_instead_of_crashing(db_session):
    """Regression: int(weight) raised TypeError/ValueError for None or a non-numeric
    string instead of returning the documented fail-closed LibraryResult, and a float
    like 1.7 was silently truncated to 1 rather than rejected."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    none_weight = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", weight=None
    )
    assert none_weight.ok is False
    assert "weight" in (none_weight.error or "")

    string_weight = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi.", weight="high"
    )
    assert string_weight.ok is False
    assert "weight" in (string_weight.error or "")

    float_weight = await service.create_variant(
        message_set_id=set_id, label="C", template_body="Hi.", weight=1.7
    )
    assert float_weight.ok is False
    assert "weight" in (float_weight.error or "")

    bool_weight = await service.create_variant(
        message_set_id=set_id, label="D", template_body="Hi.", weight=True
    )
    assert bool_weight.ok is False


@pytest.mark.asyncio
async def test_create_variant_rejects_unmatched_template_delimiters(db_session):
    """Regression: _LOOSE_BRACE_PATTERN only matches balanced {{...}} spans, so an
    unclosed "{{first_name" (or a placeholder split by a newline, which "." does not
    cross) produced no matches at all and passed validation, later rendering as
    literal, broken template syntax."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    unclosed = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi {{first_name"
    )
    assert unclosed.ok is False
    assert "unmatched" in (unclosed.error or "")

    unopened = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi first_name}}"
    )
    assert unopened.ok is False
    assert "unmatched" in (unopened.error or "")

    split_by_newline = await service.create_variant(
        message_set_id=set_id, label="C", template_body="Hi {{first_\nname}}"
    )
    assert split_by_newline.ok is False
    assert "unmatched" in (split_by_newline.error or "")


@pytest.mark.asyncio
async def test_render_treats_whitespace_only_required_value_as_missing(db_session):
    """Regression: a required value of "   " passed the `in (None, "")` check and
    rendered blank-looking personalization ("Hi    , ...") instead of failing closed,
    even though it's just as absent as an empty string for a real message."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        status="approved",
    )
    variant = await service.get_variant(created.id)

    result = await service.render(variant, {"first_name": "   "})
    assert result.ok is False
    assert result.missing_variables == ["first_name"]
    assert result.text is None


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_unknown_optional_foreign_keys(db_session, test_contact):
    """Regression: a stale/nonexistent contact_id or outbound_queue_id reached
    flush() unvalidated and crashed with an IntegrityError instead of the service's
    documented fail-closed LibraryResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )

    unknown_contact = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, contact_id=999999
    )
    assert unknown_contact.ok is False
    assert "contact" in (unknown_contact.error or "")

    unknown_queue_row = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=999999
    )
    assert unknown_queue_row.ok is False
    assert "outbound_queue_id" in (unknown_queue_row.error or "")

    # A real contact_id still works.
    real_contact = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, contact_id=test_contact.id
    )
    assert real_contact.ok is True


@pytest.mark.asyncio
async def test_disable_and_delete_advance_updated_at(db_session):
    """Regression: disabling/deleting a set or variant changed durable state without
    advancing updated_at, so a future change-cursor-based sync would miss it.

    Tests the variant and the set independently (rather than one variant under one
    disabled set) because disable_message_set() now cascades to its variants — cascading
    onto an already-disabled variant would make a direct disable_variant() call an
    idempotent no-op that legitimately does not re-advance updated_at.
    """
    service = OutboundMessageLibraryService(db_session)

    variant_set_id = await _make_set(service, set_key="variant_updated_at_set")
    variant = await service.create_variant(message_set_id=variant_set_id, label="A", template_body="Hi there.")
    variant_before = await service.get_variant(variant.id)
    variant_created_updated_at = variant_before.updated_at

    await asyncio.sleep(0.01)
    await service.disable_variant(variant.id)
    row = await db_session.get(type(variant_before), variant.id)
    assert row.updated_at > variant_created_updated_at

    set_id = await _make_set(service, set_key="set_updated_at_set")
    set_before = await service.get_message_set(set_id)
    set_created_updated_at = set_before.updated_at

    await asyncio.sleep(0.01)
    await service.disable_message_set(set_id)
    set_after_disable = await service.get_message_set(set_id)
    assert set_after_disable.updated_at > set_created_updated_at


@pytest.mark.asyncio
async def test_hard_delete_of_set_preserves_usage_history_via_set_null(db_session, test_contact):
    """Regression: message_set_id/variant_id used ON DELETE CASCADE, so a future
    hard-delete during maintenance/retention cleanup would silently erase this
    table's analytics/audit trail. They are now ON DELETE SET NULL, matching the
    existing outbound_authorization_audit pattern, so historical rows survive."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )
    usage = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=test_contact.id,
        selection_reason="only eligible approved variant",
    )
    assert usage.ok is True

    message_set_row = await db_session.get(type(await service.get_message_set(set_id)), set_id)
    await db_session.delete(message_set_row)
    await db_session.flush()

    surviving = await db_session.get(OutboundVariantUsage, usage.id)
    assert surviving is not None
    assert surviving.message_set_id is None
    assert surviving.selection_reason == "only eligible approved variant"


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 4 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_database_rejects_weight_above_100_even_bypassing_the_service(db_session):
    """Regression: the CHECK constraint only enforced the lower bound (weight >= 1),
    so a row inserted outside create_variant() (maintenance script, seed, direct ORM
    use) could carry weight > 100 and later distort weighted selection. The DB
    constraint itself must reject it, independent of the service's own validation."""
    from sqlalchemy.exc import IntegrityError

    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    variant = OutboundMessageVariant(message_set_id=set_id, label="A", template_body="Hi.", weight=150)
    db_session.add(variant)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_disable_message_set_cascades_to_its_variants(db_session):
    """Regression: disabling a set only changed the parent; list_variants_for_set()
    and get_variant() still returned its variants as enabled, and render() would
    still accept them, so a "disabled" set's content stayed fully usable."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant_a = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    variant_b = await service.create_variant(message_set_id=set_id, label="B", template_body="Hello there.")

    await service.disable_message_set(set_id)

    assert await service.list_variants_for_set(set_id) == []
    fetched_a = await service.get_variant(variant_a.id)
    fetched_b = await service.get_variant(variant_b.id)
    assert fetched_a.disabled_at is not None
    assert fetched_a.is_enabled is False
    assert fetched_b.disabled_at is not None
    assert fetched_b.is_enabled is False


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_invalid_selection_score(db_session):
    """Regression: a nonnumeric selection_score (or NaN/inf) reached flush()
    unvalidated and crashed with a conversion/bind error instead of the documented
    fail-closed LibraryResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )

    non_numeric = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_score="high"
    )
    assert non_numeric.ok is False
    assert "selection_score" in (non_numeric.error or "")

    not_finite = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_score=float("nan")
    )
    assert not_finite.ok is False

    bool_score = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_score=True
    )
    assert bool_score.ok is False

    real_score = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_score=0.87
    )
    assert real_score.ok is True


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 5 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_variant_rejects_creation_under_a_disabled_set(db_session):
    """Regression: get_message_set() still returns a disabled (not deleted) set, so
    create_variant() let a new, fully enabled variant be added under it -- undoing
    the disable-cascade for any content added afterward."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    await service.disable_message_set(set_id)

    result = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    assert result.ok is False
    assert "disabled" in (result.error or "")


@pytest.mark.asyncio
async def test_render_rejects_disabled_variant_even_when_fetched_directly(db_session):
    """Regression: get_variant() deliberately still returns a disabled variant (so it
    can be inspected), but render() never checked is_enabled/disabled_at/deleted_at,
    so a caller holding the id could keep rendering a disabled variant's content --
    the cascading-disable fix only matters if render() itself also refuses it."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")

    await service.disable_variant(created.id)
    variant = await service.get_variant(created.id)
    assert variant is not None  # still individually fetchable by design

    result = await service.render(variant)
    assert result.ok is False
    assert "not active" in (result.error or "")
    assert result.text is None


@pytest.mark.asyncio
async def test_create_variant_concurrent_duplicate_label_translates_cleanly(db_session):
    """Regression: create_variant() had the same TOCTOU race as create_message_set --
    the SAVEPOINT wrapping must not break the normal, single-threaded duplicate-label
    rejection path (the actual concurrent-transaction race itself isn't reproducible
    without a second live DB connection, same limitation noted for the set_key fix)."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    first = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    assert first.ok is True

    duplicate = await service.create_variant(message_set_id=set_id, label="A", template_body="Hello there.")
    assert duplicate.ok is False
    assert "already exists" in (duplicate.error or "")


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 6 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_variant_locked_read_still_rejects_a_disabled_set(db_session):
    """Regression: create_variant() now reads the parent set with SELECT ... FOR
    UPDATE (to serialize against a concurrent disable_message_set() UPDATE on the
    same row) rather than the plain get_message_set() read. Confirms that switch
    didn't change the ordinary, single-transaction "set already disabled" outcome.
    The actual cross-transaction race this closes isn't reproducible here (needs a
    second live DB connection), same limitation as the round 4/5 TOCTOU fixes."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    await service.disable_message_set(set_id)

    result = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    assert result.ok is False
    assert "disabled" in (result.error or "")


@pytest.mark.asyncio
async def test_create_variant_normalizes_non_string_metadata_instead_of_crashing(db_session):
    """Regression: media_kind/media_mime/language were length-checked with a raw
    len() call before normalization, so a non-sized value (e.g. an int from a
    JSON-facing caller) raised TypeError instead of being handled cleanly."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    result = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi there.",
        media_kind=12345,
        media_mime=67890,
        language=1,
    )
    assert result.ok is True
    variant = await service.get_variant(result.id)
    assert variant.media_kind == "12345"
    assert variant.media_mime == "67890"
    assert variant.language == "1"


@pytest.mark.asyncio
async def test_create_message_set_normalizes_non_string_primary_language(db_session):
    """Regression: primary_language had the same raw-len()-before-normalization gap
    as create_variant's media fields."""
    service = OutboundMessageLibraryService(db_session)
    result = await service.create_message_set(
        set_key="lead_follow_up",
        name="Lead Follow-up",
        description="d",
        category="c",
        primary_language=1,
    )
    assert result.ok is True
    message_set = await service.get_message_set(result.id)
    assert message_set.primary_language == "1"


@pytest.mark.asyncio
async def test_record_variant_usage_normalizes_non_string_source_automation(db_session):
    """Regression: source_automation had the same raw-len()-before-normalization gap."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )

    result = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, source_automation=42
    )
    assert result.ok is True
    row = await db_session.get(OutboundVariantUsage, result.id)
    assert row.source_automation == "42"


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_huge_selection_score_without_crashing(db_session):
    """Regression: an arbitrarily large Python int (e.g. 10**10000) passes the
    int/float isinstance check but raises OverflowError when math.isfinite() tries
    to convert it to a float, crashing instead of returning the fail-closed result."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )

    result = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_score=10**10000
    )
    assert result.ok is False
    assert "selection_score" in (result.error or "")


@pytest.mark.asyncio
async def test_database_rejects_closed_allowlist_values_even_bypassing_the_service(db_session):
    """Regression: variant status, set selection_strategy, and usage send_result had
    no DB-level CHECK constraint, so a maintenance script, seed, or direct ORM use
    could persist a value outside the documented closed allowlist -- bypassing the
    service's own validation entirely, same class of gap the weight bound fix (round
    4) closed for weight."""
    from sqlalchemy.exc import IntegrityError

    from app.models.schema import OutboundMessageSet

    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    bad_status_variant = OutboundMessageVariant(
        message_set_id=set_id, label="A", template_body="Hi.", status="published"
    )
    db_session.add(bad_status_variant)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    bad_strategy_set = OutboundMessageSet(
        set_key="bad_strategy", name="n", description="d", category="c", selection_strategy="ai_only_random"
    )
    db_session.add(bad_strategy_set)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()

    set_id_2 = await _make_set(service, set_key="send_result_set")
    variant_2 = await service.create_variant(message_set_id=set_id_2, label="A", template_body="Hi.")
    bad_send_result_usage = OutboundVariantUsage(
        message_set_id=set_id_2, variant_id=variant_2.id, send_result="definitely_delivered"
    )
    db_session.add(bad_send_result_usage)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 7 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_ineligible_variant(db_session):
    """Regression: only an approved, active variant was ever eligible to be
    selected, but record_variant_usage() only checked the variant existed and
    belonged to the given set -- a draft, disabled, or deleted variant id (stale,
    or a caller bypassing the selection engine) was recorded as a real selection,
    contaminating per-variant send-result/reply-rate analytics."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    draft_variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi.")
    draft_result = await service.record_variant_usage(message_set_id=set_id, variant_id=draft_variant.id)
    assert draft_result.ok is False
    assert "not an eligible" in (draft_result.error or "")

    approved_variant = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi.", status="approved"
    )
    await service.disable_variant(approved_variant.id)
    disabled_result = await service.record_variant_usage(message_set_id=set_id, variant_id=approved_variant.id)
    assert disabled_result.ok is False
    assert "not an eligible" in (disabled_result.error or "")

    eligible_variant = await service.create_variant(
        message_set_id=set_id, label="C", template_body="Hi.", status="approved"
    )
    eligible_result = await service.record_variant_usage(message_set_id=set_id, variant_id=eligible_variant.id)
    assert eligible_result.ok is True


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_queue_row_for_a_different_contact(db_session):
    """Regression: contact_id and outbound_queue_id were validated independently for
    existence, so a real contact could be paired with a real OutboundMessage row
    addressed to a completely different recipient. The resulting usage row would
    permanently misattribute that delivery/selection in per-contact analytics."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )

    contact_a = Contact(whatsapp_id="15550000001@c.us", display_name="A")
    contact_b = Contact(whatsapp_id="15550000002@c.us", display_name="B")
    db_session.add_all([contact_a, contact_b])
    await db_session.flush()

    queue_row_for_b = OutboundMessage(chat_id="15550000002@c.us", message_text="hi")
    db_session.add(queue_row_for_b)
    await db_session.flush()

    mismatched = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=contact_a.id,
        outbound_queue_id=queue_row_for_b.id,
    )
    assert mismatched.ok is False
    assert "does not belong" in (mismatched.error or "")

    matched = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=contact_b.id,
        outbound_queue_id=queue_row_for_b.id,
    )
    assert matched.ok is True


@pytest.mark.asyncio
async def test_create_variant_rejects_non_list_collection_inputs(db_session):
    """Regression: a non-list required_variables/optional_variables/tags crashed
    (an int isn't iterable) or silently corrupted (a str like "vip" iterates into
    ['v','i','p']) instead of returning the documented fail-closed result."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    int_required = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", required_variables=1
    )
    assert int_required.ok is False
    assert "required_variables" in (int_required.error or "")

    str_optional = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi.", optional_variables="vip"
    )
    assert str_optional.ok is False
    assert "optional_variables" in (str_optional.error or "")

    str_tags = await service.create_variant(
        message_set_id=set_id, label="C", template_body="Hi.", tags="vip"
    )
    assert str_tags.ok is False
    assert "tags" in (str_tags.error or "")

    valid = await service.create_variant(
        message_set_id=set_id, label="D", template_body="Hi.", tags=["vip", "lead"]
    )
    assert valid.ok is True
    variant = await service.get_variant(valid.id)
    assert variant.tags == ["vip", "lead"]


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 8 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_variant_usage_matches_queue_row_against_either_contact_identifier(db_session):
    """Regression: the round-7 fix compared only Contact.whatsapp_id, rejecting a
    legitimate pairing where the queue row targets Contact.chat_id instead -- the
    same either-field convention PushCommandService._contact_for_chat() already uses
    (or_(Contact.chat_id == ..., Contact.whatsapp_id == ...))."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )

    contact = Contact(whatsapp_id="15550000003@c.us", chat_id="15550000003-group@g.us", display_name="C")
    db_session.add(contact)
    await db_session.flush()

    queue_row_via_chat_id = OutboundMessage(chat_id="15550000003-group@g.us", message_text="hi")
    db_session.add(queue_row_via_chat_id)
    await db_session.flush()

    result = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=contact.id,
        outbound_queue_id=queue_row_via_chat_id.id,
    )
    assert result.ok is True

    other_queue_row = OutboundMessage(chat_id="99990000000@c.us", message_text="hi")
    db_session.add(other_queue_row)
    await db_session.flush()

    mismatched = await service.record_variant_usage(
        message_set_id=set_id,
        variant_id=variant.id,
        contact_id=contact.id,
        outbound_queue_id=other_queue_row.id,
    )
    assert mismatched.ok is False
    assert "does not belong" in (mismatched.error or "")


@pytest.mark.asyncio
async def test_allowlist_checks_reject_unhashable_values_instead_of_crashing(db_session):
    """Regression: `x not in <frozenset>` raises TypeError for an unhashable value
    (a list or dict) rather than evaluating to True, so a JSON-facing caller passing
    an object/array for selection_strategy/status/send_result crashed instead of
    getting the documented fail-closed LibraryResult."""
    service = OutboundMessageLibraryService(db_session)

    bad_strategy = await service.create_message_set(
        set_key="x", name="n", description="d", category="c", selection_strategy=["deterministic_score"]
    )
    assert bad_strategy.ok is False

    set_id = await _make_set(service)
    bad_status = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status={"not": "a string"}
    )
    assert bad_status.ok is False

    approved_variant = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi.", status="approved"
    )
    usage = await service.record_variant_usage(message_set_id=set_id, variant_id=approved_variant.id)
    assert usage.ok is True

    bad_send_result = await service.update_usage_send_result(usage.id, ["sent"])
    assert bad_send_result.ok is False


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 9 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_refreshes_stale_cached_lifecycle_state(db_session):
    """Regression: render() checked variant.is_enabled/disabled_at/deleted_at on
    whatever Python object the caller passed in. Since this project's sessions use
    expire_on_commit=False, a variant fetched by one session keeps stale cached
    attributes after a *different* session disables it and commits -- render()
    would substitute retired content unless it refreshes from the database first.

    A single shared session can't demonstrate this: SQLAlchemy's identity map means
    every fetch of the same row within one session returns the same Python object,
    so an in-session disable is already visible with no possible staleness -- this
    needs a second, independent session against the same database, exactly the
    "another session/worker" scenario the fix targets."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )
    variant = await service.get_variant(created.id)
    await db_session.commit()

    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test"
    )
    other_engine = create_async_engine(database_url)
    try:
        other_session_factory = async_sessionmaker(bind=other_engine, expire_on_commit=False)
        async with other_session_factory() as other_session:
            await OutboundMessageLibraryService(other_session).disable_variant(created.id)
            await other_session.commit()
    finally:
        await other_engine.dispose()

    assert variant.is_enabled is True  # confirms the object is stale in this session

    result = await service.render(variant)
    assert result.ok is False
    assert "not active" in (result.error or "")


@pytest.mark.asyncio
async def test_create_variant_rejects_non_string_tag_elements(db_session):
    """Regression: the round-7 fix validated tags was a list but not its elements.
    tags=[object()] passed the list check and crashed at flush() (not JSON
    serializable); a JSON-serializable non-string like {"tier": "vip"} would have
    silently persisted despite the model declaring list[str]."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    result = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", tags=[{"tier": "vip"}]
    )
    assert result.ok is False
    assert "tags" in (result.error or "")

    mixed = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hi.", tags=["vip", 123]
    )
    assert mixed.ok is False
    assert "tags" in (mixed.error or "")


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 10 on PR #49
# ------------------------------------------------------------------------------------


async def _run_in_second_session(coro_factory):
    """Run an async callback against a genuinely independent second session on the
    same database, then commit and dispose -- used to reproduce the
    expire_on_commit=False staleness a single shared session's identity map can't."""
    database_url = os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test"
    )
    engine = create_async_engine(database_url)
    try:
        session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with session_factory() as session:
            await coro_factory(session)
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_record_variant_usage_refreshes_stale_cached_eligibility(db_session):
    """Regression: record_variant_usage()'s eligibility check read
    variant.status/is_enabled/disabled_at off whatever session.get() returned --
    with expire_on_commit=False, session.get() returns the cached object without a
    fresh query if this session already loaded that row, so a variant disabled by a
    *different* session/worker after this session first saw it stayed "eligible"
    here, recording an ineligible selection."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )
    # Load it into this session's identity map first, same as a real caller would.
    variant = await service.get_variant(created.id)
    assert variant is not None
    await db_session.commit()

    async def _disable(other_session):
        await OutboundMessageLibraryService(other_session).disable_variant(created.id)

    await _run_in_second_session(_disable)

    result = await service.record_variant_usage(message_set_id=set_id, variant_id=created.id)
    assert result.ok is False
    assert "not an eligible" in (result.error or "")


@pytest.mark.asyncio
async def test_render_fails_closed_when_variant_is_hard_deleted_concurrently(db_session):
    """Regression: session.refresh() raises InvalidRequestError ("Could not refresh
    instance") -- not a normal empty result -- when the row was physically removed
    by another session -- the
    maintenance/retention hard-delete these tables' own migration comments say must
    stay possible. Unhandled, that would crash render() instead of returning the
    documented fail-closed RenderResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi there.", status="approved"
    )
    variant = await service.get_variant(created.id)
    assert variant is not None
    await db_session.commit()

    async def _hard_delete(other_session):
        row = await other_session.get(OutboundMessageVariant, created.id)
        await other_session.delete(row)

    await _run_in_second_session(_hard_delete)

    result = await service.render(variant)
    assert result.ok is False
    assert result.text is None


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 11 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_variant_rejects_invalid_optional_variable_names(db_session):
    """Regression: required_variables is validated implicitly by its exact-match
    comparison against the tokens actually found in template_body, but
    optional_variables has no such downstream check -- nothing in create_variant
    ever compares it to the body. A value that can never represent a real
    {{token}} (e.g. a hyphenated name) previously passed silently and persisted as
    malformed metadata for the future personalization resolver/selection engine."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)

    rejected = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi there.",
        optional_variables=["first-name"],
    )
    assert rejected.ok is False
    assert "optional_variables" in (rejected.error or "")

    accepted = await service.create_variant(
        message_set_id=set_id,
        label="B",
        template_body="Hi {{first_name}}, welcome.",
        required_variables=["first_name"],
        optional_variables=["nickname"],
    )
    assert accepted.ok is True


@pytest.mark.asyncio
async def test_render_revalidates_a_tampered_template_body(db_session):
    """Regression: render()'s undeclared-token subset check only recognizes a
    well-formed {{token}}; it silently ignores a malformed or unmatched delimiter.
    create_variant() enforces this at creation time, but a maintenance script or
    direct ORM edit could change template_body afterward without going through
    that validation at all, and render() never re-checked for it."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        status="approved",
    )
    variant = await service.get_variant(created.id)
    assert variant is not None

    variant.template_body = "Hi {{first-name}}."
    await db_session.flush()

    malformed = await service.render(variant, {"first_name": "Ada"})
    assert malformed.ok is False
    assert "malformed" in (malformed.error or "")

    variant.template_body = "Hi {{first_name"
    await db_session.flush()

    unmatched = await service.render(variant, {"first_name": "Ada"})
    assert unmatched.ok is False
    assert "unmatched" in (unmatched.error or "")


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_non_string_selection_reason(db_session):
    """Regression: selection_reason from a JSON-facing caller could be a dict or
    list; assigning it directly to the Text column raised a bind/type error at
    flush() instead of returning the documented fail-closed LibraryResult, leaving
    the session requiring rollback."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )

    result = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_reason={"why": "top score"}
    )
    assert result.ok is False
    assert "selection_reason" in (result.error or "")

    ok = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, selection_reason="highest deterministic score"
    )
    assert ok.ok is True


@pytest.mark.asyncio
async def test_record_variant_usage_is_idempotent_for_the_same_queue_row(db_session):
    """Regression: neither the service nor the schema enforced uniqueness on
    outbound_queue_id, so a producer retry (or a duplicate selection-engine call)
    with the same queued delivery inserted a second, independent usage row --
    double-counting the selection and leaving only one of the duplicates able to
    receive its final send result via update_usage_send_result()."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    queue_row = OutboundMessage(chat_id="15550000009@c.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    first = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert first.ok is True

    retry = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert retry.ok is True
    assert retry.id == first.id

    rows = (
        await db_session.execute(
            OutboundVariantUsage.__table__.select().where(
                OutboundVariantUsage.outbound_queue_id == queue_row.id
            )
        )
    ).fetchall()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_create_variant_locked_read_sees_a_set_disabled_by_another_session(db_session):
    """Regression: FOR UPDATE re-runs the query, but SQLAlchemy's identity map
    still returns whatever object this session already loaded for that primary
    key without applying the freshly locked row's column values -- found while
    adding the identical lock to record_variant_usage() in round 11. A caller
    that fetched the message set earlier in this session (e.g. via
    get_message_set(), the same thing a real caller checking "is this set usable"
    first would do) still saw is_enabled=True/disabled_at=None here even though
    another session had already disabled it, defeating the very lock this read
    exists to enforce."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    # Load it into this session's identity map first, same as a real caller would.
    message_set = await service.get_message_set(set_id)
    assert message_set is not None
    await db_session.commit()

    async def _disable(other_session):
        await OutboundMessageLibraryService(other_session).disable_message_set(set_id)

    await _run_in_second_session(_disable)

    result = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    assert result.ok is False
    assert "disabled" in (result.error or "")


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 12 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_disable_message_set_sees_a_disable_committed_by_another_session(db_session):
    """Regression: disable_message_set() read the set through get_message_set(), a
    plain cached get -- with expire_on_commit=False, a session that already loaded
    this set (e.g. to display it) would still see disabled_at=None after another
    session disabled and committed it, missing the idempotent guard, overwriting
    the original disabled_at/updated_at, and emitting a duplicate audit event."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    # Load it into this session's identity map first, same as a real caller would.
    message_set = await service.get_message_set(set_id)
    assert message_set is not None
    await db_session.commit()

    async def _disable_and_capture(other_session):
        other_service = OutboundMessageLibraryService(other_session)
        result = await other_service.disable_message_set(set_id)
        assert result.ok is True

    await _run_in_second_session(_disable_and_capture)

    original_disabled_at = (
        await db_session.execute(
            OutboundMessageSet.__table__.select().where(OutboundMessageSet.id == set_id)
        )
    ).mappings().one()["disabled_at"]
    assert original_disabled_at is not None

    # A second disable_message_set() call in *this* session must recognize the
    # set is already disabled (idempotent no-op), not silently overwrite the
    # timestamp and emit a second audit event.
    result = await service.disable_message_set(set_id)
    assert result.ok is True

    audits = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "outbound_message_set_disabled")
        )
    ).fetchall()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_delete_variant_sees_a_delete_committed_by_another_session(db_session):
    """Regression: delete_variant() read the row through a plain session.get(),
    which -- with expire_on_commit=False -- returns this session's already-cached
    object without a fresh query. A variant already loaded here (e.g. to check its
    label) and then deleted by another session would still look active here,
    missing the idempotent guard and re-running the delete/audit-log path."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    variant = await service.get_variant(created.id)
    assert variant is not None
    await db_session.commit()

    async def _delete(other_session):
        await OutboundMessageLibraryService(other_session).delete_variant(created.id)

    await _run_in_second_session(_delete)

    result = await service.delete_variant(created.id)
    assert result.ok is True

    audits = (
        await db_session.execute(
            AuditLog.__table__.select().where(AuditLog.action == "outbound_message_variant_deleted")
        )
    ).fetchall()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_render_fails_closed_instead_of_crashing_on_a_tampered_optional_token(db_session):
    """Regression: create_variant() enforces tokens_in_body == required_variables
    exactly, so a declared-optional variable can never legitimately appear as a
    literal {{token}} in the body. render()'s subset check (tokens_in_body <=
    required | optional) missed that invariant, so a body tampered with after
    creation (a maintenance script or direct ORM edit) to reference a declared
    but unsupplied optional token passed validation and then crashed
    _substitute() with a plain KeyError instead of returning a fail-closed
    RenderResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        optional_variables=["nickname"],
        status="approved",
    )
    variant = await service.get_variant(created.id)
    assert variant is not None

    variant.template_body = "Hi {{first_name}}, {{nickname}}."
    await db_session.flush()

    result = await service.render(variant, {"first_name": "Ada"})
    assert result.ok is False
    assert result.text is None


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_idempotency_key_reuse_for_a_different_selection(db_session):
    """Regression: the round-11 idempotency fix treated any existing row for the
    same outbound_queue_id as a successful retry, without checking that its
    message_set_id/variant_id/contact_id actually matched the new call. Recording
    variant B against a queue row already claimed by variant A silently returned
    A's usage id as "success", permanently misattributing the delivery in
    per-variant analytics instead of surfacing the conflict."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant_a = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    variant_b = await service.create_variant(
        message_set_id=set_id, label="B", template_body="Hello.", status="approved"
    )
    queue_row = OutboundMessage(chat_id="15550000010@c.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    first = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant_a.id, outbound_queue_id=queue_row.id
    )
    assert first.ok is True

    conflicting = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant_b.id, outbound_queue_id=queue_row.id
    )
    assert conflicting.ok is False
    assert "different selection" in (conflicting.error or "")

    rows = (
        await db_session.execute(
            OutboundVariantUsage.__table__.select().where(
                OutboundVariantUsage.outbound_queue_id == queue_row.id
            )
        )
    ).fetchall()
    assert len(rows) == 1
    assert rows[0].variant_id == variant_a.id


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 13 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_render_rejects_a_non_mapping_variables_argument(db_session):
    """Regression: `variables = variables or {}` only rescues a falsy value (None,
    {}). A JSON-facing caller supplying a truthy non-mapping -- an int, a bare
    string, a list -- reached the membership/indexing checks below and raised a
    plain TypeError instead of the documented fail-closed RenderResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        status="approved",
    )
    variant = await service.get_variant(created.id)
    assert variant is not None

    for bad_variables in (1, "first_name", ["first_name"]):
        result = await service.render(variant, bad_variables)
        assert result.ok is False
        assert "mapping" in (result.error or "")

    ok = await service.render(variant, {"first_name": "Ada"})
    assert ok.ok is True


@pytest.mark.asyncio
async def test_delete_message_set_cascade_preserves_a_concurrently_disabled_childs_timestamp(db_session):
    """Regression: the cascade's child_variants query in delete_message_set() (and
    the identical one in disable_message_set()) had no lock/populate_existing.
    Its WHERE clause only filters deleted_at, not disabled_at, so a child another
    session concurrently disabled (but hadn't deleted) still matches. If this
    session had already cached that child (e.g. via get_variant()) with a stale
    disabled_at=None, `variant.disabled_at = variant.disabled_at or now` saw the
    stale None and overwrote the real disable timestamp with this cascade's,
    losing when the child was actually disabled."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    # Load it into this session's identity map first, same as a real caller would.
    variant = await service.get_variant(created.id)
    assert variant is not None
    await db_session.commit()

    async def _disable_child(other_session):
        result = await OutboundMessageLibraryService(other_session).disable_variant(created.id)
        assert result.ok is True

    await _run_in_second_session(_disable_child)

    original_disabled_at = (
        await db_session.execute(
            OutboundMessageVariant.__table__.select().where(OutboundMessageVariant.id == created.id)
        )
    ).mappings().one()["disabled_at"]
    assert original_disabled_at is not None

    result = await service.delete_message_set(set_id)
    assert result.ok is True

    refreshed = (
        await db_session.execute(
            OutboundMessageVariant.__table__.select().where(OutboundMessageVariant.id == created.id)
        )
    ).mappings().one()
    assert refreshed["deleted_at"] is not None
    assert refreshed["disabled_at"] == original_disabled_at


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 14 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_message_set_and_get_variant_see_a_delete_committed_by_another_session(db_session):
    """Regression: get_message_set()/get_variant() read through session.get(),
    which -- with expire_on_commit=False -- returns this session's already-cached
    object without a fresh query. A set/variant fetched earlier in this session
    and then soft-deleted by another session would still pass the deleted_at
    filter here, so a long-lived caller (a dashboard poll, a producer holding the
    id) would keep treating a deleted row as active."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    # Load both into this session's identity map first, same as a real caller would.
    assert await service.get_message_set(set_id) is not None
    assert await service.get_variant(created.id) is not None
    await db_session.commit()

    async def _delete_both(other_session):
        other_service = OutboundMessageLibraryService(other_session)
        assert (await other_service.delete_variant(created.id)).ok is True
        assert (await other_service.delete_message_set(set_id)).ok is True

    await _run_in_second_session(_delete_both)

    assert await service.get_variant(created.id) is None
    assert await service.get_message_set(set_id) is None


@pytest.mark.asyncio
async def test_record_variant_usage_retry_succeeds_after_the_variant_becomes_ineligible(db_session):
    """Regression: the eligibility check ran before the idempotency lookup, so a
    delayed producer retry of a call that had already succeeded was rejected as
    "not eligible" once the variant was disabled in between -- even though the
    selection genuinely already happened and the retry should just return the
    existing usage id, not a failure."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    queue_row = OutboundMessage(chat_id="15550000011@c.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    first = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert first.ok is True

    disabled = await service.disable_variant(variant.id)
    assert disabled.ok is True

    retry = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert retry.ok is True
    assert retry.id == first.id

    rows = (
        await db_session.execute(
            OutboundVariantUsage.__table__.select().where(
                OutboundVariantUsage.outbound_queue_id == queue_row.id
            )
        )
    ).fetchall()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_render_fails_closed_on_malformed_required_variables_metadata(db_session):
    """Regression: the JSONB required_variables column has no shape constraint, so
    maintenance code or direct ORM use could persist something JSON-valid but not
    a list of strings (e.g. a list of dicts). create_variant() would never
    produce that, but render() re-validates persisted data for exactly this
    bypass scenario -- set() on a list containing an unhashable dict raised a
    plain TypeError instead of the documented fail-closed RenderResult."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(
        message_set_id=set_id,
        label="A",
        template_body="Hi {{first_name}}.",
        required_variables=["first_name"],
        status="approved",
    )
    variant = await service.get_variant(created.id)
    assert variant is not None

    variant.required_variables = [{"name": "first_name"}]
    await db_session.flush()

    result = await service.render(variant, {"first_name": "Ada"})
    assert result.ok is False
    assert "required_variables" in (result.error or "")


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 15 on PR #49
# ------------------------------------------------------------------------------------


def test_orm_metadata_declares_the_queue_idempotency_unique_index():
    """Regression: migration 034 creates ux_outbound_variant_usage_queue, but the
    mapped table declared only the send_result check. A database initialized
    through Base.metadata.create_all() with no prior migration -- as
    tests/conftest.py's setup fixture does when nothing has created the tables
    yet -- would lack the unique index entirely, letting two concurrent
    record_variant_usage() calls both pass the advisory lookup and insert
    duplicate usage rows for one queue delivery."""
    indexes = {idx.name: idx for idx in OutboundVariantUsage.__table__.indexes}
    assert "ux_outbound_variant_usage_queue" in indexes
    assert indexes["ux_outbound_variant_usage_queue"].unique is True


@pytest.mark.asyncio
async def test_list_message_sets_and_list_variants_see_a_disable_committed_by_another_session(db_session):
    """Regression: list_message_sets()/list_variants_for_set() lacked
    populate_existing=True. A set/variant this session already cached (e.g. from
    an earlier get_message_set() call) was reselected correctly by the SQL WHERE,
    but returned as the identity map's stale Python object -- most visible with
    include_disabled=True, where a dashboard/management caller would see a set
    another session just disabled as still active."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    created = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
    # Load both into this session's identity map first, same as a real caller would.
    assert await service.get_message_set(set_id) is not None
    assert await service.get_variant(created.id) is not None
    await db_session.commit()

    async def _disable_both(other_session):
        other_service = OutboundMessageLibraryService(other_session)
        assert (await other_service.disable_variant(created.id)).ok is True
        assert (await other_service.disable_message_set(set_id)).ok is True

    await _run_in_second_session(_disable_both)

    sets = await service.list_message_sets(include_disabled=True)
    assert next(s for s in sets if s.id == set_id).disabled_at is not None

    variants = await service.list_variants_for_set(set_id, include_disabled=True)
    assert next(v for v in variants if v.id == created.id).disabled_at is not None


@pytest.mark.asyncio
async def test_database_rejects_a_variant_paired_with_a_different_sets_id(db_session):
    """Regression: message_set_id and variant_id on outbound_variant_usage were
    independent foreign keys with no cross-check, so a direct ORM insert, seed,
    or maintenance script could pair a real variant with a message_set_id
    belonging to a *different* set even though record_variant_usage() already
    rejects that pairing in application code -- corrupting per-set/per-variant
    analytics grouping for anything that bypasses the service."""
    service = OutboundMessageLibraryService(db_session)
    set_a = await _make_set(service, set_key="set_a")
    set_b = await _make_set(service, set_key="set_b", name="Set B")
    variant = await service.create_variant(message_set_id=set_a, label="A", template_body="Hi.")

    db_session.add(OutboundVariantUsage(message_set_id=set_b, variant_id=variant.id))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_database_rejects_a_non_finite_selection_score(db_session):
    """Regression: record_variant_usage() rejects NaN/infinite selection_score
    before insert, but the database column had no equivalent constraint, so a
    seed, maintenance script, or direct ORM insert could persist a value that
    would corrupt any future average/ordering-based selection analytics."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi.")

    db_session.add(
        OutboundVariantUsage(message_set_id=set_id, variant_id=variant.id, selection_score=float("nan"))
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_record_variant_usage_retry_survives_a_hard_deleted_variant(db_session):
    """Regression: message_set_id/variant_id/contact_id are ON DELETE SET NULL, so
    a supported hard-delete of the variant (maintenance/retention cleanup) nulls
    variant_id on an already-recorded usage row (via its own independent foreign
    key -- message_set_id is untouched, since the set itself wasn't deleted;
    round 16 replaced an earlier composite-FK design that incorrectly nulled
    both together) without touching the row itself. A later retry with the
    *original* ids then failed the identity comparison (a real id against a
    now-None field) and was reported as a conflict against a "different
    selection" instead of the same idempotent retry it actually is."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    queue_row = OutboundMessage(chat_id="15550000012@c.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    first = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert first.ok is True

    # Hard-delete the variant directly (the supported maintenance/retention path
    # these tables' own comments describe) -- nulls variant_id on the existing
    # usage row; message_set_id survives since the set itself is untouched.
    variant_row = await db_session.get(OutboundMessageVariant, variant.id)
    await db_session.delete(variant_row)
    await db_session.flush()

    retry = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert retry.ok is True
    assert retry.id == first.id


# ------------------------------------------------------------------------------------
# Regressions for chatgpt-codex-connector review round 16 on PR #49
# ------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_record_variant_usage_rejects_reuse_when_original_selection_is_fully_erased(db_session):
    """Regression: the round-15 fix treated a None field on the existing usage row
    as unverifiable rather than mismatched, to let a retry survive a hard-delete
    of *part* of the original selection. But if the set is hard-deleted (which
    cascades to its variants), both message_set_id and variant_id null out
    together, and with no contact ever recorded, contact_id was already None too
    -- every field becomes a wildcard. A completely different later call (a
    different set, variant, and contact) then silently claimed the same
    outbound_queue_id and was reported as a successful "retry" of a selection it
    had nothing to do with."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    queue_row = OutboundMessage(chat_id="15550000013@c.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    first = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, outbound_queue_id=queue_row.id
    )
    assert first.ok is True

    # Hard-delete the set directly -- cascades to the variant, nulling both
    # message_set_id and variant_id on the existing usage row. contact_id was
    # never set, so every identity field is now None.
    set_row = await db_session.get(OutboundMessageSet, set_id)
    await db_session.delete(set_row)
    await db_session.flush()

    other_set = await _make_set(service, set_key="other_set", name="Other Set")
    other_variant = await service.create_variant(
        message_set_id=other_set, label="B", template_body="Hello.", status="approved"
    )

    conflicting = await service.record_variant_usage(
        message_set_id=other_set, variant_id=other_variant.id, outbound_queue_id=queue_row.id
    )
    assert conflicting.ok is False


@pytest.mark.asyncio
async def test_record_variant_usage_refreshes_a_stale_locked_contact(db_session):
    """Regression: the round-14 fix locked the contact with SELECT ... FOR UPDATE
    but no populate_existing=True -- the same identity-map gap rounds 12/14 fixed
    everywhere else in this file. router.py::_apply_contact_identity() routinely
    updates Contact.chat_id; a contact this session had already cached with a
    stale (e.g. missing) chat_id would still show that stale value here even
    under the lock, so the whatsapp_id/chat_id cross-check below could wrongly
    reject a queue row addressed to the contact's real, current identity."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(
        message_set_id=set_id, label="A", template_body="Hi.", status="approved"
    )
    contact = Contact(whatsapp_id="15550000014@c.us", display_name="Stale Chat")
    db_session.add(contact)
    await db_session.flush()
    # Load into this session's identity map first, same as a real caller would
    # (e.g. an earlier lookup in the same request).
    assert await db_session.get(Contact, contact.id) is not None
    await db_session.commit()

    async def _set_chat_id(other_session):
        other_contact = await other_session.get(Contact, contact.id)
        other_contact.chat_id = "15550000014-group@g.us"

    await _run_in_second_session(_set_chat_id)

    queue_row = OutboundMessage(chat_id="15550000014-group@g.us", message_text="hi")
    db_session.add(queue_row)
    await db_session.flush()

    result = await service.record_variant_usage(
        message_set_id=set_id, variant_id=variant.id, contact_id=contact.id, outbound_queue_id=queue_row.id
    )
    assert result.ok is True


def test_orm_metadata_declares_the_active_label_unique_index():
    """Regression: migration 034 declares ux_outbound_message_variants_set_label,
    but the mapped table ended without the equivalent partial unique index. On a
    schema initialized purely through Base.metadata.create_all(), two concurrent
    create_variant() calls could both pass the duplicate-label query and both
    insert the same active (message_set_id, label) pair, since the database
    constraint the SAVEPOINT handling relies on would be absent."""
    indexes = {idx.name: idx for idx in OutboundMessageVariant.__table__.indexes}
    assert "ux_outbound_message_variants_set_label" in indexes
    assert indexes["ux_outbound_message_variants_set_label"].unique is True
