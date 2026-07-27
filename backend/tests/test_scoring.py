"""Scoring is a pure function. Fixed metrics in, fixed numbers out — forever."""

from __future__ import annotations

import pytest

from analysis import scoring

FIXTURE = {
    "image": {"width": 1280, "height": 720, "bytes": 128_400, "format": "JPEG"},
    "color": {
        "harmony": {"type": "complementary", "confidence": 0.81},
        "saturation": {"mean": 0.62, "std": 0.21, "profile": "punchy"},
        "brightness": {"clippedBlack": 0.012, "clippedWhite": 0.004},
        "distinctiveness": 46.0,
    },
    "contrast": {"globalContrast": 0.58, "localContrast": {"mean": 26.0}},
    "text": {
        "wordCount": 2,
        "blocks": [
            {"capHeightPx": 128, "wcagContrast": 8.4, "passesAA": True,
             "quadrant": "bottom-left", "bbox": {"x": 0.08, "y": 0.62, "w": 0.44, "h": 0.18}},
        ],
    },
    "mobileLegibility": {
        "available": True,
        "surfaces": [
            {"surface": "mobile_feed", "width": 168, "height": 94, "capHeightPx": 16.8, "verdict": "PASS"},
            {"surface": "mobile_search", "width": 246, "height": 138, "capHeightPx": 24.6, "verdict": "PASS"},
            {"surface": "desktop_grid", "width": 360, "height": 202, "capHeightPx": 36.0, "verdict": "PASS"},
            {"surface": "desktop_sidebar", "width": 168, "height": 94, "capHeightPx": 16.8, "verdict": "PASS"},
            {"surface": "watch_page", "width": 1280, "height": 720, "capHeightPx": 128.0, "verdict": "PASS"},
        ],
    },
    "composition": {
        "focalPoint": {"x": 0.68, "y": 0.41}, "ruleOfThirdsScore": 0.86,
        "edgeDensity": 0.11, "cluttered": False, "negativeSpace": 0.31,
        "balance": {"lr": 0.94, "tb": 0.71}, "saliencyConcentration": 0.58,
    },
    "faces": {
        "count": 1,
        "faces": [{
            "areaPercent": 18.4, "quadrant": "right-center", "eyeLineUpperThird": True,
            "expression": {"label": "surprise", "confidence": 0.62},
        }],
    },
    "safeZones": {"collisions": []},
    "quality": {"sharpness": 412.8},
}

# Snapshot. Every value below was computed by hand from the formulas in ANALYSIS_SPEC.md
# before being asserted, e.g.
#   stoppingPower = 100·(0.28·1.00 + 0.26·0.55 + 0.16·1.00 + 0.18·1.00 + 0.12·0.575) = 83
#   overall       = (0.20·83 + 0.15·95 + 0.14·100 + 0.12·83 + 0.12·71 + 0.12·91
#                    + 0.10·89 + 0.05·100) = 88
# If a formula changes, this fails — and ANALYSIS_SPEC.md must change with it.
EXPECTED = {
    "overall": 88,
    "stoppingPower": 83,
    "textReadability": 95,
    "mobileLegibility": 100,
    "colorImpact": 83,
    "contrast": 71,
    "composition": 91,
    "emotionalHook": 89,
    "safeZone": 100,
}


def test_snapshot_is_stable() -> None:
    result = scoring.compute(FIXTURE)
    actual = {key: result[key] for key in EXPECTED}
    assert actual == EXPECTED


def test_scoring_is_deterministic() -> None:
    first = scoring.compute(FIXTURE)
    second = scoring.compute(FIXTURE)
    assert {k: v for k, v in first.items() if k != "reasons"} == {
        k: v for k, v in second.items() if k != "reasons"
    }


def test_weights_sum_to_one_and_are_published() -> None:
    assert sum(scoring.WEIGHTS.values()) == pytest.approx(1.0)
    result = scoring.compute(FIXTURE)
    assert result["weights"] == scoring.WEIGHTS
    assert set(result["labels"]) == set(scoring.WEIGHTS)


def test_no_text_nulls_the_text_scores_rather_than_guessing() -> None:
    metrics = {**FIXTURE, "text": {"wordCount": 0, "blocks": []},
               "mobileLegibility": {"available": False, "reason": "No text detected.", "surfaces": []}}
    result = scoring.compute(metrics)
    assert result["textReadability"] is None
    assert result["mobileLegibility"] is None
    assert set(result["excluded"]) == {"textReadability", "mobileLegibility"}
    assert "left out of the overall score" in result["excludedNote"]
    assert isinstance(result["overall"], int)


def test_overall_redistributes_weight_over_the_scores_that_exist() -> None:
    metrics = {**FIXTURE, "text": {"wordCount": 0, "blocks": []},
               "mobileLegibility": {"available": False, "surfaces": []}}
    result = scoring.compute(metrics)

    present = {k: v for k, v in result.items() if k in scoring.WEIGHTS and v is not None}
    manual = sum(scoring.WEIGHTS[k] * v for k, v in present.items()) / sum(
        scoring.WEIGHTS[k] for k in present
    )
    assert result["overall"] == round(manual)


def test_a_duration_pill_collision_costs_exactly_the_published_penalty() -> None:
    metrics = {
        **FIXTURE,
        "safeZones": {"collisions": [
            {"zone": "duration_pill", "zoneLabel": "Duration pill", "severity": "high",
             "overlapFraction": 0.41, "elementLabel": "QUIT"},
        ]},
    }
    assert scoring.compute(metrics)["safeZone"] == 100 - 35


def test_no_face_caps_the_emotional_hook_at_65() -> None:
    metrics = {**FIXTURE, "faces": {"count": 0, "faces": []}}
    result = scoring.compute(metrics)
    assert result["emotionalHook"] <= 65
    assert "No face detected" in result["reasons"]["emotionalHook"]


def test_word_count_penalty_is_monotonic() -> None:
    previous = 101
    for count in (2, 5, 8, 12):
        metrics = {**FIXTURE, "text": {**FIXTURE["text"], "wordCount": count}}
        score = scoring.compute(metrics)["textReadability"]
        assert score < previous
        previous = score


def test_every_score_carries_a_reason() -> None:
    result = scoring.compute(FIXTURE)
    for key in scoring.WEIGHTS:
        assert result["reasons"][key], f"{key} has no reason"


def test_helpers() -> None:
    assert scoring.lin(5, 0, 10) == 0.5
    assert scoring.lin(-1, 0, 10) == 0.0
    assert scoring.lin(99, 0, 10) == 1.0
    assert scoring.band(0.5, 0.4, 0.6, 0.2, 0.8) == 1.0
    assert scoring.band(0.2, 0.4, 0.6, 0.2, 0.8) == 0.0
    assert scoring.band(0.3, 0.4, 0.6, 0.2, 0.8) == pytest.approx(0.5)
