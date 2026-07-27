"""Generate the OG image and the favicon.

Drawn with Pillow rather than shipped as a binary blob so the brand values live in one
place and the asset can be regenerated when they change.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PUBLIC = Path(r"d:\Work\My Work\Web\Thumbnail Downloader\frontend\public")
PUBLIC.mkdir(parents=True, exist_ok=True)

BG = (10, 10, 13)
PANEL = (16, 16, 21)
BORDER = (35, 35, 48)
LIME = (200, 255, 61)
CYAN = (34, 211, 238)
TEXT = (242, 242, 247)
MUTED = (142, 142, 168)


def load_font(names: list[str], size: int) -> ImageFont.FreeTypeFont:
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


BOLD = ["arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"]
MONO = ["consola.ttf", "cour.ttf", "DejaVuSansMono.ttf"]
REG = ["arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"]


def reticle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, width: int) -> None:
    """The ThumbIQ mark: a measuring reticle, not a play button."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LIME, width=width)
    dot = max(2, r // 4)
    draw.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=LIME)
    tick = r // 2
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        draw.line(
            [cx + dx * (r + tick // 2), cy + dy * (r + tick // 2),
             cx + dx * (r + tick + tick // 2), cy + dy * (r + tick + tick // 2)],
            fill=LIME, width=width,
        )


# ---------- OG image, 1200x630 ----------
og = Image.new("RGB", (1200, 630), BG)
draw = ImageDraw.Draw(og)

for x in range(0, 1200, 56):
    draw.line([(x, 0), (x, 630)], fill=(18, 18, 24), width=1)
for y in range(0, 630, 56):
    draw.line([(0, y), (1200, y)], fill=(18, 18, 24), width=1)

reticle(draw, 92, 84, 22, 4)
draw.text((132, 66), "ThumbIQ", font=load_font(BOLD, 34), fill=TEXT)

draw.text((72, 168), "Steal the thumbnail.", font=load_font(BOLD, 74), fill=TEXT)
draw.text((72, 254), "Understand the strategy.", font=load_font(BOLD, 74), fill=LIME)

draw.text(
    (72, 372),
    "Every size of any thumbnail — plus the colour science, the text\n"
    "placement, and whether your words survive at phone size.",
    font=load_font(REG, 27), fill=MUTED, spacing=12,
)

# A row of measurement chips: the product is an instrument, so the OG card shows readings.
chips = [("MOBILE LEGIBILITY", "FAIL", (239, 68, 68)),
         ("WCAG CONTRAST", "8.4:1", LIME),
         ("CAP HEIGHT @168px", "9 px", (245, 158, 11)),
         ("SAFE ZONE", "100", CYAN)]
x = 72
mono_small, mono_big = load_font(MONO, 15), load_font(MONO, 30)
for label, value, colour in chips:
    width = 258
    draw.rounded_rectangle([x, 480, x + width, 570], radius=12, fill=PANEL, outline=BORDER, width=1)
    draw.text((x + 18, 498), label, font=mono_small, fill=MUTED)
    draw.text((x + 18, 522), value, font=mono_big, fill=colour)
    x += width + 14

og.save(PUBLIC / "og-image.png", "PNG", optimize=True)
print("og-image.png", (PUBLIC / "og-image.png").stat().st_size, "bytes")

# ---------- favicon ----------
icon = Image.new("RGBA", (512, 512), (10, 10, 13, 255))
draw = ImageDraw.Draw(icon)
draw.rounded_rectangle([0, 0, 511, 511], radius=110, fill=(10, 10, 13, 255))
reticle(draw, 256, 256, 132, 22)
icon.save(PUBLIC / "icon.png", "PNG", optimize=True)
icon.resize((180, 180), Image.Resampling.LANCZOS).save(PUBLIC / "apple-icon.png", "PNG")
icon.save(
    PUBLIC / "favicon.ico",
    sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
)
for name in ("icon.png", "apple-icon.png", "favicon.ico"):
    print(name, (PUBLIC / name).stat().st_size, "bytes")
