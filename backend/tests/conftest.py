"""Shared fixtures. Every image here has an answer known before the code runs."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))


def encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


@pytest.fixture
def three_color_image() -> Image.Image:
    """Exactly three colors in exactly known proportions, in vertical thirds."""
    image = Image.new("RGB", (600, 300))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 199, 299], fill=(255, 0, 0))
    draw.rectangle([200, 0, 399, 299], fill=(0, 128, 0))
    draw.rectangle([400, 0, 599, 299], fill=(0, 0, 255))
    return image


def _draw_glyph(draw: ImageDraw.ImageDraw, x: int, baseline: int, cap: int,
                width: int, stroke: int, color=(255, 255, 255)) -> None:
    """An H-shaped letterform: two stems and a crossbar.

    Not a solid bar — a solid bar has an ink fill ratio of 1.0, which the text detector
    correctly rejects (a filled rectangle is a shape, not a glyph). An H has a realistic
    fill ratio and constant stroke width, and its cap height is exactly ``cap``.
    """
    top = baseline - cap
    draw.rectangle([x, top, x + stroke - 1, baseline - 1], fill=color)
    draw.rectangle([x + width - stroke, top, x + width - 1, baseline - 1], fill=color)
    mid = top + cap // 2 - stroke // 2
    draw.rectangle([x, mid, x + width - 1, mid + stroke - 1], fill=color)


@pytest.fixture
def text_bars_image() -> tuple[Image.Image, int]:
    """Five H-shaped glyphs on a shared baseline, each exactly 60 px cap height.

    Drawn rather than rendered from a font so the expected cap height is known exactly
    on any machine, with no font file dependency and no hinting differences.
    """
    width, height, cap = 800, 450, 60
    image = Image.new("RGB", (width, height), (10, 10, 14))
    draw = ImageDraw.Draw(image)
    baseline = 300
    x = 120
    for _ in range(5):
        _draw_glyph(draw, x, baseline, cap, width=38, stroke=10)
        x += 56
    return image, cap


@pytest.fixture
def blob_image() -> tuple[Image.Image, tuple[float, float]]:
    """A single bright blob at a known normalised position on a flat dark field."""
    width, height = 640, 360
    array = np.full((height, width, 3), 18, dtype=np.uint8)
    cx, cy = 0.72, 0.35
    px, py = int(cx * width), int(cy * height)
    ys, xs = np.mgrid[0:height, 0:width]
    mask = ((xs - px) ** 2 + (ys - py) ** 2) < 45**2
    array[mask] = (250, 240, 230)
    return Image.fromarray(array), (cx, cy)


@pytest.fixture
def sharp_and_blurred() -> tuple[Image.Image, Image.Image]:
    rng = np.random.default_rng(7)
    array = rng.integers(0, 255, (300, 300, 3), dtype=np.uint8)
    sharp = Image.fromarray(array)
    return sharp, sharp.filter(ImageFilter.GaussianBlur(4))


@pytest.fixture
def duration_pill_text_image() -> Image.Image:
    """Text bars deliberately placed under YouTube's duration pill."""
    width, height = 1280, 720
    image = Image.new("RGB", (width, height), (20, 20, 26))
    draw = ImageDraw.Draw(image)
    baseline = int(height * 0.93)
    x = int(width * 0.855)
    for _ in range(4):
        _draw_glyph(draw, x, baseline, cap=40, width=26, stroke=7)
        x += 34
    return image


@pytest.fixture
def grey_placeholder_bytes() -> bytes:
    """A stand-in for YouTube's 120x90 grey no-maxres placeholder."""
    return encode(Image.new("RGB", (120, 90), (127, 127, 127)), "JPEG")
