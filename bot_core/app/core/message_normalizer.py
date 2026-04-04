from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.models.enums import ChatType
from app.utils.text import normalize_text


@dataclass(slots=True)
class NormalizedMessage:
    chat_id: str
    sender_id: str
    sender_name: str | None
    chat_type: ChatType
    message_text: str
    normalized_text: str
    message_type: str
    is_bot_mentioned: bool
    payload: dict[str, Any]


class MessageNormalizer:
    def normalize(self, event: dict[str, Any]) -> NormalizedMessage:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else event
        if not isinstance(payload, dict):
            payload = {}

        sender_id = str(payload.get("from") or payload.get("sender", {}).get("id") or "unknown@local")
        chat_id = str(payload.get("chatId") or payload.get("chat", {}).get("id") or sender_id or "unknown-chat")
        sender_name = payload.get("notifyName") or payload.get("pushName") or payload.get("sender", {}).get("name")

        message_text = self._extract_text(payload)
        normalized = normalize_text(message_text)
        message_type = str(payload.get("type") or "text")
        chat_type = ChatType.GROUP if self._is_group(payload, chat_id) else ChatType.DM
        mentions = payload.get("mentionedIds") or payload.get("mentions") or []

        return NormalizedMessage(
            chat_id=chat_id,
            sender_id=sender_id,
            sender_name=sender_name,
            chat_type=chat_type,
            message_text=message_text,
            normalized_text=normalized,
            message_type=message_type,
            is_bot_mentioned=self._is_mentioned(message_text, mentions),
            payload=payload,
        )

    @staticmethod
    def _is_group(payload: dict[str, Any], chat_id: str) -> bool:
        if bool(payload.get("isGroup")):
            return True
        return chat_id.endswith("@g.us")

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        text = payload.get("text")
        if isinstance(text, str):
            return text
        if isinstance(text, dict):
            return str(text.get("body") or text.get("text") or "")

        body = payload.get("body")
        if isinstance(body, str):
            return body

        message = payload.get("message")
        if isinstance(message, dict):
            nested_text = message.get("text")
            if isinstance(nested_text, str):
                return nested_text
            if isinstance(nested_text, dict):
                return str(nested_text.get("body") or nested_text.get("text") or "")
            nested_body = message.get("body")
            if isinstance(nested_body, str):
                return nested_body
        return ""

    @staticmethod
    def _is_mentioned(text: str, mentions: Any) -> bool:
        aliases = [a.strip().lower() for a in settings.bot_mention_aliases.split(",") if a.strip()]
        lower = text.lower()
        if any(alias in lower for alias in aliases):
            return True
        if isinstance(mentions, list) and settings.bot_wa_number:
            return settings.bot_wa_number in mentions
        return False
