"""Closest-match Google Font suggestions.

This module is deliberately not a font identifier. Identifying a typeface from a raster
image needs a licensed matching service and a reference corpus; claiming to do it from
pixel measurements would be a lie that destroys trust in every other number ThumbIQ
shows. What it does instead is measurable and honest: classify the letterform family,
measure stroke weight and width, and return the free Google fonts whose own measured
signature is closest.

Each signature is ``(classification, weightRatio, widthRatio)`` where
``weightRatio = strokeWidth / capHeight`` and ``widthRatio = glyphAdvance / capHeight``,
measured from the font's uppercase set at 200 px.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FontSignature:
    name: str
    classification: str
    weight_ratio: float
    width_ratio: float
    note: str


CATALOG: tuple[FontSignature, ...] = (
    FontSignature("Anton", "condensed", 0.21, 0.46, "The default heavy condensed of YouTube thumbnails."),
    FontSignature("Bebas Neue", "condensed", 0.14, 0.42, "Tall, narrow, all-caps by design."),
    FontSignature("Oswald", "condensed", 0.13, 0.50, "Condensed grotesque with a wider range of weights."),
    FontSignature("Fjalla One", "condensed", 0.15, 0.50, "Slightly softer condensed display."),
    FontSignature("Barlow Condensed", "condensed", 0.11, 0.48, "Lighter condensed, good for subtitles."),
    FontSignature("Big Shoulders Display", "condensed", 0.12, 0.38, "Extremely narrow display face."),
    FontSignature("Teko", "condensed", 0.13, 0.42, "Squared condensed, sports and gaming feel."),
    FontSignature("Archivo Black", "grotesque", 0.22, 0.78, "Heavy neo-grotesque, very high impact."),
    FontSignature("Inter Black", "grotesque", 0.21, 0.72, "Neutral UI grotesque at maximum weight."),
    FontSignature("Rubik Black", "grotesque", 0.22, 0.76, "Rounded-corner grotesque."),
    FontSignature("Roboto Bold", "grotesque", 0.15, 0.66, "The web's default workhorse."),
    FontSignature("Montserrat ExtraBold", "geometric-sans", 0.19, 0.80, "Wide geometric caps."),
    FontSignature("Poppins Bold", "geometric-sans", 0.16, 0.76, "Circular geometric, friendly."),
    FontSignature("Nunito Black", "geometric-sans", 0.20, 0.78, "Rounded geometric, softer edges."),
    FontSignature("Bungee", "display-brush", 0.24, 0.72, "Signage display face, built for headlines."),
    FontSignature("Titan One", "display-brush", 0.26, 0.80, "Very heavy cartoon display."),
    FontSignature("Playfair Display", "didone", 0.18, 0.62, "High-contrast serif, editorial."),
    FontSignature("Bodoni Moda", "didone", 0.17, 0.60, "Classic didone, thin hairlines."),
    FontSignature("Roboto Slab Bold", "slab-serif", 0.17, 0.70, "Low-contrast slab."),
    FontSignature("Alfa Slab One", "slab-serif", 0.26, 0.78, "Heavy slab, poster weight."),
    FontSignature("Merriweather Black", "slab-serif", 0.19, 0.74, "Sturdy reading serif at heavy weight."),
    FontSignature("Pacifico", "script", 0.14, 0.62, "Connected brush script."),
    FontSignature("Lobster", "script", 0.16, 0.60, "Condensed script with heavy strokes."),
    FontSignature("Caveat", "handwritten", 0.10, 0.52, "Casual handwriting."),
    FontSignature("Anybody", "extended", 0.18, 1.05, "Variable width, reaches wide extremes."),
    FontSignature("Archivo Expanded", "extended", 0.19, 1.02, "Wide grotesque."),
)

DISCLAIMER = "Closest match — not an exact identification."


def closest(
    classification: str, weight_ratio: float, width_ratio: float, count: int = 3
) -> list[dict[str, object]]:
    """Rank the catalog against a measured signature.

    Confidence is a similarity, not a probability: 1.0 would mean the measurements land
    exactly on a catalog signature, which real-world antialiased text never does.
    """
    scored: list[tuple[float, FontSignature]] = []
    for font in CATALOG:
        class_penalty = 0.0 if font.classification == classification else 1.0
        weight_penalty = min(1.0, abs(font.weight_ratio - weight_ratio) / 0.14)
        width_penalty = min(1.0, abs(font.width_ratio - width_ratio) / 0.45)
        distance = 0.50 * class_penalty + 0.30 * weight_penalty + 0.20 * width_penalty
        scored.append((distance, font))

    scored.sort(key=lambda pair: pair[0])
    return [
        {
            "name": font.name,
            "confidence": round(max(0.0, 1.0 - distance), 2),
            "note": font.note,
        }
        for distance, font in scored[:count]
    ]
