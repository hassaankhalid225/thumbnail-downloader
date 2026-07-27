"""Fetch the OpenCV model files ThumbIQ's face detector uses.

OpenCV 5 wheels no longer bundle the Haar cascade XML files, and the res10 SSD face
detector was never bundled. Both are downloaded here into ``backend/models/`` so the
runtime never depends on network access.

Run once after install, or let the Dockerfile run it at build time:

    python scripts/fetch_models.py

ThumbIQ still starts and analyses images if this has never been run — the faces module
reports ``available: false`` with the reason, and every other metric is unaffected.
"""

from __future__ import annotations

import hashlib
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

OPENCV_HAAR = "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"
OPENCV_3RDPARTY = (
    "https://raw.githubusercontent.com/opencv/opencv_3rdparty/"
    "dnn_samples_face_detector_20180205_fp16/"
)
OPENCV_DNN_PROTO = (
    "https://raw.githubusercontent.com/opencv/opencv/4.x/samples/dnn/face_detector/"
    "deploy.prototxt"
)
# opencv_zoo stores model weights in git-lfs, so the raw.githubusercontent path returns
# a 131-byte pointer file rather than the model. The /raw/ path resolves the pointer.
OPENCV_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models/"

# (filename, url, required) — required=False means the fallback chain still has an option.
DOWNLOADS: list[tuple[str, str, bool]] = [
    # YuNet is the primary detector: ONNX (the only DNN format OpenCV 5 still imports),
    # 232 KB, and it returns eye landmarks, so the eye-line metric is measured rather
    # than inferred from a second cascade pass.
    ("face_detection_yunet_2023mar.onnx", OPENCV_ZOO + "face_detection_yunet/face_detection_yunet_2023mar.onnx", True),
    # res10 Caffe — only usable on OpenCV 4.x, which still has the Caffe importer.
    ("res10_300x300_ssd_iter_140000_fp16.caffemodel", OPENCV_3RDPARTY + "res10_300x300_ssd_iter_140000_fp16.caffemodel", False),
    ("deploy.prototxt", OPENCV_DNN_PROTO, False),
    ("haarcascade_frontalface_default.xml", OPENCV_HAAR + "haarcascade_frontalface_default.xml", True),
    ("haarcascade_profileface.xml", OPENCV_HAAR + "haarcascade_profileface.xml", False),
    ("haarcascade_eye.xml", OPENCV_HAAR + "haarcascade_eye.xml", False),
    ("haarcascade_smile.xml", OPENCV_HAAR + "haarcascade_smile.xml", False),
]

USER_AGENT = "ThumbIQ-model-fetch/1.0"


def _download(url: str, dest: Path, attempts: int = 3) -> int:
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            if len(payload) < 1024:
                raise ValueError(f"suspiciously small response ({len(payload)} bytes)")
            dest.write_bytes(payload)
            return len(payload)
        except (urllib.error.URLError, socket.timeout, ValueError) as exc:  # noqa: PERF203
            last = exc
            print(f"    attempt {attempt + 1}/{attempts} failed: {exc}", file=sys.stderr)
    raise RuntimeError(f"could not download {url}") from last


def main() -> int:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for name, url, required in DOWNLOADS:
        dest = MODELS_DIR / name
        if dest.exists() and dest.stat().st_size > 1024:
            digest = hashlib.sha256(dest.read_bytes()).hexdigest()[:12]
            print(f"  = {name} already present ({dest.stat().st_size:,} bytes, sha256:{digest})")
            continue
        print(f"  ↓ {name}")
        try:
            size = _download(url, dest)
            print(f"    saved {size:,} bytes")
        except RuntimeError as exc:
            print(f"    {exc}", file=sys.stderr)
            failures.append(name)
            if required:
                print(
                    "    this one drives the Haar fallback — face detection will report "
                    "available: false until it is fetched",
                    file=sys.stderr,
                )

    print(f"\nModels directory: {MODELS_DIR}")
    if failures:
        print(f"Missing: {', '.join(failures)}")
        print("ThumbIQ still runs; the faces module degrades and says so.")
        return 1
    print("All models present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
