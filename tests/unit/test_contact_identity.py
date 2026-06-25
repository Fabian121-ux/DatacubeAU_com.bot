from __future__ import annotations

import pytest

from app.core.message_normalizer import MessageNormalizer
from app.core.router import InboundRouter
from app.models.schema import Contact


class FakeScalar:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class FakeContactSession:
    def __init__(self, row=None):
        self.row = row
        self.added = None
        self.flushed = False

    async def execute(self, _statement):
        return FakeScalar(self.row)

    def add(self, row):
        row.id = 1
        self.added = row
        self.row = row

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_waha_push_name_and_number_are_stored_on_contact() -> None:
    normalized = MessageNormalizer().normalize(
        {
            "chatId": "15550000001@c.us",
            "from": "15550000001@c.us",
            "sender": {"phone": "+1 555 000 0001", "pushName": "Ada"},
            "text": {"body": "hello"},
        }
    )
    router = InboundRouter.__new__(InboundRouter)
    router.session = FakeContactSession()

    contact = await router._get_or_create_contact(normalized)

    assert contact.display_name == "Ada"
    assert contact.push_name == "Ada"
    assert contact.whatsapp_phone == "+1 555 000 0001"
    assert contact.normalized_phone == "15550000001"
    assert contact.chat_id == "15550000001@c.us"
    assert contact.identity_source == "push_name"


@pytest.mark.asyncio
async def test_verified_contact_name_is_not_overwritten_by_waha_metadata() -> None:
    existing = Contact(whatsapp_id="15550000001@c.us", display_name="Manual Name", is_name_verified=True)
    normalized = MessageNormalizer().normalize(
        {
            "chatId": "15550000001@c.us",
            "from": "15550000001@c.us",
            "contact": {"name": "WAHA Name"},
            "text": {"body": "hello"},
        }
    )
    router = InboundRouter.__new__(InboundRouter)
    router.session = FakeContactSession(existing)

    contact = await router._get_or_create_contact(normalized)

    assert contact.display_name == "Manual Name"
    assert contact.contact_name == "WAHA Name"
    assert contact.identity_source == "contact_name"
