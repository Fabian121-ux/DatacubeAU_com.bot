"""Regression for a Codex review finding (PR #47, landed after an unauthorized

self-merge -- see docs/ZINA_IMPLEMENTATION_ROADMAP.md): `POST /admin/identity/registry`
looked up only the active row for a `registry_key`. If that key was tombstoned
(soft-deleted), the endpoint treated it as absent and attempted a second INSERT with
the same key -- `registry_key` carries a global unique constraint regardless of
lifecycle state, so that raised an unhandled `IntegrityError` (HTTP 500) instead of
either reviving the row or returning a clean error.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.admin import IdentityRegistryUpdate, upsert_identity_registry
from app.models.schema import IdentityRegistryEntry
from app.services.identity_registry_service import IdentityRegistryService

PROFILE = {"owner_name": "Fabian", "assistant_name": "Zina"}


@pytest.mark.asyncio
async def test_recreating_a_deleted_key_revives_the_tombstone_instead_of_crashing(db_session):
    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    assert await service.delete("skills") is True

    # Must not raise IntegrityError on the still-unique, now-tombstoned registry_key.
    result = await upsert_identity_registry(
        IdentityRegistryUpdate(
            registry_key="skills",
            name="Fabian Skills",
            description="Recreated after deletion.",
            answer="Fabian works across AI systems and automation.",
        ),
        db=db_session,
    )
    assert result["ok"] is True

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "skills")
        )
    ).scalars().all()
    assert len(rows) == 1  # revived in place, not a second row
    assert rows[0].deleted_at is None
    assert rows[0].description == "Recreated after deletion."
    assert await service.get_by_key("skills") is not None


@pytest.mark.asyncio
async def test_recreating_a_deleted_key_without_required_fields_is_a_clean_400(db_session):
    from fastapi import HTTPException

    service = IdentityRegistryService(db_session)
    await service.ensure_defaults_from_profile(PROFILE)
    await service.delete("skills")

    with pytest.raises(HTTPException) as exc_info:
        await upsert_identity_registry(
            IdentityRegistryUpdate(registry_key="skills"),
            db=db_session,
        )
    assert exc_info.value.status_code == 400

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "skills")
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].deleted_at is not None  # still tombstoned, not silently revived


@pytest.mark.asyncio
async def test_upsert_on_a_never_deleted_key_is_unaffected(db_session):
    result = await upsert_identity_registry(
        IdentityRegistryUpdate(
            registry_key="brand_new_key",
            name="New",
            description="A new entry.",
            answer="A new entry.",
        ),
        db=db_session,
    )
    assert result["ok"] is True

    # Updating the same key again goes through the ordinary active-row branch.
    result2 = await upsert_identity_registry(
        IdentityRegistryUpdate(registry_key="brand_new_key", description="Updated."),
        db=db_session,
    )
    assert result2["item"]["description"] == "Updated."

    rows = (
        await db_session.execute(
            select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == "brand_new_key")
        )
    ).scalars().all()
    assert len(rows) == 1
