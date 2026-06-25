from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import IdentityRegistryEntry
from app.services.faq_service import FAQService
from app.utils.time import utcnow


class IdentityRegistryService:
    """Authoritative registry for Zina/Fabian/project identity facts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def answer(self, message_text: str) -> str | None:
        normalized = FAQService.semantic_normalize(message_text)
        entries = await self.enabled_entries()
        if not entries:
            return None

        special = self._special_answer(normalized, entries)
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
                select(IdentityRegistryEntry).where(IdentityRegistryEntry.is_enabled.is_(True)).order_by(IdentityRegistryEntry.id)
            )
        ).scalars().all()
        return [row for row in rows if hasattr(row, "registry_key")]

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
        existing = {entry.registry_key for entry in await self.enabled_entries()}
        owner_name = profile.get("owner_name") or "Fabian"
        assistant_name = profile.get("assistant_name") or "Zina"
        defaults = [
            {
                "registry_key": "zina",
                "category": "Zina",
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
            self.session.add(IdentityRegistryEntry(**item, is_enabled=True, created_at=utcnow(), updated_at=utcnow()))
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
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    @staticmethod
    def _special_answer(normalized: str, entries: list[IdentityRegistryEntry]) -> str | None:
        by_key = {entry.registry_key: entry for entry in entries}
        owner = by_key.get("fabian")
        owner_name = owner.name if owner else "Fabian"
        assistant = by_key.get("zina")
        assistant_name = assistant.name if assistant else "Zina"

        if any(phrase in normalized for phrase in ("what is your name", "who are you", "what are you", "tell me about you")):
            return assistant.answer if assistant else f"I am {assistant_name}, {owner_name}'s AI assistant."
        if any(phrase in normalized for phrase in ("who create you", "who build you", "who made you", "who create zina", "who own zina")):
            return f"{owner_name} created {assistant_name}."
        if "why were you create" in normalized or "why do you exist" in normalized:
            return (
                f"{assistant_name} was created to help {owner_name} manage memory, project context, "
                "knowledge retrieval, WhatsApp conversations, and controlled AI access."
            )
        if "who is fabian" in normalized:
            return owner.answer if owner else f"{owner_name} is the owner and creator I assist."
        if "project" in normalized and "fabian" in normalized:
            projects = by_key.get("projects")
            return projects.answer if projects else f"{owner_name}'s core projects include Datacube AU, {assistant_name}, ZinaX, and Moxiz Gateway."
        if "service" in normalized and ("fabian" in normalized or "offer" in normalized or "provide" in normalized):
            services = by_key.get("services")
            return services.answer if services else f"{owner_name} focuses on AI-assisted systems, automation tools, and productivity-focused projects."
        if "datacube" in normalized:
            datacube = by_key.get("datacube_au")
            if "own" in normalized or "found" in normalized or "create" in normalized:
                return f"Datacube AU is owned by {owner_name}."
            return datacube.answer if datacube else f"Datacube AU is an AI-powered educational intelligence platform founded by {owner_name}."
        if "zinax" in normalized:
            zinax = by_key.get("zinax")
            return zinax.answer if zinax else f"ZinaX is a project in {owner_name}'s AI assistant and automation ecosystem."
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
