from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings
from app.services.logging_service import log_event


logger = logging.getLogger(__name__)


class WahaClientError(RuntimeError):
    pass


class WAHAClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=settings.waha_request_timeout_seconds)

    async def send_text(self, chat_id: str, text: str, session_name: str | None = None) -> dict[str, Any]:
        url = f"{settings.waha_service_url}{settings.waha_send_path}"
        payload = {
            "session": session_name or settings.waha_session_name,
            "chatId": chat_id,
            "text": text,
        }
        headers = {"Content-Type": "application/json"}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            response = await self._client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            body = response.json() if response.content else {"ok": True}
            log_event(logger, logging.INFO, "waha_send_success", chat_id=chat_id, session=payload["session"])
            return body
        except httpx.HTTPError as exc:
            log_event(logger, logging.ERROR, "waha_send_failure", chat_id=chat_id, error=str(exc))
            raise WahaClientError(f"WAHA send failed for {chat_id}: {exc}") from exc

    async def get_session_status(self, session_name: str | None = None) -> dict[str, Any]:
        name = session_name or settings.waha_session_name
        url = f"{settings.waha_service_url}{settings.waha_session_status_path}/{name}"
        headers: dict[str, str] = {}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise WahaClientError(f"WAHA session status failed for {name}: {exc}") from exc

    async def close(self) -> None:
        await self._client.aclose()
