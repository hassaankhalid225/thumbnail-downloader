"""Tier 1 — Dailymotion.

Dailymotion exposes a named-size thumbnail host that needs no API call:
``dailymotion.com/thumbnail/video/{id}`` plus ``/thumbnail/video/{id}?size=N``.
oEmbed is used only for the metadata.
"""

from __future__ import annotations

import contextlib

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services import fetcher
from services.detector import Detection

THUMB = "https://www.dailymotion.com/thumbnail/video/{id}"
SIZED = "https://s1.dmcdn.net/v/{id}/{size}"
OEMBED = "https://www.dailymotion.com/services/oembed?url={url}&format=json"

# Dailymotion's named rendition codes and the sizes they resolve to.
RENDITIONS: tuple[tuple[str, str, int, int], ...] = (
    ("x1080", "Full HD", 1920, 1080),
    ("x720", "HD", 1280, 720),
    ("x480", "SD", 854, 480),
    ("x240", "Small", 426, 240),
)


class DailymotionExtractor(Extractor):
    name = "tier1_dailymotion"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        video_id = detection.video_id
        if not video_id:
            return None

        data: dict = {}
        with contextlib.suppress(Exception):
            data = await fetcher.fetch_json(OEMBED.format(url=detection.normalized_url))

        candidates: list[Candidate] = [
            Candidate(url=THUMB.format(id=video_id), label="Native", preference=50)
        ]

        # The oEmbed thumbnail is the surest URL; the sized CDN paths are a bonus.
        oembed_thumb = data.get("thumbnail_url")
        if oembed_thumb:
            candidates.append(
                Candidate(
                    url=oembed_thumb,
                    label="oEmbed",
                    expected_width=data.get("thumbnail_width"),
                    expected_height=data.get("thumbnail_height"),
                    preference=60,
                )
            )
            # dmcdn paths end in a rendition code — swap it for each larger one.
            for code, label, width, height in RENDITIONS:
                if "/v/" in oembed_thumb:
                    prefix = oembed_thumb.rsplit("/", 1)[0]
                    candidates.append(
                        Candidate(
                            url=f"{prefix}/{code}",
                            label=label,
                            expected_width=width,
                            expected_height=height,
                            preference=40,
                        )
                    )

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

        return ThumbnailSet(
            candidates=deduped,
            resolved_via=self.name,
            video_id=video_id,
            webpage_url=detection.normalized_url,
            title=data.get("title"),
            uploader=data.get("author_name"),
        )
