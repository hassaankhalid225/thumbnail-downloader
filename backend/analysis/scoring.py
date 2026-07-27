"""The eight sub-scores and the overall ThumbIQ score.

A pure function of the deterministic metrics. Same metrics in, same numbers out, every
time — the snapshot test in ``tests/test_scoring.py`` enforces that.

Two rules that keep this honest:

* **The AI never touches these numbers.** Scoring runs before the Claude call, and its
  output is part of Claude's *input*.
* **A score with no basis is `null`, not a guess.** A thumbnail with no text has no text
  readability. Returning 70 "to be safe" would be a fabricated measurement. Null scores
  are excluded from the overall and their weight is redistributed, and the response says
  which were excluded and why.

Every formula here is published verbatim in ANALYSIS_SPEC.md and surfaced in the
"How is this scored?" popover.
"""

from __future__ import annotations

from typing import Any

WEIGHTS: dict[str, float] = {
    "stoppingPower": 0.20,
    "textReadability": 0.15,
    "mobileLegibility": 0.14,
    "colorImpact": 0.12,
    "contrast": 0.12,
    "composition": 0.12,
    "emotionalHook": 0.10,
    "safeZone": 0.05,
}

LABELS: dict[str, str] = {
    "stoppingPower": "Stopping Power",
    "textReadability": "Text Readability",
    "mobileLegibility": "Mobile Legibility",
    "colorImpact": "Color Impact",
    "contrast": "Contrast & Legibility",
    "composition": "Composition",
    "emotionalHook": "Emotional Hook",
    "safeZone": "Safe Zone Safety",
}

HARMONY_BASE: dict[str, float] = {
    "complementary": 1.00,
    "split-complementary": 0.95,
    "triadic": 0.90,
    "analogous": 0.80,
    "monochromatic": 0.70,
    "achromatic": 0.55,
    "custom": 0.50,
}

SURFACE_WEIGHTS: dict[str, float] = {
    "mobile_feed": 0.32,
    "mobile_search": 0.22,
    "desktop_sidebar": 0.18,
    "desktop_grid": 0.18,
    "watch_page": 0.10,
}

VERDICT_VALUE = {"PASS": 1.00, "WARNING": 0.55, "FAIL": 0.10}
WORD_COUNT_VALUE = ((4, 1.00), (6, 0.75), (9, 0.45))
COLLISION_PENALTY = {"high": 35, "medium": 18, "low": 7}


def lin(value: float, low: float, high: float) -> float:
    if high == low:
        return 0.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


def band(value: float, low: float, high: float, floor: float, ceil: float) -> float:
    """1 inside [low, high], ramping to 0 at floor and ceil."""
    if low <= value <= high:
        return 1.0
    if value < low:
        return lin(value, floor, low)
    return 1.0 - lin(value, high, ceil)


def _clamp_score(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def _word_value(count: int) -> float:
    for threshold, value in WORD_COUNT_VALUE:
        if count <= threshold:
            return value
    return 0.20


def compute(metrics: dict[str, Any]) -> dict[str, Any]:
    """Turn the deterministic metrics into scores, reasons and the published weights."""
    color = metrics.get("color") or {}
    text = metrics.get("text") or {}
    mobile = metrics.get("mobileLegibility") or {}
    composition = metrics.get("composition") or {}
    faces = metrics.get("faces") or {}
    safe_zones = metrics.get("safeZones") or {}
    contrast_metrics = metrics.get("contrast") or {}

    saturation_mean = float((color.get("saturation") or {}).get("mean", 0.0))
    global_contrast = float(contrast_metrics.get("globalContrast", 0.0))
    local_mean = float((contrast_metrics.get("localContrast") or {}).get("mean", 0.0))
    edge_density = float(composition.get("edgeDensity", 0.0))
    saliency_concentration = float(composition.get("saliencyConcentration", 0.0))

    face_list = faces.get("faces") or []
    largest_face = max((f["areaPercent"] for f in face_list), default=0.0)

    blocks = text.get("blocks") or []
    has_text = bool(blocks)

    scores: dict[str, int | None] = {}
    reasons: dict[str, str] = {}

    # --- 1. Stopping Power ----------------------------------------------------
    saturation_punch = band(saturation_mean, 0.45, 0.75, 0.15, 0.95)
    contrast_range = lin(global_contrast, 0.25, 0.85)
    edge_focus = band(edge_density, 0.06, 0.16, 0.01, 0.30)
    if largest_face >= 15:
        face_signal = 1.00
    elif face_list:
        face_signal = 0.55
    else:
        face_signal = 0.30
    concentration = lin(saliency_concentration, 0.35, 0.75)

    scores["stoppingPower"] = _clamp_score(
        100
        * (
            0.28 * saturation_punch
            + 0.26 * contrast_range
            + 0.16 * edge_focus
            + 0.18 * face_signal
            + 0.12 * concentration
        )
    )
    reasons["stoppingPower"] = _stopping_reason(
        saturation_mean, global_contrast, largest_face, bool(face_list), edge_density
    )

    # --- 2. Text Readability --------------------------------------------------
    if has_text:
        feed_scale = 168 / max(1, metrics.get("image", {}).get("width", 1280))
        cap_scores = [lin(b["capHeightPx"] * feed_scale, 8, 18) for b in blocks]
        wcag_scores = [lin(b["wcagContrast"], 2.0, 7.0) for b in blocks]
        word_value = _word_value(int(text.get("wordCount", 0)))

        scores["textReadability"] = _clamp_score(
            100
            * (
                0.45 * (sum(cap_scores) / len(cap_scores))
                + 0.35 * (sum(wcag_scores) / len(wcag_scores))
                + 0.20 * word_value
            )
        )
        worst_cap = min(b["capHeightPx"] * feed_scale for b in blocks)
        worst_wcag = min(b["wcagContrast"] for b in blocks)
        # Say when the count is a geometric estimate. Without OCR, ThumbIQ located the
        # text but did not read it, and "38 words" would imply a precision it doesn't have.
        count_phrase = (
            f"~{text.get('wordCount', 0)} text regions (estimated — no OCR)"
            if text.get("wordCountEstimated")
            else f"{text.get('wordCount', 0)} words"
        )
        reasons["textReadability"] = (
            f"{count_phrase}; smallest cap height renders at "
            f"{worst_cap:.0f} px in the mobile feed; lowest contrast ratio is {worst_wcag:.1f}:1."
        )
    else:
        scores["textReadability"] = None
        reasons["textReadability"] = "No text detected — nothing to read, nothing to score."

    # --- 3. Color Impact ------------------------------------------------------
    harmony = color.get("harmony") or {}
    harmony_type = harmony.get("type", "custom")
    harmony_confidence = float(harmony.get("confidence", 0.5))
    harmony_value = HARMONY_BASE.get(harmony_type, 0.5) * (0.6 + 0.4 * harmony_confidence)

    saturation_value = band(saturation_mean, 0.40, 0.80, 0.10, 1.00)
    distinctiveness = lin(float(color.get("distinctiveness", 0.0)), 20, 70)
    brightness = color.get("brightness") or {}
    clipping = float(brightness.get("clippedBlack", 0.0)) + float(brightness.get("clippedWhite", 0.0))
    penalty = 0.5 * max(0.0, clipping - 0.08)

    scores["colorImpact"] = _clamp_score(
        100
        * max(
            0.0,
            0.35 * harmony_value + 0.35 * saturation_value + 0.30 * distinctiveness - penalty,
        )
    )
    reasons["colorImpact"] = (
        f"{harmony_type.replace('-', ' ').capitalize()} palette at "
        f"{harmony_confidence:.0%} confidence, mean saturation {saturation_mean:.2f} "
        f"({(color.get('saturation') or {}).get('profile', 'unknown')})."
    )

    # --- 4. Contrast & Legibility ---------------------------------------------
    global_value = lin(global_contrast, 0.25, 0.85)
    local_value = lin(local_mean, 8, 45)
    if has_text:
        text_wcag = sum(lin(b["wcagContrast"], 2.0, 7.0) for b in blocks) / len(blocks)
        scores["contrast"] = _clamp_score(
            100 * (0.35 * global_value + 0.25 * local_value + 0.40 * text_wcag)
        )
        failing = sum(1 for b in blocks if not b["passesAA"])
        reasons["contrast"] = (
            f"Global contrast {global_contrast:.2f}; "
            f"{failing} of {len(blocks)} text blocks fall below WCAG AA (4.5:1)."
        )
    else:
        scores["contrast"] = _clamp_score(100 * (0.55 * global_value + 0.45 * local_value))
        reasons["contrast"] = (
            f"Global contrast {global_contrast:.2f}, mean local contrast {local_mean:.0f}. "
            "No text to check against WCAG."
        )

    # --- 5. Composition -------------------------------------------------------
    thirds = float(composition.get("ruleOfThirdsScore", 0.0))
    balance = composition.get("balance") or {}
    balance_mean = (float(balance.get("lr", 1.0)) + float(balance.get("tb", 1.0))) / 2
    negative_space = band(float(composition.get("negativeSpace", 0.0)), 0.15, 0.45, 0.02, 0.75)
    clutter = 1.0 - lin(edge_density, 0.18, 0.40)

    scores["composition"] = _clamp_score(
        100 * (0.30 * thirds + 0.25 * balance_mean + 0.20 * negative_space + 0.25 * clutter)
    )
    focal = composition.get("focalPoint") or {"x": 0.5, "y": 0.5}
    reasons["composition"] = (
        f"Focal point at ({focal['x']:.2f}, {focal['y']:.2f}), "
        f"{thirds:.0%} thirds alignment, "
        f"{'cluttered' if composition.get('cluttered') else 'clean'} at "
        f"{edge_density:.2f} edge density."
    )

    # --- 6. Emotional Hook ----------------------------------------------------
    if face_list:
        size_value = band(largest_face, 12, 45, 3, 70)
        primary = face_list[0]
        eye_line = primary.get("eyeLineUpperThird")
        eye_value = 1.0 if eye_line is True else 0.5 if eye_line is False else 0.6

        expression = primary.get("expression") or {}
        expression_weight = {
            "surprise": 1.00, "joy": 1.00, "anger": 0.90, "neutral": 0.50
        }.get(expression.get("label") or "", 0.5)
        expression_value = expression_weight * float(expression.get("confidence", 0.5))

        scores["emotionalHook"] = _clamp_score(
            100 * (0.45 * size_value + 0.25 * eye_value + 0.30 * expression_value)
        )
        eye_text = (
            "eye-line in the upper third"
            if eye_line is True
            else "eye-line below the upper third"
            if eye_line is False
            else "eye-line not resolvable"
        )
        reasons["emotionalHook"] = (
            f"{len(face_list)} face{'s' if len(face_list) > 1 else ''}, largest fills "
            f"{largest_face:.0f}% of the frame, {eye_text}."
        )
    else:
        scores["emotionalHook"] = _clamp_score(
            min(65.0, 100 * (0.45 * saturation_punch + 0.55 * concentration))
        )
        reasons["emotionalHook"] = (
            "No face detected. Scored on visual energy alone and capped at 65 — a human "
            "face is the strongest hook a thumbnail has."
        )

    # --- 7. Mobile Legibility -------------------------------------------------
    surfaces = mobile.get("surfaces") or []
    if mobile.get("available") and surfaces:
        total = 0.0
        weight_sum = 0.0
        for surface in surfaces:
            weight = SURFACE_WEIGHTS.get(surface["surface"], 0.0)
            total += weight * VERDICT_VALUE.get(surface["verdict"], 0.5)
            weight_sum += weight
        scores["mobileLegibility"] = _clamp_score(100 * total / weight_sum if weight_sum else 0)
        feed = next((s for s in surfaces if s["surface"] == "mobile_feed"), surfaces[0])
        reasons["mobileLegibility"] = (
            f"At {feed['width']}×{feed['height']} the largest text is "
            f"{feed['capHeightPx']:.0f} px tall — {feed['verdict']}."
        )
    else:
        scores["mobileLegibility"] = None
        reasons["mobileLegibility"] = (
            mobile.get("reason") or "No text detected, so there is nothing to shrink."
        )

    # --- 8. Safe Zone Safety --------------------------------------------------
    collisions = safe_zones.get("collisions") or []
    penalty_total = sum(COLLISION_PENALTY.get(c["severity"], 0) for c in collisions)
    scores["safeZone"] = _clamp_score(100 - penalty_total)
    if collisions:
        worst = collisions[0]
        reasons["safeZone"] = (
            f"{len(collisions)} collision{'s' if len(collisions) > 1 else ''}; worst is "
            f"{worst['elementLabel']} under the {worst['zoneLabel'].lower()} "
            f"({worst['overlapFraction']:.0%} covered)."
        )
    else:
        reasons["safeZone"] = "Nothing important sits under YouTube's UI chrome."

    # --- overall --------------------------------------------------------------
    excluded = [key for key, value in scores.items() if value is None]
    weighted = sum(WEIGHTS[k] * v for k, v in scores.items() if v is not None)
    weight_total = sum(WEIGHTS[k] for k, v in scores.items() if v is not None)
    overall = _clamp_score(weighted / weight_total) if weight_total else 0

    result: dict[str, Any] = {"overall": overall}
    result.update(scores)
    result["reasons"] = reasons
    result["labels"] = LABELS
    result["weights"] = dict(WEIGHTS)
    result["excluded"] = excluded
    result["excludedNote"] = (
        f"{', '.join(LABELS[k] for k in excluded)} could not be measured on this image and "
        "were left out of the overall score rather than filled in with a guess."
        if excluded
        else None
    )
    return result


def _stopping_reason(
    saturation: float, contrast: float, largest_face: float, has_face: bool, edges: float
) -> str:
    parts = [f"saturation {saturation:.2f}", f"contrast range {contrast:.2f}"]
    if has_face:
        parts.append(f"largest face {largest_face:.0f}% of frame")
    else:
        parts.append("no face")
    parts.append(f"edge density {edges:.2f}")
    return "Driven by " + ", ".join(parts) + "."
