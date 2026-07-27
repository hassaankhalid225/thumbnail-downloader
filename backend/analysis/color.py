"""Palette, harmony, temperature, saturation and brightness.

Clustering happens in **LAB**, not RGB. RGB distance is not perceptual: cluster there and
a deep red and a bright orange land in the same bucket while two near-identical blues
split into two. LAB is the whole reason the palette matches what a designer sees.
"""

from __future__ import annotations

import json
from typing import Any

import cv2
import numpy as np
from sklearn.cluster import KMeans

from analysis.colornames import delta_e76, nearest_name

SAMPLE_SIZE = 200
K = 6
MIN_HARMONY_COVERAGE = 5.0  # percent
MIN_CHROMA_SATURATION = 0.15  # below this a swatch has no meaningful hue


def rgb_to_lab_array(rgb: np.ndarray) -> np.ndarray:
    """sRGB uint8 image → LAB float64 image (D65, L* 0–100)."""
    array = np.asarray(rgb, dtype=np.float64) / 255.0
    linear = np.where(array <= 0.04045, array / 12.92, ((array + 0.055) / 1.055) ** 2.4)

    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    flat = linear.reshape(-1, 3)
    xyz = flat @ matrix.T
    white = np.array([0.95047, 1.00000, 1.08883])
    scaled = xyz / white

    epsilon = 216 / 24389
    kappa = 24389 / 27
    f = np.where(scaled > epsilon, np.cbrt(scaled), (kappa * scaled + 16) / 116)

    lightness = 116 * f[:, 1] - 16
    a = 500 * (f[:, 0] - f[:, 1])
    b = 200 * (f[:, 1] - f[:, 2])
    return np.stack([lightness, a, b], axis=1).reshape(rgb.shape)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    """LAB → sRGB uint8. Inverse of the above, so round-trips are exact."""
    lab = np.asarray(lab, dtype=np.float64).reshape(-1, 3)
    fy = (lab[:, 0] + 16) / 116
    fx = fy + lab[:, 1] / 500
    fz = fy - lab[:, 2] / 200

    epsilon = 216 / 24389
    kappa = 24389 / 27

    def finv(t: np.ndarray) -> np.ndarray:
        t3 = t**3
        return np.where(t3 > epsilon, t3, (116 * t - 16) / kappa)

    white = np.array([0.95047, 1.00000, 1.08883])
    xyz = np.stack([finv(fx), finv(fy), finv(fz)], axis=1) * white

    inverse = np.array(
        [
            [3.2404542, -1.5371385, -0.4985314],
            [-0.9692660, 1.8760108, 0.0415560],
            [0.0556434, -0.2040259, 1.0572252],
        ]
    )
    linear = xyz @ inverse.T
    linear = np.clip(linear, 0, 1)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    return np.clip(np.round(srgb * 255), 0, 255).astype(np.uint8)


def to_hex(rgb) -> str:
    r, g, b = (int(round(float(v))) for v in np.asarray(rgb).reshape(3))
    return f"#{r:02X}{g:02X}{b:02X}"


def _circular_arc(hues: list[float]) -> float:
    """Smallest arc on the hue circle containing every hue. 0–360."""
    if len(hues) < 2:
        return 0.0
    ordered = sorted(h % 360 for h in hues)
    gaps = [
        (ordered[(i + 1) % len(ordered)] - ordered[i]) % 360 for i in range(len(ordered))
    ]
    return 360.0 - max(gaps)


def _hue_delta(a: float, b: float) -> float:
    """Shortest angular distance between two hues, 0–180."""
    diff = abs((a - b) % 360)
    return min(diff, 360 - diff)


def classify_harmony(hues: list[float]) -> dict[str, Any]:
    """Classify the hue relationship. First match wins — see ANALYSIS_SPEC.md."""
    if len(hues) < 2:
        return {
            "type": "monochromatic" if hues else "achromatic",
            "confidence": 0.5 if hues else 1.0,
            "hues": [round(h, 1) for h in hues],
            "reason": "Only one chromatic color carries enough of the frame to compare."
        }

    arc = _circular_arc(hues)

    if arc < 20:
        return {
            "type": "monochromatic",
            "confidence": round(1.0 - arc / 20.0, 2),
            "hues": [round(h, 1) for h in hues],
            "reason": f"Every dominant hue sits inside a {arc:.0f}° arc.",
        }

    if arc < 45:
        return {
            "type": "analogous",
            "confidence": round(1.0 - (arc - 20) / 25.0 * 0.5 - 0.2, 2),
            "hues": [round(h, 1) for h in hues],
            "reason": f"Hues span {arc:.0f}°, neighbours on the wheel.",
        }

    # Triadic — three hues mutually 120° apart.
    best_triadic: tuple[float, tuple[float, float, float]] | None = None
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            for k in range(j + 1, len(hues)):
                deltas = [
                    _hue_delta(hues[i], hues[j]),
                    _hue_delta(hues[j], hues[k]),
                    _hue_delta(hues[i], hues[k]),
                ]
                error = max(abs(d - 120) for d in deltas)
                if error <= 18 and (best_triadic is None or error < best_triadic[0]):
                    best_triadic = (error, (hues[i], hues[j], hues[k]))

    # Split-complementary — a base with partners near +150 and +210.
    best_split: tuple[float, tuple[float, float, float]] | None = None
    for base in hues:
        partners = [h for h in hues if h is not base]
        for p1 in partners:
            for p2 in partners:
                if p1 is p2:
                    continue
                offset_a = (p1 - base) % 360
                offset_b = (p2 - base) % 360
                error = max(abs(offset_a - 150), abs(offset_b - 210))
                if error <= 18 and (best_split is None or error < best_split[0]):
                    best_split = (error, (base, p1, p2))

    # Complementary — any pair at 180°.
    best_complement: tuple[float, tuple[float, float]] | None = None
    for i in range(len(hues)):
        for j in range(i + 1, len(hues)):
            error = abs(_hue_delta(hues[i], hues[j]) - 180)
            if error <= 15 and (best_complement is None or error < best_complement[0]):
                best_complement = (error, (hues[i], hues[j]))

    if best_complement is not None:
        error, pair = best_complement
        return {
            "type": "complementary",
            "confidence": round(1.0 - error / 15.0 * 0.45, 2),
            "hues": [round(h, 1) for h in pair],
            "reason": f"{pair[0]:.0f}° and {pair[1]:.0f}° sit opposite each other on the wheel.",
        }
    if best_split is not None:
        error, triple = best_split
        return {
            "type": "split-complementary",
            "confidence": round(1.0 - error / 18.0 * 0.45, 2),
            "hues": [round(h, 1) for h in triple],
            "reason": f"A base at {triple[0]:.0f}° with partners either side of its opposite.",
        }
    if best_triadic is not None:
        error, triple = best_triadic
        return {
            "type": "triadic",
            "confidence": round(1.0 - error / 18.0 * 0.45, 2),
            "hues": [round(h, 1) for h in triple],
            "reason": "Three hues spaced evenly around the wheel.",
        }

    return {
        "type": "custom",
        "confidence": 0.4,
        "hues": [round(h, 1) for h in hues],
        "reason": f"Hues span {arc:.0f}° without matching a standard scheme.",
    }


def analyse(rgb: np.ndarray, hsv: np.ndarray, gray: np.ndarray) -> dict[str, Any]:
    """Full color analysis. ``rgb`` uint8 HxWx3, ``hsv`` float [0,1], ``gray`` uint8."""
    sample = cv2.resize(rgb, (SAMPLE_SIZE, SAMPLE_SIZE), interpolation=cv2.INTER_AREA)
    lab_sample = rgb_to_lab_array(sample).reshape(-1, 3)

    kmeans = KMeans(n_clusters=K, n_init=4, random_state=42, max_iter=300)
    labels = kmeans.fit_predict(lab_sample)
    centroids = kmeans.cluster_centers_

    total = float(labels.size)
    swatches: list[dict[str, Any]] = []
    for index in range(K):
        count = int(np.count_nonzero(labels == index))
        if count == 0:
            continue
        lab = centroids[index]
        rgb_value = lab_to_rgb(lab.reshape(1, 3))[0]
        hsv_value = cv2.cvtColor(rgb_value.reshape(1, 1, 3), cv2.COLOR_RGB2HSV)[0, 0]
        swatches.append(
            {
                "hex": to_hex(rgb_value),
                "rgb": [int(v) for v in rgb_value],
                "lab": [round(float(v), 2) for v in lab],
                "hsv": [round(float(hsv_value[0]) * 2, 1), round(float(hsv_value[1]) / 255, 3), round(float(hsv_value[2]) / 255, 3)],
                "coverage": round(count / total * 100, 2),
                "name": nearest_name(rgb_value),
            }
        )

    swatches.sort(key=lambda s: s["coverage"], reverse=True)

    chromatic_hues = [
        s["hsv"][0]
        for s in swatches
        if s["coverage"] >= MIN_HARMONY_COVERAGE and s["hsv"][1] >= MIN_CHROMA_SATURATION
    ]
    harmony = classify_harmony(chromatic_hues)

    # --- temperature: LAB b* is the yellow(+)/blue(−) axis --------------------
    lab_full = rgb_to_lab_array(cv2.resize(rgb, (SAMPLE_SIZE, SAMPLE_SIZE), interpolation=cv2.INTER_AREA))
    mean_b = float(lab_full[..., 2].mean())
    warm_ratio = float((lab_full[..., 2] > 0).mean())
    if mean_b > 5:
        temperature_profile = "warm"
    elif mean_b < -5:
        temperature_profile = "cool"
    else:
        temperature_profile = "neutral"

    # --- saturation ----------------------------------------------------------
    saturation = hsv[..., 1]
    saturation_mean = float(saturation.mean())
    saturation_std = float(saturation.std())
    if saturation_mean > 0.55:
        saturation_profile = "punchy"
    elif saturation_mean < 0.30:
        saturation_profile = "muted"
    else:
        saturation_profile = "balanced"

    # --- brightness ----------------------------------------------------------
    lightness = lab_full[..., 0]
    histogram, _ = np.histogram(lightness, bins=32, range=(0, 100))
    clipped_black = float((gray < 5).mean())
    clipped_white = float((gray > 250).mean())

    # --- distinctiveness: mean pairwise ΔE across the palette ----------------
    labs = [np.array(s["lab"]) for s in swatches]
    pairs = [
        delta_e76(labs[i], labs[j])
        for i in range(len(labs))
        for j in range(i + 1, len(labs))
    ]
    distinctiveness = float(np.mean(pairs)) if pairs else 0.0

    return {
        "palette": swatches,
        "harmony": harmony,
        "temperature": {
            "profile": temperature_profile,
            "meanB": round(mean_b, 2),
            "warmRatio": round(warm_ratio, 3),
        },
        "saturation": {
            "mean": round(saturation_mean, 3),
            "std": round(saturation_std, 3),
            "profile": saturation_profile,
        },
        "brightness": {
            "histogram": [int(v) for v in histogram],
            "meanL": round(float(lightness.mean()), 2),
            "clippedBlack": round(clipped_black, 4),
            "clippedWhite": round(clipped_white, 4),
        },
        "distinctiveness": round(distinctiveness, 2),
        "exports": build_exports(swatches),
    }


def build_exports(swatches: list[dict[str, Any]]) -> dict[str, Any]:
    """Ready-to-paste palette exports. Generated from the same swatches — no drift."""
    if not swatches:
        return {"css": "", "tailwind": {}, "ase": {}, "json": "[]"}

    css_lines = [":root {"]
    tailwind: dict[str, str] = {}
    ase_colors: list[dict[str, Any]] = []

    for index, swatch in enumerate(swatches, start=1):
        slug = swatch["name"].lower()
        key = f"thumbiq-{index}-{slug}"
        css_lines.append(f"  --{key}: {swatch['hex']};  /* {swatch['coverage']}% */")
        tailwind[f"{slug}-{index}"] = swatch["hex"]
        red, green, blue = swatch["rgb"]
        ase_colors.append(
            {
                "name": f"{swatch['name']} {index}",
                "model": "RGB",
                "color": [round(red / 255, 6), round(green / 255, 6), round(blue / 255, 6)],
                "type": "global",
            }
        )
    css_lines.append("}")

    return {
        "css": "\n".join(css_lines),
        "tailwind": {"colors": {"thumbiq": tailwind}},
        "ase": {
            "version": "1.0",
            "groups": [{"name": "ThumbIQ palette", "colors": ase_colors}],
        },
        "json": json.dumps([s["hex"] for s in swatches]),
    }
