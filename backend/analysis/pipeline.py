"""Orchestrates the analysis: deterministic CV first, then the grounded AI pass.

The CV work is CPU-bound, so it runs inside ``asyncio.to_thread`` behind a bounded
semaphore. Without that, four concurrent analyses would block the event loop and every
in-flight download would stall behind them.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import cv2
import numpy as np
from PIL import Image

from analysis import color as color_module
from analysis import composition as composition_module
from analysis import contrast as contrast_module
from analysis import faces as faces_module
from analysis import quality as quality_module
from analysis import safezones as safezones_module
from analysis import scoring as scoring_module
from analysis import text as text_module
from analysis.ai import analyse as ai_analyse
from config import settings
from services import cache
from services.imaging import open_image, to_array

log = logging.getLogger("thumbiq.pipeline")

_semaphore = asyncio.Semaphore(settings.analysis_concurrency)

# Analysis runs on a bounded working copy. Above ~1920px the extra pixels change no
# metric meaningfully and cost real time; below it nothing is resampled at all.
MAX_WORKING_EDGE = 1920


def _prepare(image: Image.Image) -> tuple[Image.Image, np.ndarray, np.ndarray, np.ndarray]:
    """Decode once and derive every shared view once. Nothing is computed twice."""
    width, height = image.size
    longest = max(width, height)
    working = image
    if longest > MAX_WORKING_EDGE:
        scale = MAX_WORKING_EDGE / longest
        working = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.LANCZOS,
        )

    rgb = to_array(working)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    return working, rgb, gray, hsv


def run_deterministic(payload: bytes) -> tuple[dict[str, Any], Image.Image]:
    """Every measured metric plus the scores. Synchronous, CPU-bound, no I/O."""
    started = time.perf_counter()
    image = open_image(payload)
    native_width, native_height = image.size
    working, rgb, gray, hsv = _prepare(image)

    metrics: dict[str, Any] = {
        "image": {
            "width": native_width,
            "height": native_height,
            "bytes": len(payload),
            "format": (image.format or "JPEG"),
            "analysedAt": f"{working.size[0]}x{working.size[1]}",
        }
    }

    metrics["color"] = color_module.analyse(rgb, hsv, gray)
    metrics["contrast"] = contrast_module.analyse(rgb, gray)
    metrics["text"] = text_module.analyse(rgb, gray, working)
    metrics["mobileLegibility"] = text_module.mobile_legibility(image, metrics["text"])
    metrics["composition"] = composition_module.analyse(rgb, gray, hsv)
    metrics["faces"] = faces_module.analyse(rgb, gray)
    metrics["safeZones"] = safezones_module.analyse(metrics["text"], metrics["faces"])
    metrics["quality"] = quality_module.analyse(
        gray, native_width, native_height, len(payload), image.format
    )

    metrics["scores"] = scoring_module.compute(metrics)
    metrics["timings"] = {"deterministicMs": int((time.perf_counter() - started) * 1000)}
    return metrics, image


async def analyse(
    payload: bytes,
    *,
    include_ai: bool = True,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Full analysis of one image. Returns the API-shaped payload."""
    started = time.perf_counter()
    image_hash = cache.content_hash(payload)
    cache_key = f"{image_hash}:{'ai' if include_ai else 'cv'}"

    if use_cache:
        cached = cache.get(cache.analysis_cache, cache_key)
        if cached is not None:
            result = dict(cached)
            result["cached"] = True
            result["elapsedMs"] = int((time.perf_counter() - started) * 1000)
            return result

    # A CV-only result for the same image is a valid starting point for an AI run —
    # it saves recomputing every metric just to add the verdict.
    metrics: dict[str, Any] | None = None
    image: Image.Image | None = None
    if include_ai and use_cache:
        partial = cache.get(cache.analysis_cache, f"{image_hash}:cv")
        if partial is not None:
            metrics = partial.get("_metrics")
            if metrics is not None:
                image = open_image(payload)

    if metrics is None:
        async with _semaphore:
            metrics, image = await asyncio.to_thread(run_deterministic, payload)

    scores = metrics["scores"]
    ai_result: dict[str, Any] | None = None
    ai_error: dict[str, Any] | None = None
    ai_usage: dict[str, Any] | None = None

    if include_ai:
        ai_result, ai_error, ai_usage = await ai_analyse(image, metrics, scores)

    payload_out: dict[str, Any] = {
        "success": True,
        "imageHash": image_hash,
        "image": metrics["image"],
        "scores": scores,
        "color": metrics["color"],
        "contrast": metrics["contrast"],
        "text": metrics["text"],
        "mobileLegibility": metrics["mobileLegibility"],
        "composition": metrics["composition"],
        "faces": metrics["faces"],
        "safeZones": metrics["safeZones"],
        "quality": metrics["quality"],
        "ai": ai_result,
        "aiError": ai_error,
        "aiUsage": ai_usage,
        "cached": False,
        "timings": metrics["timings"],
    }

    if use_cache:
        stored = dict(payload_out)
        stored["_metrics"] = metrics
        cache.put(cache.analysis_cache, cache_key, stored)

    payload_out["elapsedMs"] = int((time.perf_counter() - started) * 1000)
    return payload_out


def strip_internals(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if not k.startswith("_")}
