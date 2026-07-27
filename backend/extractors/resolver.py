"""The ladder. Runs tiers in order and stops at the first that returns a usable image."""

from __future__ import annotations

import logging

from extractors.base import ThumbnailSet
from extractors.dailymotion import DailymotionExtractor
from extractors.og_scraper import OpenGraphExtractor
from extractors.tiktok import TikTokExtractor
from extractors.vimeo import VimeoExtractor
from extractors.ytdlp_universal import YtDlpExtractor
from extractors.youtube import YouTubeExtractor
from services import cache
from services.detector import Detection, detect
from utils.errors import (
    BlockedHostError,
    ContentNotFoundError,
    GeoBlockedError,
    NoThumbnailError,
    RestrictedContentError,
    ThumbIQError,
)

log = logging.getLogger("thumbiq.resolver")

TIER1 = {
    "youtube": YouTubeExtractor(),
    "vimeo": VimeoExtractor(),
    "dailymotion": DailymotionExtractor(),
    "tiktok": TikTokExtractor(),
}
TIER2 = YtDlpExtractor()
TIER3 = OpenGraphExtractor()

# These say something true about the content itself, or about our refusal to fetch it.
# Falling through to the next tier would only rediscover the same answer more slowly,
# and would risk reporting "no thumbnail" for a video that is simply private — or for an
# address the SSRF guard deliberately declined.
TERMINAL = (RestrictedContentError, ContentNotFoundError, GeoBlockedError, BlockedHostError)


async def resolve(raw_url: str, *, use_cache: bool = True) -> tuple[Detection, ThumbnailSet]:
    detection = detect(raw_url)

    if use_cache:
        cached = cache.get(cache.resolution_cache, detection.normalized_url)
        if cached is not None:
            return detection, cached

    terminal: ThumbIQError | None = None

    # --- Tier 1 ---------------------------------------------------------------
    extractor = TIER1.get(detection.platform)
    if extractor is not None:
        try:
            result = await extractor.resolve(detection)
            if result and result.candidates:
                return detection, _store(detection, result, use_cache)
        except TERMINAL as exc:
            terminal = exc
        except ThumbIQError:
            raise
        except Exception:
            log.warning("tier1 %s failed for %s", detection.platform, detection.normalized_url, exc_info=True)

    # --- Tier 2 ---------------------------------------------------------------
    try:
        result = await TIER2.resolve(detection)
        if result and result.candidates:
            return detection, _store(detection, result, use_cache)
    except TERMINAL as exc:
        terminal = exc
    except ThumbIQError as exc:
        # A generic extractor failure still gets one more chance at tier 3.
        log.info("tier2 classified failure: %s", exc.code)
    except Exception:
        log.warning("tier2 failed for %s", detection.normalized_url, exc_info=True)

    # --- Tier 3 ---------------------------------------------------------------
    try:
        result = await TIER3.resolve(detection)
        if result and result.candidates:
            return detection, _store(detection, result, use_cache)
    except ThumbIQError:
        raise
    except Exception:
        log.warning("tier3 failed for %s", detection.normalized_url, exc_info=True)

    if terminal is not None:
        raise terminal
    raise NoThumbnailError()


def _store(detection: Detection, result: ThumbnailSet, use_cache: bool) -> ThumbnailSet:
    if not result.video_id:
        result.video_id = detection.video_id
    if not result.webpage_url:
        result.webpage_url = detection.normalized_url
    if use_cache:
        cache.put(cache.resolution_cache, detection.normalized_url, result)
    return result
