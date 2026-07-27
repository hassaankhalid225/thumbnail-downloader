"""Text detection, measurement and legibility.

Two layers, so this tab keeps working when Tesseract is not installed:

**Layer A — geometric localisation.** MSER regions filtered by area, aspect, fill and
stroke-width consistency. Finds *where* the text is, always, with no external binary.

**Layer B — recognition.** Tesseract at ``--psm 11`` and ``--psm 6``, merged. Reads
*what* the text says. Optional.

``textSource`` reports which layer produced the blocks, so the UI never implies ThumbIQ
read words it only saw the shape of.

Cap height is measured, not assumed: the word is binarised, the ink row profile is built,
and the baseline is the lowest row still carrying 15% of peak ink. `capHeight = baseline
− first ink row`. Descenders sit below the baseline and are correctly excluded.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import cv2
import numpy as np
from PIL import Image

from analysis import fonts
from analysis.contrast import contrast_ratio, passes_aa
from config import settings

# YouTube's real rendered sizes. Measured from the live product, not invented.
SURFACES: tuple[tuple[str, str, int, int], ...] = (
    ("mobile_feed", "Mobile feed", 168, 94),
    ("mobile_search", "Mobile search", 246, 138),
    ("desktop_grid", "Desktop home grid", 360, 202),
    ("desktop_sidebar", "Desktop sidebar", 168, 94),
    ("watch_page", "Watch page", 1280, 720),
)

CAP_HEIGHT_FAIL = 10.0
CAP_HEIGHT_WARN = 14.0

OCR_UPSCALE_TARGET = 1000  # Tesseract's accuracy collapses on small input
QUADRANTS = (
    ("top-left", "top-center", "top-right"),
    ("middle-left", "center", "middle-right"),
    ("bottom-left", "bottom-center", "bottom-right"),
)
THIRDS = ((1 / 3, 1 / 3), (2 / 3, 1 / 3), (1 / 3, 2 / 3), (2 / 3, 2 / 3))


@dataclass(slots=True)
class Word:
    x: int
    y: int
    w: int
    h: int
    text: str = ""
    confidence: float = 0.0
    source: str = "geometric"
    cap_height: float = 0.0

    @property
    def box(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.w, self.h)

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass(slots=True)
class Block:
    words: list[Word] = field(default_factory=list)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        xs = [w.x for w in self.words]
        ys = [w.y for w in self.words]
        x2 = max(w.x + w.w for w in self.words)
        y2 = max(w.y + w.h for w in self.words)
        x1, y1 = min(xs), min(ys)
        return (x1, y1, x2 - x1, y2 - y1)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words if w.text).strip()

    @property
    def cap_height(self) -> float:
        heights = [w.cap_height for w in self.words if w.cap_height > 0]
        return max(heights) if heights else 0.0


# --------------------------------------------------------------------------------
# Tesseract availability
# --------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def tesseract_info() -> dict[str, Any]:
    """Detect Tesseract once. Never raises — a missing binary is a state, not a crash."""
    import pytesseract

    command = settings.tesseract_cmd or shutil.which("tesseract")
    if not command:
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
        ):
            if shutil.which(candidate) or _exists(candidate):
                command = candidate
                break

    if not command:
        return {"available": False, "version": None, "path": None}

    pytesseract.pytesseract.tesseract_cmd = command
    try:
        version = str(pytesseract.get_tesseract_version()).split()[0]
    except Exception:
        try:
            output = subprocess.run(
                [command, "--version"], capture_output=True, text=True, timeout=10, check=False
            )
            version = output.stdout.splitlines()[0].split()[-1] if output.stdout else "unknown"
        except Exception:
            return {"available": False, "version": None, "path": command}
    return {"available": True, "version": version, "path": command}


def _exists(path: str) -> bool:
    from pathlib import Path

    return Path(path).is_file()


# --------------------------------------------------------------------------------
# Layer A — geometric localisation (MSER + stroke-width filtering)
# --------------------------------------------------------------------------------


def _stroke_width_stats(mask: np.ndarray) -> tuple[float, float]:
    """Mean and relative std of stroke width, from the distance transform of the ink.

    Text has near-constant stroke width; a leaf, a face, or a gradient does not. This is
    the single most effective non-OCR text filter.
    """
    if mask.size == 0 or not mask.any():
        return (0.0, 1.0)
    distance = cv2.distanceTransform(mask, cv2.DIST_L2, 3)
    ridge = distance[distance > 0.6 * distance.max()] if distance.max() > 0 else np.array([])
    if ridge.size < 3:
        return (0.0, 1.0)
    mean = float(ridge.mean()) * 2.0
    std = float(ridge.std()) * 2.0
    return (mean, std / mean if mean > 1e-6 else 1.0)


def _binarizations(gray: np.ndarray) -> list[np.ndarray]:
    """Four binary views: Otsu and adaptive-mean, each in both polarities.

    Two thresholds because they fail in opposite situations. Otsu is exactly right for
    the flat, high-contrast text a thumbnail actually uses, and useless across a gradient
    background. Adaptive-mean handles the gradient and produces noise on flat fields.
    Both polarities because thumbnail text is as often light-on-dark as dark-on-light.
    """
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    views: list[np.ndarray] = []

    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    views.append(otsu)
    views.append(cv2.bitwise_not(otsu))

    height, width = gray.shape[:2]
    block = max(15, (min(height, width) // 12) | 1)  # odd, and scaled to the image
    adaptive = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, block, 8
    )
    views.append(adaptive)
    views.append(cv2.bitwise_not(adaptive))
    return views


def detect_regions(gray: np.ndarray) -> list[Word]:
    """Glyph-shaped connected components, filtered to what letterforms look like.

    Connected components rather than MSER: OpenCV 5's MSER returns nothing at all on
    flat, high-contrast synthetic input (verified — it finds zero regions on a white
    rectangle against a dark field), which is precisely the kind of image a thumbnail
    headline is. Components over a pair of thresholds are predictable, testable, and
    behave the same on a poster and on a photograph.
    """
    height, width = gray.shape[:2]
    frame_area = height * width
    min_area = max(20, int(frame_area * 4e-6))
    max_area = int(frame_area * 0.05)

    # The shape filter runs vectorised over the whole stats array. A photograph can
    # produce tens of thousands of components per binarisation, and a Python loop over
    # them holds the GIL long enough to serialise every other analysis in the pool.
    candidates: list[tuple[int, int, int, int, int]] = []
    for binary in _binarizations(gray):
        count, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
        if count <= 1:
            continue
        boxes = stats[1:]  # row 0 is the background component
        x = boxes[:, cv2.CC_STAT_LEFT]
        y = boxes[:, cv2.CC_STAT_TOP]
        w = boxes[:, cv2.CC_STAT_WIDTH]
        h = boxes[:, cv2.CC_STAT_HEIGHT]
        area = boxes[:, cv2.CC_STAT_AREA]

        with np.errstate(divide="ignore", invalid="ignore"):
            aspect = np.where(h > 0, w / np.maximum(h, 1), 0.0)

        keep = (
            (area >= min_area)
            & (area <= max_area)
            & (w >= 3)
            & (h >= 6)
            & (aspect >= 0.08)
            & (aspect <= 12)
            & (h <= height * 0.75)
            & (w <= width * 0.92)
        )
        if not keep.any():
            continue
        candidates.extend(
            (int(a), int(b), int(c), int(d), int(e))
            for a, b, c, d, e in zip(x[keep], y[keep], w[keep], h[keep], area[keep])
        )

    # The stroke-width transform below is the expensive step. Display text is always
    # among the larger components, so bound the work at the largest 500.
    candidates.sort(key=lambda c: c[4], reverse=True)
    candidates = candidates[:500]

    kept: list[Word] = []
    for x, y, w, h, area in candidates:
        fill = area / (w * h)
        stem_like = aspect_is_stem(w, h)
        # A glyph's ink covers part of its box. A completely filled box is a shape, not a
        # letter — unless it's stem-shaped, which is what an I or a bar actually is.
        if fill > 0.92 and not stem_like:
            continue
        if fill < 0.10:
            continue

        crop = gray[y : y + h, x : x + w]
        if crop.size == 0:
            continue
        mask = _ink_mask(crop)
        _, relative_std = _stroke_width_stats(mask)
        if relative_std > 0.62:
            continue

        kept.append(Word(x=x, y=y, w=w, h=h, source="geometric", confidence=60.0))

    return _merge_overlaps(kept)


def aspect_is_stem(w: int, h: int) -> bool:
    """True for the narrow bar shapes that letters like I, l and 1 genuinely are."""
    if h == 0 or w == 0:
        return False
    aspect = w / h
    return aspect < 0.35 or aspect > 3.0


def _merge_overlaps(words: list[Word], iou_threshold: float = 0.5) -> list[Word]:
    """Collapse duplicate detections of the same glyph, and discard line-blobs.

    Two things have to be told apart, and containment alone cannot do it:

    * the *same glyph* found by two different thresholds — near-identical boxes, high IoU
    * a *whole line* found as one component because a threshold bled the letters together
      — a big box that fully contains several glyph boxes

    Deduping by IoU keeps glyph-level detections (a line-blob has low IoU with each
    letter inside it). Then any region that swallows two or more surviving regions is
    dropped as a blob. Keeping the outermost box instead would erase the line's letters
    and leave one shapeless rectangle, which fails every downstream measurement.
    """
    if not words:
        return []

    ordered = sorted(words, key=lambda w: w.w * w.h)  # smallest first — glyph level wins
    kept: list[Word] = []
    for word in ordered:
        if any(_iou(word.box, other.box) > iou_threshold for other in kept):
            continue
        kept.append(word)

    final: list[Word] = []
    for word in kept:
        swallowed = sum(
            1
            for other in kept
            if other is not word and _contains(word.box, other.box)
        )
        if swallowed >= 2:
            continue
        final.append(word)
    return final


def _contains(outer: tuple[int, int, int, int], inner: tuple[int, int, int, int]) -> bool:
    """True when ``inner`` sits (almost) entirely inside ``outer``."""
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    if iw * ih == 0 or iw * ih >= ow * oh:
        return False
    overlap_x = max(0, min(ox + ow, ix + iw) - max(ox, ix))
    overlap_y = max(0, min(oy + oh, iy + ih) - max(oy, iy))
    return (overlap_x * overlap_y) / (iw * ih) > 0.85


def _overlap_fraction(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = ix * iy
    smaller = min(aw * ah, bw * bh)
    return intersection / smaller if smaller > 0 else 0.0


def _ink_mask(crop: np.ndarray) -> np.ndarray:
    """Binarise a crop so the *minority* class is the ink, whatever the polarity."""
    if crop.size == 0:
        return crop
    blurred = cv2.GaussianBlur(crop, (3, 3), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if float(binary.mean()) > 127:
        binary = cv2.bitwise_not(binary)
    return binary


# --------------------------------------------------------------------------------
# Layer B — Tesseract
# --------------------------------------------------------------------------------


def recognise(image: Image.Image) -> list[Word]:
    """Run both PSM modes and merge. Returns [] when Tesseract is unavailable."""
    info = tesseract_info()
    if not info["available"]:
        return []

    import pytesseract

    width, height = image.size
    scale = max(1.0, OCR_UPSCALE_TARGET / max(1, min(width, height)))
    scale = min(scale, 4.0)
    working = (
        image.resize((int(width * scale), int(height * scale)), Image.Resampling.LANCZOS)
        if scale > 1.01
        else image
    )
    working = working.convert("L")

    collected: list[Word] = []
    for psm in (11, 6):
        try:
            data = pytesseract.image_to_data(
                working,
                config=f"--psm {psm} --oem 3",
                output_type=pytesseract.Output.DICT,
            )
        except Exception:
            continue

        for index in range(len(data.get("text", []))):
            raw = (data["text"][index] or "").strip()
            if not raw:
                continue
            try:
                confidence = float(data["conf"][index])
            except (TypeError, ValueError):
                continue
            if confidence < settings.ocr_min_confidence:
                continue
            if not re.search(r"[A-Za-z0-9\u00C0-\u024F]", raw):
                continue

            collected.append(
                Word(
                    x=int(data["left"][index] / scale),
                    y=int(data["top"][index] / scale),
                    w=max(1, int(data["width"][index] / scale)),
                    h=max(1, int(data["height"][index] / scale)),
                    text=raw,
                    confidence=confidence,
                    source="ocr",
                )
            )

    return _dedupe_ocr(collected)


def _dedupe_ocr(words: list[Word], iou_threshold: float = 0.5) -> list[Word]:
    ordered = sorted(words, key=lambda w: w.confidence, reverse=True)
    kept: list[Word] = []
    for word in ordered:
        duplicate = False
        for other in kept:
            if _iou(word.box, other.box) > iou_threshold:
                duplicate = True
                break
            if (
                word.text.lower() == other.text.lower()
                and _overlap_fraction(word.box, other.box) > 0.6
            ):
                duplicate = True
                break
        if not duplicate:
            kept.append(word)
    return kept


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    ix = max(0, min(ax2, bx2) - max(ax1, bx1))
    iy = max(0, min(ay2, by2) - max(ay1, by1))
    intersection = ix * iy
    union = aw * ah + bw * bh - intersection
    return intersection / union if union > 0 else 0.0


# --------------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------------


def measure_cap_height(gray: np.ndarray, word: Word) -> float:
    """Measure cap height from the ink row profile. See the module docstring."""
    x, y, w, h = word.box
    crop = gray[max(0, y) : y + h, max(0, x) : x + w]
    if crop.size == 0 or crop.shape[0] < 3:
        return float(h)

    mask = _ink_mask(crop)
    profile = (mask > 0).sum(axis=1).astype(np.float64)
    if profile.max() <= 0:
        return float(h)

    ink_rows = np.flatnonzero(profile > 0)
    if ink_rows.size == 0:
        return float(h)
    top = int(ink_rows[0])

    # Baseline: the lowest row still carrying 15% of peak ink. Descenders fall below it.
    threshold = 0.15 * profile.max()
    strong = np.flatnonzero(profile >= threshold)
    baseline = int(strong[-1]) if strong.size else int(ink_rows[-1])
    cap = baseline - top + 1
    return float(max(1, min(cap, h)))


def group_blocks(words: list[Word]) -> list[Block]:
    """Union-find on proximity. Two words join if they share a line and sit close."""
    if not words:
        return []

    parent = list(range(len(words)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(a: int, b: int) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            first, second = words[i], words[j]
            mean_height = (first.h + second.h) / 2
            if mean_height <= 0:
                continue
            if abs(first.cy - second.cy) > 0.6 * mean_height:
                continue
            gap = max(
                second.x - (first.x + first.w),
                first.x - (second.x + second.w),
            )
            if gap < 1.5 * mean_height:
                union(i, j)

    grouped: dict[int, Block] = {}
    for index, word in enumerate(words):
        grouped.setdefault(find(index), Block()).words.append(word)

    blocks = list(grouped.values())
    for block in blocks:
        block.words.sort(key=lambda w: (w.y, w.x))
    blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
    return blocks


def is_credible_text_block(block: Block) -> bool:
    """Gate for blocks that no OCR word vouches for.

    Without this, MSER's shape filter alone will happily report an eye and an eyebrow as
    a two-glyph text block — which is how a thumbnail with no text ends up with a text
    readability score. Real text lines share three properties that faces and foliage do
    not: consistent glyph height, a common baseline, and a horizontal run.
    """
    words = block.words
    if len(words) < 2:
        return False

    heights = np.array([w.h for w in words], dtype=np.float64)
    mean_height = float(heights.mean())
    if mean_height <= 0:
        return False
    if float(heights.std()) / mean_height > 0.30:
        return False  # glyphs in a word are the same height; random blobs are not

    bottoms = np.array([w.y + w.h for w in words], dtype=np.float64)
    if float(bottoms.std()) > 0.25 * mean_height:
        return False  # letters sit on a shared baseline

    _, _, width, height = block.bbox
    if width < height * 1.1:
        return False  # a line of text runs wider than it is tall
    if len(words) < 3 and width < height * 1.8:
        return False  # two regions only count as text if they clearly form a run

    return True


def block_colors(rgb: np.ndarray, gray: np.ndarray, bbox: tuple[int, int, int, int]):
    """Median ink color and median background color behind the block.

    The background is sampled from the non-ink pixels of a 25%-dilated box, which is
    what actually sits behind and around the letters — not a global average, which would
    report a comfortable contrast for white text on a bright patch of a dark image.
    """
    x, y, w, h = bbox
    height, width = gray.shape[:2]
    pad_x, pad_y = int(w * 0.125), int(h * 0.125)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(width, x + w + pad_x)
    y2 = min(height, y + h + pad_y)

    gray_crop = gray[y1:y2, x1:x2]
    rgb_crop = rgb[y1:y2, x1:x2]
    if gray_crop.size == 0:
        return (255, 255, 255), (0, 0, 0)

    mask = _ink_mask(gray_crop) > 0
    if mask.sum() < 4 or (~mask).sum() < 4:
        median = np.median(rgb_crop.reshape(-1, 3), axis=0)
        return tuple(int(v) for v in median), tuple(int(255 - v) for v in median)

    ink = np.median(rgb_crop[mask], axis=0)
    background = np.median(rgb_crop[~mask], axis=0)
    return tuple(int(v) for v in ink), tuple(int(v) for v in background)


def classify_font(gray: np.ndarray, block: Block) -> dict[str, Any]:
    """Measure letterform geometry and classify the family. Never claims an identity."""
    x, y, w, h = block.bbox
    crop = gray[max(0, y) : y + h, max(0, x) : x + w]
    if crop.size == 0 or crop.shape[0] < 6:
        return _unknown_font()

    mask = _ink_mask(crop)
    if not mask.any():
        return _unknown_font()

    stroke_width, stroke_contrast = _stroke_width_stats(mask)
    cap_height = block.cap_height or float(h)
    if cap_height <= 0:
        return _unknown_font()

    weight_ratio = stroke_width / cap_height

    glyph_widths = [word.w for word in block.words if word.w > 0]
    letters = sum(max(1, len(word.text)) for word in block.words) if block.text else len(block.words)
    total_width = sum(glyph_widths)
    width_ratio = (total_width / max(1, letters)) / cap_height if cap_height else 0.0

    # Serif score: ink density at the cap-band extremities vs. the middle. Serifs are
    # literally extra ink at the top and bottom terminals.
    rows = (mask > 0).sum(axis=1).astype(np.float64)
    band = max(1, int(len(rows) * 0.08))
    middle_start = int(len(rows) * 0.30)
    middle_end = max(middle_start + 1, int(len(rows) * 0.70))
    extremity = float(np.concatenate([rows[:band], rows[-band:]]).mean())
    middle = float(rows[middle_start:middle_end].mean()) or 1.0
    serif_score = extremity / middle

    # Slant from the ink's minimum-area rectangle.
    points = cv2.findNonZero(mask)
    slant = 0.0
    if points is not None and len(points) >= 5:
        (_, _), (_, _), angle = cv2.minAreaRect(points)
        slant = angle if abs(angle) <= 45 else angle - 90 if angle > 0 else angle + 90

    components = cv2.connectedComponents(mask)[0] - 1
    joined = letters > 0 and components < letters * 0.6

    if joined and abs(slant) > 12:
        classification = "script"
    elif joined:
        classification = "handwritten"
    elif stroke_contrast > 0.60:
        classification = "display-brush"
    elif serif_score > 1.35 and stroke_contrast > 0.45:
        classification = "didone"
    elif serif_score > 1.35:
        classification = "slab-serif"
    elif width_ratio and width_ratio < 0.55:
        classification = "condensed"
    elif width_ratio > 0.95:
        classification = "extended"
    elif stroke_contrast < 0.12:
        classification = "geometric-sans"
    else:
        classification = "grotesque"

    if weight_ratio < 0.09:
        weight = "light"
    elif weight_ratio < 0.13:
        weight = "regular"
    elif weight_ratio < 0.19:
        weight = "bold"
    else:
        weight = "black"

    text = block.text
    if text and text.isupper():
        case_pattern = "ALL CAPS"
    elif text and text.islower():
        case_pattern = "lowercase"
    elif text and text.istitle():
        case_pattern = "Title Case"
    elif text:
        case_pattern = "Mixed"
    else:
        case_pattern = None

    return {
        "classification": classification,
        "weight": weight,
        "italic": abs(slant) > 6,
        "casePattern": case_pattern,
        "strokeWidth": round(stroke_width, 2),
        "strokeContrast": round(stroke_contrast, 3),
        "widthRatio": round(width_ratio, 3),
        "serifScore": round(serif_score, 3),
        "slantDeg": round(float(slant), 1),
        "closestGoogleFonts": fonts.closest(classification, weight_ratio, width_ratio),
        "disclaimer": fonts.DISCLAIMER,
    }


def _unknown_font() -> dict[str, Any]:
    return {
        "classification": None,
        "weight": None,
        "italic": None,
        "casePattern": None,
        "strokeWidth": None,
        "strokeContrast": None,
        "widthRatio": None,
        "serifScore": None,
        "slantDeg": None,
        "closestGoogleFonts": [],
        "disclaimer": "Not enough legible letterform to classify.",
    }


def _quadrant(cx: float, cy: float) -> str:
    col = min(2, max(0, int(cx * 3)))
    row = min(2, max(0, int(cy * 3)))
    return QUADRANTS[row][col]


def _thirds_distance(cx: float, cy: float) -> float:
    return min(float(np.hypot(cx - tx, cy - ty)) for tx, ty in THIRDS)


# --------------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------------


def analyse(rgb: np.ndarray, gray: np.ndarray, image: Image.Image) -> dict[str, Any]:
    """Full text analysis. Never raises; reports what it could and could not do."""
    height, width = gray.shape[:2]
    info = tesseract_info()

    ocr_words = recognise(image)
    geometric_words = detect_regions(gray)

    if ocr_words:
        words = list(ocr_words)
        # Keep geometric regions that OCR missed entirely — stylised display type often
        # defeats recognition while still being obviously text.
        for candidate in geometric_words:
            if all(_iou(candidate.box, word.box) < 0.3 for word in words):
                words.append(candidate)
        source = "ocr"
    else:
        words = geometric_words
        source = "geometric"

    for word in words:
        word.cap_height = measure_cap_height(gray, word)

    blocks = group_blocks(words)

    # A block backed by a recognised word is text by definition. A block that only MSER
    # believes in has to prove itself — see is_credible_text_block.
    blocks = [b for b in blocks if b.text or is_credible_text_block(b)]

    block_payload: list[dict[str, Any]] = []
    union_mask = np.zeros((height, width), dtype=bool)

    for block in blocks:
        x, y, w, h = block.bbox
        ink, background = block_colors(rgb, gray, (x, y, w, h))
        ratio = contrast_ratio(ink, background)
        cx = (x + w / 2) / width
        cy = (y + h / 2) / height
        union_mask[y : y + h, x : x + w] = True

        block_payload.append(
            {
                "text": block.text or None,
                "words": [w_.text for w_ in block.words if w_.text],
                "confidence": round(
                    float(np.mean([w_.confidence for w_ in block.words])), 1
                ),
                "bbox": {
                    "x": round(x / width, 4),
                    "y": round(y / height, 4),
                    "w": round(w / width, 4),
                    "h": round(h / height, 4),
                },
                "bboxPx": {"x": x, "y": y, "w": w, "h": h},
                "capHeightPx": round(block.cap_height, 1),
                "heightPercent": round(h / height * 100, 2),
                "wcagContrast": ratio,
                "passesAA": passes_aa(ratio, large_text=block.cap_height >= height * 0.06),
                "passesAALarge": passes_aa(ratio, large_text=True),
                "textColor": "#{:02X}{:02X}{:02X}".format(*ink),
                "backgroundColor": "#{:02X}{:02X}{:02X}".format(*background),
                "quadrant": _quadrant(cx, cy),
                "thirdsDistance": round(_thirds_distance(cx, cy), 4),
            }
        )

    # Count only what survived into a block. Counting every raw MSER region would report
    # "17 words" for an image whose credible text is a single two-word headline.
    retained = [w for block in blocks for w in block.words]
    word_count = (
        sum(1 for w in retained if w.text)
        if source == "ocr"
        else len(retained)
    )
    if word_count <= 4:
        verdict = "excellent"
    elif word_count <= 6:
        verdict = "good"
    elif word_count <= 9:
        verdict = "busy"
    else:
        verdict = "overloaded"

    largest = max(blocks, key=lambda b: b.bbox[2] * b.bbox[3], default=None)
    font_read = classify_font(gray, largest) if largest else _unknown_font()

    return {
        "available": True,
        "textSource": source,
        "engine": f"tesseract {info['version']}" if info["available"] else "mser-geometric",
        "recognitionAvailable": info["available"],
        "recognitionNote": (
            None
            if info["available"]
            else "Tesseract is not installed, so ThumbIQ located the text but did not read it. "
            "Placement, size, contrast and mobile legibility are still measured."
        ),
        "blocks": block_payload,
        "wordCount": word_count,
        "wordCountVerdict": verdict,
        "wordCountEstimated": source != "ocr",
        "textAreaRatio": round(float(union_mask.mean()), 4),
        "fontRead": font_read,
    }


def mobile_legibility(
    image: Image.Image, text_result: dict[str, Any]
) -> dict[str, Any]:
    """Re-measure the text at the five sizes YouTube actually renders at."""
    blocks = text_result.get("blocks") or []
    if not blocks:
        return {
            "available": False,
            "reason": "No text detected, so there is nothing to become illegible.",
            "surfaces": [],
        }

    native_width, native_height = image.size
    largest_cap = max(block["capHeightPx"] for block in blocks)
    original_words = {
        word.lower() for block in blocks for word in (block.get("words") or [])
    }
    can_reocr = tesseract_info()["available"] and bool(original_words)

    surfaces: list[dict[str, Any]] = []
    for surface_id, label, width, height in SURFACES:
        scale = width / native_width
        cap_at_surface = largest_cap * scale

        if cap_at_surface < CAP_HEIGHT_FAIL:
            verdict = "FAIL"
            reason = (
                f"Cap height is {cap_at_surface:.0f} px here — under the 10 px floor, "
                "so the text is a smudge."
            )
        elif cap_at_surface < CAP_HEIGHT_WARN:
            verdict = "WARNING"
            reason = (
                f"Cap height is {cap_at_surface:.0f} px — readable if someone stops to "
                "look, missed if they are scrolling."
            )
        else:
            verdict = "PASS"
            reason = f"Cap height is {cap_at_surface:.0f} px — comfortably legible."

        recovery: float | None = None
        if can_reocr:
            rendered = image.resize((width, height), Image.Resampling.LANCZOS)
            recovered = {w.text.lower() for w in recognise(rendered) if w.text}
            if original_words:
                hits = sum(
                    1
                    for word in original_words
                    if any(word in got or got in word for got in recovered)
                )
                recovery = round(hits / len(original_words), 3)

        surfaces.append(
            {
                "surface": surface_id,
                "label": label,
                "width": width,
                "height": height,
                "capHeightPx": round(cap_at_surface, 1),
                "verdict": verdict,
                "reason": reason,
                "ocrRecoveryRatio": recovery,
            }
        )

    return {"available": True, "reason": None, "surfaces": surfaces}
