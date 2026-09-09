from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, IdentityRegistryEntry
from app.services.faq_service import FAQService
from app.utils.time import utcnow


class IdentityRegistryService:
    """Authoritative registry for Zina/Fabian/project identity facts."""

    SEARCH_LIMIT = 50

    #: registry keys some hardcoded fallback -- `_special_answer` below, and
    #: `BotConfigService.identity_reply()`'s own separate legacy fallback -- will
    #: otherwise substitute a default answer for when no active entry exists. Used to
    #: tell "never seeded" apart from "the OWNER intentionally deleted this" so a
    #: deletion can't be silently undone by either hardcoded fallback layer. This is
    #: every key `ensure_defaults_from_profile` seeds, since both fallback layers
    #: reference some subset of them.
    _DEFAULT_FALLBACK_KEYS = (
        "zina",
        "fabian",
        "services",
        "datacube_au",
        "zinax",
        "moxiz_gateway",
        "projects",
        "skills",
    )

    def __init__(self, session: AsyncSession):
        self.session = session

    async def answer(self, message_text: str) -> str | None:
        normalized = FAQService.semantic_normalize(message_text)
        entries = await self.enabled_entries()
        deleted_keys = await self.unavailable_default_keys()
        if not entries and not deleted_keys:
            return None

        target_keys = self._explicit_target_keys(normalized)
        if target_keys & deleted_keys:
            # The query is unambiguously about one or more specific default facts and
            # at least one is unavailable -- refuse outright instead of falling
            # through to the scored-match loop below, where some other, unrelated
            # entry might coincidentally mention the same name (e.g. the "projects"
            # entry's own summary answer lists every project -- Datacube AU, ZinaX,
            # etc -- by name; the "zina" entry's own keywords include "created" and
            # "built") and silently resurrect the fact through a different door.
            return None

        special = self._special_answer(normalized, entries, deleted_keys)
        if special:
            return special

        best_entry = None
        best_score = 0.0
        for entry in entries:
            score = self.score_entry(normalized, entry)
            if score > best_score:
                best_entry = entry
                best_score = score
        if best_entry and best_score >= 0.62:
            best_entry.updated_at = utcnow()
            await self.session.flush()
            return best_entry.answer
        return None

    async def enabled_entries(self) -> list[IdentityRegistryEntry]:
        rows = (
            await self.session.execute(
                select(IdentityRegistryEntry)
                .where(IdentityRegistryEntry.is_enabled.is_(True))
                .where(IdentityRegistryEntry.deleted_at.is_(None))
                .order_by(IdentityRegistryEntry.id)
            )
        ).scalars().all()
        return [row for row in rows if hasattr(row, "registry_key")]

    async def unavailable_default_keys(self) -> set[str]:
        """Default registry keys that are not fully active right now.

        Covers both explicit tombstones (`deleted_at` set) and a default that merely
        exists but is disabled (`is_enabled=False`, `deleted_at` still NULL) -- for
        example, a previously-deleted key recreated via the admin API with
        `enabled=False`, which clears the tombstone without making the row active
        again. Both states mean a real row reflects the OWNER's current intent and a
        hardcoded fallback literal must not silently stand in for it.

        Public so any caller with its own hardcoded identity fallback (e.g.
        `BotConfigService.identity_reply()`) can also suppress it, not only
        `_special_answer`/`answer()`'s own scored-match layer.
        """
        rows = (
            await self.session.execute(
                select(IdentityRegistryEntry.registry_key)
                .where(IdentityRegistryEntry.registry_key.in_(self._DEFAULT_FALLBACK_KEYS))
                .where(
                    or_(
                        IdentityRegistryEntry.deleted_at.is_not(None),
                        IdentityRegistryEntry.is_enabled.is_(False),
                    )
                )
            )
        ).scalars().all()
        return set(rows)

    @staticmethod
    def _explicit_target_keys(normalized: str) -> frozenset[str]:
        """Which default registry key(s), if any, a query's phrase is unambiguously

        about -- mirrors `_special_answer`'s own branch conditions exactly, including
        which branches depend on more than one key (e.g. "who created you" reads as
        stale if *either* "zina" or "fabian" is unavailable, matching that branch's
        own `or` check), plus "moxiz" (which has no `_special_answer` branch of its
        own but is still a single, unambiguous project name). `answer()` refuses a
        query outright when any of its returned keys is unavailable, rather than
        letting the scored-match loop substitute a different entry that happens to
        mention the same name or share a keyword (e.g. the "projects" entry's own
        summary answer lists every project by name; the "zina" entry's own keywords
        include "created" and "built").

        The specific phrase branches above are checked first so their more precise
        semantics win (e.g. "who created you" needing *both* keys). Below that, a
        bare mention of "zina" or "fabian" by name is *also* treated as targeting
        that key -- e.g. "who is zina?" or "what is zina" match no phrase above (only
        "what is *your* name"/"who are *you*" do) but are just as identity-routed in
        practice (see `IntentClassifier._is_identity_question`), and the same
        "projects entry lists every name" leak applies to them too. Both can be
        returned together (e.g. "tell me about fabian and zina").
        """
        if any(phrase in normalized for phrase in ("what is your name", "who are you", "what are you", "tell me about you")):
            return frozenset({"zina"})
        if any(phrase in normalized for phrase in ("who create you", "who build you", "who made you", "who create zina", "who own zina")):
            return frozenset({"zina", "fabian"})
        if "why were you create" in normalized or "why do you exist" in normalized:
            return frozenset({"zina"})
        if "who is fabian" in normalized:
            return frozenset({"fabian"})
        if "project" in normalized and "fabian" in normalized:
            return frozenset({"projects"})
        if "service" in normalized and ("fabian" in normalized or "offer" in normalized or "provide" in normalized):
            return frozenset({"services"})
        if "datacube" in normalized:
            return frozenset({"datacube_au"})
        if "zinax" in normalized:
            return frozenset({"zinax"})
        if "moxiz" in normalized:
            return frozenset({"moxiz_gateway"})
        named: set[str] = set()
        if "zina" in normalized:
            named.add("zina")
        if "fabian" in normalized:
            named.add("fabian")
        return frozenset(named)

    async def get_by_key(self, registry_key: str) -> IdentityRegistryEntry | None:
        """Fetch a single entry by key, including disabled ones, excluding deleted ones."""
        key = str(registry_key or "").strip()
        if not key:
            return None
        return (
            await self.session.execute(
                select(IdentityRegistryEntry)
                .where(IdentityRegistryEntry.registry_key == key)
                .where(IdentityRegistryEntry.deleted_at.is_(None))
            )
        ).scalar_one_or_none()

    async def search(
        self, query: str, *, include_disabled: bool = False, limit: int = SEARCH_LIMIT
    ) -> list[IdentityRegistryEntry]:
        """Substring search over key/name/category/description, excluding deleted rows.

        This is a simple, explainable filter -- consistent with the registry's existing
        scoring approach elsewhere in this file, not a new retrieval mechanism.
        """
        term = str(query or "").strip().lower()
        bounded_limit = max(1, min(int(limit), 200))
        stmt = select(IdentityRegistryEntry).where(IdentityRegistryEntry.deleted_at.is_(None))
        if not include_disabled:
            stmt = stmt.where(IdentityRegistryEntry.is_enabled.is_(True))
        if term:
            pattern = f"%{term}%"
            stmt = stmt.where(
                or_(
                    IdentityRegistryEntry.registry_key.ilike(pattern),
                    IdentityRegistryEntry.name.ilike(pattern),
                    IdentityRegistryEntry.category.ilike(pattern),
                    IdentityRegistryEntry.description.ilike(pattern),
                )
            )
        stmt = stmt.order_by(IdentityRegistryEntry.id).limit(bounded_limit)
        return (await self.session.execute(stmt)).scalars().all()

    async def delete(self, registry_key: str, *, request_id: str | None = None) -> bool:
        """Soft-delete: tombstone the row rather than removing it.

        Consistent with the tombstone pattern used elsewhere in this codebase (view-once
        metadata, private media artifacts) -- deletion is monotonic and auditable, not a
        hard row removal. A deleted entry is excluded from enabled_entries/get_by_key/
        search and can never be resurrected by ensure_defaults_from_profile (it only
        seeds keys that are absent from *enabled* entries, and a deleted key stays
        absent from that set, so it also will not silently reappear as a default).
        """
        entry = await self.get_by_key(registry_key)
        if entry is None:
            return False
        entry.deleted_at = utcnow()
        entry.is_enabled = False
        entry.updated_at = utcnow()
        self.session.add(
            AuditLog(
                action="identity_registry_deleted",
                entity_type="identity_registry",
                entity_id=entry.registry_key,
                details_json={"request_id": request_id},
            )
        )
        await self.session.flush()
        return True

    async def resolve_references(self, text_value: str) -> str:
        if "{{identity:" not in text_value:
            return text_value
        entries = {entry.registry_key: entry for entry in await self.enabled_entries()}

        def repl(match: re.Match[str]) -> str:
            key = match.group(1).strip()
            entry = entries.get(key)
            return entry.answer if entry else f"I do not have an active identity record for {key.replace('_', ' ')}."

        return re.sub(r"\{\{\s*identity:([a-zA-Z0-9_\-]+)\s*\}\}", repl, text_value)

    async def ensure_defaults_from_profile(self, profile: dict[str, str]) -> None:
        """Seed default entries the first time each registry_key is ever seen.

        Existence is checked against *every* row for that key -- enabled, disabled, or
        deleted -- because `registry_key` carries a unique constraint regardless of
        lifecycle state. Checking only enabled rows was a real bug: a default that was
        merely disabled (not deleted) would look "absent" here and a second insert with
        the same key would raise an IntegrityError on flush. Deleted defaults are also
        never resurrected by this method, since their key still occupies the unique
        constraint until explicitly recreated by a human.
        """
        existing = set(
            (
                await self.session.execute(select(IdentityRegistryEntry.registry_key))
            ).scalars().all()
        )
        owner_name = profile.get("owner_name") or "Fabian"
        assistant_name = profile.get("assistant_name") or "Zina"
        defaults = [
            {
                "registry_key": "zina",
                "category": "Zina",
                "entity_type": "assistant",
                "name": assistant_name,
                "description": f"{assistant_name} is {owner_name}'s personal AI assistant.",
                "aliases": [assistant_name, "assistant", "you"],
                "keywords": ["assistant", "name", "created", "built", "owner"],
                "entities": [assistant_name, owner_name],
                "answer": f"I am {assistant_name}, {owner_name}'s AI assistant.",
                "facts_json": {"owner": owner_name, "type": "AI assistant"},
            },
            {
                "registry_key": "fabian",
                "category": "Owner",
                "entity_type": "person",
                "name": owner_name,
                "description": profile.get("owner_bio") or f"{owner_name} is the owner and creator I assist.",
                "aliases": [owner_name, "owner", "creator"],
                "keywords": ["owner", "creator", "developer", "builder"],
                "entities": [owner_name],
                "answer": profile.get("owner_bio") or f"{owner_name} is the owner and creator I assist.",
                "facts_json": {"role": "Owner and creator"},
            },
            {
                "registry_key": "services",
                "category": "Services",
                "entity_type": "meta",
                "name": "Fabian Services",
                "description": profile.get("services") or "Fabian builds AI-assisted systems, automation tools, and productivity-focused projects.",
                "aliases": ["services", "what Fabian offers"],
                "keywords": ["services", "automation", "ai", "systems", "productivity"],
                "entities": [owner_name, "Datacube AU", assistant_name],
                "answer": profile.get("services") or "Fabian focuses on AI-assisted systems, automation tools, WhatsApp assistant systems, and productivity-focused projects.",
                "facts_json": {"services": profile.get("services") or ""},
            },
            {
                "registry_key": "datacube_au",
                "category": "Datacube AU",
                "entity_type": "project",
                "name": "Datacube AU",
                "description": "Datacube AU is part of Fabian's AI assistant and automation ecosystem.",
                "aliases": ["Datacube", "Datacube AU"],
                "keywords": ["datacube", "project", "assistant", "automation", "knowledge"],
                "entities": ["Datacube AU", owner_name],
                "answer": f"Datacube AU is an AI-powered assistant and knowledge automation project created by {owner_name}.",
                "facts_json": {"owner": owner_name, "project": True},
            },
            {
                "registry_key": "zinax",
                "category": "ZinaX",
                "entity_type": "project",
                "name": "ZinaX",
                "description": "ZinaX is a project in Fabian's AI assistant ecosystem.",
                "aliases": ["ZinaX"],
                "keywords": ["zinax", "project", "assistant", "automation"],
                "entities": ["ZinaX", owner_name],
                "answer": f"ZinaX is part of {owner_name}'s AI assistant and automation ecosystem.",
                "facts_json": {"owner": owner_name, "project": True},
            },
            {
                "registry_key": "moxiz_gateway",
                "category": "Projects",
                "entity_type": "project",
                "name": "Moxiz Gateway",
                "description": "Moxiz Gateway is part of Fabian's broader product and automation ecosystem.",
                "aliases": ["Moxiz", "Moxiz Gateway"],
                "keywords": ["moxiz", "gateway", "project", "automation"],
                "entities": ["Moxiz Gateway", owner_name],
                "answer": f"Moxiz Gateway is part of {owner_name}'s broader product and automation ecosystem.",
                "facts_json": {"owner": owner_name, "project": True},
            },
            {
                "registry_key": "projects",
                "category": "Projects",
                "entity_type": "meta",
                "name": "Fabian Projects",
                "description": profile.get("projects") or f"{owner_name}'s active ecosystem includes Datacube AU, {assistant_name}, ZinaX, and Moxiz Gateway.",
                "aliases": ["projects", "Fabian projects", "what Fabian is building"],
                "keywords": ["projects", "building", "datacube", "zina", "zinax", "moxiz"],
                "entities": [owner_name, "Datacube AU", assistant_name, "ZinaX", "Moxiz Gateway"],
                "answer": profile.get("projects") or f"{owner_name}'s core projects include Datacube AU, {assistant_name}, ZinaX, and Moxiz Gateway.",
                "facts_json": {"projects": profile.get("projects") or ""},
            },
            {
                "registry_key": "skills",
                "category": "Skills",
                "entity_type": "meta",
                "name": "Fabian Skills",
                "description": profile.get("skills") or f"{owner_name} works across AI systems, automation, Python, FastAPI, TypeScript, Docker, cybersecurity, and workflow tooling.",
                "aliases": ["skills", "Fabian skills", "what Fabian can do"],
                "keywords": ["skills", "ai", "python", "fastapi", "typescript", "docker", "cybersecurity", "automation"],
                "entities": [owner_name],
                "answer": profile.get("skills") or f"{owner_name} works with AI systems, Python, FastAPI, TypeScript, Node.js, Docker, cybersecurity, and workflow automation.",
                "facts_json": {"skills": profile.get("skills") or ""},
            },
        ]
        for item in defaults:
            if item["registry_key"] in existing:
                continue
            self.session.add(
                IdentityRegistryEntry(
                    **item, source="system_default", is_enabled=True, created_at=utcnow(), updated_at=utcnow()
                )
            )
        await self.session.flush()

    @classmethod
    def score_entry(cls, normalized_query: str, entry: IdentityRegistryEntry) -> float:
        candidates = [entry.name, entry.description, entry.answer]
        candidates.extend(cls._coerce_list(entry.aliases))
        candidates.extend(cls._coerce_list(entry.keywords))
        base = max(
            (FAQService.score_match(normalized_query, FAQService.semantic_normalize(candidate)) for candidate in candidates if candidate),
            default=0.0,
        )
        entities = {FAQService.semantic_normalize(item) for item in cls._coerce_list(entry.entities)}
        entity_bonus = 0.12 if any(entity and entity in normalized_query for entity in entities) else 0.0
        owner_bonus = 0.1 if entry.registry_key in {"fabian", "zina"} and {"name", "create", "own"} & FAQService._keywords(normalized_query) else 0.0
        return min(1.0, base + entity_bonus + owner_bonus)

    @staticmethod
    def serialize(entry: IdentityRegistryEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "registry_key": entry.registry_key,
            "category": entry.category,
            "name": entry.name,
            "description": entry.description,
            "aliases": IdentityRegistryService._coerce_list(entry.aliases),
            "keywords": IdentityRegistryService._coerce_list(entry.keywords),
            "entities": IdentityRegistryService._coerce_list(entry.entities),
            "answer": entry.answer,
            "facts_json": entry.facts_json or {},
            "is_enabled": entry.is_enabled,
            "enabled": entry.is_enabled,
            "source": entry.source,
            "entity_type": entry.entity_type,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    @staticmethod
    def _special_answer(
        normalized: str, entries: list[IdentityRegistryEntry], deleted_keys: set[str] | None = None
    ) -> str | None:
        """Phrase-matched shortcuts for the most common identity questions.

        `deleted_keys` names default registry keys the OWNER has explicitly deleted.
        For those, this returns None instead of the hardcoded fallback text below --
        an intentional deletion must not be silently undone by substituting the same
        default fact back in just because no active row remains to answer from.
        """
        deleted_keys = deleted_keys or set()
        by_key = {entry.registry_key: entry for entry in entries}
        owner = by_key.get("fabian")
        owner_name = owner.name if owner else "Fabian"
        assistant = by_key.get("zina")
        assistant_name = assistant.name if assistant else "Zina"

        if any(phrase in normalized for phrase in ("what is your name", "who are you", "what are you", "tell me about you")):
            if assistant:
                return assistant.answer
            return None if "zina" in deleted_keys else f"I am {assistant_name}, {owner_name}'s AI assistant."
        if any(phrase in normalized for phrase in ("who create you", "who build you", "who made you", "who create zina", "who own zina")):
            if "zina" in deleted_keys or "fabian" in deleted_keys:
                return None
            return f"{owner_name} created {assistant_name}."
        if "why were you create" in normalized or "why do you exist" in normalized:
            if "zina" in deleted_keys:
                return None
            return (
                f"{assistant_name} was created to help {owner_name} manage memory, project context, "
                "knowledge retrieval, WhatsApp conversations, and controlled AI access."
            )
        if "who is fabian" in normalized:
            if owner:
                return owner.answer
            return None if "fabian" in deleted_keys else f"{owner_name} is the owner and creator I assist."
        if "project" in normalized and "fabian" in normalized:
            projects = by_key.get("projects")
            if projects:
                return projects.answer
            return None if "projects" in deleted_keys else f"{owner_name}'s core projects include Datacube AU, {assistant_name}, ZinaX, and Moxiz Gateway."
        if "service" in normalized and ("fabian" in normalized or "offer" in normalized or "provide" in normalized):
            services = by_key.get("services")
            if services:
                return services.answer
            return None if "services" in deleted_keys else f"{owner_name} focuses on AI-assisted systems, automation tools, and productivity-focused projects."
        if "datacube" in normalized:
            datacube = by_key.get("datacube_au")
            if "datacube_au" in deleted_keys:
                return None
            if "own" in normalized or "found" in normalized or "create" in normalized:
                return f"Datacube AU is owned by {owner_name}."
            return datacube.answer if datacube else f"Datacube AU is an AI-powered educational intelligence platform founded by {owner_name}."
        if "zinax" in normalized:
            zinax = by_key.get("zinax")
            if zinax:
                return zinax.answer
            return None if "zinax" in deleted_keys else f"ZinaX is a project in {owner_name}'s AI assistant and automation ecosystem."
        return None

    @staticmethod
    def _coerce_list(value: Any) -> list[str]:
        if not value:
            return []
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []
