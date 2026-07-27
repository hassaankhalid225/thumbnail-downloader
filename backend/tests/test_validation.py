"""Candidate validation — including the grey-placeholder trap."""

from __future__ import annotations

import pytest

from extractors import base
from extractors.base import Candidate, validate_candidates
from services.fetcher import ProbeResult
from utils.imagemeta import parse_dimensions


def _probe(**kwargs) -> ProbeResult:
    defaults = dict(
        url="https://i.ytimg.com/vi/ID/maxresdefault.jpg",
        ok=True, status=200, content_length=120_000,
        content_type="image/jpeg", width=1280, height=720,
    )
    defaults.update(kwargs)
    return ProbeResult(**defaults)


@pytest.mark.asyncio
async def test_a_real_maxres_candidate_survives(monkeypatch) -> None:
    async def probe(url, **_):
        return _probe(url=url)

    monkeypatch.setattr(base.fetcher, "probe_image", probe)
    result = await validate_candidates(
        [Candidate(url="https://x/maxresdefault.jpg", label="Max HD",
                   expected_width=1280, expected_height=720)]
    )
    assert len(result) == 1
    assert result[0].width == 1280
    assert result[0].bytes == 120_000


@pytest.mark.asyncio
async def test_the_grey_placeholder_is_rejected_despite_http_200(monkeypatch) -> None:
    """YouTube serves a 120x90 grey image with HTTP 200 when maxres does not exist.

    Status alone says yes. Byte count alone can be fooled. Decoded dimensions settle it.
    """
    async def probe(url, **_):
        return _probe(url=url, content_length=1_097, width=120, height=90)

    monkeypatch.setattr(base.fetcher, "probe_image", probe)
    result = await validate_candidates(
        [Candidate(url="https://x/maxresdefault.jpg", label="Max HD",
                   expected_width=1280, expected_height=720)]
    )
    assert result == []


@pytest.mark.asyncio
async def test_a_full_size_placeholder_is_still_rejected_on_dimensions(monkeypatch) -> None:
    """Byte count above the floor, but the pixels say 120x90 — still rejected."""
    async def probe(url, **_):
        return _probe(url=url, content_length=9_000, width=120, height=90)

    monkeypatch.setattr(base.fetcher, "probe_image", probe)
    result = await validate_candidates(
        [Candidate(url="https://x/maxresdefault.jpg", label="Max HD",
                   expected_width=1280, expected_height=720)]
    )
    assert result == []


@pytest.mark.asyncio
async def test_a_404_candidate_is_dropped(monkeypatch) -> None:
    async def probe(url, **_):
        return _probe(url=url, ok=False, status=404, content_length=None,
                      width=None, height=None)

    monkeypatch.setattr(base.fetcher, "probe_image", probe)
    assert await validate_candidates([Candidate(url="https://x/a.jpg", label="a")]) == []


@pytest.mark.asyncio
async def test_candidates_come_back_largest_first(monkeypatch) -> None:
    sizes = {"big": (1280, 720), "small": (320, 180)}

    async def probe(url, **_):
        key = "big" if "big" in url else "small"
        width, height = sizes[key]
        return _probe(url=url, width=width, height=height)

    monkeypatch.setattr(base.fetcher, "probe_image", probe)
    result = await validate_candidates(
        [
            Candidate(url="https://x/small.jpg", label="small", expected_width=320, expected_height=180),
            Candidate(url="https://x/big.jpg", label="big", expected_width=1280, expected_height=720),
        ]
    )
    assert [c.label for c in result] == ["big", "small"]


def test_header_dimension_parsing() -> None:
    png = (
        b"\x89PNG\r\n\x1a\n" + (13).to_bytes(4, "big") + b"IHDR"
        + (1280).to_bytes(4, "big") + (720).to_bytes(4, "big") + b"\x08\x06\x00\x00\x00"
    )
    assert parse_dimensions(png) == (1280, 720)

    gif = b"GIF89a" + (320).to_bytes(2, "little") + (180).to_bytes(2, "little") + b"\x00" * 8
    assert parse_dimensions(gif) == (320, 180)

    assert parse_dimensions(b"<html>not an image</html>") is None


def test_real_jpeg_and_webp_headers_parse(three_color_image) -> None:
    import io

    for fmt, expected in (("JPEG", (600, 300)), ("WEBP", (600, 300)), ("PNG", (600, 300))):
        buffer = io.BytesIO()
        three_color_image.save(buffer, fmt)
        assert parse_dimensions(buffer.getvalue()[:32768]) == expected
