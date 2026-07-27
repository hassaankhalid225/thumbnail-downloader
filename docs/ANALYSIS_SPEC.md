# ThumbIQ — Analysis Spec

Every number in the UI is produced by one of the formulas below, from real pixels.
Claude never sets a number; it only reads these and explains them.

Notation: `lin(x, a, b)` = `clip((x − a) / (b − a), 0, 1)`.
`band(x, lo, hi, floor, ceil)` = 1 inside `[lo, hi]`, ramping linearly to 0 at `floor`
and `ceil`, 0 outside. All normalised coordinates are fractions of image width/height.

---

## 0. Shared decode

The image is decoded once into an RGB `uint8` ndarray. Derived views computed once and
reused by every module: linear-light RGB, CIE LAB (D65), HSV, 8-bit grayscale,
Canny edges, and the saliency map. Nothing is decoded twice.

---

## 1. Color — `analysis/color.py`

| Metric | Formula | Range | Meaning |
|---|---|---|---|
| `palette[]` | 200×200 Lanczos downsample → sRGB→linear→XYZ(D65)→LAB → **KMeans k=6**, `n_init=4`, `random_state=42`. Cluster centroids converted back to sRGB. | 6 swatches | perceptually-clustered dominant colors |
| `coverage` | `cluster_pixel_count / 40000 × 100` | 0–100 % | share of frame |
| `name` | nearest of the 148 CSS named colors by ΔE76 in LAB | string | human label |
| `harmony.type` | hue relationships among swatches with `coverage ≥ 5%` and `S ≥ 0.15` (achromatic swatches excluded). Circular hue arithmetic in degrees. | enum | see below |
| `harmony.confidence` | `1 − error / tolerance`, clipped | 0–1 | how cleanly it fits |
| `temperature` | mean LAB `b*` over the full image. `> +5` warm, `< −5` cool, else neutral. `warmRatio` = fraction of pixels with `b* > 0` | enum + 0–1 | |
| `saturation.mean/std` | HSV `S` over full image | 0–1 | `punchy` ≥ 0.55, `muted` < 0.30, else `balanced` |
| `brightness.histogram` | 32-bin histogram of LAB `L*` | counts | |
| `brightness.clippedBlack/White` | fraction of grayscale pixels `< 5` / `> 250` | 0–1 | blown highlights / crushed shadows |

**Harmony classification** (evaluated in order, first match wins):

| Type | Test | Tolerance |
|---|---|---|
| `monochromatic` | max circular hue arc across all chromatic swatches < 20° | 20° |
| `analogous` | max circular hue arc < 45° | 45° |
| `complementary` | some pair with `|Δhue − 180| ≤ 15` | 15° |
| `split-complementary` | some base hue with partners near `+150` and `+210` (±18) | 18° |
| `triadic` | three hues mutually `120 ± 18` apart | 18° |
| `custom` | none of the above | — |

**Exports** — CSS custom properties, a Tailwind `colors` object, and an Adobe-ASE-compatible
JSON group. All generated from the same swatch list, no rounding drift.

---

## 2. Contrast — `analysis/contrast.py`

WCAG 2.1 exactly:

```
c_lin = c/12.92                    if c ≤ 0.04045
      = ((c + 0.055)/1.055)^2.4    otherwise
L     = 0.2126·R_lin + 0.7152·G_lin + 0.0722·B_lin
ratio = (max(L1,L2) + 0.05) / (min(L1,L2) + 0.05)          →  1.0 … 21.0
```

| Metric | Formula | Range |
|---|---|---|
| `globalContrast` | `p95(L) − p5(L)` over the luminance image | 0–1 |
| `rmsContrast` | `std(L)` | 0–1 |
| `localContrast.mean/max` | grayscale `std` inside 16×16 tiles, averaged / maximum | 0–255 |

Sanity anchors used in tests: black↔white = **21.00**, `#767676`↔white = **4.54**.

---

## 3. Text — `analysis/text.py`

Two independent layers, so the tab still works when Tesseract is absent.

**Layer A — geometric localisation (always available).** Connected components over four
binarisations — Otsu and adaptive-mean, each in both polarities. Two thresholds because
they fail in opposite situations: Otsu is exactly right for the flat, high-contrast text
a thumbnail actually uses and useless across a gradient; adaptive-mean handles the
gradient and is noisy on flat fields. Both polarities because thumbnail text is as often
light-on-dark as dark-on-light.

Components are filtered to text-like shapes by area (`4e-6 … 0.05` of frame), aspect
(`0.08 … 12`), fill ratio (`0.10 … 0.92`, with stem-shaped glyphs like `I` and `l`
exempted from the upper bound), and stroke-width consistency (`std/mean < 0.62`, stroke
width from the distance transform of the ink mask). The filter runs vectorised over the
whole component-stats array — a photograph can produce tens of thousands of components,
and a Python loop over them holds the GIL long enough to serialise every other analysis
in the pool.

> **Why not MSER?** The original design used it. OpenCV 5's MSER returns *zero* regions
> on flat, high-contrast synthetic input — verified against a white rectangle on a dark
> field, which is precisely the shape a thumbnail headline is. Connected components over
> a pair of thresholds behave identically on a poster and on a photograph, and are
> testable against an image whose answer is known in advance.

**Duplicate handling.** Two distinct problems have to be told apart, and containment
alone cannot do it: the *same glyph* found by two thresholds (near-identical boxes, high
IoU), and a *whole line* found as one component because a threshold bled the letters
together (a big box containing several glyph boxes). Deduping by IoU keeps glyph-level
detections; any surviving region that fully contains two or more others is then dropped
as a line-blob. Keeping the outermost box instead would erase a line's letters and leave
one shapeless rectangle that fails every downstream measurement.

**Credibility gate.** A block that no recognised word vouches for must prove itself:
glyph heights within 30 % of their mean, a shared baseline (bottom-edge σ < 0.25 × mean
height), a horizontal run (width ≥ 1.1 × height), and at least two regions. Without this,
the shape filter alone reports an eye and an eyebrow as a two-glyph text block — which is
how a thumbnail with no text ends up with a text-readability score.

Surviving regions are grouped into lines and blocks by the union-find proximity rule
below.

**Layer B — recognition (Tesseract, optional).** `image_to_data` at `--psm 11` (sparse)
and `--psm 6` (uniform block), on a copy upscaled so the shortest side is ≥ 1000 px
(bbox coordinates divided back by the scale factor). Words with `conf ≥ 55` are kept.
The two passes are merged: same normalised text and `IoU > 0.5` → keep the higher
confidence. Recognised words are matched onto Layer-A regions by IoU; unmatched OCR words
are added as their own regions.

`textSource` reports `"ocr"` or `"geometric"` so the UI never implies it read words it
did not.

**Block grouping** — union-find over word boxes; two boxes join if the vertical centre
offset is `< 0.6 × mean height` and the horizontal gap is `< 1.5 × mean height`.

| Metric | Formula | Range |
|---|---|---|
| `capHeightPx` | crop the word, Otsu-binarise, build the ink row profile. Baseline = lowest row whose ink density ≥ 15 % of the profile max. `capHeight = baseline − first_ink_row`. Measured, not assumed. | px |
| `heightPercent` | `bbox.h / image_h × 100` | 0–100 |
| `wordCount` | number of retained word regions | int |
| `textAreaRatio` | area of the **union mask** of all block bboxes ÷ image area (no double counting) | 0–1, sweet spot 0.08–0.25 |
| `quadrant` | block centroid → 3×3 grid cell | enum |
| `thirdsDistance` | euclidean distance from block centroid to nearest of the four `{⅓,⅔}²` intersections, in normalised space | 0–0.4714 |
| `wcagContrast` | ink color = median RGB of Otsu-foreground pixels; background = median RGB of the non-ink pixels inside a bbox dilated by 25 % — so it samples what actually sits behind the letters. WCAG ratio between the two. | 1–21 |
| `passesAA` / `passesAALarge` | `≥ 4.5` / `≥ 3.0` | bool |

**Font-style classification** — never claims exact identification.

| Input | How it is measured |
|---|---|
| `strokeWidth` | `2 × mean(distance transform maxima)` over the ink mask |
| `strokeContrast` | `std(stroke widths) / mean(stroke widths)` |
| `widthRatio` | mean glyph advance width ÷ cap height |
| `serifScore` | ink density in the top 8 % and bottom 8 % of the cap band ÷ density in the middle 40 % |
| `slant` | `minAreaRect` angle of the ink mask, sign-corrected |

| Classification | Rule |
|---|---|
| `condensed` | `widthRatio < 0.55` |
| `extended` | `widthRatio > 0.95` |
| `didone` | `serifScore > 1.35` and `strokeContrast > 0.45` |
| `slab-serif` | `serifScore > 1.35` and `strokeContrast < 0.25` |
| `grotesque` | `serifScore ≤ 1.35`, `0.12 ≤ strokeContrast ≤ 0.28` |
| `geometric-sans` | `serifScore ≤ 1.35`, `strokeContrast < 0.12` |
| `script` / `handwritten` | `|slant| > 12°` and connected components ≪ glyph count (letters join) |
| `display-brush` | `strokeContrast > 0.6` with irregular stroke profile |

Weight from `strokeWidth / capHeight`: `< 0.09` light, `< 0.13` regular, `< 0.19` bold,
else `black`. Italic when `|slant| > 6°`. Case pattern read from the recognised string
when available.

**Closest Google Fonts** — a table of free Google fonts, each carrying a measured
signature `(classification, weightRatio, widthRatio)`. The three nearest by weighted
euclidean distance are returned, `confidence = 1 − d/d_max`. Always labelled
*"Closest match — not an exact identification."*

---

## 4. Mobile legibility

The thumbnail is physically Lanczos-downscaled to the five sizes YouTube actually
renders at, and re-measured:

| Surface | Rendered size |
|---|---|
| `mobile_feed` | 168 × 94 |
| `mobile_search` | 246 × 138 |
| `desktop_grid` | 360 × 202 |
| `desktop_sidebar` | 168 × 94 |
| `watch_page` | 1280 × 720 |

Two numbers per surface:

- `capHeightPx` — the largest block's cap height scaled by `surface_width / native_width`.
  Exact arithmetic on a measured quantity.
- `ocrRecoveryRatio` — OCR is re-run **on the actual downscaled render** and the fraction
  of originally-detected words still recovered is reported. This is the honest answer to
  "can anything still read this?" It is `null` when Tesseract is unavailable.

Verdict from cap height, per the brief: `< 10 px` **FAIL**, `10–14 px` **WARNING**,
`> 14 px` **PASS**.

---

## 5. Composition — `analysis/composition.py`

| Metric | Formula | Range |
|---|---|---|
| saliency map | Hou & Zhang spectral residual: grayscale → 64×64 → FFT → `logAmp − boxfilter(logAmp, 3)` → inverse FFT with original phase → magnitude² → Gaussian σ=2.5 → normalise → resize to frame. Uses `cv2.saliency.StaticSaliencySpectralResidual` when the contrib module is present; the NumPy path is the identical algorithm and is the fallback. | 0–1 |
| `focalPoint` | intensity-weighted centroid of the saliency map after thresholding at its 80th percentile | (0–1, 0–1) |
| `ruleOfThirdsScore` | `1 − d / 0.4714`, where `d` is the distance from the focal point to the nearest `{⅓,⅔}²` intersection and `0.4714` is the worst possible such distance (a corner) | 0–1 |
| `edgeDensity` | Canny edge pixels ÷ total pixels; thresholds auto-set from the grayscale median (`0.66·m`, `1.33·m`). `cluttered` above **0.18** | 0–1 |
| `negativeSpace` | fraction of 16×16 tiles with edge density `< 0.02` **and** luminance std `< 12` | 0–1 |
| `balance.lr` / `.tb` | weight map `w = norm(S) · norm(localContrast) · norm(edges)`; `1 − |A − B| / (A + B)` for left/right and top/bottom sums | 0–1 |
| `depth.backgroundBlur` | `1 − min(1, lapVar(background) / lapVar(subject))`, where subject = saliency above its 60th percentile | 0–1 |

---

## 6. Faces — `analysis/faces.py`

Detector preference, best first. The response always reports which one ran, in
`detector` — a YuNet detection and a Haar detection are not the same evidence, and
presenting them identically would be dishonest.

| Order | Detector | Notes |
|---|---|---|
| 1 | **YuNet** (`face_detection_yunet_2023mar.onnx`, confidence ≥ 0.55) | The strongest option available, and the only DNN format OpenCV 5 still imports. Returns five landmarks, so the eye-line is measured directly rather than inferred from a second cascade pass. |
| 2 | `res10_300x300_ssd` Caffe | Only loadable on OpenCV 4.x — the Caffe importer was removed in 5. Kept for deployments pinned to 4.x. |
| 3 | Haar cascades | Frontal + profile (plus a mirrored profile pass), merged by NMS at IoU 0.35. No model download beyond the XML files. |
| 4 | none | `available: false`, with the reason and the fix named. |

Models are fetched by `scripts/fetch_models.py` and baked into the Docker image at build
time, so the running container never needs network access for them.

| Metric | Formula |
|---|---|
| `areaPercent` | `bbox area / image area × 100` |
| `quadrant` | face centroid → 3×3 grid cell |
| `eyeLineUpperThird` | eyes located with `haarcascade_eye` inside the face ROI; the mean eye-centre `y` is compared against `y < 1/3`. **`null`** when no eyes are resolvable — not guessed. |
| `expression` | *estimate*, geometric: smile cascade hit rate, mouth-open ratio (ink/edge energy in the lower face third relative to the middle third), and eye-open ratio. Maps to `joy / surprise / anger / neutral` with a confidence. Always returned under `"method": "geometric-estimate"` and labelled an estimate in the UI. |

---

## 7. Safe zones — `analysis/safezones.py`

Real YouTube chrome, in normalised coordinates:

| Zone | Region |
|---|---|
| `duration_pill` | x 0.84–0.98, y 0.82–0.95 |
| `cc_badge` | x 0.02–0.14, y 0.82–0.95 |
| `progress_bar` | x 0.00–1.00, y 0.96–1.00 |
| `hover_crop` | outer 2 % border |

A collision is any overlap with a text block or face bbox. Severity is the fraction of the
**element** covered: `> 0.35` high, `> 0.12` medium, `> 0` low.

---

## 8. Technical quality — `analysis/quality.py`

| Metric | Formula |
|---|---|
| `sharpness` | variance of the Laplacian (`float64`, 3×3 kernel) |
| `noise` | Immerkær estimator: `σ = sqrt(π/2) / (6(W−2)(H−2)) · Σ|I ∗ M|`, `M = [[1,−2,1],[−2,4,−2],[1,−2,1]]`, normalised by 255 |
| `compressionArtifacts` | mean gradient energy across 8-px block boundaries ÷ mean gradient energy elsewhere. `< 1.15` low, `< 1.45` medium, else high |
| `meetsYouTubeSpec` | `w ≥ 1280` **and** `h ≥ 720` **and** aspect within 1 % of 16:9 **and** `bytes ≤ 2 MB` |

---

## 9. Scoring — `analysis/scoring.py`

Eight sub-scores, 0–100, each a pure function of the metrics above. A score is `null`
when its inputs genuinely do not exist (no text detected → no readability score); null
scores are excluded from the overall and their weight is redistributed proportionally.
The UI shows `—`, never a fabricated number.

### Weights (published here, and in the "How is this scored?" popover)

| Sub-score | Weight |
|---|---|
| Stopping Power | **0.20** |
| Text Readability | **0.15** |
| Mobile Legibility | **0.14** |
| Color Impact | **0.12** |
| Contrast & Legibility | **0.12** |
| Composition | **0.12** |
| Emotional Hook | **0.10** |
| Safe Zone Safety | **0.05** |

`overall = Σ(wᵢ · sᵢ) / Σ(wᵢ)` over non-null scores, rounded to the nearest integer.

### Sub-score formulas

**Stopping Power**
```
satPunch   = band(satMean, 0.45, 0.75, 0.15, 0.95)
range      = lin(globalContrast, 0.25, 0.85)
edgeFocus  = band(edgeDensity, 0.06, 0.16, 0.01, 0.30)
faceSignal = 1.00 if largestFace ≥ 15%  else 0.55 if any face  else 0.30
salConc    = lin(fraction of saliency mass in the top 20% of area, 0.35, 0.75)
score      = 100 · (0.28·satPunch + 0.26·range + 0.16·edgeFocus + 0.18·faceSignal + 0.12·salConc)
```

**Text Readability** — `null` if no text
```
capScore  = mean over blocks of lin(capHeightPx@168×94, 8, 18)
wcag      = mean over blocks of lin(wcagContrast, 2.0, 7.0)
words     = 1.00 (1–4) | 0.75 (5–6) | 0.45 (7–9) | 0.20 (10+)
score     = 100 · (0.45·capScore + 0.35·wcag + 0.20·words)
```

**Color Impact**
```
base      = {complementary 1.00, split-complementary 0.95, triadic 0.90,
             analogous 0.80, monochromatic 0.70, custom 0.50}
harmony   = base · (0.6 + 0.4·confidence)
sat       = band(satMean, 0.40, 0.80, 0.10, 1.00)
distinct  = lin(mean pairwise ΔE76 between swatches, 20, 70)
penalty   = 0.5 · max(0, clippedBlack + clippedWhite − 0.08)
score     = 100 · clip(0.35·harmony + 0.35·sat + 0.30·distinct − penalty, 0, 1)
```

**Contrast & Legibility**
```
with text:    100 · (0.35·lin(globalContrast,0.25,0.85) + 0.25·lin(localMean,8,45) + 0.40·meanTextWcag)
without text: 100 · (0.55·lin(globalContrast,0.25,0.85) + 0.45·lin(localMean,8,45))
```

**Composition**
```
100 · (0.30·thirds + 0.25·mean(balance.lr, balance.tb)
     + 0.20·band(negativeSpace, 0.15, 0.45, 0.02, 0.75)
     + 0.25·(1 − lin(edgeDensity, 0.18, 0.40)))
```

**Emotional Hook**
```
faces present: 100 · (0.45·band(largestFaceArea%, 12, 45, 3, 70)
                    + 0.25·(1.0 upper-third | 0.5 lower | 0.6 unknown)
                    + 0.30·expressionWeight · expressionConfidence)
               expressionWeight = surprise 1.00 | joy 1.00 | anger 0.90 | neutral 0.50
no faces:      min(65, 100 · (0.45·satPunch + 0.55·salConc))   — capped, with the reason stated
```

**Mobile Legibility** — `null` if no text
```
v(surface) = 1.00 PASS | 0.55 WARNING | 0.10 FAIL
score      = 100 · (0.32·mobile_feed + 0.22·mobile_search + 0.18·desktop_sidebar
                  + 0.18·desktop_grid + 0.10·watch_page)
```

**Safe Zone Safety**
```
score = max(0, 100 − Σ collisions(high 35 | medium 18 | low 7))
```

Every sub-score is returned alongside a `reason` string generated from the deterministic
inputs — e.g. *"Cap height is 9 px in the mobile feed; anything under 10 px is unreadable."*

---

## 10. The Claude pass — `analysis/ai.py`

Model `claude-opus-4-8`, adaptive thinking, `effort: high`, structured output enforced by
`output_config.format`. The image is downscaled to a 1568 px long edge before base64
encoding. The system prompt is frozen and carries the cache breakpoint; the per-thumbnail
metrics JSON goes after it.

Claude is instructed that the measurements are the only permitted source of numbers,
colors and ratios, and to return `null` for anything it cannot determine. It cannot change
a score — scoring has already run and its output is part of Claude's input.

Failure of any kind returns HTTP 200 with `ai: null` and a populated `aiError`.
