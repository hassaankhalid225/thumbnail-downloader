"""Shared work between the endpoints: resolve → fetch → build the ladder.

Kept in one place so ``/api/thumbnails``, ``/api/analyze`` and ``/api/download`` all see
exactly the same bytes, the same content hash and the same rendition cache. Two endpoints
computing "the" thumbnail slightly differently is how a download ends up not matching the
image that was analysed.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from extractors.base import Candidate, ThumbnailSet
from extractors.resolver import resolve
from services import cache, fetcher, imaging
from services.detector import Detection, detect
from utils.errors import NoThumbnailError


async def fetch_native(candidates: list[Candidate]) -> tuple[bytes, Candidate]:
    """Download the best candidate that actually decodes, walking down the list.

    A candidate can pass header validation and still be a broken file. Rather than
    failing the request, the ladder steps down — that is the whole point of having one.
    """
    last_error: Exception | None = None
    for candidate in candidates[:4]:
        cached = cache.get(cache.image_cache, candidate.url)
        if cached is not None:
            return cached, candidate
        try:
            result = await fetcher.fetch_image(candidate.url)
        except Exception as exc:  # noqa: PERF203
            last_error = exc
            continue
        try:
            probe = imaging.open_image(result.content)
            candidate.width, candidate.height = probe.size
            candidate.bytes = len(result.content)
        except Exception as exc:
            last_error = exc
            continue
        cache.put(cache.image_cache, candidate.url, result.content)
        return result.content, candidate

    if last_error is not None:
        raise NoThumbnailError() from last_error
    raise NoThumbnailError()


async def build_payload(raw_url: str, *, use_cache: bool = True) -> dict[str, Any]:
    """The full ``/api/thumbnails`` response, with every byte count measured."""
    started = time.perf_counter()
    detection = detect(raw_url)

    # The assembled payload is cached, not just the resolution. Without this, a repeat
    # view re-runs all 24 encodes to rebuild byte counts that haven't changed — the
    # single most expensive part of the request, redone for nothing.
    payload_key = f"payload:{detection.normalized_url}"
    if use_cache:
        cached = cache.get(cache.resolution_cache, payload_key)
        if cached is not None and imaging.get_rendition(cached["imageHash"], "hd", "jpg"):
            result = dict(cached)
            result["cached"] = True
            result["elapsedMs"] = int((time.perf_counter() - started) * 1000)
            return result

    detection, thumbnails = await resolve(raw_url)

    payload_bytes, native = await fetch_native(thumbnails.candidates)
    image_hash = cache.content_hash(payload_bytes)

    renditions, source_image = await asyncio.to_thread(
        imaging.build_ladder, payload_bytes, image_hash
    )
    native_width, native_height = source_image.size

    payload = {
        "success": True,
        "platform": detection.platform,
        "platformName": detection.platform_name,
        "videoId": thumbnails.video_id,
        "title": thumbnails.title,
        "uploader": thumbnails.uploader,
        "duration": thumbnails.duration,
        "views": thumbnails.views,
        "publishedAt": thumbnails.published_at,
        "sourceUrl": detection.normalized_url,
        "webpageUrl": thumbnails.webpage_url,
        "imageHash": image_hash,
        "native": {
            "url": native.url,
            "label": native.label,
            "width": native_width,
            "height": native_height,
            "bytes": len(payload_bytes),
            "aspect": _aspect(native_width, native_height),
        },
        "candidates": [c.to_dict() for c in thumbnails.candidates],
        "sizes": [rendition.to_dict() for rendition in renditions],
        "bestSizeId": _best_size_id(renditions),
        "resolvedVia": thumbnails.resolved_via,
        "cached": False,
    }

    if use_cache:
        cache.put(cache.resolution_cache, payload_key, payload)

    payload = dict(payload)
    payload["elapsedMs"] = int((time.perf_counter() - started) * 1000)
    return payload


async def native_bytes_for(raw_url: str) -> tuple[bytes, str, Detection, ThumbnailSet]:
    """Native image bytes + content hash, for the analyze and download paths."""
    detection, thumbnails = await resolve(raw_url)
    payload, _ = await fetch_native(thumbnails.candidates)
    return payload, cache.content_hash(payload), detection, thumbnails


async def ensure_renditions(payload: bytes, image_hash: str) -> None:
    """Make sure the rendition cache is populated before a download is served."""
    if imaging.get_rendition(image_hash, "hd", "jpg") is not None:
        return
    await asyncio.to_thread(imaging.build_ladder, payload, image_hash)


def _aspect(width: int, height: int) -> str:
    if not height:
        return "unknown"
    ratio = width / height
    for label, value in (("16:9", 16 / 9), ("4:3", 4 / 3), ("1:1", 1.0), ("9:16", 9 / 16)):
        if abs(ratio - value) / value < 0.02:
            return label
    return f"{ratio:.2f}:1"


def _best_size_id(renditions: list[imaging.Rendition]) -> str:
    """The largest entry that is still genuinely native — what a user should download."""
    native_entries = [r for r in renditions if r.source == "native"]
    pool = native_entries or renditions
    return max(pool, key=lambda r: r.entry.width * r.entry.height).entry.id
