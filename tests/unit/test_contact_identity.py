from __future__ import annotations

import pytest

from app.core.message_normalizer import MessageNormalizer
from app.core.router import InboundRouter
from app.models.schema import Contact


class FakeScalar:
    def __init__(self, row):
        self.row = row

    def scalar_one(self):
        return self.row

    def scalar_one_or_none(self):
        return self.row

    def one_or_none(self):
        return self.row

    def scalars(self):
        # Match the SQLAlchemy Result.scalars() API used by the alias lookup.
        return self

    def all(self):
        # The fake session models a single canonical row; when that lookup misses,
        # the alternate-chat lookup must return no rows rather than raising.
        return [] if self.row is None else [self.row]


class FakeContactSession:
    def __init__(self, row=None):
        self.row = row
        if row is not None and row.id is None:
            row.id = 1  # Existing rows returned by a database already have a primary key.
        self.added = None
        self.flushed = False

    async def execute(self, statement, _params=None):
        # The consent service asks PostgreSQL whether a pending STOP/opt-out
        # exists. Model SELECT EXISTS as a scalar boolean, not as the Contact row
        # returned by the other ORM queries in this fake session.
        if str(statement).lstrip().upper().startswith("SELECT EXISTS"):
            return FakeScalar(False)

        # _mapped_direct_chat_ids selects two scalar columns, while the router's
        # contact lookups select the ORM entity. Preserve each result shape.
        descriptions = getattr(statement, "column_descriptions", ())
        if len(descriptions) == 2:
            row = None if self.row is None else (self.row.whatsapp_id, self.row.chat_id)
            return FakeScalar(row)
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
