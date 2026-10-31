from __future__ import annotations

import httpx
import pytest

from app.services.waha_client import WAHAClient, WahaClientError
import app.services.waha_client as waha_module


@pytest.mark.asyncio
async def test_send_text_request_error_is_not_reissued(monkeypatch):
    monkeypatch.setattr(waha_module.settings, "waha_request_retry_count", 5)
    client = WAHAClient()
    calls = 0

    async def fail_request(method, url, *, headers, json):
        nonlocal calls
        calls += 1
        request = httpx.Request(method, url)
        raise httpx.ConnectError("lost response", request=request)

    monkeypatch.setattr(client._client, "request", fail_request)
    try:
        with pytest.raises(WahaClientError):
            await client.send_text("222@c.us", "one attempt")
    finally:
        await client.close()

    assert calls == 1


@pytest.mark.asyncio
async def test_send_media_request_error_is_not_reissued(monkeypatch):
    monkeypatch.setattr(waha_module.settings, "waha_request_retry_count", 5)
    client = WAHAClient()
    calls = 0

    async def fail_request(method, url, *, headers, json):
        nonlocal calls
        calls += 1
        request = httpx.Request(method, url)
        raise httpx.ConnectError("lost response", request=request)

    monkeypatch.setattr(client._client, "request", fail_request)
    try:
        with pytest.raises(WahaClientError):
            await client.send_media(
                "222@c.us",
                media_url="https://example.invalid/private-capability",
                caption="one attempt",
            )
    finally:
        await client.close()

    assert calls == 1
