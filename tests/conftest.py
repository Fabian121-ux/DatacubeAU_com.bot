from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.message_normalizer import NormalizedMessage
from app.models.enums import ChatType
from app.models.scheduled_action import ScheduledAction
from app.models.schema import (
    AdminAccount,
    AICall,
    AIUsageEvent,
    AIUsageQuota,
    AuditLog,
    BotConfig,
    Contact,
    ConversationSummary,
    ConversationTimeline,
    FeedbackReview,
    ForcedReplyTarget,
    FAQEntry,
    FAQImportCandidate,
    GroupMetadata,
    IdentityRegistryEntry,
    InternetCache,
    InternetUsageEvent,
    Message,
    OutboundMessage,
    CommandCatalogEntry,
    UserTrigger,
    UserMemory,
    UserMemoryTimeline,
)
from app.services.memory_service import MemoryContextPackage
from app.utils.text import normalize_text
from app.db import Base


# Single source of truth for per-test database cleanup, ordered child-before-parent.
#
# A table missing from this tuple keeps any row a test committed, which leaks state
# into later tests and across repeated local runs against the same database. That is
# how committed `admin_accounts` rows survived teardown and made unrelated
# command-control tests fail on `admin_accounts_normalized_whatsapp_id_key`.
CLEANUP_MODELS = (
    ScheduledAction,
    OutboundMessage,
    AIUsageEvent,
    InternetUsageEvent,
    InternetCache,
    AIUsageQuota,
    AICall,
    Message,
    GroupMetadata,
    ConversationSummary,
    ConversationTimeline,
    FeedbackReview,
    ForcedReplyTarget,
    UserTrigger,
    UserMemoryTimeline,
    UserMemory,
    FAQImportCandidate,
    FAQEntry,
    IdentityRegistryEntry,
    CommandCatalogEntry,
    Contact,
    AdminAccount,
    AuditLog,
    BotConfig,
)


# Tables created by raw SQL migrations have no ORM model, so the model-based cleanup
# above cannot reach them. `outbound_approvals` and `outbound_authorization_audit` are
# removed transitively by their cascading parents, but the rest survive teardown.
# A leaked `inbound_webhook_receipts` row makes a later test's webhook look like a
# duplicate delivery, which silently suppresses routing.
CLEANUP_RAW_TABLES = (
    "inbound_webhook_receipts",
    "outbound_approvals",
    "outbound_authorization_audit",
    "contact_automation_policies",
    "view_once_media_metadata",
)


async def _purge_database_state(session) -> None:
    """Remove every row this suite may have committed, in dependency-safe order."""
    for model in CLEANUP_MODELS:
        await session.execute(delete(model))
    if CLEANUP_RAW_TABLES:
        # Skip tables that do not exist yet, so a database predating a migration does
        # not fail the fixture. Names are internal constants, never test input.
        present = (
            await session.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename = ANY(:names)"
                ),
                {"names": list(CLEANUP_RAW_TABLES)},
            )
        ).scalars().all()
        for table in present:
            await session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    await session.commit()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
    )
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
    )
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        await engine.dispose()
        pytest.skip(f"test database is unavailable: {exc}")

    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with Session() as session:
        await _purge_database_state(session)
        yield session
        await session.rollback()
        await _purge_database_state(session)
    await engine.dispose()


@pytest_asyncio.fixture
async def test_contact(db_session):
    contact = Contact(whatsapp_id="15550000001@c.us", display_name="Test User")
    db_session.add(contact)
    await db_session.flush()
    return contact


@pytest.fixture
def normalized_dm_message() -> NormalizedMessage:
    return NormalizedMessage(
        chat_id="15550000001@c.us",
        sender_id="15550000001@c.us",
        sender_name="Test User",
        chat_type=ChatType.DM,
        message_text="hello",
        normalized_text=normalize_text("hello"),
        message_type="text",
        is_bot_mentioned=False,
        payload={"source": "test"},
    )


@dataclass
class MockOpenRouterResult:
    text: str = "AI answer from Zina."
    model: str = "test-model"
    prompt_hash: str = "test-prompt-hash"
    prompt_tokens: int = 10
    completion_tokens: int = 5
    latency_ms: int = 12
    request_json: dict[str, Any] | None = None
    response_json: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.request_json is None:
            self.request_json = {"mock": True}
        if self.response_json is None:
            self.response_json = {"mock": True}


class MockOpenRouterClient:
    calls = 0

    async def generate(self, **_: Any) -> MockOpenRouterResult:
        type(self).calls += 1
        return MockOpenRouterResult()

    async def close(self) -> None:
        return None


@pytest.fixture
def mock_openrouter():
    MockOpenRouterClient.calls = 0
    return MockOpenRouterClient


class MockWahaClient:
    def __init__(self, status: dict[str, Any] | None = None, error: Exception | None = None):
        self.status = status or {"status": "WORKING"}
        self.error = error
        self.closed = False

    async def get_session_status(self) -> dict[str, Any]:
        if self.error:
            raise self.error
        return self.status

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def mock_waha():
    return MockWahaClient


class MockMemoryService:
    def __init__(self, onboarding_reply: str | None = None):
        self.onboarding_reply = onboarding_reply
        self.checked = False

    async def check_onboarding(self, *_: Any) -> tuple[str | None, str | None]:
        self.checked = True
        if self.onboarding_reply:
            return self.onboarding_reply, "ask_name"
        return None, None

    async def get_memory(self, *_: Any) -> None:
        return None

    def get_memory_context(self, *_: Any) -> str:
        return ""

    async def set_global_chat(self, *_: Any) -> None:
        return None

    async def get_context_package(self, contact_id: int, **_: Any) -> MemoryContextPackage:
        return MemoryContextPackage(contact_id=contact_id)

    def build_continuation_reply(self, *_: Any) -> None:
        return None

    @staticmethod
    def diagnostics_for_package(package: MemoryContextPackage | None) -> dict[str, Any]:
        if not package:
            return {"retrieved_items": 0, "used": []}
        return {"retrieved_items": package.retrieved_item_count, "used": package.used_sections}


@pytest.fixture
def mock_memory_service():
    return MockMemoryService
