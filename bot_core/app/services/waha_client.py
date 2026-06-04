from __future__ import annotations

import asyncio
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
            body = await self._request("POST", url, headers=headers, json=payload)
            log_event(logger, logging.INFO, "waha_send_success", chat_id=chat_id, session=payload["session"])
            return body
        except (httpx.HTTPError, RuntimeError) as exc:
            log_event(logger, logging.ERROR, "waha_send_failure", chat_id=chat_id, error=str(exc))
            raise WahaClientError(f"WAHA send failed for {chat_id}: {exc}") from exc

    async def get_session_status(self, session_name: str | None = None) -> dict[str, Any]:
        name = session_name or settings.waha_session_name
        url = f"{settings.waha_service_url}{settings.waha_session_status_path}/{name}"
        headers: dict[str, str] = {}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            return await self._request("GET", url, headers=headers)
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA session status failed for {name}: {exc}") from exc

    async def start_session(self, session_name: str | None = None) -> dict[str, Any]:
        name = session_name or settings.waha_session_name
        url = f"{settings.waha_service_url}/api/sessions/start"
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            body = await self._request("POST", url, headers=headers, json={"name": name})
            log_event(logger, logging.INFO, "waha_session_start_requested", session=name)
            return body
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA session start failed for {name}: {exc}") from exc

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        attempts = max(1, settings.waha_request_retry_count + 1)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.request(method, url, headers=headers, json=json)
                response.raise_for_status()
                return response.json() if response.content else {"ok": True}
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if not self._should_retry_status(exc.response.status_code) or attempt == attempts:
                    raise
            except httpx.RequestError as exc:
                last_error = exc
                if attempt == attempts:
                    raise

            log_event(
                logger,
                logging.WARNING,
                "waha_request_retry",
                attempt=attempt,
                max_attempts=attempts,
                method=method,
                url=url,
                error=str(last_error),
            )
            await asyncio.sleep(settings.waha_request_retry_backoff_seconds * attempt)

        raise RuntimeError(f"WAHA request exhausted retries for {method} {url}: {last_error}")

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code >= 500 or status_code in {408, 425, 429}
