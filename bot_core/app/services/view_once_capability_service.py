from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ViewOnceCapability:
    """Bounded transport evidence for one candidate WhatsApp view-once message.

    This service deliberately does not infer view-once status from `hasMedia` or from
    message type alone. Current WAHA does not expose a documented normalized
    `view_once` field across engines, so only explicit engine/payload evidence may
    authorize later `.vv` retrieval.
    """

    source_message_id: str | None
    is_view_once: bool | None
    media_url: str | None
    media_mime: str | None
    media_type: str | None
    evidence_source: str
    reason: str

    @property
    def retrievable_now(self) -> bool:
        return self.is_view_once is True and bool(self.media_url)


class ViewOnceCapabilityService:
    """Extract conservative view-once evidence from authenticated WAHA payloads.

    `True` means an explicit view-once marker was present. `False` means an explicit
    negative marker was present. `None` means WAHA did not provide reliable evidence.
    A plain media message is therefore never upgraded to view-once by inference.
    """

    _BOOL_KEYS = frozenset(
        {
            "viewonce",
            "view_once",
            "isviewonce",
            "is_view_once",
        }
    )
    _WRAPPER_KEYS = frozenset(
        {
            "viewoncemessage",
            "viewoncemessagev2",
            "viewoncemessagev2extension",
        }
    )
    _MAX_DEPTH = 8

    @classmethod
    def inspect_message_payload(cls, payload: Any) -> ViewOnceCapability:
        if not isinstance(payload, dict):
            return ViewOnceCapability(
                source_message_id=None,
                is_view_once=None,
                media_url=None,
                media_mime=None,
                media_type=None,
                evidence_source="waha_payload",
                reason="WAHA payload unavailable or invalid.",
            )

        marker = cls._explicit_view_once(payload)
        media = cls._media(payload)
        source_id = cls._message_id(payload)
        if marker is True and media[0]:
            reason = "Explicit WAHA/engine view-once evidence and retrievable media URL are present."
        elif marker is True:
            reason = "Explicit view-once evidence is present, but WAHA exposed no retrievable media URL."
        elif marker is False:
            reason = "WAHA explicitly marks this message as not view-once."
        else:
            reason = "WAHA exposed no explicit view-once marker; ordinary media is not treated as view-once."
        return ViewOnceCapability(
            source_message_id=source_id,
            is_view_once=marker,
            media_url=media[0],
            media_mime=media[1],
            media_type=media[2],
            evidence_source="waha_payload",
            reason=reason,
        )

    @classmethod
    def inspect_reply_snapshot(cls, payload: Any) -> ViewOnceCapability:
        if not isinstance(payload, dict):
            return cls.inspect_message_payload(payload)
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return ViewOnceCapability(
                source_message_id=None,
                is_view_once=None,
                media_url=None,
                media_mime=None,
                media_type=None,
                evidence_source="waha_reply_snapshot",
                reason="Reply to a source message before using a view-once command.",
            )

        marker = cls._explicit_view_once(reply_to)
        media = cls._media(reply_to)
        source_id = cls._scalar_id(reply_to.get("id"))
        if marker is True and media[0]:
            reason = "Quoted WAHA snapshot contains explicit view-once evidence and a retrievable media URL."
        elif marker is True:
            reason = "Quoted message is explicitly view-once, but its media is no longer retrievable from WAHA."
        elif marker is False:
            reason = "Quoted WAHA snapshot explicitly marks the media as not view-once."
        else:
            reason = "Quoted WAHA snapshot has no explicit view-once evidence; retrieval is denied rather than guessed."
        return ViewOnceCapability(
            source_message_id=source_id,
            is_view_once=marker,
            media_url=media[0],
            media_mime=media[1],
            media_type=media[2],
            evidence_source="waha_reply_snapshot",
            reason=reason,
        )

    @classmethod
    def _explicit_view_once(cls, payload: Any, depth: int = 0) -> bool | None:
        if depth > cls._MAX_DEPTH:
            return None
        if isinstance(payload, dict):
            explicit_false = False
            for key, value in payload.items():
                normalized = str(key).replace("-", "").replace("_", "").lower()
                if normalized in cls._WRAPPER_KEYS and isinstance(value, dict):
                    return True
                if normalized in cls._BOOL_KEYS:
                    parsed = cls._parse_bool(value)
                    if parsed is True:
                        return True
                    if parsed is False:
                        explicit_false = True
            for value in payload.values():
                nested = cls._explicit_view_once(value, depth + 1)
                if nested is True:
                    return True
                if nested is False:
                    explicit_false = True
            return False if explicit_false else None
        if isinstance(payload, list):
            explicit_false = False
            for value in payload[:50]:
                nested = cls._explicit_view_once(value, depth + 1)
                if nested is True:
                    return True
                if nested is False:
                    explicit_false = True
            return False if explicit_false else None
        return None

    @staticmethod
    def _parse_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        text = str(value or "").strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
        return None

    @classmethod
    def _message_id(cls, payload: dict[str, Any]) -> str | None:
        for value in (
            payload.get("id"),
            cls._nested(payload, "message", "id"),
            cls._nested(payload, "_data", "id"),
        ):
            scalar = cls._scalar_id(value)
            if scalar:
                return scalar
        return None

    @classmethod
    def _media(cls, payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
        candidates = []
        direct = payload.get("media")
        if isinstance(direct, dict):
            candidates.append(direct)
        for path in (
            ("message", "media"),
            ("_data", "media"),
        ):
            value = cls._nested(payload, *path)
            if isinstance(value, dict):
                candidates.append(value)

        for media in candidates:
            url = str(media.get("url") or "").strip() or None
            mime = str(media.get("mimetype") or media.get("mimeType") or media.get("mime") or "").strip() or None
            media_type = str(media.get("type") or "").strip() or None
            if url or mime or media_type:
                return url, mime, media_type
        return None, None, None

    @staticmethod
    def _nested(payload: Any, *path: str) -> Any:
        current = payload
        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current

    @staticmethod
    def _scalar_id(value: Any) -> str | None:
        if isinstance(value, dict):
            value = value.get("_serialized") or value.get("id")
        text = str(value or "").strip()
        if not text or len(text) > 200:
            return None
        return text
