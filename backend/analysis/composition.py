"""Composition: focal point, thirds, clutter, negative space, balance, depth."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from analysis import saliency as saliency_module

TILE = 16
CLUTTER_THRESHOLD = 0.18
THIRDS = ((1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3))

# Worst possible distance from any point in the frame to the nearest thirds
# intersection — a corner, at hypot(1/3, 1/3). Used to normalise the thirds score.
MAX_THIRDS_DISTANCE = float(np.hypot(1 / 3, 1 / 3))


def _canny(gray: np.ndarray) -> np.ndarray:
    """Canny with thresholds derived from the image's own median — no magic constants."""
    median = float(np.median(gray))
    lower = int(max(0, 0.66 * median))
    upper = int(min(255, 1.33 * median))
    if upper <= lower:
        lower, upper = 50, 150
    return cv2.Canny(gray, lower, upper)


def _normalise(array: np.ndarray) -> np.ndarray:
    low, high = float(array.min()), float(array.max())
    if high - low < 1e-9:
        return np.zeros_like(array, dtype=np.float64)
    return (array.astype(np.float64) - low) / (high - low)


def analyse(rgb: np.ndarray, gray: np.ndarray, hsv: np.ndarray) -> dict[str, Any]:
    height, width = gray.shape[:2]

    saliency_map, backend = saliency_module.compute(gray)
    focal_x, focal_y = saliency_module.centroid(saliency_map)
    concentration = saliency_module.concentration(saliency_map)

    distance = min(float(np.hypot(focal_x - tx, focal_y - ty)) for tx, ty in THIRDS)
    thirds_score = max(0.0, 1.0 - distance / MAX_THIRDS_DISTANCE)

    edges = _canny(gray)
    edge_density = float((edges > 0).mean())

    # --- negative space: quiet tiles, both edge-free and flat -----------------
    # Vectorised over tiles. The equivalent Python double loop runs 3,600 iterations on
    # a 1280x720 frame while holding the GIL, which serialises every concurrent analysis
    # in the pool — it was the single slowest thing in the pipeline.
    gray_f = gray.astype(np.float64)
    tiles_y = max(1, height // TILE)
    tiles_x = max(1, width // TILE)
    crop_h, crop_w = tiles_y * TILE, tiles_x * TILE

    tiled_gray = (
        gray_f[:crop_h, :crop_w]
        .reshape(tiles_y, TILE, tiles_x, TILE)
        .transpose(0, 2, 1, 3)
        .reshape(tiles_y, tiles_x, TILE * TILE)
    )
    tiled_edges = (
        (edges[:crop_h, :crop_w] > 0)
        .reshape(tiles_y, TILE, tiles_x, TILE)
        .transpose(0, 2, 1, 3)
        .reshape(tiles_y, tiles_x, TILE * TILE)
    )

    quiet_mask = (tiled_edges.mean(axis=2) < 0.02) & (tiled_gray.std(axis=2) < 12)
    negative_space = float(quiet_mask.mean()) if quiet_mask.size else 0.0

    # --- visual balance -------------------------------------------------------
    saturation = _normalise(hsv[..., 1])
    edge_weight = _normalise(cv2.GaussianBlur(edges.astype(np.float64), (0, 0), 6))
    mean = cv2.blur(gray_f, (TILE, TILE))
    variance = np.clip(cv2.blur(gray_f * gray_f, (TILE, TILE)) - mean * mean, 0, None)
    local_contrast = _normalise(np.sqrt(variance))

    weight = saturation * local_contrast * edge_weight + 1e-6
    left = float(weight[:, : width // 2].sum())
    right = float(weight[:, width - width // 2 :].sum())
    top = float(weight[: height // 2, :].sum())
    bottom = float(weight[height - height // 2 :, :].sum())

    def balance(a: float, b: float) -> float:
        total = a + b
        return round(1.0 - abs(a - b) / total, 4) if total > 0 else 1.0

    # --- depth: is the background softer than the subject? --------------------
    subject_mask = saliency_map >= np.percentile(saliency_map, 60)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    subject_values = laplacian[subject_mask]
    background_values = laplacian[~subject_mask]
    subject_variance = float(subject_values.var()) if subject_values.size else 0.0
    background_variance = float(background_values.var()) if background_values.size else 0.0
    background_blur = (
        round(1.0 - min(1.0, background_variance / subject_variance), 4)
        if subject_variance > 1e-6
        else 0.0
    )

    return {
        "focalPoint": {"x": focal_x, "y": focal_y},
        "ruleOfThirdsScore": round(thirds_score, 4),
        "thirdsDistance": round(distance, 4),
        "edgeDensity": round(edge_density, 4),
        "cluttered": edge_density > CLUTTER_THRESHOLD,
        "negativeSpace": round(negative_space, 4),
        "balance": {"lr": balance(left, right), "tb": balance(top, bottom)},
        "depth": {
            "backgroundBlur": background_blur,
            "subjectLapVar": round(subject_variance, 2),
            "backgroundLapVar": round(background_variance, 2),
        },
        "saliencyConcentration": concentration,
        "saliencyBackend": backend,
    }
