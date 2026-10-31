from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class MediaDispatchPlan:
    """Exact transport operation chosen for one already-authorized media row."""

    operation: str
    media_kind: str
    mimetype: str | None
    filename: str | None
    caption: str | None


@dataclass(frozen=True, slots=True)
class MediaDispatchDecision:
    plan: MediaDispatchPlan | None
    reason: str

    @property
    def allowed(self) -> bool:
        return self.plan is not None


class OutboundMediaDispatchService:
    """Map an authorized Outbound Queue row onto one exact WAHA media operation.

    This service is deliberately *not* an authorization mechanism. It runs only after
    the P0 final authorization fence and the outbound safety limits have already
    allowed the row, and it can only narrow behaviour: it either selects one exact
    typed transport operation or fails closed. It can never make an unauthorized row
    sendable, and it never inspects approvals, policies, or owner identity.

    Media semantics are kept explicit so a video/audio artifact can never be delivered
    through the image endpoint:

        image                 -> send_image
        video                 -> send_video
        voice note / PTT      -> send_voice
        generic audio / file  -> send_file

    Unknown kinds, and declared-kind/MIME disagreements, fail closed.
    """

    _IMAGE = "image"
    _VIDEO = "video"
    _AUDIO = "audio"
    _FILE = "file"

    # Declared queue media_type -> (transport operation, expected MIME family).
    # A `None` family accepts any valid MIME because generic files are type-agnostic.
    _DECLARED_KINDS: dict[str, tuple[str, str | None]] = {
        "image": ("send_image", _IMAGE),
        "photo": ("send_image", _IMAGE),
        "video": ("send_video", _VIDEO),
        "voice": ("send_voice", _AUDIO),
        "ptt": ("send_voice", _AUDIO),
        "audio": ("send_file", _AUDIO),
        "document": ("send_file", None),
        "file": ("send_file", None),
        "sticker": ("send_file", None),
    }

    @classmethod
    def plan(cls, message: Any) -> MediaDispatchDecision:
        media_url = str(getattr(message, "media_url", "") or "").strip()
        if not media_url:
            return MediaDispatchDecision(None, "queue row has no media locator to dispatch")

        declared = str(getattr(message, "media_type", "") or "").strip().lower()
        metadata = getattr(message, "formatting_json", None)
        metadata = metadata if isinstance(metadata, dict) else {}
        mimetype = str(metadata.get("media_mime") or "").strip().lower() or None
        caption = getattr(message, "media_caption", None) or getattr(message, "message_text", None)

        # Legacy compatibility: rows created before typed media carried no declared kind
        # and no MIME. The existing worker treated those as images, so that exact
        # behaviour is preserved rather than silently retargeted or newly rejected.
        if not declared and mimetype is None:
            return MediaDispatchDecision(
                MediaDispatchPlan("send_media", cls._IMAGE, None, None, caption),
                "legacy untyped media row retains existing image-only delivery",
            )

        if declared and declared not in cls._DECLARED_KINDS:
            return MediaDispatchDecision(None, f"unknown outbound media kind: {declared}")

        mime_family = cls._mime_family(mimetype) if mimetype else None
        if mimetype is not None and mime_family is None:
            return MediaDispatchDecision(None, f"unsupported or malformed outbound media MIME: {mimetype}")

        if not declared:
            # No declared kind, but a valid MIME is present. Derive the kind from the
            # MIME rather than guessing. Audio is ambiguous between a voice note and an
            # audio file, so it fails closed instead of assuming PTT semantics.
            if mime_family == cls._AUDIO:
                return MediaDispatchDecision(
                    None,
                    "audio media requires an explicit voice or audio kind before transport",
                )
            operation = {
                cls._IMAGE: "send_image",
                cls._VIDEO: "send_video",
                cls._FILE: "send_file",
            }[mime_family]
            return cls._typed(operation, mime_family, mimetype, metadata, caption)

        operation, expected_family = cls._DECLARED_KINDS[declared]

        if mimetype is None:
            # A typed non-image operation requires a real MIME. Falling back to the
            # legacy image path here would send video/audio through /api/sendImage.
            if operation != "send_image":
                return MediaDispatchDecision(
                    None,
                    f"outbound {declared} media requires an explicit MIME type before transport",
                )
            return MediaDispatchDecision(
                MediaDispatchPlan("send_media", cls._IMAGE, None, None, caption),
                "legacy image media row retains existing image-only delivery",
            )

        if expected_family is not None and mime_family != expected_family:
            return MediaDispatchDecision(
                None,
                f"outbound media kind '{declared}' conflicts with MIME '{mimetype}'",
            )

        return cls._typed(operation, declared, mimetype, metadata, caption)

    @classmethod
    def _typed(
        cls,
        operation: str,
        media_kind: str,
        mimetype: str,
        metadata: dict[str, Any],
        caption: str | None,
    ) -> MediaDispatchDecision:
        return MediaDispatchDecision(
            MediaDispatchPlan(
                operation,
                media_kind,
                mimetype,
                cls._safe_filename(metadata.get("media_filename")),
                caption,
            ),
            f"exact typed {media_kind} dispatch via {operation}",
        )

    @staticmethod
    def _mime_family(mimetype: str) -> str | None:
        value = str(mimetype or "").strip().lower()
        if "/" not in value:
            return None
        top, _, subtype = value.partition("/")
        if not top.strip() or not subtype.strip():
            return None
        if top == "image":
            return OutboundMediaDispatchService._IMAGE
        if top == "video":
            return OutboundMediaDispatchService._VIDEO
        if top == "audio":
            return OutboundMediaDispatchService._AUDIO
        return OutboundMediaDispatchService._FILE

    @staticmethod
    def _safe_filename(value: Any) -> str | None:
        """Return a display filename only when it cannot escape a directory.

        The filename is transport metadata, so an unsafe value is dropped rather than
        failing an otherwise authorized delivery.
        """
        name = str(value or "").strip()
        if not name or len(name) > 200:
            return None
        if "/" in name or "\\" in name or name.startswith(".") or "\x00" in name:
            return None
        return name
