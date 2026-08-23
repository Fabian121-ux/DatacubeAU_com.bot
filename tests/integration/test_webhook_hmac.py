import hashlib
import hmac
import json
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings

@pytest.mark.asyncio
async def test_webhook_missing_hmac():
    settings.whatsapp_hook_hmac_key = "test_secret"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/waha", json={"event": "message", "payload": {"id": "123"}})
    assert response.status_code == 401
    assert response.json()["reason"] == "missing_hmac_signature"

@pytest.mark.asyncio
async def test_webhook_invalid_algorithm():
    settings.whatsapp_hook_hmac_key = "test_secret"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/waha",
            json={"event": "message", "payload": {"id": "123"}},
            headers={"X-Webhook-Hmac": "fake", "X-Webhook-Hmac-Algorithm": "sha256"}
        )
    assert response.status_code == 400
    assert response.json()["reason"] == "unsupported_hmac_algorithm"

@pytest.mark.asyncio
async def test_webhook_invalid_hmac():
    settings.whatsapp_hook_hmac_key = "test_secret"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/waha",
            json={"event": "message", "payload": {"id": "123"}},
            headers={"X-Webhook-Hmac": "fake_invalid", "X-Webhook-Hmac-Algorithm": "sha512"}
        )
    assert response.status_code == 401
    assert response.json()["reason"] == "invalid_hmac_signature"

@pytest.mark.asyncio
async def test_webhook_valid_hmac(db_session):
    settings.whatsapp_hook_hmac_key = "test_secret"
    body = json.dumps({"event": "message", "payload": {"id": "valid_123"}})
    signature = hmac.new(b"test_secret", body.encode("utf-8"), hashlib.sha512).hexdigest()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/waha",
            content=body,
            headers={"X-Webhook-Hmac": signature, "X-Webhook-Hmac-Algorithm": "sha512"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
