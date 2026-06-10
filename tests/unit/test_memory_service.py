from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.schema import UserMemoryTimeline
from app.services.memory_service import MemoryService


class FakeMemorySession:
    def __init__(self):
        self.added = []
        self.deleted = []
        self.executed = []
        self.flushed = False

    def add(self, model):
        self.added.append(model)

    async def delete(self, model):
        self.deleted.append(model)

    async def execute(self, statement):
        self.executed.append(statement)

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_memory_create_retrieve_update_delete_and_timeline_cleanup(db_session, test_contact) -> None:
    service = MemoryService(db_session)

    created = await service.upsert_memory(
        test_contact.id,
        user_name="Ada",
        preferences="short replies",
        profession="developer",
        onboarding_complete=True,
    )
    await service.log_memory_fact(
        test_contact.id,
        memory_text="profession: developer",
        source="admin",
        confidence=0.91,
    )

    retrieved = await service.get_memory(test_contact.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_name == "Ada"
    assert retrieved.profession == "developer"

    updated = await service.upsert_memory(
        test_contact.id,
        user_name=None,
        preferences="concise technical replies",
        projects="Datacube AU",
        goals="ship reliable assistants",
    )
    assert updated.user_name == "Ada"
    assert updated.preferences == "concise technical replies"
    assert updated.projects == "Datacube AU"

    timeline_count = (
        await db_session.execute(
            select(func.count(UserMemoryTimeline.id)).where(UserMemoryTimeline.contact_id == test_contact.id)
        )
    ).scalar_one()
    assert timeline_count == 1

    assert await service.delete_memory(test_contact.id) is True
    assert await service.get_memory(test_contact.id) is None
    timeline_count_after_delete = (
        await db_session.execute(
            select(func.count(UserMemoryTimeline.id)).where(UserMemoryTimeline.contact_id == test_contact.id)
        )
    ).scalar_one()
    assert timeline_count_after_delete == 0
    assert await service.delete_memory(test_contact.id) is False


@pytest.mark.asyncio
async def test_upsert_memory_create_and_update_without_database() -> None:
    session = FakeMemorySession()
    service = MemoryService(session)  # type: ignore[arg-type]

    async def no_memory(_contact_id):
        return None

    service.get_memory = no_memory  # type: ignore[method-assign]
    created = await service.upsert_memory(
        10,
        user_name="Ada",
        preferences="concise",
        context_notes="likes examples",
        onboarding_complete=True,
        profession="developer",
        interests="AI",
        projects="Datacube AU",
        goals="reliable automation",
        communication_style="direct",
        relationship="client",
    )

    assert created in session.added
    assert created.user_name == "Ada"
    assert created.onboarding_complete is True
    assert session.flushed is True

    async def existing_memory(_contact_id):
        return created

    service.get_memory = existing_memory  # type: ignore[method-assign]
    updated = await service.upsert_memory(10, user_name=None, preferences="technical", projects="Zina")

    assert updated is created
    assert updated.user_name == "Ada"
    assert updated.preferences == "technical"
    assert updated.projects == "Zina"


@pytest.mark.asyncio
async def test_log_and_delete_memory_without_database() -> None:
    session = FakeMemorySession()
    service = MemoryService(session)  # type: ignore[arg-type]

    entry = await service.log_memory_fact(10, memory_text="x" * 1500, source="admin-source-too-long", confidence=5.0)

    assert isinstance(entry, UserMemoryTimeline)
    assert entry in session.added
    assert len(entry.memory_text) == 1200
    assert entry.source == "admin-source-too-long"
    assert entry.confidence == 1.0

    class ExistingMemory:
        contact_id = 10

    async def existing_memory(_contact_id):
        return ExistingMemory()

    service.get_memory = existing_memory  # type: ignore[method-assign]

    assert await service.delete_memory(10) is True
    assert len(session.executed) == 1
    assert len(session.deleted) == 1


@pytest.mark.asyncio
async def test_extract_profile_from_message_without_database() -> None:
    service = MemoryService(FakeMemorySession())  # type: ignore[arg-type]

    class Memory:
        profession = None
        interests = "AI"
        projects = None
        goals = None
        communication_style = None
        relationship = None

    memory = Memory()
    facts = []

    async def get_memory(_contact_id):
        return memory

    async def log_fact(_contact_id, **kwargs):
        facts.append(kwargs)

    service.get_memory = get_memory  # type: ignore[method-assign]
    service.log_memory_fact = log_fact  # type: ignore[method-assign]

    changed = await service.extract_profile_from_message(
        10,
        "I'm a developer. I like AI automation. I'm building Zina.",
    )

    assert "profession: developer" in changed
    assert "projects: Zina" in changed
    assert memory.interests == "AI; AI automation"
    assert len(facts) == len(changed)


@pytest.mark.asyncio
async def test_extract_profile_from_message_merges_facts_and_creates_timeline(db_session, test_contact) -> None:
    service = MemoryService(db_session)
    message = (
        "I'm a backend engineer. I am interested in AI automation. "
        "I'm building a WhatsApp assistant. My goal is ship production systems. "
        "Please keep concise replies. Fabian is my mentor."
    )

    changed = await service.extract_profile_from_message(test_contact.id, message)
    memory = await service.get_memory(test_contact.id)

    assert memory is not None
    assert "profession:" in changed[0]
    assert memory.profession == "backend engineer"
    assert memory.interests == "AI automation"
    assert memory.projects == "a WhatsApp assistant"
    assert memory.goals == "ship production systems"
    assert memory.communication_style == "concise replies"
    assert memory.relationship == "mentor"

    timeline_rows = (
        await db_session.execute(
            select(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == test_contact.id)
        )
    ).scalars().all()
    assert len(timeline_rows) == len(changed)
    assert all(row.source == "chat_extraction" for row in timeline_rows)
    assert all(0.0 <= row.confidence <= 1.0 for row in timeline_rows)

    duplicate = await service.extract_profile_from_message(test_contact.id, "I'm a backend engineer.")
    assert duplicate == []


def test_memory_context_includes_profile_fields() -> None:
    class Memory:
        user_name = "Ada"
        preferences = "concise"
        context_notes = "likes examples"
        profession = "developer"
        interests = "AI"
        projects = "Datacube AU"
        goals = "reliable automation"
        communication_style = "direct"
        relationship = "client"

    context = MemoryService(None).get_memory_context(Memory())  # type: ignore[arg-type]

    assert "User name: Ada" in context
    assert "Profession: developer" in context
    assert "Relationship to Fabian: client" in context
    assert MemoryService(None).get_memory_context(None) == ""  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("I'm a backend engineer", {"profession": "backend engineer"}),
        ("I like AI automation", {"interests": "AI automation"}),
        ("I'm building Datacube AU", {"projects": "Datacube AU"}),
        ("My goal is reduce repeated support conversations", {"goals": "reduce repeated support conversations"}),
        ("Please keep concise replies", {"communication_style": "concise replies"}),
        ("Fabian is my mentor", {"relationship": "mentor"}),
        ("hi", {}),
    ],
)
def test_profile_field_extraction(message: str, expected: dict[str, str]) -> None:
    assert MemoryService._extract_profile_fields(message) == expected


def test_merge_fact_deduplicates_and_appends() -> None:
    assert MemoryService._merge_fact(None, "AI") == "AI"
    assert MemoryService._merge_fact("AI automation", "AI") == "AI automation"
    assert MemoryService._merge_fact("AI", "backend systems") == "AI; backend systems"


@pytest.mark.asyncio
async def test_onboarding_starts_with_name_and_logs_fact() -> None:
    service = MemoryService(None)  # type: ignore[arg-type]
    calls = {"upsert": [], "facts": []}

    async def get_memory(_contact_id):
        return None

    async def upsert_memory(contact_id, **kwargs):
        calls["upsert"].append((contact_id, kwargs))

    async def log_memory_fact(contact_id, **kwargs):
        calls["facts"].append((contact_id, kwargs))

    service.get_memory = get_memory  # type: ignore[method-assign]
    service.upsert_memory = upsert_memory  # type: ignore[method-assign]
    service.log_memory_fact = log_memory_fact  # type: ignore[method-assign]

    reply, stage = await service.check_onboarding(10, "My name is Ada")

    assert stage == "ask_preferences"
    assert "Nice to meet you, Ada!" in reply
    assert calls["upsert"] == [(10, {"user_name": "Ada"})]
    assert calls["facts"][0][1]["memory_text"] == "user_name: Ada"


@pytest.mark.asyncio
async def test_onboarding_asks_for_name_when_new_user_has_no_name() -> None:
    service = MemoryService(None)  # type: ignore[arg-type]
    created = []

    async def get_memory(_contact_id):
        return None

    async def upsert_memory(contact_id, **kwargs):
        created.append((contact_id, kwargs))

    service.get_memory = get_memory  # type: ignore[method-assign]
    service.upsert_memory = upsert_memory  # type: ignore[method-assign]

    reply, stage = await service.check_onboarding(10, "hello")

    assert reply == "Welcome! 👋 What's your name?"
    assert stage == "ask_name"
    assert created == [(10, {})]


@pytest.mark.asyncio
async def test_onboarding_existing_user_preferences_and_skip_paths() -> None:
    class Memory:
        user_name = "Ada"
        onboarding_complete = False

    service = MemoryService(None)  # type: ignore[arg-type]
    updates = []

    async def get_memory(_contact_id):
        return Memory()

    async def upsert_memory(contact_id, **kwargs):
        updates.append((contact_id, kwargs))

    service.get_memory = get_memory  # type: ignore[method-assign]
    service.upsert_memory = upsert_memory  # type: ignore[method-assign]

    skip_reply, skip_stage = await service.check_onboarding(10, "skip")
    pref_reply, pref_stage = await service.check_onboarding(10, "I like detailed examples")

    assert skip_stage is None
    assert "All set, Ada!" in skip_reply
    assert pref_stage is None
    assert "Got it, Ada!" in pref_reply
    assert updates[0] == (10, {"onboarding_complete": True})
    assert updates[1] == (10, {"preferences": "I like detailed examples", "onboarding_complete": True})


@pytest.mark.asyncio
async def test_onboarding_complete_user_returns_no_reply() -> None:
    class Memory:
        user_name = "Ada"
        onboarding_complete = True

    service = MemoryService(None)  # type: ignore[arg-type]

    async def get_memory(_contact_id):
        return Memory()

    service.get_memory = get_memory  # type: ignore[method-assign]

    assert await service.check_onboarding(10, "hello") == (None, None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("My name is Ada Lovelace", "Ada Lovelace"),
        ("call me grace", "Grace"),
        ("Backend automation", "Backend Automation"),
        ("I am a developer", None),
    ],
)
def test_name_extraction(text: str, expected: str | None) -> None:
    assert MemoryService._extract_name(text) == expected
