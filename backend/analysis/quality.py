"""Technical quality: sharpness, noise, compression artifacts, spec compliance."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

# YouTube's published thumbnail recommendation.
SPEC_MIN_WIDTH = 1280
SPEC_MIN_HEIGHT = 720
SPEC_MAX_BYTES = 2 * 1024 * 1024
SPEC_ASPECT = 16 / 9
ASPECT_TOLERANCE = 0.01

# Immerkær's noise-estimation kernel.
_NOISE_KERNEL = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)


def estimate_noise(gray: np.ndarray) -> float:
    """Immerkær (1996) fast noise variance estimate, normalised to 0–1."""
    height, width = gray.shape[:2]
    if height < 4 or width < 4:
        return 0.0
    convolved = cv2.filter2D(gray.astype(np.float64), -1, _NOISE_KERNEL)
    sigma = float(np.abs(convolved).sum())
    sigma *= np.sqrt(0.5 * np.pi) / (6.0 * (width - 2) * (height - 2))
    return float(min(1.0, sigma / 255.0))


def block_artifact_ratio(gray: np.ndarray) -> float:
    """Gradient energy on 8-px JPEG block boundaries vs. everywhere else.

    A cleanly encoded image has no reason for its gradients to prefer multiples of 8.
    A heavily re-compressed one does, and the ratio climbs above 1.
    """
    height, width = gray.shape[:2]
    if height < 24 or width < 24:
        return 1.0

    gray_f = gray.astype(np.float64)
    horizontal = np.abs(np.diff(gray_f, axis=1))
    vertical = np.abs(np.diff(gray_f, axis=0))

    columns = np.arange(horizontal.shape[1])
    rows = np.arange(vertical.shape[0])
    boundary_columns = (columns + 1) % 8 == 0
    boundary_rows = (rows + 1) % 8 == 0

    boundary = np.concatenate(
        [horizontal[:, boundary_columns].ravel(), vertical[boundary_rows, :].ravel()]
    )
    interior = np.concatenate(
        [horizontal[:, ~boundary_columns].ravel(), vertical[~boundary_rows, :].ravel()]
    )
    if boundary.size == 0 or interior.size == 0:
        return 1.0
    interior_mean = float(interior.mean())
    if interior_mean < 1e-6:
        return 1.0
    return float(boundary.mean() / interior_mean)


def analyse(
    gray: np.ndarray, width: int, height: int, byte_size: int, image_format: str | None
) -> dict[str, Any]:
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    noise = estimate_noise(gray)
    ratio = block_artifact_ratio(gray)

    if ratio < 1.15:
        artifacts = "low"
    elif ratio < 1.45:
        artifacts = "medium"
    else:
        artifacts = "high"

    aspect_value = width / height if height else 0.0
    aspect_ok = abs(aspect_value - SPEC_ASPECT) / SPEC_ASPECT <= ASPECT_TOLERANCE

    notes: list[str] = []
    if width < SPEC_MIN_WIDTH or height < SPEC_MIN_HEIGHT:
        notes.append(
            f"{width}×{height} is below YouTube's recommended 1280×720 minimum."
        )
    if not aspect_ok:
        notes.append(
            f"Aspect ratio is {aspect_value:.3f}:1, not 16:9 — YouTube will letterbox or crop."
        )
    if byte_size > SPEC_MAX_BYTES:
        notes.append(
            f"{byte_size / 1_048_576:.1f} MB exceeds YouTube's 2 MB upload limit."
        )
    if sharpness < 100:
        notes.append("Low Laplacian variance — the image reads as soft or out of focus.")
    if artifacts == "high":
        notes.append("Strong 8×8 block edges — this has been re-compressed several times.")

    return {
        "sharpness": round(sharpness, 2),
        "sharpnessVerdict": "soft" if sharpness < 100 else "acceptable" if sharpness < 300 else "crisp",
        "noise": round(noise, 4),
        "compressionArtifacts": artifacts,
        "blockRatio": round(ratio, 3),
        "width": width,
        "height": height,
        "bytes": byte_size,
        "format": image_format,
        "aspect": f"{aspect_value:.3f}:1",
        "aspectIs16x9": aspect_ok,
        "meetsYouTubeSpec": (
            width >= SPEC_MIN_WIDTH
            and height >= SPEC_MIN_HEIGHT
            and aspect_ok
            and byte_size <= SPEC_MAX_BYTES
        ),
        "specNotes": notes,
    }
