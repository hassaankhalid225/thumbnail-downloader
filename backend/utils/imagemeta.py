"""Read an image's true pixel dimensions from its header bytes alone.

This is what makes honest validation cheap. YouTube's grey placeholder returns HTTP 200
with a plausible-looking response; the only reliable way to catch it is to know the
decoded size. Downloading ten full candidates to find out would cost megabytes — parsing
the first 32 KB of each costs almost nothing and gives the same answer.

Supports JPEG, PNG, WebP (all three chunk forms), GIF, BMP and AVIF/HEIF.
Returns ``None`` when the header is truncated or the format is unknown, and the caller
falls back to a full decode.
"""

from __future__ import annotations

import struct

# JPEG frame markers that carry dimensions. Excludes DHT/DAC/RST/SOI/EOI/SOS.
_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}


def parse_dimensions(data: bytes) -> tuple[int, int] | None:
    """Return ``(width, height)`` or ``None`` if undeterminable from these bytes."""
    if len(data) < 16:
        return None

    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return _png(data)
    if data.startswith(b"\xff\xd8"):
        return _jpeg(data)
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return _webp(data)
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"BM") and len(data) >= 26:
        width, height = struct.unpack("<ii", data[18:26])
        return (abs(width), abs(height))
    if data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis", b"heic", b"heix", b"mif1"):
        return _isobmff(data)
    return None


def _png(data: bytes) -> tuple[int, int] | None:
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    return (width, height) if width and height else None


def _jpeg(data: bytes) -> tuple[int, int] | None:
    offset = 2
    end = len(data)
    while offset + 3 < end:
        if data[offset] != 0xFF:
            offset += 1
            continue
        marker = data[offset + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue
        if marker == 0xFF:
            offset += 1
            continue
        if offset + 4 > end:
            return None
        segment_length = struct.unpack(">H", data[offset + 2 : offset + 4])[0]
        if segment_length < 2:
            return None
        if marker in _SOF_MARKERS:
            if offset + 9 > end:
                return None
            height, width = struct.unpack(">HH", data[offset + 5 : offset + 9])
            return (width, height) if width and height else None
        if marker == 0xDA:  # start of scan — dimensions would have come first
            return None
        offset += 2 + segment_length
    return None


def _webp(data: bytes) -> tuple[int, int] | None:
    chunk = data[12:16]
    if chunk == b"VP8 " and len(data) >= 30:
        width, height = struct.unpack("<HH", data[26:30])
        return (width & 0x3FFF, height & 0x3FFF)
    if chunk == b"VP8L" and len(data) >= 25:
        bits = struct.unpack("<I", data[21:25])[0]
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    if chunk == b"VP8X" and len(data) >= 30:
        width = int.from_bytes(data[24:27], "little") + 1
        height = int.from_bytes(data[27:30], "little") + 1
        return (width, height)
    return None


def _isobmff(data: bytes) -> tuple[int, int] | None:
    """Walk ISO-BMFF boxes for the ``ispe`` property (AVIF / HEIF)."""
    index = data.find(b"ispe")
    if index == -1 or index + 12 > len(data):
        return None
    width, height = struct.unpack(">II", data[index + 8 : index + 16])
    return (width, height) if width and height else None
