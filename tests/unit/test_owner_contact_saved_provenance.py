from app.models.schema import Contact
from app.services.owner_management_command_service import OwnerManagementCommandService


def test_saved_contact_stays_saved_after_inbound_identity_source_changes():
    contact = Contact(
        whatsapp_id="2348012345678@c.us",
        contact_name="Amanda Christabel",
        push_name="Amanda",
        identity_source="push_name",
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
