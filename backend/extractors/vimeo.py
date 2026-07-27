"""Tier 1 — Vimeo, via oEmbed.

Vimeo returns a thumbnail URL with a size suffix baked into the filename
(``…-d_295x166``) or as query params on the newer ``i.vimeocdn.com`` form. Both are
rewritten to request larger renditions, and every rewrite is validated — Vimeo happily
serves a smaller image than you asked for rather than 404ing.
"""

from __future__ import annotations

import contextlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services import fetcher
from services.detector import Detection

OEMBED = "https://vimeo.com/api/oembed.json?url={url}&width=1920"

# Requested renditions, largest first.
RENDITIONS: tuple[tuple[str, int, int], ...] = (
    ("Full HD", 1920, 1080),
    ("HD", 1280, 720),
    ("SD", 640, 360),
    ("Small", 295, 166),
)

_SIZE_SUFFIX = re.compile(r"-d_\d+x\d+(?:\?.*)?$")
_LEGACY_SIZE = re.compile(r"_\d+x\d+(\.\w+)$")


class VimeoExtractor(Extractor):
    name = "tier1_vimeo"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        data: dict = {}
        with contextlib.suppress(Exception):
            data = await fetcher.fetch_json(OEMBED.format(url=detection.normalized_url))
        if not data:
            return None

        base = data.get("thumbnail_url")
        if not base:
            return None

        candidates: list[Candidate] = []
        seen: set[str] = set()
        for label, width, height in RENDITIONS:
            url = _resize(base, width, height)
            if url in seen:
                continue
            seen.add(url)
            candidates.append(
                Candidate(url=url, label=label, expected_width=width, expected_height=height)
            )

        # The URL as Vimeo gave it, at whatever size it declares.
        if base not in seen:
            candidates.append(
                Candidate(
                    url=base,
                    label="Native",
                    expected_width=data.get("thumbnail_width"),
                    expected_height=data.get("thumbnail_height"),
                )
            )

        # Vimeo serves whatever it has rather than 404ing an oversized request, so the
        # dimension check is relaxed: the probe reports the real size and the ladder
        # dedupes by that.
        validated = await validate_candidates(candidates, strict_dimensions=False)
        if not validated:
            return None

        deduped: list[Candidate] = []
        seen_dims: set[tuple[int | None, int | None]] = set()
        for candidate in validated:
            key = (candidate.width, candidate.height)
            if key in seen_dims:
                continue
            seen_dims.add(key)
            deduped.append(candidate)

        return ThumbnailSet(
            candidates=deduped,
            resolved_via=self.name,
            video_id=detection.video_id or str(data.get("video_id") or "") or None,
            webpage_url=data.get("uri") and f"https://vimeo.com{data['uri']}" or detection.normalized_url,
            title=data.get("title"),
            uploader=data.get("author_name"),
            duration=data.get("duration"),
            published_at=(data.get("upload_date") or "").split(" ")[0] or None,
        )


def _resize(url: str, width: int, height: int) -> str:
    """Rewrite a Vimeo thumbnail URL to request a specific rendition."""
    parsed = urlparse(url)

    # Newer form: i.vimeocdn.com/video/1234-abc-d_295x166
    if _SIZE_SUFFIX.search(parsed.path) or "-d_" in parsed.path:
        path = re.sub(r"-d_\d+x\d+", f"-d_{width}x{height}", parsed.path)
        return urlunparse(parsed._replace(path=path))

    # Legacy form: i.vimeocdn.com/video/1234_295x166.jpg
    if _LEGACY_SIZE.search(parsed.path):
        path = _LEGACY_SIZE.sub(rf"_{width}x{height}\1", parsed.path)
        return urlunparse(parsed._replace(path=path))

    # Query-param form.
    query = parse_qs(parsed.query)
    query["w"] = [str(width)]
    query["h"] = [str(height)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
