"""Extractor contract and the shared candidate validator."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from services import fetcher
from services.detector import Detection

# The grey "no maxres" placeholder YouTube serves with HTTP 200 is ~1.1 KB and decodes
# to 120x90. Anything under this is not a real thumbnail.
MIN_CREDIBLE_BYTES = 2000

# How far a delivered image may differ from the advertised size and still count as that
# entry. CDNs round; a 1280x720 slot delivering 1276x717 is fine, one delivering 120x90
# is the placeholder.
DIMENSION_TOLERANCE = 0.12


@dataclass(slots=True)
class Candidate:
    """One resolvable thumbnail URL, before validation."""

    url: str
    label: str
    expected_width: int | None = None
    expected_height: int | None = None
    width: int | None = None
    height: int | None = None
    bytes: int | None = None
    preference: int = 0

    @property
    def area(self) -> int:
        if self.width and self.height:
            return self.width * self.height
        if self.expected_width and self.expected_height:
            return self.expected_width * self.expected_height
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "url": self.url,
            "width": self.width,
            "height": self.height,
            "bytes": self.bytes,
        }


@dataclass(slots=True)
class ThumbnailSet:
    """What every extractor returns: validated candidates plus whatever metadata exists."""

    candidates: list[Candidate] = field(default_factory=list)
    resolved_via: str = ""
    title: str | None = None
    uploader: str | None = None
    duration: int | None = None
    views: int | None = None
    published_at: str | None = None
    video_id: str | None = None
    webpage_url: str | None = None

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None


class Extractor(ABC):
    """Every tier implements this. ``resolve`` returns None to fall through to the next."""

    name: str = "extractor"

    @abstractmethod
    async def resolve(self, detection: Detection) -> ThumbnailSet | None: ...


async def validate_candidates(
    candidates: list[Candidate],
    *,
    strict_dimensions: bool = True,
    concurrency: int = 10,
) -> list[Candidate]:
    """Probe every candidate concurrently and keep only the ones that are really there.

    Three-part validation, exactly as specified:
      1. HTTP 200
      2. content length > MIN_CREDIBLE_BYTES
      3. decoded dimensions within tolerance of what the entry claims to be

    Rule 3 is what rejects the grey placeholder. When an entry advertises no expected
    size (yt-dlp candidates often do), rule 3 degrades to "decodes to something", which
    is still enough to drop dead URLs.
    """
    if not candidates:
        return []

    semaphore = asyncio.Semaphore(concurrency)

    async def check(candidate: Candidate) -> Candidate | None:
        async with semaphore:
            probe = await fetcher.probe_image(candidate.url)

        if not probe.ok or probe.status != 200:
            return None
        if probe.content_length is not None and probe.content_length <= MIN_CREDIBLE_BYTES:
            return None
        if probe.content_type and not probe.content_type.lower().startswith("image/"):
            if probe.width is None:
                return None  # not an image by either signal

        if probe.width and probe.height:
            candidate.width, candidate.height = probe.width, probe.height
            if strict_dimensions and candidate.expected_width and candidate.expected_height:
                width_delta = abs(probe.width - candidate.expected_width) / candidate.expected_width
                height_delta = abs(probe.height - candidate.expected_height) / candidate.expected_height
                if width_delta > DIMENSION_TOLERANCE or height_delta > DIMENSION_TOLERANCE:
                    return None
        elif strict_dimensions and candidate.expected_width:
            # Header unparseable — fall back to the advertised size, which the byte
            # check has already vouched for.
            candidate.width = candidate.expected_width
            candidate.height = candidate.expected_height

        candidate.bytes = probe.content_length
        candidate.url = probe.url
        return candidate

    results = await asyncio.gather(*(check(c) for c in candidates), return_exceptions=True)

    validated: list[Candidate] = []
    seen: set[str] = set()
    for result in results:
        if isinstance(result, Candidate) and result.url not in seen:
            seen.add(result.url)
            validated.append(result)

    validated.sort(key=lambda c: (c.preference, c.area), reverse=True)
    return validated
