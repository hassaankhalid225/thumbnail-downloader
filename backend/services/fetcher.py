"""Guarded outbound HTTP.

Every byte ThumbIQ fetches from the internet goes through here. Three jobs:

1. **SSRF guard.** Resolve the hostname first, reject private / loopback / link-local /
   CGNAT / reserved destinations, and re-check on *every* redirect hop — a public host
   that 302s to ``http://169.254.169.254/`` is the whole attack.
2. **Size cap.** Stream the body and abort the moment it passes the cap, rather than
   reading a 500 MB response into memory and then complaining.
3. **Honest validation.** A HEAD that returns 200 is not proof of an image; the caller
   gets back the status, the content length and the content type so it can decide.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from config import settings
from utils.errors import BlockedHostError, ImageTooLargeError
from utils.imagemeta import parse_dimensions

# A real browser UA. Several CDNs (Instagram, Facebook, Pinterest) return 403 to
# anything that self-identifies as a script.
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
)

DEFAULT_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}

HTML_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

MAX_REDIRECTS = 5


@dataclass(slots=True)
class HeadResult:
    url: str
    ok: bool
    status: int
    content_length: int | None
    content_type: str | None

    @property
    def is_image(self) -> bool:
        return bool(self.content_type and self.content_type.lower().startswith("image/"))


@dataclass(slots=True)
class FetchResult:
    url: str
    content: bytes
    content_type: str | None
    status: int


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
        return True
    if ip.is_reserved or ip.is_unspecified:
        return True
    if isinstance(ip, ipaddress.IPv4Address):
        # 100.64.0.0/10 — carrier-grade NAT. Not flagged private by ipaddress.
        if ip in ipaddress.ip_network("100.64.0.0/10"):
            return True
        # 0.0.0.0/8 and 192.0.0.0/24 (IETF protocol assignments).
        if ip in ipaddress.ip_network("0.0.0.0/8"):
            return True
    else:
        # IPv4-mapped IPv6 (::ffff:127.0.0.1) hides a loopback behind a v6 address.
        mapped = getattr(ip, "ipv4_mapped", None)
        if mapped is not None and _ip_is_blocked(mapped):
            return True
        if ip in ipaddress.ip_network("fc00::/7"):  # unique local
            return True
    return False


async def assert_public_host(url: str) -> None:
    """Resolve the URL's host and raise BlockedHostError if any address is non-public."""
    if settings.allow_private_hosts:
        return

    host = urlparse(url).hostname
    if not host:
        raise BlockedHostError()

    # A literal IP needs no DNS round trip.
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if _ip_is_blocked(literal):
            raise BlockedHostError()
        return

    try:
        infos = await asyncio.to_thread(
            socket.getaddrinfo, host, None, 0, socket.SOCK_STREAM
        )
    except (socket.gaierror, UnicodeError) as exc:
        raise BlockedHostError("That host could not be resolved") from exc

    if not infos:
        raise BlockedHostError("That host could not be resolved")

    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address.split("%")[0])
        except ValueError:
            continue
        if _ip_is_blocked(ip):
            raise BlockedHostError()


def _client(timeout: float | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(
            timeout or settings.total_timeout, connect=settings.connect_timeout
        ),
        follow_redirects=False,  # we walk redirects ourselves so each hop is checked
        headers=DEFAULT_HEADERS,
        http2=False,
    )


async def _walk(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str] | None,
    stream: bool,
):
    """Follow redirects manually, re-running the SSRF guard on every hop."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        await assert_public_host(current)
        request = client.build_request(method, current, headers=headers)
        response = await client.send(request, stream=stream)
        if response.is_redirect and response.headers.get("location"):
            location = str(response.url.join(response.headers["location"]))
            if stream:
                await response.aclose()
            else:
                await response.aread()
                await response.aclose()
            current = location
            continue
        return response, current
    raise BlockedHostError("Too many redirects")


async def head(url: str, *, timeout: float = 10.0) -> HeadResult:
    """HEAD a URL. Never raises for an HTTP-level failure — that is data, not an error.

    Falls back to a ranged GET when the server rejects HEAD (405/501) or omits
    Content-Length, which several CDNs do.
    """
    try:
        async with _client(timeout) as client:
            response, final_url = await _walk(client, "HEAD", url, None, stream=False)
            status = response.status_code
            length_header = response.headers.get("content-length")
            content_type = response.headers.get("content-type")

            needs_get = status in (403, 405, 501) or (status == 200 and not length_header)
            if needs_get:
                ranged = dict(DEFAULT_HEADERS)
                ranged["Range"] = "bytes=0-2047"
                probe, final_url = await _walk(client, "GET", url, ranged, stream=True)
                try:
                    status = probe.status_code
                    content_type = probe.headers.get("content-type") or content_type
                    content_range = probe.headers.get("content-range")
                    if content_range and "/" in content_range:
                        tail = content_range.rsplit("/", 1)[-1]
                        length_header = tail if tail.isdigit() else length_header
                    elif probe.headers.get("content-length") and status == 200:
                        length_header = probe.headers["content-length"]
                    if status == 206:
                        status = 200
                finally:
                    await probe.aclose()

            length = int(length_header) if length_header and length_header.isdigit() else None
            return HeadResult(
                url=final_url,
                ok=200 <= status < 300,
                status=status,
                content_length=length,
                content_type=content_type,
            )
    except BlockedHostError:
        raise
    except (httpx.HTTPError, ValueError):
        return HeadResult(url=url, ok=False, status=0, content_length=None, content_type=None)


@dataclass(slots=True)
class ProbeResult:
    url: str
    ok: bool
    status: int
    content_length: int | None
    content_type: str | None
    width: int | None
    height: int | None

    @property
    def is_image(self) -> bool:
        return bool(self.content_type and self.content_type.lower().startswith("image/"))


async def probe_image(url: str, *, header_bytes: int = 32768) -> ProbeResult:
    """Ranged GET of the first ``header_bytes`` so the real pixel dimensions are known.

    This is how the grey-placeholder trap is caught: a candidate can return HTTP 200 with
    a believable content-length and still decode to 120×90. Parsing the header is the
    only check that actually settles it, and it costs one small ranged request.
    """
    try:
        async with _client(12.0) as client:
            headers = dict(DEFAULT_HEADERS)
            headers["Range"] = f"bytes=0-{header_bytes - 1}"
            response, final_url = await _walk(client, "GET", url, headers, stream=True)
            try:
                status = response.status_code
                content_type = response.headers.get("content-type")

                total: int | None = None
                content_range = response.headers.get("content-range")
                if content_range and "/" in content_range:
                    tail = content_range.rsplit("/", 1)[-1]
                    if tail.isdigit():
                        total = int(tail)
                elif response.headers.get("content-length", "").isdigit() and status == 200:
                    total = int(response.headers["content-length"])

                payload = b""
                if status in (200, 206):
                    async for chunk in response.aiter_bytes(16384):
                        payload += chunk
                        if len(payload) >= header_bytes:
                            break

                dimensions = parse_dimensions(payload) if payload else None
                if total is None and status == 200 and len(payload) < header_bytes:
                    total = len(payload)  # whole body arrived; that is the real size

                return ProbeResult(
                    url=final_url,
                    ok=status in (200, 206),
                    status=200 if status == 206 else status,
                    content_length=total,
                    content_type=content_type or _sniff_type(payload),
                    width=dimensions[0] if dimensions else None,
                    height=dimensions[1] if dimensions else None,
                )
            finally:
                await response.aclose()
    except BlockedHostError:
        raise
    except (httpx.HTTPError, ValueError, OSError):
        return ProbeResult(
            url=url, ok=False, status=0, content_length=None,
            content_type=None, width=None, height=None,
        )


async def fetch_image(url: str, *, max_bytes: int | None = None) -> FetchResult:
    """Download an image, enforcing the byte cap while streaming."""
    cap = max_bytes or settings.max_image_bytes

    async with _client() as client:
        response, final_url = await _walk(client, "GET", url, None, stream=True)
        try:
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"{response.status_code}", request=response.request, response=response
                )

            content_type = response.headers.get("content-type", "")
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > cap:
                raise ImageTooLargeError()

            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes(65536):
                total += len(chunk)
                if total > cap:
                    raise ImageTooLargeError()
                chunks.append(chunk)

            payload = b"".join(chunks)

            # Some CDNs mislabel content type; sniff the magic bytes as the real check.
            if not content_type.lower().startswith("image/") and not _looks_like_image(payload):
                raise BlockedHostError("That URL did not return an image")

            return FetchResult(
                url=final_url,
                content=payload,
                content_type=content_type or _sniff_type(payload),
                status=response.status_code,
            )
        finally:
            await response.aclose()


async def fetch_html(url: str) -> str:
    """Fetch a page as text, capped at MAX_HTML_BYTES."""
    async with _client() as client:
        response, _ = await _walk(client, "GET", url, HTML_HEADERS, stream=True)
        try:
            response.raise_for_status()
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes(65536):
                total += len(chunk)
                chunks.append(chunk)
                if total > settings.max_html_bytes:
                    break
            encoding = response.charset_encoding or "utf-8"
            return b"".join(chunks).decode(encoding, errors="replace")
        finally:
            await response.aclose()


async def fetch_json(url: str, *, timeout: float = 12.0) -> dict:
    """Fetch a JSON document (oEmbed endpoints)."""
    async with _client(timeout) as client:
        headers = dict(HTML_HEADERS)
        headers["Accept"] = "application/json,*/*;q=0.8"
        response, _ = await _walk(client, "GET", url, headers, stream=False)
        response.raise_for_status()
        return response.json()


_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
)


def _sniff_type(payload: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if payload.startswith(magic):
            return mime
    if payload[:4] == b"RIFF" and payload[8:12] == b"WEBP":
        return "image/webp"
    if payload[4:12] in (b"ftypavif", b"ftypavis"):
        return "image/avif"
    return None


def _looks_like_image(payload: bytes) -> bool:
    return _sniff_type(payload) is not None
