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
    _SAME_MESSAGE_KEYS = ("message", "_data")
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
        source_id = cls._message_id(reply_to)
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
    def reply_media_size(cls, payload: Any) -> int | None:
        """Return the largest reported size across supported quoted-media locations."""
        if not isinstance(payload, dict):
            return None
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return None

        sizes: list[int] = []
        for media in cls._media_candidates(reply_to):
            raw = media.get("fileSize")
            if raw is None:
                raw = media.get("filesize")
            if raw is None:
                raw = media.get("size")
            if raw is None:
                continue
            try:
                size = int(raw)
            except (TypeError, ValueError):
                continue
            sizes.append(max(0, size))
        return max(sizes) if sizes else None

    @classmethod
    def _explicit_view_once(cls, payload: Any, depth: int = 0) -> bool | None:
        """Resolve explicit evidence for one message representation, fail closed.

        Direct boolean markers, wrapper evidence, and supported alternate same-message
        representations are all inspected before deciding. Any explicit negative
        evidence wins over positive evidence, including when the root is positive but
        a supported nested representation is explicitly negative. This prevents
        classification from depending on key/container order.
        """
        if depth > cls._MAX_DEPTH or not isinstance(payload, dict):
            return None

        saw_true = False
        saw_false = False

        for key, value in payload.items():
            normalized = str(key).replace("-", "").replace("_", "").lower()
            if normalized not in cls._BOOL_KEYS:
                continue
            parsed = cls._parse_bool(value)
            if parsed is False:
                saw_false = True
            elif parsed is True:
                saw_true = True

        for key, value in payload.items():
            normalized = str(key).replace("-", "").replace("_", "").lower()
            if normalized in cls._WRAPPER_KEYS and isinstance(value, dict):
                saw_true = True

        for key in cls._SAME_MESSAGE_KEYS:
            nested_payload = payload.get(key)
            if not isinstance(nested_payload, dict):
                continue
            nested = cls._explicit_view_once(nested_payload, depth + 1)
            if nested is True:
                saw_true = True
            elif nested is False:
                saw_false = True

        if saw_false:
            return False
        if saw_true:
            return True
        return None

    @staticmethod
    def _parse_bool(value: Any) -> bool | None:
        if isinstance(value, bool):
            return value
        text = "" if value is None else str(value).strip().lower()
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
    def _media_candidates(cls, payload: dict[str, Any]) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        direct = payload.get("media")
        if isinstance(direct, dict):
            candidates.append(direct)
        for path in (("message", "media"), ("_data", "media")):
            value = cls._nested(payload, *path)
            if isinstance(value, dict):
                candidates.append(value)
        return candidates

    @classmethod
    def _media(cls, payload: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
        candidates = cls._media_candidates(payload)
        selected_url: str | None = None
        selected_mime: str | None = None
        selected_type: str | None = None
        observed_categories: set[str] = set()

        for media in candidates:
            url = str(media.get("url") or "").strip() or None
            mime = str(media.get("mimetype") or media.get("mimeType") or media.get("mime") or "").strip() or None
            media_type = str(media.get("type") or "").strip() or None

            mime_category = cls._media_category(None, mime)
            type_category = cls._media_category(media_type, None)
            if mime_category:
                observed_categories.add(mime_category)
            if type_category:
                observed_categories.add(type_category)

            if selected_url is None and url:
                selected_url = url
            if selected_mime is None and mime:
                selected_mime = mime
            if selected_type is None and media_type:
                selected_type = media_type

        if len(observed_categories) > 1:
            return selected_url, None, None
        return selected_url, selected_mime, selected_type

    @staticmethod
    def _media_category(media_type: str | None, mime: str | None) -> str | None:
        candidate = str(media_type or "").strip().lower()
        mime_value = str(mime or "").strip().lower()
        if candidate in {"image", "video"}:
            return candidate
        if mime_value.startswith("image/"):
            return "image"
        if mime_value.startswith("video/"):
            return "video"
        return None

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
