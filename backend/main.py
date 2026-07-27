"""ThumbIQ API entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Make the package importable when uvicorn is launched from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from slowapi.middleware import SlowAPIMiddleware  # noqa: E402

from config import settings  # noqa: E402
from middleware.rate_limit import limiter  # noqa: E402
from routers import analyze, batch, download, health, thumbnails  # noqa: E402
from utils.errors import InvalidUrlError, RateLimitedError, ThumbIQError  # noqa: E402

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("thumbiq")

app = FastAPI(
    title="ThumbIQ API",
    version=settings.version,
    description=(
        "Resolve, render and measure video thumbnails. "
        "Every number this API returns comes from a measurement of a real pixel."
    ),
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Retry-After"],
    max_age=600,
)

app.include_router(health.router)
app.include_router(thumbnails.router)
app.include_router(analyze.router)
app.include_router(batch.router)
app.include_router(download.router)


@app.exception_handler(ThumbIQError)
async def thumbiq_error_handler(request: Request, exc: ThumbIQError) -> JSONResponse:
    if exc.status >= 500:
        log.error("%s on %s: %s", exc.code, request.url.path, exc.message)
    return JSONResponse(status_code=exc.status, content=exc.to_body(), headers=exc.headers)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after = str(getattr(exc, "retry_after", 60) or 60)
    error = RateLimitedError(headers={"Retry-After": retry_after})
    return JSONResponse(status_code=429, content=error.to_body(), headers=error.headers)


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """A malformed body is, from the user's side, a bad link. Say that, not a schema dump."""
    error = InvalidUrlError()
    if any("urls" in str(err.get("loc", "")) for err in exc.errors()):
        error = InvalidUrlError("Paste between two and four links to compare")
    return JSONResponse(status_code=error.status, content=error.to_body())


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "extractor_failed",
                "message": "Could not process this link. Please try again",
                "detail": None,
            },
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "ThumbIQ API",
        "version": settings.version,
        "docs": "/api/docs",
        "health": "/api/health",
    }


async def _warm_up() -> None:
    """Run the pipeline once on a tiny synthetic image at boot.

    scikit-learn's first KMeans and OpenCV's first DNN forward pass cost well over a
    second of one-time initialisation. Paying that here means the first real user
    request is as fast as the hundredth, instead of three times slower.
    """
    import asyncio
    import io

    from PIL import Image

    from analysis.pipeline import run_deterministic

    buffer = io.BytesIO()
    Image.new("RGB", (256, 144), (90, 120, 160)).save(buffer, "JPEG")
    try:
        await asyncio.to_thread(run_deterministic, buffer.getvalue())
    except Exception:  # noqa: BLE001 — a warm-up failure must never block startup
        log.warning("warm-up pass failed; first request will be slower", exc_info=True)


@app.on_event("startup")
async def on_startup() -> None:
    from analysis import faces as faces_module
    from analysis.ai import is_configured
    from analysis.text import tesseract_info

    ocr = tesseract_info()
    log.info(
        "ThumbIQ %s ready — tesseract:%s faces:%s ai:%s",
        settings.version,
        ocr["version"] or "missing",
        faces_module.detector_name(),
        "configured" if is_configured() else "not configured",
    )
    await _warm_up()
    log.info("warm-up complete")
