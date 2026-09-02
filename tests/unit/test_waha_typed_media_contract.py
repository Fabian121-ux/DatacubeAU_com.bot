from __future__ import annotations

import httpx
import pytest

from app.services.waha_client import WAHAClient, WahaClientError
import app.services.waha_client as waha_module


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "kwargs", "expected_path", "expected_extra"),
    [
        (
            "send_image",
            {"mimetype": "image/jpeg", "caption": "image", "filename": "photo.jpg"},
            "/api/sendImage",
            {"caption": "image"},
        ),
        (
            "send_video",
            {"mimetype": "video/mp4", "caption": "video", "filename": "clip.mp4"},
            "/api/sendVideo",
            {"caption": "video", "convert": False, "asNote": False},
        ),
        (
            "send_voice",
            {"mimetype": "audio/ogg", "filename": "voice.ogg"},
            "/api/sendVoice",
            {"convert": False},
        ),
        (
            "send_file",
            {"mimetype": "audio/mpeg", "caption": "audio", "filename": "track.mp3"},
            "/api/sendFile",
            {"caption": "audio"},
        ),
    ],
)
async def test_typed_media_uses_exact_waha_endpoint_and_remote_file_contract(
    monkeypatch,
    method_name,
    kwargs,
    expected_path,
    expected_extra,
):
    client = WAHAClient()
    captured: dict[str, object] = {}

    async def fake_request(method, url, *, headers, json, retry_safe=True):
        captured.update(
            method=method,
            url=url,
            headers=headers,
            json=json,
            retry_safe=retry_safe,
        )
        return {"ok": True}

    monkeypatch.setattr(client, "_request", fake_request)
    try:
        result = await getattr(client, method_name)(
            "222@c.us",
            media_url="https://example.invalid/private-capability",
            **kwargs,
        )
    finally:
        await client.close()

    assert result == {"ok": True}
    assert captured["method"] == "POST"
    assert captured["url"] == f"{waha_module.settings.waha_service_url}{expected_path}"
    assert captured["retry_safe"] is False
    payload = captured["json"]
    assert payload["session"] == waha_module.settings.waha_session_name
    assert payload["chatId"] == "222@c.us"
    assert payload["file"] == {
        "url": "https://example.invalid/private-capability",
        "mimetype": kwargs["mimetype"],
        "filename": kwargs["filename"],
    }
    for key, value in expected_extra.items():
        assert payload[key] == value


@pytest.mark.asyncio
async def test_typed_media_rejects_missing_or_malformed_mime_before_transport(monkeypatch):
    client = WAHAClient()
    calls = 0

    async def should_not_request(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("transport should not be called")

    monkeypatch.setattr(client, "_request", should_not_request)
    try:
        with pytest.raises(WahaClientError, match="valid MIME type"):
            await client.send_video(
                "222@c.us",
                media_url="https://example.invalid/private-capability",
                mimetype="video",
            )
    finally:
        await client.close()

    assert calls == 0


@pytest.mark.asyncio
async def test_typed_media_request_error_is_never_reissued(monkeypatch):
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
            await client.send_video(
                "222@c.us",
                media_url="https://example.invalid/private-capability",
                mimetype="video/mp4",
                filename="clip.mp4",
            )
    finally:
        await client.close()

    assert calls == 1
