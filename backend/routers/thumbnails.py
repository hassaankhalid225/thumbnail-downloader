"""POST /api/thumbnails — resolve a URL to its native thumbnail and the size ladder."""

from __future__ import annotations

from fastapi import APIRouter, Request

from middleware.rate_limit import THUMBNAILS_LIMIT, limiter
from models.request import UrlRequest
from services.orchestrator import build_payload

router = APIRouter(prefix="/api", tags=["thumbnails"])


@router.post("/thumbnails")
@limiter.limit(THUMBNAILS_LIMIT)
async def get_thumbnails(request: Request, body: UrlRequest):
    return await build_payload(body.url)
