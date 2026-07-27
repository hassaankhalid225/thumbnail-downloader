"""POST /api/analyze, /api/analyze/upload, /api/analyze/compare."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, File, Form, Request, UploadFile
from slowapi.util import get_remote_address

from analysis.pipeline import analyse, strip_internals
from config import settings
from middleware.rate_limit import ANALYZE_LIMIT, ai_budget, limiter
from models.request import AnalyzeRequest, CompareRequest
from services import cache, imaging
from services.orchestrator import native_bytes_for
from utils.errors import ImageTooLargeError, ThumbIQError, UnreadableImageError

router = APIRouter(prefix="/api", tags=["analyze"])


def _ai_allowed(request: Request, requested: bool) -> tuple[bool, dict[str, Any] | None]:
    """Hourly AI budget. Exceeding it degrades the response, it does not fail it."""
    if not requested:
        return False, None
    client = get_remote_address(request)
    allowed, retry_in = ai_budget.allow(client)
    if allowed:
        return True, None
    return False, {
        "code": "ai_budget_exhausted",
        "message": (
            f"You've used this hour's {settings.rate_limit_ai_per_hour} AI analyses. "
            f"Try again in {retry_in // 60 + 1} minute(s) — every measurement below is still live."
        ),
        "retryable": True,
    }


@router.post("/analyze")
@limiter.limit(ANALYZE_LIMIT)
async def analyze(request: Request, body: AnalyzeRequest):
    payload, image_hash, detection, thumbnails = await native_bytes_for(body.url)

    # A specific ladder size can be analysed instead of the native image — useful for
    # checking what a 9:16 crop of your own thumbnail actually looks like.
    target = payload
    if body.sizeId and body.sizeId not in ("native", ""):
        await asyncio.to_thread(imaging.build_ladder, payload, image_hash)
        rendition = imaging.get_rendition(image_hash, body.sizeId, "jpg")
        if rendition is not None:
            target = rendition

    include_ai, budget_error = _ai_allowed(request, body.includeAI)
    result = await analyse(target, include_ai=include_ai)
    result = strip_internals(result)

    if budget_error is not None and result.get("aiError") is None:
        result["aiError"] = budget_error

    result["platform"] = detection.platform
    result["platformName"] = detection.platform_name
    result["videoId"] = thumbnails.video_id
    result["title"] = thumbnails.title
    result["uploader"] = thumbnails.uploader
    result["sourceUrl"] = detection.normalized_url
    result["sizeId"] = body.sizeId
    return result


@router.post("/analyze/upload")
@limiter.limit(ANALYZE_LIMIT)
async def analyze_upload(
    request: Request,
    image: UploadFile = File(...),
    includeAI: bool = Form(True),
):
    """Analyse a creator's own draft — no extraction step, straight to measurement."""
    payload = await image.read()
    if not payload:
        raise UnreadableImageError()
    if len(payload) > settings.max_image_bytes:
        raise ImageTooLargeError()

    # Decode before anything else so a non-image upload fails with the right message.
    await asyncio.to_thread(imaging.open_image, payload)

    include_ai, budget_error = _ai_allowed(request, includeAI)
    result = strip_internals(await analyse(payload, include_ai=include_ai))
    if budget_error is not None and result.get("aiError") is None:
        result["aiError"] = budget_error

    result["platform"] = "upload"
    result["platformName"] = "Your upload"
    result["videoId"] = None
    result["title"] = image.filename
    result["uploader"] = None
    result["sourceUrl"] = None
    result["sizeId"] = "native"

    # Populate the rendition cache so the upload is downloadable in every size too.
    image_hash = cache.content_hash(payload)
    await asyncio.to_thread(imaging.build_ladder, payload, image_hash)
    return result


@router.post("/analyze/compare")
@limiter.limit(ANALYZE_LIMIT)
async def compare(request: Request, body: CompareRequest):
    started = time.perf_counter()
    include_ai, budget_error = _ai_allowed(request, body.includeAI)

    async def one(url: str) -> dict[str, Any]:
        try:
            payload, _, detection, thumbnails = await native_bytes_for(url)
            analysis = strip_internals(await analyse(payload, include_ai=include_ai))
            if budget_error is not None and analysis.get("aiError") is None:
                analysis["aiError"] = budget_error
            return {
                "url": url,
                "ok": True,
                "platform": detection.platform,
                "platformName": detection.platform_name,
                "title": thumbnails.title,
                "uploader": thumbnails.uploader,
                "thumbnailUrl": thumbnails.candidates[0].url if thumbnails.candidates else None,
                "analysis": analysis,
                "error": None,
            }
        except ThumbIQError as exc:
            return {"url": url, "ok": False, "analysis": None, "error": exc.to_body()["error"]}
        except Exception:
            return {
                "url": url,
                "ok": False,
                "analysis": None,
                "error": {"code": "extractor_failed", "message": "Could not process this link", "detail": None},
            }

    # A compare with AI on is four Claude calls; two at a time keeps it responsive
    # without hammering the rate limit.
    semaphore = asyncio.Semaphore(2 if include_ai else 4)

    async def guarded(url: str) -> dict[str, Any]:
        async with semaphore:
            return await one(url)

    results = await asyncio.gather(*(guarded(url) for url in body.urls))

    return {
        "success": True,
        "results": list(results),
        "winner": _pick_winner(list(results)),
        "elapsedMs": int((time.perf_counter() - started) * 1000),
    }


CATEGORIES = (
    "stoppingPower", "textReadability", "mobileLegibility", "colorImpact",
    "contrast", "composition", "emotionalHook", "safeZone",
)


def _pick_winner(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Overall winner plus a per-category breakdown. Null scores never win a category."""
    usable = [
        (index, item)
        for index, item in enumerate(results)
        if item["ok"] and item.get("analysis")
    ]
    if not usable:
        return None

    best_index, best = max(usable, key=lambda pair: pair[1]["analysis"]["scores"]["overall"])

    categories: dict[str, Any] = {}
    for category in CATEGORIES:
        values = [
            item["analysis"]["scores"].get(category) if item["ok"] and item.get("analysis") else None
            for item in results
        ]
        scored = [(i, v) for i, v in enumerate(values) if isinstance(v, int)]
        if not scored:
            categories[category] = {"winnerIndex": None, "values": values, "margin": None}
            continue
        winner_index, winner_value = max(scored, key=lambda pair: pair[1])
        runner_up = max((v for i, v in scored if i != winner_index), default=winner_value)
        categories[category] = {
            "winnerIndex": winner_index,
            "values": values,
            "margin": winner_value - runner_up,
        }

    wins = sum(1 for c in categories.values() if c["winnerIndex"] == best_index)
    scores = best["analysis"]["scores"]
    reasons = scores.get("reasons") or {}
    strongest = max(
        (c for c in CATEGORIES if isinstance(scores.get(c), int)),
        key=lambda c: scores[c],
        default=None,
    )

    reason = f"Highest overall at {scores['overall']}, and wins {wins} of {len(CATEGORIES)} categories."
    if strongest and reasons.get(strongest):
        # Use the published human label, not the raw camelCase key.
        label = (scores.get("labels") or {}).get(strongest, strongest)
        reason += f" Strongest on {label.lower()}: {reasons[strongest]}"

    return {
        "url": best["url"],
        "index": best_index,
        "overall": scores["overall"],
        "reason": reason,
        "categories": categories,
    }
