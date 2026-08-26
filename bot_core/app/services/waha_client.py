from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote, urlencode

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

    async def send_media(
        self,
        chat_id: str,
        *,
        media_url: str,
        caption: str | None = None,
        session_name: str | None = None,
    ) -> dict[str, Any]:
        url = f"{settings.waha_service_url}{settings.waha_send_image_path}"
        payload = {
            "session": session_name or settings.waha_session_name,
            "chatId": chat_id,
            "file": {"url": media_url},
            "caption": caption or "",
        }
        headers = {"Content-Type": "application/json"}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            body = await self._request("POST", url, headers=headers, json=payload)
            log_event(logger, logging.INFO, "waha_media_send_success", chat_id=chat_id, session=payload["session"])
            return body
        except (httpx.HTTPError, RuntimeError) as exc:
            log_event(logger, logging.ERROR, "waha_media_send_failure", chat_id=chat_id, error=str(exc))
            raise WahaClientError(f"WAHA media send failed for {chat_id}: {exc}") from exc

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

    async def get_chats(self, session_name: str | None = None) -> list[dict[str, Any]]:
        name = session_name or settings.waha_session_name
        path = settings.waha_chats_path.format(session=name)
        url = f"{settings.waha_service_url}{path}"
        headers: dict[str, str] = {}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            payload = await self._request("GET", url, headers=headers)
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA chat metadata failed for {name}: {exc}") from exc
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("data", "chats", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    async def get_chat_message(
        self,
        *,
        chat_id: str,
        message_id: str,
        session_name: str | None = None,
    ) -> dict[str, Any]:
        """Fetch one concrete WAHA message by chat/message ID.

        This is used for message-specific outbound-origin correlation during the narrow
        send/timeout race. It is a read-only lookup and never becomes another message
        source of truth; PostgreSQL remains authoritative for Zina state.
        """
        name = session_name or settings.waha_session_name
        encoded_chat = quote(str(chat_id), safe="")
        encoded_message = quote(str(message_id), safe="")
        url = f"{settings.waha_service_url}/api/{quote(str(name), safe='')}/chats/{encoded_chat}/messages/{encoded_message}"
        headers: dict[str, str] = {}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            payload = await self._request("GET", url, headers=headers)
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA message lookup failed for {chat_id}/{message_id}: {exc}") from exc
        if not isinstance(payload, dict):
            raise WahaClientError(f"WAHA message lookup returned an invalid response for {chat_id}/{message_id}")
        return payload

    async def get_contacts(
        self,
        session_name: str | None = None,
        *,
        limit: int = 500,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return one validated paginated WAHA contact page.

        WAHA currently documents `/api/contacts/all` as a JSON array. Wrapper keys are
        retained for backward compatibility, but an unrecognized/malformed successful
        payload is an error rather than an empty address book. This prevents callers
        from treating a response-shape change as proof that every saved contact was
        removed.
        """
        name = session_name or settings.waha_session_name
        query = urlencode(
            {
                "session": name,
                "limit": max(1, min(int(limit), 1000)),
                "offset": max(0, int(offset)),
                "sortBy": "id",
                "sortOrder": "asc",
            }
        )
        url = f"{settings.waha_service_url}/api/contacts/all?{query}"
        headers: dict[str, str] = {}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            payload = await self._request("GET", url, headers=headers)
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA contact sync failed for {name}: {exc}") from exc

        contacts: Any
        if isinstance(payload, list):
            contacts = payload
        elif isinstance(payload, dict):
            contacts = None
            for key in ("data", "contacts", "items"):
                if key not in payload:
                    continue
                value = payload.get(key)
                if not isinstance(value, list):
                    raise WahaClientError(
                        f"WAHA contact sync returned malformed '{key}' page for {name}"
                    )
                contacts = value
                break
            if contacts is None:
                raise WahaClientError(
                    f"WAHA contact sync returned an unrecognized response shape for {name}"
                )
        else:
            raise WahaClientError(
                f"WAHA contact sync returned a non-list response for {name}"
            )

        if any(
            not isinstance(item, dict) or not self._contact_entry_has_person_identifier(item)
            for item in contacts
        ):
            raise WahaClientError(
                f"WAHA contact sync returned a malformed contact entry for {name}"
            )
        return contacts

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

    async def start_typing(self, chat_id: str, session_name: str | None = None) -> dict[str, Any]:
        return await self._typing_request("/api/startTyping", chat_id, session_name=session_name)

    async def stop_typing(self, chat_id: str, session_name: str | None = None) -> dict[str, Any]:
        return await self._typing_request("/api/stopTyping", chat_id, session_name=session_name)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> Any:
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

    async def _typing_request(
        self,
        path: str,
        chat_id: str,
        *,
        session_name: str | None = None,
    ) -> dict[str, Any]:
        url = f"{settings.waha_service_url}{path}"
        payload = {
            "session": session_name or settings.waha_session_name,
            "chatId": chat_id,
        }
        headers = {"Content-Type": "application/json"}
        if settings.waha_api_key:
            headers["X-Api-Key"] = settings.waha_api_key
        try:
            return await self._request("POST", url, headers=headers, json=payload)
        except (httpx.HTTPError, RuntimeError) as exc:
            raise WahaClientError(f"WAHA typing presence failed for {chat_id}: {exc}") from exc

    @classmethod
    def _contact_entry_has_person_identifier(cls, item: dict[str, Any]) -> bool:
        candidates = (
            item.get("id"),
            item.get("contactId"),
            cls._nested_value(item, "_data", "id", "_serialized"),
            cls._nested_value(item, "_data", "id"),
            item.get("jid"),
        )
        for value in candidates:
            if isinstance(value, dict):
                value = value.get("_serialized") or value.get("id")
            text = str(value or "").strip().lower()
            if not text:
                continue
            if text.endswith("@c.us") or text.endswith("@s.whatsapp.net") or text.endswith("@lid"):
                return True
            if text.endswith("@g.us") or text == "status@broadcast" or text.endswith("@newsletter") or text.endswith("@broadcast"):
                return True
        return False

    @staticmethod
    def _nested_value(payload: dict[str, Any], *path: str) -> Any:
        current: Any = payload
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _should_retry_status(status_code: int) -> bool:
        return status_code >= 500 or status_code in {408, 425, 429}
