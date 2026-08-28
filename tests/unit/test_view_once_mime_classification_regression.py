from __future__ import annotations

from app.services.view_once_command_service import ViewOnceCommandService


def test_image_label_with_non_image_mime_fails_closed() -> None:
    assert ViewOnceCommandService._safe_media_type("image", "application/pdf") is None
    assert ViewOnceCommandService._safe_media_type("image", "text/plain") is None


def test_image_label_with_image_mime_remains_supported() -> None:
    assert ViewOnceCommandService._safe_media_type("image", "image/jpeg") == "image"
    assert ViewOnceCommandService._safe_media_type("image", None) == "image"


def test_video_label_with_non_video_mime_fails_closed() -> None:
    assert ViewOnceCommandService._safe_media_type("video", "application/octet-stream") is None
    assert ViewOnceCommandService._safe_media_type("video", "image/png") is None
