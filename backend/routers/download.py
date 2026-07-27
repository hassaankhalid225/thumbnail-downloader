"""POST /api/download and /api/download/zip. Everything is streamed from memory."""

from __future__ import annotations

import io
import zipfile

from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from middleware.rate_limit import DOWNLOAD_LIMIT, limiter
from models.request import DownloadRequest, ZipRequest
from services import imaging
from services.orchestrator import ensure_renditions, native_bytes_for
from utils.errors import NoThumbnailError

router = APIRouter(prefix="/api", tags=["download"])

ZIP_README = """ThumbIQ download
================

These thumbnails are the property of the creators who made them.

Use them for research, study and inspiration. Don't republish someone else's
thumbnail as your own.

Sizes marked "upscaled" in the app were rendered above their native resolution.
The pixels are interpolated — no detail was added that wasn't in the source.

thumbiq.app
"""


@router.post("/download")
@limiter.limit(DOWNLOAD_LIMIT)
async def download(request: Request, body: DownloadRequest):
    if body.sizeId not in imaging.LADDER_BY_ID:
        raise NoThumbnailError(f"Unknown size '{body.sizeId}'")

    payload, image_hash, detection, thumbnails = await native_bytes_for(body.url)
    await ensure_renditions(payload, image_hash)

    encoded = imaging.get_rendition(image_hash, body.sizeId, body.format)
    if encoded is None:
        raise NoThumbnailError("That size could not be generated")

    filename = imaging.download_filename(
        detection.platform, thumbnails.video_id, body.sizeId, body.format
    )
    return Response(
        content=encoded,
        media_type=imaging.MIME[body.format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(encoded)),
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.post("/download/zip")
@limiter.limit(DOWNLOAD_LIMIT)
async def download_zip(request: Request, body: ZipRequest):
    payload, image_hash, detection, thumbnails = await native_bytes_for(body.url)
    await ensure_renditions(payload, image_hash)

    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for item in body.items:
            if item.sizeId not in imaging.LADDER_BY_ID:
                continue
            encoded = imaging.get_rendition(image_hash, item.sizeId, item.format)
            if encoded is None:
                continue
            archive.writestr(
                imaging.download_filename(
                    detection.platform, thumbnails.video_id, item.sizeId, item.format
                ),
                encoded,
            )
            written += 1
        archive.writestr("README.txt", ZIP_README)

    if written == 0:
        raise NoThumbnailError("None of the requested sizes could be generated")

    buffer.seek(0)
    safe_id = "".join(
        ch for ch in (thumbnails.video_id or "image") if ch.isalnum() or ch in "-_"
    )[:40]
    filename = f"thumbiq_{detection.platform}_{safe_id or 'image'}.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(buffer.getbuffer().nbytes),
        },
    )
