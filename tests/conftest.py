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
from app.models.schema import Contact, FAQEntry, UserMemory, UserMemoryTimeline
from app.utils.text import normalize_text


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
        for model in (UserMemoryTimeline, UserMemory, FAQEntry, Contact):
            await session.execute(delete(model))
        await session.commit()
        yield session
        await session.rollback()
        for model in (UserMemoryTimeline, UserMemory, FAQEntry, Contact):
            await session.execute(delete(model))
        await session.commit()
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


@pytest.fixture
def mock_memory_service():
    return MockMemoryService
