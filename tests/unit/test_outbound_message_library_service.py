"""Foundational data-model layer for the Intelligent Outbound Message Library.

Roadmap Phase 17 (docs/ZINA_IMPLEMENTATION_ROADMAP.md): reusable message sets and
their approved template variants, plus an analytics/audit trail of which variant was
selected for which contact and why. This service answers "WHAT COULD ZINA SAY?" only
-- it has zero outbound authority, is not wired into any producer or delivery path,
and selecting/rendering a variant never sends anything or implies send authority.
These tests cover CRUD lifecycle, fail-closed validation, and template rendering.
"""

from __future__ import annotations

import pytest

from app.models.schema import AuditLog, OutboundVariantUsage
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

    result = service.render(variant, {"first_name": "Ada", "project": "ZinaX"})
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

    missing_entirely = service.render(variant, {"first_name": "Ada"})
    assert missing_entirely.ok is False
    assert missing_entirely.missing_variables == ["project"]
    assert missing_entirely.text is None

    empty_value = service.render(variant, {"first_name": "Ada", "project": ""})
    assert empty_value.ok is False
    assert empty_value.missing_variables == ["project"]

    no_variables_at_all = service.render(variant, None)
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

    result = service.render(variant, {"first_name": "Ada"})
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
    variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")

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

    result = service.render(variant, {"first_name": "   "})
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
    variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")

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
    advancing updated_at, so a future change-cursor-based sync would miss it."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")

    set_before = await service.get_message_set(set_id)
    set_created_at_updated_at = set_before.updated_at

    await service.disable_message_set(set_id)
    set_after_disable = await service.get_message_set(set_id)
    assert set_after_disable.updated_at > set_created_at_updated_at

    variant_before = await service.get_variant(variant.id)
    variant_created_updated_at = variant_before.updated_at

    await service.disable_variant(variant.id)
    row = await db_session.get(type(variant_before), variant.id)
    assert row.updated_at > variant_created_updated_at


@pytest.mark.asyncio
async def test_hard_delete_of_set_preserves_usage_history_via_set_null(db_session, test_contact):
    """Regression: message_set_id/variant_id used ON DELETE CASCADE, so a future
    hard-delete during maintenance/retention cleanup would silently erase this
    table's analytics/audit trail. They are now ON DELETE SET NULL, matching the
    existing outbound_authorization_audit pattern, so historical rows survive."""
    service = OutboundMessageLibraryService(db_session)
    set_id = await _make_set(service)
    variant = await service.create_variant(message_set_id=set_id, label="A", template_body="Hi there.")
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
