"""The size ladder, the og scraper, and the API's error contract."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from extractors.og_scraper import extract_candidates, extract_title
from services import cache, imaging

HTML_FIXTURE = """
<!doctype html>
<html><head>
  <title>Fallback title</title>
  <meta property="og:site_name" content="Example Network">
  <meta property="og:title" content="The real title">
  <meta name="twitter:image" content="/relative/twitter.jpg">
  <meta property="og:image" content="https://cdn.example.com/og.jpg">
  <meta property="og:image:secure_url" content="https://cdn.example.com/secure.jpg">
  <link rel="image_src" href="https://cdn.example.com/link.jpg">
</head><body>
  <img src="https://cdn.example.com/tiny.jpg" width="16" height="16">
  <img src="https://cdn.example.com/hero.jpg" width="1280" height="720">
</body></html>
"""


def _bytes(image: Image.Image, fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, fmt)
    return buffer.getvalue()


# --- og scraper ------------------------------------------------------------------


def test_og_priority_order_is_respected() -> None:
    candidates = extract_candidates(HTML_FIXTURE, "https://example.com/post")
    urls = [c.url for c in candidates]
    assert urls[0] == "https://cdn.example.com/secure.jpg"
    assert "https://cdn.example.com/og.jpg" in urls
    assert "https://example.com/relative/twitter.jpg" in urls, "relative URLs must resolve"
    assert "https://cdn.example.com/link.jpg" in urls
    assert "https://cdn.example.com/hero.jpg" in urls
    assert "https://cdn.example.com/tiny.jpg" not in urls, "a 16px icon is not a thumbnail"


def test_og_title_prefers_the_open_graph_tag() -> None:
    assert extract_title(HTML_FIXTURE) == "The real title"


def test_a_page_with_no_images_yields_nothing() -> None:
    assert extract_candidates("<html><head><title>x</title></head></html>", "https://x.com") == []


# --- size ladder ------------------------------------------------------------------


@pytest.fixture
def ladder_from_720p():
    payload = _bytes(Image.new("RGB", (1280, 720), (180, 40, 30)))
    image_hash = cache.content_hash(payload)
    renditions, source = imaging.build_ladder(payload, image_hash)
    return renditions, source, image_hash


def test_every_ladder_entry_is_produced(ladder_from_720p) -> None:
    renditions, _, _ = ladder_from_720p
    assert {r.entry.id for r in renditions} == {
        "fhd", "hd", "sd", "hq", "mq", "tiny", "vertical", "square"
    }


def test_upscales_are_labelled_upscaled_and_downscales_are_not(ladder_from_720p) -> None:
    renditions, _, _ = ladder_from_720p
    by_id = {r.entry.id: r for r in renditions}

    assert by_id["fhd"].source == "upscaled", "1920 wide from a 1280 source is an upscale"
    assert by_id["vertical"].source == "upscaled"
    assert by_id["square"].source == "upscaled"
    assert by_id["hd"].source == "native"
    assert by_id["sd"].source == "native"
    assert by_id["mq"].source == "native"
    assert "Upscaled" in by_id["fhd"].note or "upscaled" in by_id["fhd"].note.lower()


def test_aspect_changes_report_the_crop_they_took(ladder_from_720p) -> None:
    renditions, _, _ = ladder_from_720p
    by_id = {r.entry.id: r for r in renditions}
    assert by_id["hd"].crop is None, "16:9 from 16:9 needs no crop"
    assert by_id["vertical"].crop is not None
    assert by_id["vertical"].crop["anchoredTo"] == "saliency"
    assert 0 <= by_id["vertical"].crop["x"] <= 1


def test_byte_counts_are_measured_not_estimated(ladder_from_720p) -> None:
    renditions, _, image_hash = ladder_from_720p
    for rendition in renditions:
        for fmt in imaging.FORMATS:
            encoded = imaging.get_rendition(image_hash, rendition.entry.id, fmt)
            assert encoded is not None
            assert rendition.bytes_by_format[fmt] == len(encoded)


def test_downloaded_renditions_have_the_advertised_dimensions(ladder_from_720p) -> None:
    renditions, _, image_hash = ladder_from_720p
    for rendition in renditions:
        for fmt in imaging.FORMATS:
            decoded = Image.open(io.BytesIO(imaging.get_rendition(image_hash, rendition.entry.id, fmt)))
            assert decoded.size == (rendition.entry.width, rendition.entry.height)


def test_filenames_are_descriptive_and_safe() -> None:
    name = imaging.download_filename("youtube", "dQw4w9WgXcQ", "hd", "webp")
    assert name == "thumbiq_youtube_dQw4w9WgXcQ_1280x720.webp"
    dirty = imaging.download_filename("youtube", "../../etc/passwd", "hd", "jpg")
    assert "/" not in dirty and ".." not in dirty


def test_exif_is_stripped_on_decode() -> None:
    image = Image.new("RGB", (100, 100), (10, 20, 30))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=b"Exif\x00\x00some-private-gps-data")
    decoded = imaging.open_image(buffer.getvalue())
    reencoded = imaging.encode(decoded, "jpg")
    assert b"some-private-gps-data" not in reencoded


def test_ai_downscale_caps_the_long_edge() -> None:
    large = Image.new("RGB", (4000, 2250))
    assert max(imaging.downscale_for_ai(large).size) == 1568
    small = Image.new("RGB", (800, 450))
    assert imaging.downscale_for_ai(small).size == (800, 450)


# --- API error contract ------------------------------------------------------------


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app, raise_server_exceptions=False)


def test_health_reports_what_is_degraded_without_failing(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "opencv" in body
    assert isinstance(body["degraded"], list)


@pytest.mark.parametrize(
    ("url", "status", "code"),
    [
        ("garbage text here", 400, "invalid_url"),
        ("", 400, "invalid_url"),
        ("ftp://youtube.com/watch?v=dQw4w9WgXcQ", 400, "invalid_url"),
    ],
)
def test_bad_input_returns_the_published_error(client, url, status, code) -> None:
    response = client.post("/api/thumbnails", json={"url": url})
    assert response.status_code == status
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["error"]["message"]
    assert "Traceback" not in response.text


def test_an_ssrf_attempt_is_refused(client) -> None:
    response = client.post("/api/thumbnails", json={"url": "http://169.254.169.254/latest/"})
    assert response.status_code in (400, 404, 422)
    assert response.json()["error"]["code"] in ("blocked_host", "no_thumbnail", "unsupported_platform")


def test_compare_requires_at_least_two_links(client) -> None:
    response = client.post("/api/analyze/compare", json={"urls": ["https://youtu.be/dQw4w9WgXcQ"]})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_url"


def test_an_unknown_size_is_rejected_by_name(client) -> None:
    response = client.post(
        "/api/download",
        json={"url": "https://youtu.be/dQw4w9WgXcQ", "sizeId": "gigantic", "format": "jpg"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "no_thumbnail"


def test_a_non_image_upload_is_rejected_with_a_human_message(client) -> None:
    response = client.post(
        "/api/analyze/upload",
        files={"image": ("notes.txt", b"this is not an image", "text/plain")},
        data={"includeAI": "false"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unreadable_image"
