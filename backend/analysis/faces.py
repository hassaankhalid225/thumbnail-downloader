"""Face detection and the engagement geometry that follows from it.

Detector preference, best first:
  1. **YuNet** (``face_detection_yunet_2023mar.onnx``) — the strongest option available,
     and the only DNN format OpenCV 5 still imports. It also returns eye landmarks, so
     the eye-line metric is a direct measurement rather than a second cascade pass.
  2. ``res10_300x300_ssd`` Caffe DNN — only loadable on OpenCV 4.x, which still has the
     Caffe importer. Kept for deployments pinned to 4.x.
  3. Haar cascades, frontal + profile, merged by NMS. No download beyond the XML files.
  4. nothing — reported honestly as ``available: false``

The response always names which backend ran. A score built on a Haar detection and a
score built on a DNN detection are not the same evidence, and pretending otherwise
would be dishonest.

Expression is an **estimate** derived from geometry (smile cascade, mouth-open ratio,
eye-open ratio) and is labelled as such everywhere it surfaces. It is not a trained
expression classifier and never claims to be.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from config import settings

DNN_CONFIDENCE = 0.55
NMS_IOU = 0.35

QUADRANTS = (
    ("top-left", "top-center", "top-right"),
    ("left-center", "center", "right-center"),
    ("bottom-left", "bottom-center", "bottom-right"),
)


@lru_cache(maxsize=1)
def _yunet_path() -> Path | None:
    path = settings.models_dir / "face_detection_yunet_2023mar.onnx"
    if not path.is_file() or path.stat().st_size < 100_000:
        return None
    if not hasattr(cv2, "FaceDetectorYN"):
        return None
    return path


@lru_cache(maxsize=1)
def _dnn() -> Any | None:
    """res10 Caffe SSD. OpenCV 5 removed the Caffe importer, so this is 4.x-only."""
    directory: Path = settings.models_dir
    prototxt = directory / "deploy.prototxt"
    weights = directory / "res10_300x300_ssd_iter_140000_fp16.caffemodel"
    if not (prototxt.is_file() and weights.is_file()):
        return None
    if not hasattr(cv2.dnn, "readNetFromCaffe"):
        return None
    try:
        return cv2.dnn.readNetFromCaffe(str(prototxt), str(weights))
    except (cv2.error, AttributeError):
        return None


@lru_cache(maxsize=8)
def _cascade(name: str) -> Any | None:
    """Load a cascade from backend/models/ first, then OpenCV's bundled data dir."""
    candidates = [settings.models_dir / name]
    try:
        candidates.append(Path(cv2.data.haarcascades) / name)
    except AttributeError:
        pass
    for path in candidates:
        if path.is_file():
            classifier = cv2.CascadeClassifier(str(path))
            if not classifier.empty():
                return classifier
    return None


def detector_name() -> str:
    if _yunet_path() is not None:
        return "yunet"
    if _dnn() is not None:
        return "dnn_res10"
    if _cascade("haarcascade_frontalface_default.xml") is not None:
        return "haar_cascade"
    return "unavailable"


def _detect_yunet(rgb: np.ndarray) -> list[tuple[int, int, int, int, float, dict | None]]:
    """YuNet detection. Returns landmarks alongside each box when available."""
    path = _yunet_path()
    if path is None:
        return []
    height, width = rgb.shape[:2]
    try:
        detector = cv2.FaceDetectorYN.create(
            str(path), "", (width, height), DNN_CONFIDENCE, 0.3, 5000
        )
        detector.setInputSize((width, height))
        _, raw = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    except (cv2.error, AttributeError):
        return []

    if raw is None:
        return []

    found: list[tuple[int, int, int, int, float, dict | None]] = []
    for row in raw:
        x, y, w, h = (int(round(float(v))) for v in row[:4])
        confidence = float(row[-1])
        x, y = max(0, x), max(0, y)
        w = min(w, width - x)
        h = min(h, height - y)
        if w < 8 or h < 8:
            continue
        # Columns 4..13 are right-eye, left-eye, nose, right mouth, left mouth (x, y).
        landmarks = {
            "rightEye": [float(row[4]), float(row[5])],
            "leftEye": [float(row[6]), float(row[7])],
            "nose": [float(row[8]), float(row[9])],
            "mouthRight": [float(row[10]), float(row[11])],
            "mouthLeft": [float(row[12]), float(row[13])],
        }
        found.append((x, y, w, h, confidence, landmarks))
    return found


def _nms(boxes: list[tuple[int, int, int, int, float]]) -> list[tuple[int, int, int, int, float]]:
    ordered = sorted(boxes, key=lambda b: b[4], reverse=True)
    kept: list[tuple[int, int, int, int, float]] = []
    for box in ordered:
        if all(_iou(box[:4], other[:4]) < NMS_IOU for other in kept):
            kept.append(box)
    return kept


def _iou(a, b) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = ix * iy
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


def _detect_dnn(rgb: np.ndarray) -> list[tuple[int, int, int, int, float]]:
    net = _dnn()
    if net is None:
        return []
    height, width = rgb.shape[:2]
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    blob = cv2.dnn.blobFromImage(
        cv2.resize(bgr, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
    )
    net.setInput(blob)
    detections = net.forward()

    found: list[tuple[int, int, int, int, float]] = []
    for index in range(detections.shape[2]):
        confidence = float(detections[0, 0, index, 2])
        if confidence < DNN_CONFIDENCE:
            continue
        box = detections[0, 0, index, 3:7] * np.array([width, height, width, height])
        x1, y1, x2, y2 = (int(round(v)) for v in box)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)
        if x2 - x1 < 8 or y2 - y1 < 8:
            continue
        found.append((x1, y1, x2 - x1, y2 - y1, confidence))
    return _nms(found)


def _detect_haar(gray: np.ndarray) -> list[tuple[int, int, int, int, float]]:
    height, width = gray.shape[:2]
    minimum = max(24, int(min(height, width) * 0.06))
    equalised = cv2.equalizeHist(gray)

    found: list[tuple[int, int, int, int, float]] = []
    for name, confidence in (
        ("haarcascade_frontalface_default.xml", 0.70),
        ("haarcascade_profileface.xml", 0.55),
    ):
        classifier = _cascade(name)
        if classifier is None:
            continue
        detections = classifier.detectMultiScale(
            equalised, scaleFactor=1.1, minNeighbors=6, minSize=(minimum, minimum)
        )
        for x, y, w, h in detections:
            found.append((int(x), int(y), int(w), int(h), confidence))

    # Profile faces on a mirrored copy catch heads turned the other way.
    profile = _cascade("haarcascade_profileface.xml")
    if profile is not None:
        flipped = cv2.flip(equalised, 1)
        for x, y, w, h in profile.detectMultiScale(
            flipped, scaleFactor=1.1, minNeighbors=6, minSize=(minimum, minimum)
        ):
            found.append((int(width - x - w), int(y), int(w), int(h), 0.50))

    return _nms(found)


def _eye_line(gray: np.ndarray, box: tuple[int, int, int, int]) -> float | None:
    """Mean eye-centre y as a fraction of the frame. None when eyes aren't resolvable."""
    classifier = _cascade("haarcascade_eye.xml")
    if classifier is None:
        return None
    x, y, w, h = box
    roi = gray[y : y + int(h * 0.65), x : x + w]
    if roi.size == 0 or min(roi.shape[:2]) < 20:
        return None
    eyes = classifier.detectMultiScale(
        cv2.equalizeHist(roi), scaleFactor=1.1, minNeighbors=6,
        minSize=(max(8, w // 12), max(8, h // 14)),
    )
    if len(eyes) == 0:
        return None
    centres = [y + ey + eh / 2 for ex, ey, ew, eh in eyes]
    return float(np.mean(centres)) / gray.shape[0]


def _expression(
    gray: np.ndarray,
    box: tuple[int, int, int, int],
    landmarks: dict | None = None,
    frame: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Geometric expression estimate. Labelled an estimate wherever it appears."""
    x, y, w, h = box
    face = gray[y : y + h, x : x + w]
    if face.size == 0 or min(face.shape[:2]) < 30:
        return _unknown_expression()

    smile = _cascade("haarcascade_smile.xml")
    smiling = False
    if smile is not None:
        lower = face[int(h * 0.55) :, :]
        if lower.size and min(lower.shape[:2]) >= 12:
            hits = smile.detectMultiScale(
                cv2.equalizeHist(lower), scaleFactor=1.2, minNeighbors=22,
                minSize=(max(10, w // 5), max(6, h // 10)),
            )
            smiling = len(hits) > 0

    # Mouth-open proxy: edge energy in the mouth band relative to the cheek band above
    # it. An open mouth is a dark aperture with strong horizontal edges; a closed one is
    # quiet. When YuNet gave landmarks the band is placed on the measured mouth corners
    # instead of a fixed fraction of the face box.
    edges = cv2.Canny(cv2.equalizeHist(face), 60, 160)
    mouth_top, mouth_bottom = int(h * 0.62), int(h * 0.92)
    mouth_left, mouth_right = int(w * 0.25), int(w * 0.75)
    if landmarks:
        mouth_y = (landmarks["mouthLeft"][1] + landmarks["mouthRight"][1]) / 2 - y
        mouth_half = abs(landmarks["mouthLeft"][0] - landmarks["mouthRight"][0]) / 2
        mouth_centre_x = (landmarks["mouthLeft"][0] + landmarks["mouthRight"][0]) / 2 - x
        if 0 < mouth_y < h and mouth_half > 2:
            mouth_top = max(0, int(mouth_y - mouth_half * 0.6))
            mouth_bottom = min(h, int(mouth_y + mouth_half * 0.6))
            mouth_left = max(0, int(mouth_centre_x - mouth_half * 1.1))
            mouth_right = min(w, int(mouth_centre_x + mouth_half * 1.1))

    lower_band = edges[mouth_top:mouth_bottom, mouth_left:mouth_right]
    mid_band = edges[int(h * 0.35) : int(h * 0.60), int(w * 0.25) : int(w * 0.75)]
    lower_energy = float((lower_band > 0).mean()) if lower_band.size else 0.0
    mid_energy = float((mid_band > 0).mean()) if mid_band.size else 1e-6
    mouth_open = lower_energy / max(mid_energy, 1e-6)

    # Eye-open proxy: vertical extent of the detected eye boxes relative to face height.
    eye_classifier = _cascade("haarcascade_eye.xml")
    eye_openness = 0.0
    if eye_classifier is not None:
        upper = face[: int(h * 0.6), :]
        if upper.size and min(upper.shape[:2]) >= 12:
            eyes = eye_classifier.detectMultiScale(
                cv2.equalizeHist(upper), scaleFactor=1.1, minNeighbors=6,
                minSize=(max(8, w // 12), max(6, h // 14)),
            )
            if len(eyes):
                eye_openness = float(np.mean([eh for _, _, _, eh in eyes])) / h
    elif landmarks:
        # No eye cascade available: use the eye-to-mouth vertical span as a weak proxy
        # for how wide-open the face reads. Reported the same way — as an estimate.
        eye_y = (landmarks["rightEye"][1] + landmarks["leftEye"][1]) / 2
        mouth_y = (landmarks["mouthLeft"][1] + landmarks["mouthRight"][1]) / 2
        eye_openness = min(0.3, abs(mouth_y - eye_y) / max(h, 1) * 0.35)

    if mouth_open > 1.9 and eye_openness > 0.14:
        label, confidence = "surprise", min(0.85, 0.40 + (mouth_open - 1.9) * 0.20)
    elif smiling:
        label, confidence = "joy", 0.70 if mouth_open > 1.3 else 0.55
    elif mouth_open > 1.6 and eye_openness <= 0.14:
        label, confidence = "anger", 0.45
    else:
        label, confidence = "neutral", 0.50

    return {
        "label": label,
        "confidence": round(float(min(confidence, 0.9)), 2),
        "method": "geometric-estimate",
        "signals": {
            "smileCascadeHit": smiling,
            "mouthOpenRatio": round(mouth_open, 2),
            "eyeOpenRatio": round(eye_openness, 3),
        },
        "disclaimer": "Estimated from facial geometry, not a trained expression classifier.",
    }


def _unknown_expression() -> dict[str, Any]:
    return {
        "label": None,
        "confidence": 0.0,
        "method": "geometric-estimate",
        "signals": {},
        "disclaimer": "Face too small to estimate an expression from.",
    }


def _quadrant(cx: float, cy: float) -> str:
    col = min(2, max(0, int(cx * 3)))
    row = min(2, max(0, int(cy * 3)))
    return QUADRANTS[row][col]


def analyse(rgb: np.ndarray, gray: np.ndarray) -> dict[str, Any]:
    backend = detector_name()
    if backend == "unavailable":
        return {
            "available": False,
            "detector": "unavailable",
            "count": 0,
            "faces": [],
            "note": "No face-detection model found. Run scripts/fetch_models.py to enable it.",
        }

    if backend == "yunet":
        boxes = _detect_yunet(rgb)
    elif backend == "dnn_res10":
        boxes = [(*box, None) for box in _detect_dnn(rgb)]
    else:
        boxes = [(*box, None) for box in _detect_haar(gray)]

    height, width = gray.shape[:2]
    frame_area = height * width

    faces: list[dict[str, Any]] = []
    for x, y, w, h, confidence, landmarks in boxes:
        cx = (x + w / 2) / width
        cy = (y + h / 2) / height

        # YuNet gives the eye positions directly; without it, fall back to the cascade.
        if landmarks:
            eye_line = (landmarks["rightEye"][1] + landmarks["leftEye"][1]) / 2 / height
        else:
            eye_line = _eye_line(gray, (x, y, w, h))

        faces.append(
            {
                "bbox": {
                    "x": round(x / width, 4),
                    "y": round(y / height, 4),
                    "w": round(w / width, 4),
                    "h": round(h / height, 4),
                },
                "bboxPx": {"x": x, "y": y, "w": w, "h": h},
                "confidence": round(confidence, 2),
                "areaPercent": round(w * h / frame_area * 100, 2),
                "quadrant": _quadrant(cx, cy),
                "eyeLineY": round(eye_line, 4) if eye_line is not None else None,
                "eyeLineUpperThird": (eye_line < 1 / 3) if eye_line is not None else None,
                "eyeLineSource": "landmarks" if landmarks else ("cascade" if eye_line is not None else None),
                "landmarks": (
                    {
                        key: [round(px / width, 4), round(py / height, 4)]
                        for key, (px, py) in landmarks.items()
                    }
                    if landmarks
                    else None
                ),
                "expression": _expression(gray, (x, y, w, h), landmarks, (width, height)),
            }
        )

    faces.sort(key=lambda f: f["areaPercent"], reverse=True)

    notes = {
        "yunet": None,
        "dnn_res10": None,
        "haar_cascade": (
            "Haar cascade fallback in use — less reliable on angled or partly occluded "
            "faces than the DNN detectors. Run scripts/fetch_models.py to enable YuNet."
        ),
    }

    return {
        "available": True,
        "detector": backend,
        "count": len(faces),
        "faces": faces,
        "note": notes.get(backend),
    }
