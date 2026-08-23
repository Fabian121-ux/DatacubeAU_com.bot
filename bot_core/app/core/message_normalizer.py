from __future__ import annotations

from dataclasses import dataclass, field
import re
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
    sender_alternate_ids: list[str] = field(default_factory=list)
    sender_identity: dict[str, Any] = field(default_factory=dict)


class MessageNormalizer:
    def normalize(self, event: dict[str, Any]) -> NormalizedMessage:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else event
        if not isinstance(payload, dict):
            payload = {}

        chat_id = str(payload.get("chatId") or payload.get("chat", {}).get("id") or payload.get("from") or "unknown-chat")
        sender_candidates = self._sender_id_candidates(payload, chat_id)
        sender_id = sender_candidates[0] if sender_candidates else "unknown@local"
        alternate_ids = sender_candidates[1:]
        chat_id = str(payload.get("chatId") or payload.get("chat", {}).get("id") or sender_id or "unknown-chat")
        sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
        contact = payload.get("contact") if isinstance(payload.get("contact"), dict) else {}
        contact_name = contact.get("name") or contact.get("shortName") or payload.get("contactName")
        push_name = sender.get("pushName") or payload.get("pushName") or contact.get("pushName") or payload.get("notifyName")
        profile_name = sender.get("name") or payload.get("notifyName")
        phone = sender.get("phone") or contact.get("phone") or payload.get("phone")
        sender_name = contact_name or push_name or profile_name or self._temporary_phone_name(phone or sender_id)
        sender_identity = {
            "display_name": sender_name,
            "contact_name": contact_name,
            "push_name": push_name,
            "profile_name": profile_name,
            "phone": phone,
            "normalized_phone": self._normalize_phone(phone or sender_id),
            "chat_id": chat_id,
            "sender_id": sender_id,
            "alternate_ids": alternate_ids,
            "waha_contact_id": contact.get("id") or contact.get("_serialized"),
            "waha_participant_id": payload.get("participant") or payload.get("participantId") or payload.get("author"),
            "profile_image_url": sender.get("profilePicUrl") or contact.get("profilePicUrl") or payload.get("profilePicUrl"),
        }

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
            sender_alternate_ids=alternate_ids,
            sender_identity=sender_identity,
        )

    @classmethod
    def _sender_id_candidates(cls, payload: dict[str, Any], chat_id: str) -> list[str]:
        sender = payload.get("sender") if isinstance(payload.get("sender"), dict) else {}
        raw_values = [
            payload.get("participant"),
            payload.get("participantId"),
            payload.get("author"),
            payload.get("authorId"),
            payload.get("senderId"),
            sender.get("id"),
            sender.get("_serialized"),
            payload.get("from"),
            sender.get("lid"),
            sender.get("phone"),
            payload.get("fromMe") if isinstance(payload.get("fromMe"), str) else None,
        ]
        if not cls._is_group(payload, chat_id):
            raw_values.append(chat_id)
        candidates: list[str] = []
        for raw in raw_values:
            if raw is None:
                continue
            value = str(raw).strip()
            if not value or value in {"True", "False"}:
                continue
            if value.endswith("@g.us"):
                continue
            if value not in candidates:
                candidates.append(value)
        return candidates

    @staticmethod
    def _normalize_phone(value: Any) -> str | None:
        text = str(value or "")
        if "@lid" in text:
            return None
        left = text.split("@", 1)[0]
        digits = re.sub(r"\D+", "", left)
        return digits or None

    @classmethod
    def _temporary_phone_name(cls, value: Any) -> str | None:
        if "@lid" in str(value or ""):
            return None
        digits = cls._normalize_phone(value)
        return digits if digits and len(digits) >= 7 else None

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
