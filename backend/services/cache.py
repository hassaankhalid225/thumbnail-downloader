"""In-memory TTL caches. Nothing here is ever written to disk — see LEGAL.md.

Four caches with distinct lifetimes and distinct jobs. All bounded, all evicting, all
gone on restart.
"""

from __future__ import annotations

import hashlib
import threading
from typing import Any

from cachetools import TTLCache

from config import settings

_lock = threading.RLock()

#: normalised URL -> resolved ThumbnailSet payload
resolution_cache: TTLCache[str, Any] = TTLCache(
    maxsize=settings.cache_max_resolutions, ttl=settings.cache_ttl_seconds
)

#: image URL -> raw bytes, so a re-analysis costs no bandwidth
image_cache: TTLCache[str, bytes] = TTLCache(
    maxsize=settings.cache_max_images, ttl=settings.cache_ttl_seconds
)

#: (image sha256, size id, format) -> encoded bytes
rendition_cache: TTLCache[tuple[str, str, str], bytes] = TTLCache(
    maxsize=settings.cache_max_renditions, ttl=settings.cache_ttl_seconds
)

#: (image sha256, includeAI) -> full analysis payload.
#: This is the cache that stops an identical thumbnail costing a second Claude call.
analysis_cache: TTLCache[str, Any] = TTLCache(
    maxsize=settings.cache_max_analyses, ttl=settings.cache_ttl_seconds
)


def content_hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def get(cache: TTLCache, key) -> Any | None:
    with _lock:
        return cache.get(key)


def put(cache: TTLCache, key, value) -> None:
    with _lock:
        cache[key] = value


def stats() -> dict[str, int]:
    with _lock:
        return {
            "resolution": len(resolution_cache),
            "image": len(image_cache),
            "rendition": len(rendition_cache),
            "analysis": len(analysis_cache),
        }


def clear_all() -> None:
    with _lock:
        resolution_cache.clear()
        image_cache.clear()
        rendition_cache.clear()
        analysis_cache.clear()
