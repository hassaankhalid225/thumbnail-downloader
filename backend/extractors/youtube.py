"""Tier 1 — YouTube. Pure URL construction, no API key, no subprocess.

Target is under 300 ms: build the ten known ``i.ytimg.com`` paths, probe all of them
concurrently, keep what really exists. ``hqdefault.jpg`` is the guaranteed floor — it
exists for every video that exists, so if even that fails, the video does not.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services import fetcher
from services.detector import Detection

IMG_BASE = "https://i.ytimg.com/vi/{id}/{name}"
WEBP_BASE = "https://i.ytimg.com/vi_webp/{id}/{name}"

# (name, label, width, height, preference). Preference orders equal-area entries:
# maxresdefault beats hq720 beats the webp variant at the same 1280x720.
LADDER: tuple[tuple[str, str, int, int, int], ...] = (
    ("maxresdefault.jpg", "Max HD", 1280, 720, 100),
    ("hq720.jpg", "HD 720", 1280, 720, 90),
    ("sddefault.jpg", "SD", 640, 480, 70),
    ("hqdefault.jpg", "HQ", 480, 360, 60),
    ("mqdefault.jpg", "MQ", 320, 180, 50),
    ("default.jpg", "Default", 120, 90, 30),
)

WEBP_LADDER: tuple[tuple[str, str, int, int, int], ...] = (
    ("maxresdefault.webp", "WebP Max", 1280, 720, 85),
    ("sddefault.webp", "WebP SD", 640, 480, 65),
)

# Storyboard frames. Always 120x90; useful as an absolute last resort and as an
# alternative crop, never as a headline size.
FRAMES: tuple[tuple[str, str, int, int, int], ...] = (
    ("1.jpg", "Frame 1", 120, 90, 10),
    ("2.jpg", "Frame 2", 120, 90, 9),
    ("3.jpg", "Frame 3", 120, 90, 8),
)

OEMBED = "https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={id}&format=json"


class YouTubeExtractor(Extractor):
    name = "tier1_youtube"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        video_id = detection.video_id
        if not video_id:
            return None

        candidates = [
            Candidate(
                url=IMG_BASE.format(id=video_id, name=name),
                label=label,
                expected_width=width,
                expected_height=height,
                preference=preference,
            )
            for name, label, width, height, preference in LADDER
        ]
        candidates += [
            Candidate(
                url=WEBP_BASE.format(id=video_id, name=name),
                label=label,
                expected_width=width,
                expected_height=height,
                preference=preference,
            )
            for name, label, width, height, preference in WEBP_LADDER
        ]
        candidates += [
            Candidate(
                url=IMG_BASE.format(id=video_id, name=name),
                label=label,
                expected_width=width,
                expected_height=height,
                preference=preference,
            )
            for name, label, width, height, preference in FRAMES
        ]

        validated, meta = await asyncio.gather(
            validate_candidates(candidates, strict_dimensions=True),
            _oembed_metadata(video_id),
        )

        if not validated:
            return None

        return ThumbnailSet(
            candidates=validated,
            resolved_via=self.name,
            video_id=video_id,
            webpage_url=f"https://www.youtube.com/watch?v={video_id}",
            title=meta.get("title"),
            uploader=meta.get("author_name"),
        )


async def _oembed_metadata(video_id: str) -> dict[str, Any]:
    """Title and channel name, free and keyless. Never blocks resolution if it fails."""
    with contextlib.suppress(Exception):
        return await fetcher.fetch_json(OEMBED.format(id=video_id), timeout=6.0)
    return {}
