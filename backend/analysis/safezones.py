"""YouTube UI chrome collisions.

The duration pill is the single most common real-world thumbnail mistake: a creator
places their punchline word in the bottom-right corner, and every viewer sees a black
rounded rectangle sitting on top of it. Nothing in the creator's editor shows this.

Zones are in normalised coordinates and match where YouTube actually draws its chrome.
"""

from __future__ import annotations

from typing import Any

ZONES: tuple[dict[str, Any], ...] = (
    {
        "id": "duration_pill",
        "label": "Duration pill",
        "x": 0.84, "y": 0.82, "w": 0.14, "h": 0.13,
        "note": "The timestamp badge. Drawn on every video, on every surface.",
    },
    {
        "id": "cc_badge",
        "label": "CC / live badge",
        "x": 0.02, "y": 0.82, "w": 0.12, "h": 0.13,
        "note": "Subtitles and live indicators appear here.",
    },
    {
        "id": "progress_bar",
        "label": "Watched progress bar",
        "x": 0.0, "y": 0.96, "w": 1.0, "h": 0.04,
        "note": "A red strip across the bottom once a viewer has started the video.",
    },
    {
        "id": "hover_crop",
        "label": "Hover-preview crop",
        "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
        "border": 0.02,
        "note": "Some surfaces crop the outer 2% during hover previews.",
    },
)

SEVERITY_HIGH = 0.35
SEVERITY_MEDIUM = 0.12


def _overlap_area(a: dict[str, float], b: dict[str, float]) -> float:
    x1 = max(a["x"], b["x"])
    y1 = max(a["y"], b["y"])
    x2 = min(a["x"] + a["w"], b["x"] + b["w"])
    y2 = min(a["y"] + a["h"], b["y"] + b["h"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def _border_overlap(element: dict[str, float], border: float) -> float:
    """Fraction of the element that falls inside the outer border ring."""
    total = element["w"] * element["h"]
    if total <= 0:
        return 0.0
    inner = {"x": border, "y": border, "w": 1 - 2 * border, "h": 1 - 2 * border}
    inside = _overlap_area(element, inner)
    return max(0.0, (total - inside) / total)


def _severity(fraction: float) -> str:
    if fraction > SEVERITY_HIGH:
        return "high"
    if fraction > SEVERITY_MEDIUM:
        return "medium"
    return "low"


def analyse(text_result: dict[str, Any], face_result: dict[str, Any]) -> dict[str, Any]:
    elements: list[tuple[str, str, dict[str, float]]] = []

    for block in text_result.get("blocks") or []:
        label = block.get("text") or f"text block at {block['quadrant']}"
        elements.append(("text", label, block["bbox"]))

    for index, face in enumerate(face_result.get("faces") or [], start=1):
        elements.append(("face", f"face {index}", face["bbox"]))

    collisions: list[dict[str, Any]] = []
    for zone in ZONES:
        for kind, label, bbox in elements:
            element_area = bbox["w"] * bbox["h"]
            if element_area <= 0:
                continue

            if "border" in zone:
                fraction = _border_overlap(bbox, zone["border"])
            else:
                fraction = _overlap_area(bbox, zone) / element_area

            if fraction <= 0.001:
                continue

            collisions.append(
                {
                    "zone": zone["id"],
                    "zoneLabel": zone["label"],
                    "severity": _severity(fraction),
                    "overlapFraction": round(fraction, 3),
                    "element": kind,
                    "elementLabel": label,
                    "region": {k: zone[k] for k in ("x", "y", "w", "h")},
                    "advice": _advice(zone["id"], kind, label),
                }
            )

    order = {"high": 0, "medium": 1, "low": 2}
    collisions.sort(key=lambda c: (order[c["severity"]], -c["overlapFraction"]))

    return {
        "collisions": collisions,
        "zones": [
            {k: zone[k] for k in ("id", "label", "x", "y", "w", "h", "note")}
            for zone in ZONES
        ],
        "clean": not collisions,
    }


def _advice(zone_id: str, kind: str, label: str) -> str:
    subject = f'"{label}"' if kind == "text" and label else f"the {label}"
    if zone_id == "duration_pill":
        return f"Move {subject} left or up — the duration badge sits on top of it."
    if zone_id == "cc_badge":
        return f"Shift {subject} inward; the CC and live badges render in that corner."
    if zone_id == "progress_bar":
        return f"Lift {subject} above the bottom 4% — the watched progress bar covers it."
    return f"Pull {subject} in from the edge; the outer 2% can be cropped on hover."
