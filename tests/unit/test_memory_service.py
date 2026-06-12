from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.enums import ChatType, Direction
from app.models.schema import Contact, ConversationSession, ConversationSummary, ConversationTimeline, Message, UserMemoryTimeline
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
        display_name="Ada L.",
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
        relationship_type="customer",
        personality_notes="pragmatic",
    )

    assert created in session.added
    assert created.display_name == "Ada L."
    assert created.user_name == "Ada"
    assert created.onboarding_complete is True
    assert created.relationship_type == "customer"
    assert created.personality_notes == "pragmatic"
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
    assert len(session.executed) == 3
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


@pytest.mark.asyncio
async def test_relationship_profile_creation_and_context_retrieval(db_session, test_contact) -> None:
    service = MemoryService(db_session)

    await service.ensure_relationship_profile(test_contact.id, "Kingsley")
    profile = await service.upsert_memory(
        test_contact.id,
        interests="Cybersecurity; VPS Hosting",
        goals="find internship opportunities",
        relationship_type="friend",
        personality_notes="prefers direct technical answers",
        onboarding_complete=True,
    )
    await service.log_timeline_event(
        test_contact.id,
        topic="cybersecurity internships",
        summary="Asked about cybersecurity internships",
        importance_score=0.82,
        source="admin",
    )

    package = await service.get_context_package(test_contact.id, query="internship")

    assert profile.display_name == "Kingsley"
    assert profile.relationship_type == "friend"
    assert package.profile["display_name"] == "Kingsley"
    assert package.profile["relationship_type"] == "friend"
    assert package.timeline_entries[0]["topic"] == "cybersecurity internships"
    assert "User: Kingsley" in package.context_text
    assert "Relationship: friend" in package.context_text


@pytest.mark.asyncio
async def test_timeline_creation_search_and_deletion(db_session, test_contact) -> None:
    service = MemoryService(db_session)
    entry = await service.log_timeline_event(
        test_contact.id,
        topic="VPS deployment",
        summary="Requested VPS deployment help",
        importance_score=0.88,
        source="router_trace",
    )

    rows = await service.search_timeline(test_contact.id, query="VPS")

    assert rows[0].id == entry.id
    assert rows[0].topic == "VPS deployment"
    assert await service.delete_timeline_entry(test_contact.id, entry.id) is True
    assert await service.search_timeline(test_contact.id) == []
    assert await service.delete_timeline_entry(test_contact.id, entry.id) is False


@pytest.mark.asyncio
async def test_summary_generation_at_thresholds(db_session, test_contact) -> None:
    service = MemoryService(db_session)
    chat_id = test_contact.whatsapp_id
    db_session.add(
        ConversationSession(
            chat_id=chat_id,
            chat_type=ChatType.DM.value,
            summary="decision:kb_reply | user:Asked about Linux server setup | assistant:Use a VPS checklist",
            last_intent="kb_reply",
        )
    )
    await service.log_timeline_event(
        test_contact.id,
        topic="Linux server setup",
        summary="Discussed Linux server setup",
        importance_score=0.7,
        source="router_trace",
    )
    for index in range(25):
        db_session.add(
            Message(
                contact_id=test_contact.id,
                chat_id=chat_id,
                chat_type=ChatType.DM.value,
                direction=Direction.INBOUND.value if index % 2 == 0 else Direction.OUTBOUND.value,
                message_text=f"message {index}",
                normalized_text=f"message {index}",
            )
        )
    await db_session.flush()

    created = await service.generate_due_summaries(test_contact.id, chat_id=chat_id, thresholds=[25, 50])
    duplicate = await service.generate_due_summaries(test_contact.id, chat_id=chat_id, thresholds=[25, 50])
    summaries = (await db_session.execute(select(ConversationSummary))).scalars().all()

    assert len(created) == 1
    assert created[0].threshold == 25
    assert duplicate == []
    assert len(summaries) == 1
    assert "Linux server setup" in summaries[0].summary
    assert "Linux server setup" in summaries[0].topics


@pytest.mark.asyncio
async def test_conversation_continuation_reply(db_session, test_contact) -> None:
    service = MemoryService(db_session)
    await service.upsert_memory(
        test_contact.id,
        display_name="Kingsley",
        relationship_type="friend",
        onboarding_complete=True,
    )
    await service.log_timeline_event(
        test_contact.id,
        topic="cybersecurity internships",
        summary="Asked about cybersecurity internships",
        importance_score=0.8,
        source="router_trace",
    )

    package = await service.get_context_package(test_contact.id, query="hi")
    reply = service.build_continuation_reply("Hi", package)

    assert reply == "Welcome back Kingsley. Last time we discussed cybersecurity internships. How is that going?"


@pytest.mark.asyncio
async def test_memory_answer_for_profile_and_timeline_questions(db_session, test_contact) -> None:
    service = MemoryService(db_session)
    await service.upsert_memory(
        test_contact.id,
        display_name="Kingsley",
        interests="Cybersecurity; VPS Hosting",
        relationship_type="friend",
        onboarding_complete=True,
    )
    await service.log_timeline_event(
        test_contact.id,
        topic="VPS deployment",
        summary="Requested VPS deployment help",
        importance_score=0.8,
        source="router_trace",
    )

    package = await service.get_context_package(test_contact.id, query="what do you remember about me")
    profile_answer = service.build_memory_answer("What do you remember about me?", package)
    timeline_answer = service.build_memory_answer("What did we discuss last time?", package)

    assert profile_answer is not None
    assert profile_answer[1] == "Memory"
    assert "Cybersecurity" in profile_answer[0]
    assert timeline_answer is not None
    assert timeline_answer[1] == "Memory + Timeline"
    assert "VPS deployment" in timeline_answer[0]


@pytest.mark.asyncio
async def test_context_retrieval_is_contact_scoped(db_session, test_contact) -> None:
    other = Contact(whatsapp_id="15550000002@c.us", display_name="Other User")
    db_session.add(other)
    await db_session.flush()
    service = MemoryService(db_session)
    await service.upsert_memory(test_contact.id, display_name="Kingsley", interests="Cybersecurity")
    await service.upsert_memory(other.id, display_name="Private User", interests="Private Topic")
    await service.log_timeline_event(
        test_contact.id,
        topic="Datacube AU",
        summary="Discussed Datacube AU roadmap",
        source="admin",
    )
    await service.log_timeline_event(
        other.id,
        topic="Private Topic",
        summary="Discussed private unrelated topic",
        source="admin",
    )

    package = await service.get_context_package(test_contact.id)

    assert "Kingsley" in package.context_text
    assert "Datacube AU" in package.context_text
    assert "Private User" not in package.context_text
    assert "Private Topic" not in package.context_text


def test_memory_context_includes_profile_fields() -> None:
    class Memory:
        display_name = "Ada L."
        user_name = "Ada"
        preferences = "concise"
        context_notes = "likes examples"
        profession = "developer"
        interests = "AI"
        projects = "Datacube AU"
        goals = "reliable automation"
        communication_style = "direct"
        relationship = "client"
        relationship_type = "customer"
        personality_notes = "likes practical examples"

    context = MemoryService(None).get_memory_context(Memory())  # type: ignore[arg-type]

    assert "Display name: Ada L." in context
    assert "User name: Ada" in context
    assert "Profession: developer" in context
    assert "Relationship to Fabian: client" in context
    assert "Relationship type: customer" in context
    assert "Personality notes: likes practical examples" in context
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


def test_parse_summary_thresholds() -> None:
    assert MemoryService.parse_summary_thresholds("25, 50, bad, 100") == (25, 50, 100)
    assert MemoryService.parse_summary_thresholds([10, 5, 10]) == (5, 10)
    assert MemoryService.parse_summary_thresholds("bad") == (25, 50, 100)


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
    assert "Nice to meet you, Ada." in reply
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

    assert reply == "Welcome. What's your name?"
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
