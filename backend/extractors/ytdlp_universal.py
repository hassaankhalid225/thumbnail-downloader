"""Tier 2 — yt-dlp, metadata only.

This one path covers Instagram, Facebook, X, Twitch, Reddit, Pinterest, LinkedIn,
Rumble, Odysee, Bilibili, Kick, Streamable, SoundCloud artwork, BitChute, VK and every
other site yt-dlp has an extractor for.

``skip_download=True`` is not optional — ThumbIQ never touches a video stream. It reads
publicly available metadata and nothing else (see LEGAL.md).
"""

from __future__ import annotations

import asyncio
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError as YTExtractorError

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services.detector import Detection
from utils.errors import ThumbIQError, classify_upstream_error

YDL_OPTS: dict[str, Any] = {
    "skip_download": True,
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "socket_timeout": 15,
    "extract_flat": False,
    "ignoreerrors": False,
    "nocheckcertificate": False,
    "retries": 1,
    "extractor_retries": 1,
    "playlist_items": "1",
}


class YtDlpExtractor(Extractor):
    name = "tier2_ytdlp"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(_extract, detection.normalized_url),
                timeout=45.0,
            )
        except TimeoutError:
            return None
        except ThumbIQError:
            # A classified upstream failure (private / deleted / geo-blocked) is a real
            # answer, not a reason to try the next tier with the same result.
            raise
        except Exception:
            return None

        if not info:
            return None

        candidates = _candidates_from(info)
        if not candidates:
            return None

        validated = await validate_candidates(candidates, strict_dimensions=False)
        if not validated:
            return None

        deduped: list[Candidate] = []
        seen: set[tuple[int | None, int | None]] = set()
        for candidate in validated:
            key = (candidate.width, candidate.height)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)

        upload_date = info.get("upload_date")
        published = (
            f"{upload_date[0:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            if upload_date and len(upload_date) == 8
            else None
        )

        return ThumbnailSet(
            candidates=deduped,
            resolved_via=self.name,
            video_id=info.get("id"),
            webpage_url=info.get("webpage_url") or detection.normalized_url,
            title=info.get("title"),
            uploader=info.get("uploader") or info.get("channel") or info.get("creator"),
            duration=int(info["duration"]) if info.get("duration") else None,
            views=info.get("view_count"),
            published_at=published,
        )


def _extract(url: str) -> dict[str, Any] | None:
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
    except (DownloadError, YTExtractorError) as exc:
        raise classify_upstream_error(str(exc)) from exc

    if not info:
        return None
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        return entries[0] if entries else None
    return info


def _candidates_from(info: dict[str, Any]) -> list[Candidate]:
    """Sort yt-dlp's thumbnail list by pixel area, dedupe by URL, label honestly."""
    raw = info.get("thumbnails") or []
    seen: set[str] = set()
    entries: list[Candidate] = []

    for item in raw:
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        width = item.get("width")
        height = item.get("height")
        label = item.get("id") or (f"{width}×{height}" if width and height else "Thumbnail")
        entries.append(
            Candidate(
                url=url,
                label=str(label),
                expected_width=width,
                expected_height=height,
                preference=int(item.get("preference") or 0),
            )
        )

    single = info.get("thumbnail")
    if single and single not in seen:
        entries.append(Candidate(url=single, label="Primary", preference=1))

    entries.sort(key=lambda c: (c.area, c.preference), reverse=True)
    # Probing every candidate on a site that lists 40 of them is wasteful; the top 12
    # by area always contain the usable ones.
    return entries[:12]
