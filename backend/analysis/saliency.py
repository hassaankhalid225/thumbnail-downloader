"""Spectral-residual saliency (Hou & Zhang, CVPR 2007).

Shared by ``composition.py`` (focal point, balance, depth) and ``imaging.py`` (anchoring
the crop for non-16:9 renditions, so a 9:16 export keeps the subject instead of slicing
through it).

Uses ``cv2.saliency.StaticSaliencySpectralResidual`` when the contrib module is present.
The NumPy path is the same algorithm implemented directly, so the two agree to within
float noise and the module never becomes a hard dependency.
"""

from __future__ import annotations

import cv2
import numpy as np

WORKING_SIZE = 64  # the resolution the original paper operates at


def _numpy_spectral_residual(gray: np.ndarray) -> np.ndarray:
    small = cv2.resize(gray, (WORKING_SIZE, WORKING_SIZE), interpolation=cv2.INTER_AREA)
    spectrum = np.fft.fft2(small.astype(np.float64))
    amplitude = np.abs(spectrum)
    phase = np.angle(spectrum)

    log_amplitude = np.log1p(amplitude)
    averaged = cv2.blur(log_amplitude, (3, 3))
    residual = log_amplitude - averaged

    reconstructed = np.fft.ifft2(np.exp(residual + 1j * phase))
    saliency = np.abs(reconstructed) ** 2
    saliency = cv2.GaussianBlur(saliency, (0, 0), sigmaX=2.5)
    return saliency


def compute(gray: np.ndarray) -> tuple[np.ndarray, str]:
    """Return a float32 saliency map in [0, 1] at the input resolution, plus the backend."""
    height, width = gray.shape[:2]
    backend = "numpy_spectral_residual"

    small: np.ndarray | None = None
    if hasattr(cv2, "saliency"):
        try:
            detector = cv2.saliency.StaticSaliencySpectralResidual_create()
            ok, raw = detector.computeSaliency(gray)
            if ok and raw is not None:
                small = np.asarray(raw, dtype=np.float64)
                backend = "cv2.saliency"
        except cv2.error:
            small = None

    if small is None:
        small = _numpy_spectral_residual(gray)

    resized = cv2.resize(small, (width, height), interpolation=cv2.INTER_LINEAR)
    low, high = float(resized.min()), float(resized.max())
    if high - low < 1e-12:
        return np.zeros((height, width), dtype=np.float32), backend
    normalized = (resized - low) / (high - low)
    return normalized.astype(np.float32), backend


def centroid(saliency: np.ndarray, percentile: float = 80.0) -> tuple[float, float]:
    """Intensity-weighted centroid of the top ``100 - percentile``% of saliency mass.

    Thresholding first matters: an unthresholded centroid on a diffuse map always drifts
    to the middle of the frame, which would score every thumbnail as centre-weighted.
    """
    threshold = float(np.percentile(saliency, percentile))
    mask = saliency >= threshold
    weights = np.where(mask, saliency, 0.0).astype(np.float64)
    total = float(weights.sum())
    if total <= 0:
        return (0.5, 0.5)

    height, width = saliency.shape
    ys, xs = np.mgrid[0:height, 0:width]
    x = float((weights * xs).sum() / total) / max(width - 1, 1)
    y = float((weights * ys).sum() / total) / max(height - 1, 1)
    return (round(min(max(x, 0.0), 1.0), 4), round(min(max(y, 0.0), 1.0), 4))


def concentration(saliency: np.ndarray, area_fraction: float = 0.20) -> float:
    """Fraction of total saliency mass held by the brightest ``area_fraction`` of pixels.

    High values mean one clear subject; low values mean the eye has nowhere to land.
    """
    flat = saliency.reshape(-1).astype(np.float64)
    total = float(flat.sum())
    if total <= 0:
        return 0.0
    count = max(1, int(flat.size * area_fraction))
    top = np.partition(flat, -count)[-count:]
    return round(float(top.sum() / total), 4)
