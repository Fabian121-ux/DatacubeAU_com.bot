from __future__ import annotations

import pytest

from app.models.schema import AdminAccount
from app.services.admin_management_service import AdminManagementService


class FakeAdminSession:
    def __init__(self):
        self.rows: list[AdminAccount] = []
        self.deleted: list[AdminAccount] = []

    def add(self, row: AdminAccount) -> None:
        row.id = len(self.rows) + 1
        self.rows.append(row)

    async def flush(self) -> None:
        return None

    async def delete(self, row: AdminAccount) -> None:
        self.deleted.append(row)
        self.rows.remove(row)


class MemoryAdminService(AdminManagementService):
    def __init__(self, session: FakeAdminSession):
        self.session = session

    async def list_admins(self, *, include_disabled: bool = True, search: str | None = None):
        rows = list(self.session.rows)
        if not include_disabled:
            rows = [row for row in rows if row.is_enabled]
        return rows

    async def _get(self, admin_id: int) -> AdminAccount:
        for row in self.session.rows:
            if row.id == admin_id:
                return row
        raise ValueError("not found")

    async def _get_by_normalized(self, normalized: str) -> AdminAccount | None:
        for row in self.session.rows:
            if row.normalized_whatsapp_id == normalized:
                return row
        return None


def test_admin_number_normalization() -> None:
    assert AdminManagementService.normalize_whatsapp_id("+234 801 234 5678") == "2348012345678@c.us"
    assert AdminManagementService.normalize_whatsapp_id("2348012345678@s.whatsapp.net") == "2348012345678@c.us"
    assert AdminManagementService.normalize_whatsapp_id("12345@lid") == "12345@lid"


@pytest.mark.asyncio
async def test_duplicate_admin_numbers_are_rejected() -> None:
    session = FakeAdminSession()
    service = MemoryAdminService(session)

    await service.create_admin(name="Fabian", whatsapp_number="+2348012345678")

    with pytest.raises(ValueError, match="already exists"):
        await service.create_admin(name="Duplicate", whatsapp_number="2348012345678@c.us")


@pytest.mark.asyncio
async def test_final_primary_admin_cannot_be_disabled_or_removed() -> None:
    session = FakeAdminSession()
    service = MemoryAdminService(session)
    primary = await service.create_admin(name="Fabian", whatsapp_number="+2348012345678", is_primary=True)

    with pytest.raises(ValueError, match="final active primary"):
        await service.set_enabled(primary.id, False)

    with pytest.raises(ValueError, match="final active primary"):
        await service.delete_admin(primary.id)
