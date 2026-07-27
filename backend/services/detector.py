"""Platform detection and video-ID extraction.

The YouTube ID regex is deliberately strict: exactly 11 characters from
``[A-Za-z0-9_-]``, and the character *after* the ID must not extend it. A loose regex
is how thumbnail tools end up requesting ``i.ytimg.com/vi/dQw4w9WgXcQ1/...`` and
rendering a broken card.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse, urlunparse

from utils.errors import InvalidUrlError

YOUTUBE_ID = r"[A-Za-z0-9_-]{11}"

# Path-based YouTube forms. Each pattern anchors the ID and then requires a boundary,
# so a 12-character token never matches as an 11-character ID.
_YT_PATH_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p)
    for p in (
        rf"^/shorts/({YOUTUBE_ID})(?:[/?#]|$)",
        rf"^/embed/({YOUTUBE_ID})(?:[/?#]|$)",
        rf"^/live/({YOUTUBE_ID})(?:[/?#]|$)",
        rf"^/v/({YOUTUBE_ID})(?:[/?#]|$)",
        rf"^/e/({YOUTUBE_ID})(?:[/?#]|$)",
        rf"^/({YOUTUBE_ID})(?:[/?#]|$)",  # youtu.be/ID
    )
)

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "gaming.youtube.com",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_YOUTU_BE_HOSTS = {"youtu.be", "www.youtu.be"}

# hostname suffix -> (platform id, display name). Longest suffix wins.
_PLATFORM_HOSTS: dict[str, tuple[str, str]] = {
    "youtube.com": ("youtube", "YouTube"),
    "youtu.be": ("youtube", "YouTube"),
    "youtube-nocookie.com": ("youtube", "YouTube"),
    "vimeo.com": ("vimeo", "Vimeo"),
    "player.vimeo.com": ("vimeo", "Vimeo"),
    "dailymotion.com": ("dailymotion", "Dailymotion"),
    "dai.ly": ("dailymotion", "Dailymotion"),
    "tiktok.com": ("tiktok", "TikTok"),
    "vm.tiktok.com": ("tiktok", "TikTok"),
    "vt.tiktok.com": ("tiktok", "TikTok"),
    "instagram.com": ("instagram", "Instagram"),
    "instagr.am": ("instagram", "Instagram"),
    "facebook.com": ("facebook", "Facebook"),
    "fb.watch": ("facebook", "Facebook"),
    "fb.com": ("facebook", "Facebook"),
    "twitter.com": ("twitter", "X (Twitter)"),
    "x.com": ("twitter", "X (Twitter)"),
    "t.co": ("twitter", "X (Twitter)"),
    "twitch.tv": ("twitch", "Twitch"),
    "clips.twitch.tv": ("twitch", "Twitch"),
    "reddit.com": ("reddit", "Reddit"),
    "redd.it": ("reddit", "Reddit"),
    "pinterest.com": ("pinterest", "Pinterest"),
    "pin.it": ("pinterest", "Pinterest"),
    "linkedin.com": ("linkedin", "LinkedIn"),
    "lnkd.in": ("linkedin", "LinkedIn"),
    "rumble.com": ("rumble", "Rumble"),
    "odysee.com": ("odysee", "Odysee"),
    "bilibili.com": ("bilibili", "Bilibili"),
    "b23.tv": ("bilibili", "Bilibili"),
    "kick.com": ("kick", "Kick"),
    "streamable.com": ("streamable", "Streamable"),
    "soundcloud.com": ("soundcloud", "SoundCloud"),
    "bitchute.com": ("bitchute", "BitChute"),
    "vk.com": ("vk", "VK"),
    "snapchat.com": ("snapchat", "Snapchat"),
    "vimeo.io": ("vimeo", "Vimeo"),
}

# Platforms with a Tier-1 fast path.
FAST_PATH_PLATFORMS = {"youtube", "vimeo", "dailymotion", "tiktok"}


@dataclass(frozen=True, slots=True)
class Detection:
    platform: str
    platform_name: str
    video_id: str | None
    normalized_url: str
    original_url: str

    @property
    def has_fast_path(self) -> bool:
        return self.platform in FAST_PATH_PLATFORMS


def _normalize(raw: str) -> str:
    """Add a scheme when the user pasted a bare host, and strip whitespace."""
    url = (raw or "").strip()
    if not url:
        raise InvalidUrlError()
    # Reject obvious non-URLs early so the user gets the right message immediately.
    if " " in url or "\n" in url:
        raise InvalidUrlError()
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", url):
        if "." not in url.split("/")[0]:
            raise InvalidUrlError()
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise InvalidUrlError()
    if not parsed.hostname:
        raise InvalidUrlError()
    return urlunparse(parsed)


def extract_youtube_id(url: str) -> str | None:
    """Return the 11-char video ID from any YouTube URL shape, or None.

    Handles: watch?v=, youtu.be/, /shorts/, /embed/, /live/, /v/, m., music.,
    youtube-nocookie, and any of those carrying extra query params (&t=, ?si=,
    &list=, &index=).
    """
    try:
        parsed = urlparse(url if "://" in url else "https://" + url)
    except ValueError:
        return None

    # A YouTube ID only means anything over http(s). ftp://youtube.com/watch?v=… is not
    # a link ThumbIQ can act on, and returning an ID for it would send the ladder off to
    # build URLs for a request that can never be made.
    if parsed.scheme not in ("http", "https"):
        return None

    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"

    if host in _YOUTU_BE_HOSTS:
        for pattern in _YT_PATH_PATTERNS:
            match = pattern.match(path)
            if match:
                return match.group(1)
        return None

    if host not in _YOUTUBE_HOSTS:
        return None

    # watch?v=ID — the canonical form.
    query = parse_qs(parsed.query)
    for key in ("v", "video_id"):
        for value in query.get(key, []):
            if re.fullmatch(YOUTUBE_ID, value):
                return value

    for pattern in _YT_PATH_PATTERNS:
        match = pattern.match(path)
        if match:
            # /watch and /playlist are not ID paths even though they are 11 chars away
            # from looking like one; the leading-segment patterns below guard that.
            candidate = match.group(1)
            if candidate.lower() in {"watch", "playlist", "results", "channel", "feed"}:
                continue
            return candidate

    # /attribution_link?u=/watch%3Fv%3DID and other wrapped forms.
    for value in query.get("u", []) + query.get("url", []):
        nested = extract_youtube_id("https://www.youtube.com" + value)
        if nested:
            return nested

    return None


def _extract_vimeo_id(url: str) -> str | None:
    parsed = urlparse(url)
    match = re.search(r"/(\d{6,12})(?:[/?#]|$)", parsed.path)
    return match.group(1) if match else None


def _extract_dailymotion_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.endswith("dai.ly"):
        match = re.match(r"^/([a-zA-Z0-9]{5,20})", parsed.path)
        return match.group(1) if match else None
    match = re.search(r"/video/([a-zA-Z0-9]{5,20})", parsed.path)
    return match.group(1) if match else None


def _extract_tiktok_id(url: str) -> str | None:
    match = re.search(r"/video/(\d{6,25})", urlparse(url).path)
    if match:
        return match.group(1)
    # vm.tiktok.com/XXXXXXX short links carry no numeric id until resolved.
    return None


def is_channel_url(url: str) -> bool:
    """True for a channel / profile URL rather than a single video."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    path = parsed.path or "/"

    if host.endswith("youtube.com"):
        if path.startswith("/@"):
            return True
        return bool(re.match(r"^/(channel|c|user)/", path))
    if host.endswith("tiktok.com"):
        return bool(re.match(r"^/@[^/]+/?$", path))
    if host.endswith("vimeo.com"):
        return bool(re.match(r"^/(user\d+|[a-zA-Z][\w-]*)/?$", path)) and not _extract_vimeo_id(url)
    if host.endswith(("instagram.com", "twitter.com", "x.com", "twitch.tv", "rumble.com")):
        return bool(re.match(r"^/[\w.\-]+/?$", path))
    return False


def detect(raw_url: str) -> Detection:
    """Classify a URL. Raises InvalidUrlError for anything that isn't a usable link."""
    url = _normalize(raw_url)
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        lookup_host = host[4:]
    else:
        lookup_host = host

    platform, platform_name = "generic", "Web page"
    best_len = -1
    for suffix, (pid, pname) in _PLATFORM_HOSTS.items():
        if lookup_host == suffix or lookup_host.endswith("." + suffix):
            if len(suffix) > best_len:
                platform, platform_name, best_len = pid, pname, len(suffix)

    video_id: str | None = None
    if platform == "youtube":
        video_id = extract_youtube_id(url)
    elif platform == "vimeo":
        video_id = _extract_vimeo_id(url)
    elif platform == "dailymotion":
        video_id = _extract_dailymotion_id(url)
    elif platform == "tiktok":
        video_id = _extract_tiktok_id(url)

    return Detection(
        platform=platform,
        platform_name=platform_name,
        video_id=video_id,
        normalized_url=url,
        original_url=raw_url.strip(),
    )
