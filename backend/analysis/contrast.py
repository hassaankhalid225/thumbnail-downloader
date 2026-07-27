"""WCAG 2.1 contrast, implemented to the letter of the spec.

Anchors that must hold, and are asserted in the test suite:
  black on white          → 21.00
  #767676 on white        → 4.54  (the canonical AA boundary example)
  mid-grey on itself      → 1.00
"""

from __future__ import annotations

import cv2
import numpy as np

TILE = 16


def srgb_to_linear(channel: np.ndarray) -> np.ndarray:
    """sRGB [0,1] → linear light. The 0.04045 knee is part of the standard."""
    return np.where(
        channel <= 0.04045,
        channel / 12.92,
        np.power((channel + 0.055) / 1.055, 2.4),
    )


def relative_luminance(rgb: np.ndarray) -> np.ndarray:
    """WCAG relative luminance for an RGB array of any shape ending in 3.

    Accepts uint8 (0–255) or float (0–1).
    """
    array = np.asarray(rgb, dtype=np.float64)
    if array.max() > 1.0:
        array = array / 255.0
    linear = srgb_to_linear(array)
    return (
        0.2126 * linear[..., 0] + 0.7152 * linear[..., 1] + 0.0722 * linear[..., 2]
    )


def contrast_ratio(color_a, color_b) -> float:
    """WCAG contrast ratio between two RGB colors. Range 1.0 … 21.0."""
    luminance_a = float(relative_luminance(np.asarray(color_a, dtype=np.float64).reshape(1, 3))[0])
    luminance_b = float(relative_luminance(np.asarray(color_b, dtype=np.float64).reshape(1, 3))[0])
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def passes_aa(ratio: float, large_text: bool = False) -> bool:
    return ratio >= (3.0 if large_text else 4.5)


def passes_aaa(ratio: float, large_text: bool = False) -> bool:
    return ratio >= (4.5 if large_text else 7.0)


def analyse(rgb: np.ndarray, gray: np.ndarray) -> dict:
    """Global and local contrast for the whole frame."""
    luminance = relative_luminance(rgb)
    p5, p95 = np.percentile(luminance, [5, 95])
    global_contrast = float(p95 - p5)

    # Local contrast: standard deviation inside 16x16 tiles. Computed with a box filter
    # rather than a Python loop — sqrt(E[x²] − E[x]²).
    gray_f = gray.astype(np.float64)
    mean = cv2.blur(gray_f, (TILE, TILE))
    mean_of_squares = cv2.blur(gray_f * gray_f, (TILE, TILE))
    variance = np.clip(mean_of_squares - mean * mean, 0, None)
    local = np.sqrt(variance)

    return {
        "globalContrast": round(global_contrast, 4),
        "rmsContrast": round(float(luminance.std()), 4),
        "localContrast": {
            "mean": round(float(local.mean()), 2),
            "max": round(float(local.max()), 2),
            "p90": round(float(np.percentile(local, 90)), 2),
        },
        "luminance": {
            "mean": round(float(luminance.mean()), 4),
            "p5": round(float(p5), 4),
            "p95": round(float(p95), 4),
        },
    }
