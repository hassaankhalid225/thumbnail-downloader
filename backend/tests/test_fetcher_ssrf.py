"""The SSRF guard and the size cap."""

from __future__ import annotations

import pytest

from services import fetcher
from utils.errors import BlockedHostError

BLOCKED = [
    "http://127.0.0.1:8000/x.jpg",
    "http://localhost:8000/x.jpg",
    "http://169.254.169.254/latest/meta-data/",   # cloud metadata — the classic target
    "http://10.0.0.1/a.png",
    "http://172.16.0.1/a.png",
    "http://192.168.1.1/a.png",
    "http://100.64.0.1/a.png",                    # CGNAT
    "http://0.0.0.0/a.png",
    "http://[::1]/a.png",
    "http://[fc00::1]/a.png",
    "http://[::ffff:127.0.0.1]/a.png",            # IPv4-mapped loopback
]


@pytest.mark.asyncio
@pytest.mark.parametrize("url", BLOCKED)
async def test_private_destinations_are_blocked(url: str) -> None:
    with pytest.raises(BlockedHostError):
        await fetcher.assert_public_host(url)


@pytest.mark.asyncio
async def test_a_public_literal_address_is_allowed() -> None:
    await fetcher.assert_public_host("https://93.184.215.14/image.png")


@pytest.mark.asyncio
async def test_a_url_without_a_host_is_blocked() -> None:
    with pytest.raises(BlockedHostError):
        await fetcher.assert_public_host("http:///nohost")


def test_magic_byte_sniffing() -> None:
    assert fetcher._sniff_type(b"\xff\xd8\xff\xe0rest") == "image/jpeg"
    assert fetcher._sniff_type(b"\x89PNG\r\n\x1a\nrest") == "image/png"
    assert fetcher._sniff_type(b"RIFF____WEBPVP8 ") == "image/webp"
    assert fetcher._sniff_type(b"<!DOCTYPE html>") is None
