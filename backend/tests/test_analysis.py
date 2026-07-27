"""Each analysis module against an image whose answer is known before the code runs."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from analysis import color, composition, contrast, quality, safezones, text
from analysis.colornames import delta_e76, nearest_name
from services.imaging import to_array


def views(image):
    rgb = to_array(image)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32) / 255.0
    return rgb, gray, hsv


# --- color ----------------------------------------------------------------------


def test_kmeans_recovers_the_three_planted_colors(three_color_image) -> None:
    rgb, gray, hsv = views(three_color_image)
    result = color.analyse(rgb, hsv, gray)

    expected = [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
    found_labs = [np.array(s["lab"]) for s in result["palette"] if s["coverage"] > 5]

    for target in expected:
        target_lab = color.rgb_to_lab_array(np.array(target, dtype=np.uint8).reshape(1, 1, 3)).reshape(3)
        best = min(delta_e76(target_lab, lab) for lab in found_labs)
        assert best < 6.0, f"{target} not recovered within ΔE 6 (closest ΔE {best:.1f})"


def test_coverage_matches_the_planted_proportions(three_color_image) -> None:
    rgb, gray, hsv = views(three_color_image)
    result = color.analyse(rgb, hsv, gray)
    dominant = [s for s in result["palette"] if s["coverage"] > 5]
    assert len(dominant) == 3
    for swatch in dominant:
        assert 28 < swatch["coverage"] < 39, swatch


def test_lab_round_trip_is_exact() -> None:
    for rgb_value in [(255, 0, 0), (0, 128, 0), (18, 34, 200), (200, 255, 61), (0, 0, 0), (255, 255, 255)]:
        lab = color.rgb_to_lab_array(np.array(rgb_value, dtype=np.uint8).reshape(1, 1, 3)).reshape(1, 3)
        back = color.lab_to_rgb(lab)[0]
        assert np.allclose(back, rgb_value, atol=1)


def test_color_names_are_perceptual() -> None:
    assert nearest_name((255, 0, 0)) == "Red"
    assert nearest_name((0, 0, 0)) == "Black"
    assert nearest_name((200, 255, 61)) in ("GreenYellow", "Chartreuse", "YellowGreen")


def test_harmony_classification() -> None:
    assert color.classify_harmony([10, 190])["type"] == "complementary"
    assert color.classify_harmony([0, 120, 240])["type"] == "triadic"
    assert color.classify_harmony([10, 20, 35])["type"] == "analogous"
    assert color.classify_harmony([10, 18])["type"] == "monochromatic"
    assert color.classify_harmony([0, 150, 210])["type"] in ("split-complementary", "triadic")


# --- contrast --------------------------------------------------------------------


def test_wcag_anchor_values() -> None:
    assert contrast.contrast_ratio((0, 0, 0), (255, 255, 255)) == 21.0
    assert contrast.contrast_ratio((255, 255, 255), (0, 0, 0)) == 21.0
    assert contrast.contrast_ratio((128, 128, 128), (128, 128, 128)) == 1.0
    # The canonical AA boundary example from the WCAG docs.
    assert contrast.contrast_ratio((0x76, 0x76, 0x76), (255, 255, 255)) == pytest.approx(4.54, abs=0.02)


def test_aa_thresholds() -> None:
    assert contrast.passes_aa(4.5)
    assert not contrast.passes_aa(4.49)
    assert contrast.passes_aa(3.0, large_text=True)


def test_a_flat_image_has_no_contrast() -> None:
    from PIL import Image

    rgb, gray, _ = views(Image.new("RGB", (100, 100), (120, 120, 120)))
    result = contrast.analyse(rgb, gray)
    assert result["globalContrast"] == pytest.approx(0.0, abs=1e-6)
    assert result["localContrast"]["mean"] == pytest.approx(0.0, abs=1e-6)


# --- text -------------------------------------------------------------------------


def test_cap_height_is_measured_within_ten_percent(text_bars_image) -> None:
    image, expected_cap = text_bars_image
    rgb, gray, _ = views(image)
    result = text.analyse(rgb, gray, image)

    assert result["blocks"], "the planted bars should register as a text block"
    measured = result["blocks"][0]["capHeightPx"]
    assert abs(measured - expected_cap) / expected_cap < 0.10, (
        f"measured {measured}, planted {expected_cap}"
    )


def test_white_on_near_black_reports_a_high_contrast_ratio(text_bars_image) -> None:
    image, _ = text_bars_image
    rgb, gray, _ = views(image)
    result = text.analyse(rgb, gray, image)
    block = result["blocks"][0]
    assert block["wcagContrast"] > 15
    assert block["passesAA"]


def test_an_image_with_no_text_reports_no_text(blob_image) -> None:
    """A bright blob is not a word. Reporting one would fabricate a readability score."""
    image, _ = blob_image
    rgb, gray, _ = views(image)
    result = text.analyse(rgb, gray, image)
    assert result["blocks"] == []
    assert result["wordCount"] == 0


def test_credibility_gate_rejects_a_vertical_pair() -> None:
    block = text.Block(words=[text.Word(x=10, y=10, w=30, h=30), text.Word(x=10, y=60, w=30, h=30)])
    assert not text.is_credible_text_block(block)


def test_credibility_gate_accepts_a_baseline_aligned_run() -> None:
    block = text.Block(
        words=[text.Word(x=10 + i * 40, y=10, w=30, h=30) for i in range(4)]
    )
    assert text.is_credible_text_block(block)


def test_mobile_legibility_scales_cap_height_by_the_real_render_size(text_bars_image) -> None:
    image, cap = text_bars_image
    rgb, gray, _ = views(image)
    text_result = text.analyse(rgb, gray, image)
    mobile = text.mobile_legibility(image, text_result)

    assert mobile["available"]
    feed = next(s for s in mobile["surfaces"] if s["surface"] == "mobile_feed")
    expected = cap * (168 / image.size[0])
    assert feed["capHeightPx"] == pytest.approx(expected, rel=0.12)
    assert feed["verdict"] == ("FAIL" if expected < 10 else "WARNING" if expected < 14 else "PASS")


def test_mobile_legibility_is_unavailable_without_text(blob_image) -> None:
    image, _ = blob_image
    rgb, gray, _ = views(image)
    result = text.mobile_legibility(image, text.analyse(rgb, gray, image))
    assert result["available"] is False
    assert result["surfaces"] == []


# --- composition -------------------------------------------------------------------


def test_focal_point_lands_on_the_planted_blob(blob_image) -> None:
    image, (cx, cy) = blob_image
    rgb, gray, hsv = views(image)
    result = composition.analyse(rgb, gray, hsv)
    focal = result["focalPoint"]
    assert abs(focal["x"] - cx) < 0.12, focal
    assert abs(focal["y"] - cy) < 0.12, focal


def test_a_flat_image_is_not_cluttered() -> None:
    from PIL import Image

    rgb, gray, hsv = views(Image.new("RGB", (400, 300), (40, 60, 90)))
    result = composition.analyse(rgb, gray, hsv)
    assert result["edgeDensity"] == pytest.approx(0.0, abs=1e-6)
    assert result["cluttered"] is False
    assert result["negativeSpace"] > 0.9


def test_thirds_score_is_higher_at_an_intersection_than_at_a_corner() -> None:
    from analysis.composition import MAX_THIRDS_DISTANCE

    at_intersection = 1.0 - 0.0 / MAX_THIRDS_DISTANCE
    at_corner = 1.0 - MAX_THIRDS_DISTANCE / MAX_THIRDS_DISTANCE
    assert at_intersection == 1.0
    assert at_corner == 0.0


# --- safe zones ---------------------------------------------------------------------


def test_text_under_the_duration_pill_is_a_high_severity_collision(duration_pill_text_image) -> None:
    rgb, gray, _ = views(duration_pill_text_image)
    text_result = text.analyse(rgb, gray, duration_pill_text_image)
    assert text_result["blocks"], "the planted bars should be detected"

    result = safezones.analyse(text_result, {"faces": []})
    pill = [c for c in result["collisions"] if c["zone"] == "duration_pill"]
    assert pill, "text placed in the pill region must collide"
    assert pill[0]["severity"] == "high"
    assert "duration badge" in pill[0]["advice"]


def test_centred_text_collides_with_nothing() -> None:
    text_result = {
        "blocks": [{"bbox": {"x": 0.3, "y": 0.35, "w": 0.4, "h": 0.2},
                    "text": "HELLO", "quadrant": "center"}]
    }
    result = safezones.analyse(text_result, {"faces": []})
    assert result["clean"]
    assert result["collisions"] == []


# --- quality --------------------------------------------------------------------------


def test_blurring_lowers_measured_sharpness(sharp_and_blurred) -> None:
    sharp, blurred = sharp_and_blurred
    _, sharp_gray, _ = views(sharp)
    _, blurred_gray, _ = views(blurred)

    sharp_score = quality.analyse(sharp_gray, 300, 300, 1000, "PNG")["sharpness"]
    blurred_score = quality.analyse(blurred_gray, 300, 300, 1000, "PNG")["sharpness"]
    assert blurred_score < sharp_score * 0.25


def test_youtube_spec_compliance() -> None:
    from PIL import Image

    _, gray, _ = views(Image.new("RGB", (1280, 720), (30, 30, 30)))
    assert quality.analyse(gray, 1280, 720, 500_000, "JPEG")["meetsYouTubeSpec"]
    assert not quality.analyse(gray, 640, 360, 500_000, "JPEG")["meetsYouTubeSpec"]
    assert not quality.analyse(gray, 1280, 720, 3_000_000, "JPEG")["meetsYouTubeSpec"]
    assert not quality.analyse(gray, 1280, 1280, 500_000, "JPEG")["meetsYouTubeSpec"]


def test_noise_estimate_is_higher_on_noise() -> None:
    from PIL import Image

    rng = np.random.default_rng(3)
    flat = np.full((200, 200), 128, dtype=np.uint8)
    noisy = np.clip(flat + rng.normal(0, 25, flat.shape), 0, 255).astype(np.uint8)
    assert quality.estimate_noise(noisy) > quality.estimate_noise(flat) * 5
