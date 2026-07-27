"""POST /api/batch/channel — the last N thumbnails of a channel, plus a pattern report.

Deterministic analysis only. Running 24 Claude calls because someone pasted a channel URL
would be a large bill the user did not ask for; the pattern report is more useful than 24
individual verdicts anyway.
"""

from __future__ import annotations

import asyncio
import collections
import time
from typing import Any

import numpy as np
from fastapi import APIRouter, Request
from yt_dlp import YoutubeDL

from analysis.colornames import delta_e76
from analysis.pipeline import analyse, strip_internals
from config import settings
from middleware.rate_limit import BATCH_LIMIT, limiter
from models.request import ChannelRequest
from services.detector import detect
from services.orchestrator import native_bytes_for
from utils.errors import ThumbIQError, UnsupportedPlatformError, classify_upstream_error

router = APIRouter(prefix="/api", tags=["batch"])

FLAT_OPTS: dict[str, Any] = {
    "skip_download": True,
    "quiet": True,
    "no_warnings": True,
    "extract_flat": "in_playlist",
    "socket_timeout": 20,
    "ignoreerrors": True,
    "retries": 1,
}

QUADRANTS = (
    ("top-left", "top-center", "top-right"),
    ("middle-left", "center", "middle-right"),
    ("bottom-left", "bottom-center", "bottom-right"),
)


@router.post("/batch/channel")
@limiter.limit(BATCH_LIMIT)
async def channel(request: Request, body: ChannelRequest):
    started = time.perf_counter()
    detection = detect(body.url)
    limit = min(body.limit, settings.batch_max_items)

    listing = await asyncio.to_thread(_list_videos, detection.normalized_url, limit)
    if not listing["entries"]:
        raise UnsupportedPlatformError(
            "We couldn't list videos for that channel — paste a channel or profile URL"
        )

    semaphore = asyncio.Semaphore(settings.batch_concurrency)

    async def one(entry: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            url = entry.get("url") or entry.get("webpage_url")
            try:
                payload, _, _, thumbnails = await native_bytes_for(url)
                analysis = strip_internals(await analyse(payload, include_ai=False))
                return {
                    "ok": True,
                    "videoId": entry.get("id"),
                    "title": entry.get("title") or thumbnails.title,
                    "url": url,
                    "thumbnailUrl": thumbnails.candidates[0].url if thumbnails.candidates else None,
                    "scores": analysis["scores"],
                    "color": {"palette": analysis["color"]["palette"][:4]},
                    "text": {
                        "wordCount": analysis["text"]["wordCount"],
                        "blocks": [
                            {"quadrant": b["quadrant"], "capHeightPx": b["capHeightPx"]}
                            for b in analysis["text"]["blocks"]
                        ],
                    },
                    "faces": {"count": analysis["faces"]["count"]},
                    "error": None,
                }
            except ThumbIQError as exc:
                return {"ok": False, "videoId": entry.get("id"), "title": entry.get("title"),
                        "url": url, "error": exc.to_body()["error"]}
            except Exception:
                return {"ok": False, "videoId": entry.get("id"), "title": entry.get("title"),
                        "url": url, "error": {"code": "extractor_failed",
                                              "message": "Could not process this video", "detail": None}}

    items = list(await asyncio.gather(*(one(entry) for entry in listing["entries"])))
    successful = [item for item in items if item["ok"]]

    return {
        "success": True,
        "channel": {
            "name": listing["title"],
            "url": detection.normalized_url,
            "videoCount": len(successful),
            "requested": limit,
        },
        "items": items,
        "pattern": _pattern_report(successful),
        "elapsedMs": int((time.perf_counter() - started) * 1000),
    }


def _list_videos(url: str, limit: int) -> dict[str, Any]:
    options = dict(FLAT_OPTS)
    options["playlistend"] = limit
    try:
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise classify_upstream_error(str(exc)) from exc

    if not info:
        return {"title": None, "entries": []}

    entries: list[dict[str, Any]] = []
    for entry in (info.get("entries") or [])[: limit * 2]:
        if not entry:
            continue
        # A channel page can list playlists as well as videos; keep only the videos.
        if entry.get("_type") == "playlist" and entry.get("entries"):
            for nested in entry["entries"]:
                if nested and (nested.get("url") or nested.get("webpage_url")):
                    entries.append(nested)
        elif entry.get("url") or entry.get("webpage_url"):
            entries.append(entry)
        if len(entries) >= limit:
            break

    return {"title": info.get("title") or info.get("channel") or info.get("uploader"),
            "entries": entries[:limit]}


def _pattern_report(items: list[dict[str, Any]]) -> dict[str, Any]:
    """What this channel does *repeatedly* — the thing one thumbnail can never show."""
    if not items:
        return {
            "recurringPalette": [], "dominantTextPlacement": None, "faceUsageRate": 0.0,
            "averageWordCount": 0.0, "averageScores": {}, "consistencyScore": 0,
            "consistencyBasis": "No thumbnails could be analysed.",
        }

    # --- recurring palette: cluster every swatch across every thumbnail in LAB ---
    swatches = [s for item in items for s in item["color"]["palette"]]
    clusters: list[dict[str, Any]] = []
    for swatch in swatches:
        lab = np.array(swatch["lab"])
        for cluster in clusters:
            if delta_e76(lab, cluster["lab"]) < 18:
                cluster["members"].append(swatch)
                cluster["lab"] = np.mean([np.array(m["lab"]) for m in cluster["members"]], axis=0)
                break
        else:
            clusters.append({"lab": lab, "members": [swatch]})

    clusters.sort(key=lambda c: sum(m["coverage"] for m in c["members"]), reverse=True)
    recurring = []
    for cluster in clusters[:6]:
        representative = max(cluster["members"], key=lambda m: m["coverage"])
        thumbnails_using = len(
            {id(item) for item in items for s in item["color"]["palette"] if s in cluster["members"]}
        )
        recurring.append(
            {
                "hex": representative["hex"],
                "name": representative["name"],
                "frequency": round(min(1.0, thumbnails_using / len(items)), 3),
                "meanCoverage": round(
                    float(np.mean([m["coverage"] for m in cluster["members"]])), 2
                ),
            }
        )

    # --- text placement heatmap ---
    counter: collections.Counter[str] = collections.Counter()
    for item in items:
        for block in item["text"]["blocks"]:
            counter[block["quadrant"]] += 1
    total_blocks = sum(counter.values())
    heatmap = [
        [round(counter[QUADRANTS[row][col]] / total_blocks, 3) if total_blocks else 0.0
         for col in range(3)]
        for row in range(3)
    ]
    dominant = counter.most_common(1)[0] if counter else None

    face_rate = sum(1 for item in items if item["faces"]["count"] > 0) / len(items)
    word_counts = [item["text"]["wordCount"] for item in items]

    score_keys = [k for k in items[0]["scores"] if isinstance(items[0]["scores"].get(k), int)]
    average_scores = {
        key: round(
            float(np.mean([i["scores"][key] for i in items if isinstance(i["scores"].get(key), int)])), 1
        )
        for key in score_keys
    }

    # --- consistency: low variance across palette, placement and face usage ---
    palette_spread = float(np.mean([c["frequency"] for c in recurring])) if recurring else 0.0
    placement_share = (dominant[1] / total_blocks) if dominant and total_blocks else 0.0
    face_consistency = abs(face_rate - 0.5) * 2  # 0 = half and half, 1 = always or never
    word_variance = float(np.std(word_counts)) if word_counts else 0.0
    word_consistency = max(0.0, 1.0 - word_variance / 4.0)

    consistency = int(
        round(
            100
            * (
                0.35 * palette_spread
                + 0.25 * placement_share
                + 0.20 * face_consistency
                + 0.20 * word_consistency
            )
        )
    )

    return {
        "recurringPalette": recurring,
        "dominantTextPlacement": (
            {"quadrant": dominant[0], "share": round(placement_share, 3), "heatmap": heatmap}
            if dominant
            else None
        ),
        "faceUsageRate": round(face_rate, 3),
        "averageWordCount": round(float(np.mean(word_counts)), 2) if word_counts else 0.0,
        "wordCountStdDev": round(word_variance, 2),
        "averageScores": average_scores,
        "consistencyScore": consistency,
        "consistencyBasis": (
            f"Measured across {len(items)} thumbnails: palette recurrence "
            f"{palette_spread:.0%}, dominant text placement {placement_share:.0%}, "
            f"face usage {face_rate:.0%}, word-count spread ±{word_variance:.1f}."
        ),
    }
