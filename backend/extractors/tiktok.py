"""Tier 1 — TikTok, via the public oEmbed endpoint.

Returns a 720×1280 vertical cover most of the time. The endpoint rate-limits
aggressively, and when it does this extractor returns ``None`` so the ladder falls
through to yt-dlp rather than failing the request.
"""

from __future__ import annotations

import contextlib

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services import fetcher
from services.detector import Detection

OEMBED = "https://www.tiktok.com/oembed?url={url}"


class TikTokExtractor(Extractor):
    name = "tier1_tiktok"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        data: dict = {}
        with contextlib.suppress(Exception):
            data = await fetcher.fetch_json(OEMBED.format(url=detection.normalized_url))
        if not data or not data.get("thumbnail_url"):
            return None

        candidates = [
            Candidate(
                url=data["thumbnail_url"],
                label="Cover",
                expected_width=data.get("thumbnail_width"),
                expected_height=data.get("thumbnail_height"),
                preference=50,
            )
        ]

        validated = await validate_candidates(candidates, strict_dimensions=False)
        if not validated:
            return None

        return ThumbnailSet(
            candidates=validated,
            resolved_via=self.name,
            video_id=detection.video_id or str(data.get("embed_product_id") or "") or None,
            webpage_url=detection.normalized_url,
            title=data.get("title"),
            uploader=data.get("author_name"),
        )
