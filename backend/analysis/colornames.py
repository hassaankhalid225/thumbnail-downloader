"""Nearest human-readable color name, matched in LAB rather than RGB.

Matching in RGB gives wrong answers that look like bugs to a user — a mid teal lands
nearest to "gray" because RGB distance has nothing to do with perceived difference.
LAB with ΔE76 gives the name a person would actually say.

The table is the 148 CSS named colors, which is the vocabulary a designer already has.
"""

from __future__ import annotations

import numpy as np

CSS_COLORS: dict[str, tuple[int, int, int]] = {
    "AliceBlue": (240, 248, 255), "AntiqueWhite": (250, 235, 215), "Aqua": (0, 255, 255),
    "Aquamarine": (127, 255, 212), "Azure": (240, 255, 255), "Beige": (245, 245, 220),
    "Bisque": (255, 228, 196), "Black": (0, 0, 0), "BlanchedAlmond": (255, 235, 205),
    "Blue": (0, 0, 255), "BlueViolet": (138, 43, 226), "Brown": (165, 42, 42),
    "BurlyWood": (222, 184, 135), "CadetBlue": (95, 158, 160), "Chartreuse": (127, 255, 0),
    "Chocolate": (210, 105, 30), "Coral": (255, 127, 80), "CornflowerBlue": (100, 149, 237),
    "Cornsilk": (255, 248, 220), "Crimson": (220, 20, 60), "Cyan": (0, 255, 255),
    "DarkBlue": (0, 0, 139), "DarkCyan": (0, 139, 139), "DarkGoldenRod": (184, 134, 11),
    "DarkGray": (169, 169, 169), "DarkGreen": (0, 100, 0), "DarkKhaki": (189, 183, 107),
    "DarkMagenta": (139, 0, 139), "DarkOliveGreen": (85, 107, 47), "DarkOrange": (255, 140, 0),
    "DarkOrchid": (153, 50, 204), "DarkRed": (139, 0, 0), "DarkSalmon": (233, 150, 122),
    "DarkSeaGreen": (143, 188, 143), "DarkSlateBlue": (72, 61, 139),
    "DarkSlateGray": (47, 79, 79), "DarkTurquoise": (0, 206, 209), "DarkViolet": (148, 0, 211),
    "DeepPink": (255, 20, 147), "DeepSkyBlue": (0, 191, 255), "DimGray": (105, 105, 105),
    "DodgerBlue": (30, 144, 255), "FireBrick": (178, 34, 34), "FloralWhite": (255, 250, 240),
    "ForestGreen": (34, 139, 34), "Fuchsia": (255, 0, 255), "Gainsboro": (220, 220, 220),
    "GhostWhite": (248, 248, 255), "Gold": (255, 215, 0), "GoldenRod": (218, 165, 32),
    "Gray": (128, 128, 128), "Green": (0, 128, 0), "GreenYellow": (173, 255, 47),
    "HoneyDew": (240, 255, 240), "HotPink": (255, 105, 180), "IndianRed": (205, 92, 92),
    "Indigo": (75, 0, 130), "Ivory": (255, 255, 240), "Khaki": (240, 230, 140),
    "Lavender": (230, 230, 250), "LavenderBlush": (255, 240, 245), "LawnGreen": (124, 252, 0),
    "LemonChiffon": (255, 250, 205), "LightBlue": (173, 216, 230), "LightCoral": (240, 128, 128),
    "LightCyan": (224, 255, 255), "LightGoldenRodYellow": (250, 250, 210),
    "LightGray": (211, 211, 211), "LightGreen": (144, 238, 144), "LightPink": (255, 182, 193),
    "LightSalmon": (255, 160, 122), "LightSeaGreen": (32, 178, 170),
    "LightSkyBlue": (135, 206, 250), "LightSlateGray": (119, 136, 153),
    "LightSteelBlue": (176, 196, 222), "LightYellow": (255, 255, 224), "Lime": (0, 255, 0),
    "LimeGreen": (50, 205, 50), "Linen": (250, 240, 230), "Magenta": (255, 0, 255),
    "Maroon": (128, 0, 0), "MediumAquaMarine": (102, 205, 170), "MediumBlue": (0, 0, 205),
    "MediumOrchid": (186, 85, 211), "MediumPurple": (147, 112, 219),
    "MediumSeaGreen": (60, 179, 113), "MediumSlateBlue": (123, 104, 238),
    "MediumSpringGreen": (0, 250, 154), "MediumTurquoise": (72, 209, 204),
    "MediumVioletRed": (199, 21, 133), "MidnightBlue": (25, 25, 112),
    "MintCream": (245, 255, 250), "MistyRose": (255, 228, 225), "Moccasin": (255, 228, 181),
    "NavajoWhite": (255, 222, 173), "Navy": (0, 0, 128), "OldLace": (253, 245, 230),
    "Olive": (128, 128, 0), "OliveDrab": (107, 142, 35), "Orange": (255, 165, 0),
    "OrangeRed": (255, 69, 0), "Orchid": (218, 112, 214), "PaleGoldenRod": (238, 232, 170),
    "PaleGreen": (152, 251, 152), "PaleTurquoise": (175, 238, 238),
    "PaleVioletRed": (219, 112, 147), "PapayaWhip": (255, 239, 213),
    "PeachPuff": (255, 218, 185), "Peru": (205, 133, 63), "Pink": (255, 192, 203),
    "Plum": (221, 160, 221), "PowderBlue": (176, 224, 230), "Purple": (128, 0, 128),
    "RebeccaPurple": (102, 51, 153), "Red": (255, 0, 0), "RosyBrown": (188, 143, 143),
    "RoyalBlue": (65, 105, 225), "SaddleBrown": (139, 69, 19), "Salmon": (250, 128, 114),
    "SandyBrown": (244, 164, 96), "SeaGreen": (46, 139, 87), "SeaShell": (255, 245, 238),
    "Sienna": (160, 82, 45), "Silver": (192, 192, 192), "SkyBlue": (135, 206, 235),
    "SlateBlue": (106, 90, 205), "SlateGray": (112, 128, 144), "Snow": (255, 250, 250),
    "SpringGreen": (0, 255, 127), "SteelBlue": (70, 130, 180), "Tan": (210, 180, 140),
    "Teal": (0, 128, 128), "Thistle": (216, 191, 216), "Tomato": (255, 99, 71),
    "Turquoise": (64, 224, 208), "Violet": (238, 130, 238), "Wheat": (245, 222, 179),
    "White": (255, 255, 255), "WhiteSmoke": (245, 245, 245), "Yellow": (255, 255, 0),
    "YellowGreen": (154, 205, 50),
}

_NAMES: list[str] = list(CSS_COLORS.keys())
_RGB = np.array([CSS_COLORS[name] for name in _NAMES], dtype=np.float64)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """sRGB (0–255) → CIE LAB, D65. Written out so it matches color.py exactly."""
    array = np.asarray(rgb, dtype=np.float64).reshape(-1, 3) / 255.0
    linear = np.where(array <= 0.04045, array / 12.92, ((array + 0.055) / 1.055) ** 2.4)

    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = linear @ matrix.T
    white = np.array([0.95047, 1.00000, 1.08883])
    scaled = xyz / white

    epsilon = 216 / 24389
    kappa = 24389 / 27
    f = np.where(scaled > epsilon, np.cbrt(scaled), (kappa * scaled + 16) / 116)

    lightness = 116 * f[:, 1] - 16
    a = 500 * (f[:, 0] - f[:, 1])
    b = 200 * (f[:, 1] - f[:, 2])
    return np.stack([lightness, a, b], axis=1)


_LAB = _rgb_to_lab(_RGB)


def nearest_name(rgb: tuple[int, int, int] | np.ndarray) -> str:
    """Closest CSS color name by ΔE76 in LAB."""
    lab = _rgb_to_lab(np.asarray(rgb, dtype=np.float64).reshape(1, 3))
    distances = np.linalg.norm(_LAB - lab, axis=1)
    return _NAMES[int(np.argmin(distances))]


def delta_e76(lab_a: np.ndarray, lab_b: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(lab_a, dtype=np.float64) - np.asarray(lab_b, dtype=np.float64)))
