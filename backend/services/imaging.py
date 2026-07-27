"""The size ladder, generated honestly.

Two rules drive this module:

1. **Never sell a fake 1080p.** Every rendition is tagged ``native`` or ``upscaled``
   based on whether the target exceeds the source on either axis. Upscales get a mild
   unsharp mask and say so.
2. **Never guess a file size.** Each rendition is encoded in all three formats and the
   real byte count is measured. The UI shows measurements, not estimates.

Aspect changes (SD 4:3, Vertical 9:16, Square 1:1) cover-crop around the measured
saliency centroid rather than the geometric centre, so a 9:16 export of a thumbnail
whose subject sits on the right keeps the subject.
"""

from __future__ import annotations

import io
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np
from PIL import Image, ImageFilter

from analysis import saliency as saliency_module
from services import cache
from utils.errors import UnreadableImageError

Format = Literal["jpg", "png", "webp"]
FORMATS: tuple[Format, ...] = ("jpg", "png", "webp")

PIL_FORMAT = {"jpg": "JPEG", "png": "PNG", "webp": "WEBP"}
MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}

JPEG_QUALITY = 92
WEBP_QUALITY = 92

# Upscale sharpening. Deliberately mild — enough to counter Lanczos softening, not
# enough to manufacture detail that was never in the source.
UNSHARP = ImageFilter.UnsharpMask(radius=1.2, percent=55, threshold=3)


@dataclass(frozen=True, slots=True)
class LadderEntry:
    id: str
    label: str
    width: int
    height: int
    aspect: str


LADDER: tuple[LadderEntry, ...] = (
    LadderEntry("fhd", "Full HD", 1920, 1080, "16:9"),
    LadderEntry("hd", "HD", 1280, 720, "16:9"),
    LadderEntry("sd", "SD", 640, 480, "4:3"),
    LadderEntry("hq", "HQ", 480, 360, "4:3"),
    LadderEntry("mq", "MQ", 320, 180, "16:9"),
    LadderEntry("tiny", "Tiny", 120, 90, "4:3"),
    LadderEntry("vertical", "Vertical HD", 1080, 1920, "9:16"),
    LadderEntry("square", "Square", 1080, 1080, "1:1"),
)

LADDER_BY_ID = {entry.id: entry for entry in LADDER}


@dataclass(slots=True)
class Rendition:
    entry: LadderEntry
    source: Literal["native", "upscaled"]
    crop: dict[str, Any] | None
    bytes_by_format: dict[str, int] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.entry.id,
            "label": self.entry.label,
            "width": self.entry.width,
            "height": self.entry.height,
            "aspect": self.entry.aspect,
            "source": self.source,
            "bytes": self.bytes_by_format.get("jpg", 0),
            "bytesByFormat": dict(self.bytes_by_format),
            "formats": list(FORMATS),
            "crop": self.crop,
            "note": self.note,
        }


def open_image(payload: bytes) -> Image.Image:
    """Decode to RGB, dropping EXIF (privacy) and honouring EXIF orientation first."""
    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
    except Exception as exc:
        raise UnreadableImageError() from exc

    try:
        from PIL import ImageOps

        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    elif image.mode == "RGBA":
        background = Image.new("RGB", image.size, (0, 0, 0))
        background.paste(image, mask=image.split()[-1])
        image = background
    return image


def to_array(image: Image.Image) -> np.ndarray:
    """RGB uint8 ndarray."""
    return np.asarray(image.convert("RGB"), dtype=np.uint8)


def encode(image: Image.Image, fmt: Format) -> bytes:
    buffer = io.BytesIO()
    if fmt == "jpg":
        image.convert("RGB").save(buffer, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    elif fmt == "png":
        image.convert("RGB").save(buffer, "PNG", optimize=True, compress_level=6)
    else:
        image.convert("RGB").save(buffer, "WEBP", quality=WEBP_QUALITY, method=4)
    return buffer.getvalue()


def _focal_point(array: np.ndarray) -> tuple[float, float]:
    gray = cv2.cvtColor(array, cv2.COLOR_RGB2GRAY)
    saliency_map, _ = saliency_module.compute(gray)
    return saliency_module.centroid(saliency_map)


def _cover_crop(
    image: Image.Image, target_aspect: float, focal: tuple[float, float]
) -> tuple[Image.Image, dict[str, Any] | None]:
    """Crop to ``target_aspect`` keeping the focal point in frame, then report the region."""
    width, height = image.size
    source_aspect = width / height
    if abs(source_aspect - target_aspect) < 0.01:
        return image, None

    if source_aspect > target_aspect:
        crop_width = int(round(height * target_aspect))
        crop_height = height
    else:
        crop_width = width
        crop_height = int(round(width / target_aspect))

    crop_width = min(crop_width, width)
    crop_height = min(crop_height, height)

    centre_x = focal[0] * width
    centre_y = focal[1] * height
    left = int(round(centre_x - crop_width / 2))
    top = int(round(centre_y - crop_height / 2))
    left = max(0, min(left, width - crop_width))
    top = max(0, min(top, height - crop_height))

    cropped = image.crop((left, top, left + crop_width, top + crop_height))
    region = {
        "x": round(left / width, 4),
        "y": round(top / height, 4),
        "w": round(crop_width / width, 4),
        "h": round(crop_height / height, 4),
        "anchoredTo": "saliency",
    }
    return cropped, region


def _render_one(
    source: Image.Image, entry: LadderEntry, focal: tuple[float, float], image_hash: str
) -> Rendition:
    target_aspect = entry.width / entry.height
    cropped, crop_region = _cover_crop(source, target_aspect, focal)
    crop_width, crop_height = cropped.size

    upscaling = entry.width > crop_width or entry.height > crop_height
    rendered = cropped.resize((entry.width, entry.height), Image.Resampling.LANCZOS)
    if upscaling:
        rendered = rendered.filter(UNSHARP)

    note_parts: list[str] = []
    if crop_region:
        note_parts.append(
            f"Cropped to {entry.aspect} around the measured focal point "
            f"({focal[0]:.2f}, {focal[1]:.2f})."
        )
    if upscaling:
        note_parts.append(
            f"Upscaled from {crop_width}×{crop_height} with Lanczos plus a mild "
            "unsharp mask — no detail is added that wasn't in the source."
        )
    else:
        note_parts.append(f"Downscaled from {crop_width}×{crop_height} with Lanczos.")

    rendition = Rendition(
        entry=entry,
        source="upscaled" if upscaling else "native",
        crop=crop_region,
        note=" ".join(note_parts),
    )

    for fmt in FORMATS:
        encoded = encode(rendered, fmt)
        rendition.bytes_by_format[fmt] = len(encoded)
        cache.put(cache.rendition_cache, (image_hash, entry.id, fmt), encoded)

    return rendition


def build_ladder(payload: bytes, image_hash: str) -> tuple[list[Rendition], Image.Image]:
    """Render every ladder entry in every format and measure the real byte counts.

    Twenty-four encodes, and PNG at 1920×1080 is not cheap — done serially this is the
    slowest part of the whole request. Pillow releases the GIL during resize and encode,
    so a thread pool gives a genuine speedup rather than just concurrency theatre.

    Results go into the rendition cache keyed by ``(image_hash, size_id, format)``, so
    ``/api/download`` is a cache read and never a second encode or a second upstream
    fetch.
    """
    source = open_image(payload)
    focal = _focal_point(to_array(source))

    with ThreadPoolExecutor(max_workers=min(8, (os.cpu_count() or 4))) as pool:
        futures = {
            pool.submit(_render_one, source, entry, focal, image_hash): entry
            for entry in LADDER
        }
        by_id = {futures[future].id: future.result() for future in as_completed(futures)}

    # Return in the declared ladder order, not completion order.
    return [by_id[entry.id] for entry in LADDER], source


def get_rendition(image_hash: str, size_id: str, fmt: str) -> bytes | None:
    return cache.get(cache.rendition_cache, (image_hash, size_id, fmt))


def downscale_for_ai(image: Image.Image, long_edge: int = 1568) -> Image.Image:
    """Claude's vision path gains nothing above 1568px on the long edge and costs tokens."""
    width, height = image.size
    longest = max(width, height)
    if longest <= long_edge:
        return image
    scale = long_edge / longest
    return image.resize(
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        Image.Resampling.LANCZOS,
    )


def download_filename(platform: str, video_id: str | None, size_id: str, fmt: str) -> str:
    entry = LADDER_BY_ID.get(size_id)
    dimensions = f"{entry.width}x{entry.height}" if entry else size_id
    safe_id = "".join(ch for ch in (video_id or "image") if ch.isalnum() or ch in "-_")[:40]
    return f"thumbiq_{platform}_{safe_id or 'image'}_{dimensions}.{fmt}"
