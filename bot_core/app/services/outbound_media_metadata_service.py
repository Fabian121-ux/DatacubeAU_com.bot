from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse


@dataclass(frozen=True, slots=True)
class CanonicalOutboundMedia:
    """One validated media attachment ready to be stored on an OutboundMessage row."""

    media_url: str
    media_kind: str
    media_caption: str | None
    mimetype: str | None
    filename: str | None
    provenance: str

    def queue_metadata(self) -> dict[str, Any]:
        """Metadata merged into `formatting_json` for the typed delivery worker."""
        metadata: dict[str, Any] = {"media_provenance": self.provenance}
        if self.mimetype:
            metadata["media_mime"] = self.mimetype
        if self.filename:
            metadata["media_filename"] = self.filename
        return metadata


@dataclass(frozen=True, slots=True)
class OutboundMediaDecision:
    media: CanonicalOutboundMedia | None
    reason: str

    @property
    def accepted(self) -> bool:
        return self.media is not None


class OutboundMediaMetadataService:
    """Single producer-side contract for outbound media on the router path.

    Producers (internet service, reply planner, future tool/AI producers) must not
    invent their own media conventions. Every attachment is canonicalized here before
    it reaches the Outbound Queue, so the typed delivery worker receives one consistent
    representation and the authority hash binds a validated locator.

    This is a *normalizer*, not an authorization step. Rejecting media never grants a
    send; the surviving text reply still passes the P0 approval fence unchanged.
    """

    MAX_URL_LENGTH = 2048
    _ALLOWED_SCHEMES = frozenset({"http", "https"})

    _KIND_ALIASES: dict[str, str] = {
        "image": "image",
        "photo": "image",
        "picture": "image",
        "gif": "image",
        "sticker": "sticker",
        "video": "video",
        "voice": "voice",
        "ptt": "voice",
        "audio": "audio",
        "document": "document",
        "file": "document",
    }

    # Extension -> (MIME, media kind). Used only as a hint when a producer supplied no
    # explicit MIME. Unknown extensions stay `None` rather than being guessed, so the
    # delivery worker keeps its existing capability-truthful behaviour.
    _EXTENSION_HINTS: dict[str, tuple[str, str]] = {
        "jpg": ("image/jpeg", "image"),
        "jpeg": ("image/jpeg", "image"),
        "png": ("image/png", "image"),
        "webp": ("image/webp", "image"),
        "gif": ("image/gif", "image"),
        "mp4": ("video/mp4", "video"),
        "mov": ("video/quicktime", "video"),
        "webm": ("video/webm", "video"),
        "mp3": ("audio/mpeg", "audio"),
        "m4a": ("audio/mp4", "audio"),
        "ogg": ("audio/ogg", "audio"),
        "opus": ("audio/ogg", "audio"),
        "wav": ("audio/wav", "audio"),
        "pdf": ("application/pdf", "document"),
    }

    _MIME_FAMILIES: dict[str, str] = {
        "image": "image",
        "video": "video",
        "audio": "audio",
    }

    @classmethod
    def normalize(
        cls,
        *,
        media_url: Any,
        media_kind: Any = None,
        media_caption: Any = None,
        mimetype: Any = None,
        filename: Any = None,
        provenance: str = "unknown",
    ) -> OutboundMediaDecision:
        url = cls._safe_url(media_url)
        if url is None:
            return OutboundMediaDecision(None, "media locator is missing, malformed, or uses an unsupported scheme")

        declared_kind = str(media_kind or "").strip().lower()
        if declared_kind and declared_kind not in cls._KIND_ALIASES:
            return OutboundMediaDecision(None, f"unsupported outbound media kind: {declared_kind}")
        kind = cls._KIND_ALIASES.get(declared_kind) if declared_kind else None

        explicit_mime = cls._safe_mime(mimetype)
        if mimetype and explicit_mime is None:
            return OutboundMediaDecision(None, f"malformed outbound media MIME: {mimetype}")

        hint_mime, hint_kind = cls._extension_hint(url)
        resolved_mime = explicit_mime or hint_mime

        if kind is None:
            # No producer-declared kind. Adopt the extension hint when it is
            # unambiguous, otherwise stay untyped and let the worker keep its existing
            # legacy image behaviour rather than guessing a transport operation.
            kind = hint_kind or "image"

        if resolved_mime is not None:
            family = cls._MIME_FAMILIES.get(resolved_mime.split("/", 1)[0])
            expected = cls._expected_family(kind)
            if expected is not None and family != expected:
                # An explicit producer MIME that disagrees with the declared kind is
                # contradictory evidence, so the attachment is dropped rather than
                # delivered through a guessed endpoint.
                return OutboundMediaDecision(
                    None,
                    f"outbound media kind '{kind}' conflicts with MIME '{resolved_mime}'",
                )

        caption = str(media_caption).strip() if media_caption is not None and str(media_caption).strip() else None
        return OutboundMediaDecision(
            CanonicalOutboundMedia(
                media_url=url,
                media_kind=kind,
                media_caption=caption,
                mimetype=resolved_mime,
                filename=cls._safe_filename(filename),
                provenance=str(provenance or "unknown").strip().lower() or "unknown",
            ),
            "canonical outbound media accepted",
        )

    @classmethod
    def _expected_family(cls, kind: str) -> str | None:
        if kind == "image":
            return "image"
        if kind == "video":
            return "video"
        if kind in {"voice", "audio"}:
            return "audio"
        return None

    @classmethod
    def _safe_url(cls, value: Any) -> str | None:
        raw = str(value or "").strip()
        if not raw or len(raw) > cls.MAX_URL_LENGTH:
            return None
        if any(character.isspace() for character in raw) or "\x00" in raw:
            return None
        try:
            parsed = urlparse(raw)
        except ValueError:
            return None
        if parsed.scheme.lower() not in cls._ALLOWED_SCHEMES or not parsed.netloc:
            return None
        # Reject traversal even when percent-encoded, so a locator can never be used to
        # reach outside an intended media path on the transport side.
        if ".." in unquote(parsed.path):
            return None
        return raw

    @staticmethod
    def _safe_mime(value: Any) -> str | None:
        raw = str(value or "").strip().lower()
        if not raw or "/" not in raw or any(character.isspace() for character in raw):
            return None
        top, _, subtype = raw.partition("/")
        if not top or not subtype:
            return None
        return raw

    @classmethod
    def _extension_hint(cls, url: str) -> tuple[str | None, str | None]:
        path = urlparse(url).path
        _, _, extension = path.rpartition(".")
        hint = cls._EXTENSION_HINTS.get(extension.strip().lower())
        return hint if hint else (None, None)

    @staticmethod
    def _safe_filename(value: Any) -> str | None:
        name = str(value or "").strip()
        if not name or len(name) > 200:
            return None
        if "/" in name or "\\" in name or name.startswith(".") or "\x00" in name:
            return None
        return name
