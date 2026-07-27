"""The single error vocabulary for ThumbIQ.

Every failure path in the backend raises one of these. The exception handler in
``main.py`` turns them into the exact status codes and human messages published in
``API_SPEC.md`` — so a user never sees a stack trace and never sees a message written
by a library.
"""

from __future__ import annotations

from typing import Any


class ThumbIQError(Exception):
    """Base class. ``code`` and ``message`` are contractual — they are in API_SPEC.md."""

    status: int = 500
    code: str = "internal_error"
    message: str = "Something went wrong. Please try again"

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        self.headers = headers or {}
        super().__init__(self.message)

    def to_body(self) -> dict[str, Any]:
        return {
            "success": False,
            "error": {"code": self.code, "message": self.message, "detail": self.detail},
        }


class InvalidUrlError(ThumbIQError):
    status, code = 400, "invalid_url"
    message = "Please enter a valid video or post link"


class BlockedHostError(ThumbIQError):
    status, code = 400, "blocked_host"
    message = "That address can't be fetched"


class RestrictedContentError(ThumbIQError):
    status, code = 403, "restricted"
    message = "This content is private or restricted"


class ContentNotFoundError(ThumbIQError):
    status, code = 404, "not_found"
    message = "This video no longer exists"


class NoThumbnailError(ThumbIQError):
    status, code = 404, "no_thumbnail"
    message = "No thumbnail found for this link"


class ImageTooLargeError(ThumbIQError):
    status, code = 413, "image_too_large"
    message = "That image is too large to process"


class UnsupportedPlatformError(ThumbIQError):
    status, code = 422, "unsupported_platform"
    message = "We can't read this platform yet — tell us about it"


class RateLimitedError(ThumbIQError):
    status, code = 429, "rate_limited"
    message = "Too many requests. Please wait a moment"


class GeoBlockedError(ThumbIQError):
    status, code = 451, "geo_blocked"
    message = "This content isn't available in our server region"


class ExtractorError(ThumbIQError):
    status, code = 500, "extractor_failed"
    message = "Could not process this link. Please try again"


class AnalysisError(ThumbIQError):
    status, code = 500, "analysis_failed"
    message = "Could not analyse this image. Please try again"


class UnreadableImageError(ThumbIQError):
    status, code = 422, "unreadable_image"
    message = "That file isn't an image we can read"


# --- yt-dlp / upstream message classification -------------------------------------

# yt-dlp reports everything as DownloadError with a human string. These fragments are
# how the real world spells each failure; matching them is what turns a generic 500
# into the correct 403 / 404 / 451.
_RESTRICTED_MARKERS = (
    "private video",
    "sign in to confirm your age",
    "age-restricted",
    "login required",
    "requires authentication",
    "members-only",
    "this video is available to this channel's members",
    "sign in to confirm you",
    "account has been terminated",
    "join this channel",
)

_NOT_FOUND_MARKERS = (
    "video unavailable",
    "does not exist",
    "has been removed",
    "no longer available",
    "was deleted",
    "not found",
    "404",
    "unable to find",
    "removed by the uploader",
)

_GEO_MARKERS = (
    "not available in your country",
    "geo restricted",
    "geo-restricted",
    "blocked it in your country",
    "not available from your location",
)

_UNSUPPORTED_MARKERS = (
    "unsupported url",
    "no suitable extractor",
    "is not a valid url",
)


def classify_upstream_error(raw: str) -> ThumbIQError:
    """Map an upstream (usually yt-dlp) message onto the published error table."""
    text = (raw or "").lower()

    for marker in _RESTRICTED_MARKERS:
        if marker in text:
            return RestrictedContentError()
    for marker in _GEO_MARKERS:
        if marker in text:
            return GeoBlockedError()
    for marker in _NOT_FOUND_MARKERS:
        if marker in text:
            return ContentNotFoundError()
    for marker in _UNSUPPORTED_MARKERS:
        if marker in text:
            return UnsupportedPlatformError()
    return ExtractorError()
