from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api import health
from app.db import get_db_session
from app.services.waha_client import WahaClientError


class FakeDB:
    def __init__(self, fail: bool = False):
        self.fail = fail

    async def execute(self, *_):
        if self.fail:
            raise RuntimeError("db unavailable")
        return None


class WorkingWahaClient:
    async def get_session_status(self):
        return {"status": "WORKING"}

    async def close(self) -> None:
        return None


class FailingWahaClient:
    async def get_session_status(self):
        raise WahaClientError("WAHA unavailable")

    async def close(self) -> None:
        return None


def make_app(fake_db: FakeDB) -> FastAPI:
    app = FastAPI()
    app.include_router(health.router)

    async def override_db():
        yield fake_db

    app.dependency_overrides[get_db_session] = override_db
    return app


@pytest.mark.asyncio
async def test_health_returns_ok_when_database_available(monkeypatch) -> None:
    monkeypatch.setattr(health, "WAHAClient", WorkingWahaClient)
    app = make_app(FakeDB())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"


@pytest.mark.asyncio
async def test_dependency_health_reports_waha_degraded_without_breaking_health(monkeypatch) -> None:
    monkeypatch.setattr(health, "WAHAClient", FailingWahaClient)
    app = make_app(FakeDB())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health_response = await client.get("/health")
        dependency_response = await client.get("/health/dependencies")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"
    assert dependency_response.status_code == 200
    payload = dependency_response.json()
    assert payload["status"] == "degraded"
    assert payload["database"] == "ok"
    assert payload["waha"]["status"] == "error"
    assert "WAHA unavailable" in payload["waha"]["detail"]
    assert payload["openrouter"]["enabled"] in {True, False}


@pytest.mark.asyncio
async def test_health_returns_503_when_database_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(health, "WAHAClient", WorkingWahaClient)
    app = make_app(FakeDB(fail=True))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "error"
