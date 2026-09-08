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
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.schema import AuditLog, Contact, OutboundMessage, OutboundMessageVariant, OutboundVariantUsage
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
