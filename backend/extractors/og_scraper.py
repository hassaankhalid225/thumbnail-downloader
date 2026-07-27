"""Tier 3 — Open Graph scrape. The last resort before a clean 404.

Reads the page HTML with a real browser User-Agent and takes the first usable image in
the published priority order. No JavaScript execution, no headless browser: if a page
only exposes its image to a JS runtime, ThumbIQ says it could not find one rather than
pretending otherwise.
"""

from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from extractors.base import Candidate, Extractor, ThumbnailSet, validate_candidates
from services import fetcher
from services.detector import Detection
from utils.errors import BlockedHostError

# Priority order, exactly as specified.
META_PRIORITY: tuple[tuple[str, str, str], ...] = (
    ("property", "og:image:secure_url", "og:image:secure_url"),
    ("property", "og:image", "og:image"),
    ("property", "og:image:url", "og:image:url"),
    ("name", "twitter:image", "twitter:image"),
    ("name", "twitter:image:src", "twitter:image:src"),
    ("property", "twitter:image", "twitter:image"),
)


class OpenGraphExtractor(Extractor):
    name = "tier3_opengraph"

    async def resolve(self, detection: Detection) -> ThumbnailSet | None:
        try:
            html = await fetcher.fetch_html(detection.normalized_url)
        except BlockedHostError:
            # A refused destination is a real answer with its own published message.
            # Swallowing it here would report "no thumbnail found" for an address we
            # deliberately declined to fetch.
            raise
        except Exception:
            return None

        candidates = extract_candidates(html, detection.normalized_url)
        if not candidates:
            return None

        validated = await validate_candidates(candidates, strict_dimensions=False)
        if not validated:
            return None

        return ThumbnailSet(
            candidates=validated,
            resolved_via=self.name,
            video_id=detection.video_id,
            webpage_url=detection.normalized_url,
            title=extract_title(html),
            uploader=extract_site_name(html),
        )


def _parse(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def extract_candidates(html: str, base_url: str) -> list[Candidate]:
    """Pull image URLs out of a page in priority order. Pure function — unit-testable."""
    soup = _parse(html)
    found: list[Candidate] = []
    seen: set[str] = set()
    preference = 100

    def add(url: str | None, label: str, pref: int, width=None, height=None) -> None:
        if not url:
            return
        absolute = urljoin(base_url, url.strip())
        if not absolute.startswith(("http://", "https://")) or absolute in seen:
            return
        seen.add(absolute)
        found.append(
            Candidate(
                url=absolute,
                label=label,
                expected_width=width,
                expected_height=height,
                preference=pref,
            )
        )

    for attribute, value, label in META_PRIORITY:
        for tag in soup.find_all("meta", attrs={attribute: value}):
            add(tag.get("content"), label, preference)
            preference -= 1

    for tag in soup.find_all("link", rel=lambda v: v and "image_src" in v):
        add(tag.get("href"), "link:image_src", 40)

    # Largest declared <img> as the true fallback. Only images that state their size are
    # considered — an unsized <img> is as likely to be a 16px icon as the hero.
    sized: list[tuple[int, str]] = []
    for tag in soup.find_all("img"):
        source = tag.get("src") or tag.get("data-src")
        if not source:
            continue
        try:
            width = int(str(tag.get("width", "0")).replace("px", "") or 0)
            height = int(str(tag.get("height", "0")).replace("px", "") or 0)
        except ValueError:
            continue
        if width >= 320 and height >= 180:
            sized.append((width * height, source))
    sized.sort(reverse=True)
    for _, source in sized[:3]:
        add(source, "largest <img>", 20)

    return found


def extract_title(html: str) -> str | None:
    soup = _parse(html)
    for attribute, value in (("property", "og:title"), ("name", "twitter:title")):
        tag = soup.find("meta", attrs={attribute: value})
        if tag and tag.get("content"):
            return tag["content"].strip()
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return None


def extract_site_name(html: str) -> str | None:
    soup = _parse(html)
    tag = soup.find("meta", attrs={"property": "og:site_name"})
    return tag["content"].strip() if tag and tag.get("content") else None
