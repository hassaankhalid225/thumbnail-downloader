"""GET /api/health — what is working, what is degraded, and what it has cost."""

from __future__ import annotations

import time
from typing import Any

import cv2
from fastapi import APIRouter

from analysis import faces as faces_module
from analysis.ai import is_configured, usage_ledger
from analysis.text import tesseract_info
from config import settings
from services import cache

router = APIRouter(prefix="/api", tags=["health"])

_STARTED = time.time()


@router.get("/health")
async def health() -> dict[str, Any]:
    ocr = tesseract_info()
    detector = faces_module.detector_name()

    try:
        import yt_dlp

        ytdlp_version = yt_dlp.version.__version__
    except Exception:
        ytdlp_version = None

    degraded: list[str] = []
    if not ocr["available"]:
        degraded.append(
            "Tesseract is not installed — text is located geometrically but not transcribed."
        )
    if detector == "unavailable":
        degraded.append(
            "No face-detection model — run scripts/fetch_models.py to enable the faces module."
        )
    if not is_configured():
        degraded.append(
            "No Anthropic API key — the AI verdict is unavailable, every measurement still runs."
        )

    return {
        "status": "degraded" if degraded else "ok",
        "version": settings.version,
        "uptime": int(time.time() - _STARTED),
        "ytDlp": ytdlp_version,
        "tesseract": ocr["version"],
        "opencv": cv2.__version__,
        "faceDetector": detector,
        "saliency": "cv2.saliency" if hasattr(cv2, "saliency") else "numpy_spectral_residual",
        "ai": {
            "enabled": settings.ai_enabled,
            "model": settings.ai_model,
            "configured": is_configured(),
        },
        "aiUsage": usage_ledger.snapshot(),
        "cache": cache.stats(),
        "limits": {
            "thumbnailsPerMin": settings.rate_limit_thumbnails_per_min,
            "analyzePerMin": settings.rate_limit_analyze_per_min,
            "aiPerHour": settings.rate_limit_ai_per_hour,
            "maxImageBytes": settings.max_image_bytes,
        },
        "degraded": degraded,
    }
