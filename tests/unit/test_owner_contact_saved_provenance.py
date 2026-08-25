from datetime import datetime, timezone

from app.models.schema import Contact
from app.services.owner_management_command_service import OwnerManagementCommandService


def test_saved_contact_stays_saved_after_inbound_identity_source_changes():
    contact = Contact(
        whatsapp_id="2348012345678@c.us",
        contact_name="Amanda Christabel",
        push_name="Amanda",
        identity_source="push_name",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-25T18:00:00+00:00",
        },
    )

    assert OwnerManagementCommandService._is_saved(contact) is True


def test_push_or_display_name_without_address_book_name_is_unsaved():
    contact = Contact(
        whatsapp_id="2348099999999@c.us",
        display_name="Mandy",
        push_name="Mandy",
        identity_source="push_name",
    )

    assert OwnerManagementCommandService._is_saved(contact) is False


def test_explicit_removed_saved_marker_overrides_stale_contact_name():
    contact = Contact(
        whatsapp_id="2348088888888@c.us",
        contact_name="Formerly Saved",
        identity_json={
            "is_saved_contact": False,
            "saved_contact_synced_at": "2026-08-25T19:00:00+00:00",
            "saved_contact_reconciled_reason": "absent_from_full_waha_contact_scan",
        },
    )

    assert OwnerManagementCommandService._is_saved(contact) is False


def test_saved_evidence_timestamp_comes_from_sync_marker_not_contact_updated_at():
    contact = Contact(
        whatsapp_id="2348077777777@c.us",
        contact_name="Amanda",
        updated_at=datetime(2026, 8, 25, 20, 30, tzinfo=timezone.utc),
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-25T18:15:00+00:00",
        },
    )

    assert OwnerManagementCommandService._saved_evidence_at(contact) == datetime(
        2026, 8, 25, 18, 15, tzinfo=timezone.utc
    )
