# 🎯 MASTER PROMPT — ThumbIQ (Multi-Platform Thumbnail Downloader + AI Analyzer)
# Claude Code Pro Max — Full Production Build
# Copy this ENTIRE prompt and paste into Claude Code

---

You are a world-class senior full-stack engineer, computer-vision developer and UI/UX designer. Your task is to build **ThumbIQ** — a production-grade, stunning, fully functional **Multi-Platform Thumbnail Downloader + AI Thumbnail Analyzer** from scratch.

**The core insight this product is built on:** Right now a creator has to use TWO tools — one janky site to download a competitor's thumbnail, and then guess by eye why it works. There is NO tool that downloads the thumbnail in every size AND tells you *why it performs* — the color science, the text placement, the mobile legibility, the focal point. ThumbIQ is that combined tool.

This is NOT a demo or prototype. Every feature must work in real production. No dummy data. No placeholder functions. No fake scores. Every number the UI shows must come from a real measurement of a real pixel.

---

## PHASE 0 — RESEARCH & SETUP (Do this FIRST before writing any code)

### Step 0.1 — Read All Relevant Skills
```bash
cat /mnt/skills/public/frontend-design/SKILL.md
```
Study it fully. Apply ALL design guidelines throughout the entire project.

Also load the Claude API skill before writing ANY AI-analysis code — do not write Anthropic SDK calls from memory:
```bash
cat ~/.claude/skills/claude-api/SKILL.md
cat ~/.claude/skills/claude-api/python/claude-api/README.md
```

### Step 0.2 — Research Latest Versions
```bash
npm info next version
npm info tailwindcss version
npm info framer-motion version
python3 -m pip index versions yt-dlp 2>/dev/null | head -5
python3 -m pip index versions anthropic 2>/dev/null | head -5
python3 -m pip index versions opencv-python-headless 2>/dev/null | head -5
python3 -m pip index versions pillow 2>/dev/null | head -5
```

### Step 0.3 — Verify System Dependencies
```bash
which yt-dlp || pip install yt-dlp --break-system-packages
yt-dlp --version
which tesseract || echo "INSTALL: apt-get install -y tesseract-ocr"
tesseract --version
python3 -c "import cv2; print(cv2.__version__)" || echo "INSTALL opencv-python-headless"
echo $ANTHROPIC_API_KEY | head -c 8   # must be set for AI analysis
```

### Step 0.4 — Create Project Structure
```bash
mkdir -p ~/thumbiq && cd ~/thumbiq
```

### Step 0.5 — Create Full Documentation Before Coding
Create these files BEFORE touching any source code:

- **`ARCHITECTURE.md`** — full system architecture, the 3-tier thumbnail resolution ladder, the hybrid analysis pipeline, data flow
- **`PROJECT_PLAN.md`** — phase-by-phase implementation plan
- **`API_SPEC.md`** — every endpoint with request/response schemas
- **`ANALYSIS_SPEC.md`** — every metric: exact formula, input, output range, what it means, how it maps to a score
- **`COMPONENT_MAP.md`** — every UI component, props, state, purpose
- **`LEGAL.md`** — copyright / fair-use position, retention policy, DMCA process

---

## PHASE 1 — BACKEND CORE (FastAPI)

### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI (async)
- **Universal extractor:** yt-dlp
- **Image processing:** Pillow + OpenCV (`opencv-python-headless`) + NumPy
- **Clustering:** scikit-learn (KMeans for palette)
- **OCR:** pytesseract (Tesseract) — with EasyOCR as optional fallback
- **AI:** `anthropic` Python SDK
- **HTTP:** httpx (async, with proper User-Agent + timeouts)
- **Cache:** cachetools TTL cache (in-memory) — thumbnails cached max 60 min, then evicted
- **Rate limiting:** slowapi
- **ZIP:** stdlib `zipfile` + `io.BytesIO` (never write user content to disk permanently)

### File Structure
```
backend/
├── main.py                     # FastAPI app entry
├── routers/
│   ├── thumbnails.py           # /api/thumbnails
│   ├── analyze.py              # /api/analyze, /api/analyze/compare
│   ├── batch.py                # /api/batch/channel
│   ├── download.py             # /api/download, /api/download/zip
│   └── health.py               # /api/health
├── extractors/
│   ├── base.py                 # Extractor ABC -> returns ThumbnailSet
│   ├── youtube.py              # Tier-1 fast path (pure URL construction)
│   ├── vimeo.py                # oEmbed
│   ├── dailymotion.py          # oEmbed + direct URL
│   ├── tiktok.py               # oEmbed -> yt-dlp fallback
│   ├── ytdlp_universal.py      # Tier-2: works for ALL remaining platforms
│   └── og_scraper.py           # Tier-3: og:image / twitter:image last resort
├── analysis/
│   ├── pipeline.py             # Orchestrates deterministic -> AI
│   ├── color.py                # Palette, harmony, temperature, saturation
│   ├── composition.py          # Thirds, focal point, edge density, neg. space
│   ├── text.py                 # OCR, text boxes, size, placement, legibility
│   ├── faces.py                # Face detect, size %, position, eye-line
│   ├── contrast.py             # WCAG contrast, local contrast maps
│   ├── quality.py              # Sharpness, noise, exposure, compression
│   ├── safezones.py            # Duration pill / UI overlay collision check
│   ├── scoring.py              # Deterministic metrics -> 8 sub-scores
│   └── ai.py                   # Claude vision pass (grounded by metrics)
├── services/
│   ├── detector.py             # Platform URL detection
│   ├── imaging.py              # Resize ladder, format conversion, upscale
│   ├── fetcher.py              # Safe image fetch (SSRF guard, size caps)
│   └── cache.py
├── models/
│   ├── request.py
│   └── response.py
├── middleware/rate_limit.py
├── utils/validators.py
├── requirements.txt
└── .env.example
```

---

## PHASE 2 — THE THUMBNAIL RESOLUTION LADDER (Most Important Backend Logic)

Never rely on one method. Every URL goes through a 3-tier ladder and **stops at the first tier that returns a usable image**.

### Tier 1 — Platform Fast Path (target: <300ms, zero subprocess)

**YouTube — pure URL construction, no API key, no yt-dlp.**

Extract the 11-char video ID from ALL of these formats:
```
youtube.com/watch?v=ID
youtu.be/ID
youtube.com/shorts/ID
youtube.com/embed/ID
youtube.com/live/ID
youtube.com/v/ID
m.youtube.com/watch?v=ID
music.youtube.com/watch?v=ID
youtube-nocookie.com/embed/ID
+ any of the above with extra query params (&t=, ?si=, playlists)
```
Regex must be strict: `[a-zA-Z0-9_-]{11}`.

Then build the full ladder and **HEAD-check every one** (concurrently with `asyncio.gather`):

| Label | URL pattern | Native size |
|---|---|---|
| Max HD | `https://i.ytimg.com/vi/{ID}/maxresdefault.jpg` | 1280×720 |
| HD 720 | `https://i.ytimg.com/vi/{ID}/hq720.jpg` | 1280×720 |
| SD | `https://i.ytimg.com/vi/{ID}/sddefault.jpg` | 640×480 |
| HQ | `https://i.ytimg.com/vi/{ID}/hqdefault.jpg` | 480×360 |
| MQ | `https://i.ytimg.com/vi/{ID}/mqdefault.jpg` | 320×180 |
| Default | `https://i.ytimg.com/vi/{ID}/default.jpg` | 120×90 |
| WebP Max | `https://i.ytimg.com/vi_webp/{ID}/maxresdefault.webp` | 1280×720 |
| Frame 1/2/3 | `https://i.ytimg.com/vi/{ID}/1.jpg` `2.jpg` `3.jpg` | 120×90 |

**CRITICAL GOTCHA — you MUST handle this:** `maxresdefault.jpg` does not exist for many videos. YouTube sometimes 404s and sometimes returns a **grey 120×90 placeholder with HTTP 200**. So validation = `status == 200` **AND** `content-length > 2000` **AND** decoded dimensions match the expected size. If it fails, drop that entry from the list — never show a broken card.

`hqdefault.jpg` always exists — use it as the guaranteed floor.

**Vimeo:** `https://vimeo.com/api/oembed.json?url={url}` → `thumbnail_url`. The returned URL has a `_295x166`-style suffix — strip/replace it to request larger renditions, then validate.

**Dailymotion:** `https://www.dailymotion.com/thumbnail/video/{id}` plus oEmbed for metadata.

**TikTok:** `https://www.tiktok.com/oembed?url={url}` → `thumbnail_url` (usually 720×1280 vertical). Falls through to Tier 2 when oEmbed is rate-limited.

### Tier 2 — yt-dlp Universal (works for everything else)

Run yt-dlp in **metadata-only mode** — never download the video:
```python
ydl_opts = {
    "skip_download": True,
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "socket_timeout": 15,
    "extract_flat": False,
}
info = ydl.extract_info(url, download=False)
# info["thumbnails"] -> [{"url":..., "width":..., "height":..., "preference":...}]
# info["thumbnail"]  -> best single
```
Sort `thumbnails[]` by `width * height` descending, dedupe by URL, validate each with a HEAD request, and return the set.

This one path covers: **Instagram, Facebook, Twitter/X, Twitch, Reddit, Pinterest, LinkedIn, Snapchat, Rumble, Odysee, Bilibili, Kick, Streamable, SoundCloud artwork, Bitchute, VK** and 1000+ more sites.

### Tier 3 — Open Graph Scraper (last resort)

Fetch the page HTML with a real browser User-Agent and read, in priority order:
`og:image:secure_url` → `og:image` → `twitter:image` → `twitter:image:src` → first `<link rel="image_src">` → largest `<img>` in the document head area.

If all three tiers fail, return a clean 404 with the message *"No thumbnail found for this link"* — never a stack trace.

### Size Ladder Generation — and be HONEST about it

After resolving the best native source, generate the standard download ladder with Pillow (Lanczos):

| Name | Size | Aspect |
|---|---|---|
| Full HD | 1920×1080 | 16:9 |
| HD | 1280×720 | 16:9 |
| SD | 640×480 | 4:3 |
| HQ | 480×360 | 4:3 |
| MQ | 320×180 | 16:9 |
| Tiny | 120×90 | 4:3 |
| Vertical HD | 1080×1920 | 9:16 (Shorts/Reels/TikTok) |
| Square | 1080×1080 | 1:1 |

**Non-negotiable honesty rule:** every generated size must be tagged `"source": "native"` or `"source": "upscaled"`. If the native source is 1280×720, the Full HD 1920×1080 entry is `upscaled` and the UI **must** show a small "Upscaled" badge on that card. Do not silently sell users a fake 1080p. Apply a mild unsharp mask on upscales and say so in the tooltip.

Also offer format conversion for every size: **JPG / PNG / WebP**.

### Fetcher Safety (`services/fetcher.py`) — do not skip
- Block private/loopback/link-local IP ranges (SSRF guard) before fetching
- Max download size 20 MB — abort the stream past that
- Timeout 15s connect / 30s total
- Only accept `image/*` content types
- Strip EXIF on re-encode (privacy)

---

## PHASE 3 — THE AI ANALYSIS ENGINE (This Is The Product)

**Architecture rule that makes this tool trustworthy:** run **deterministic computer vision FIRST**, then hand those hard numbers to Claude as grounding context. The model writes the *insight*; the code produces the *facts*. Claude must never invent a hex code, a pixel measurement, or a contrast ratio — those come from NumPy.

### 3.1 — Color Analysis (`analysis/color.py`)

- Downsample to 200×200, convert RGB → **LAB** color space (perceptually uniform — do NOT cluster in RGB)
- **KMeans, k=6** → dominant palette. For each swatch return: `hex`, `rgb`, `lab`, `coverage_percent`, `human_name` (nearest CSS/xkcd color name)
- **Color harmony detection** — convert the top swatch hues to HSV degrees and classify the relationship:
  - Complementary (~180° ± 15)
  - Split-complementary (~150°/210°)
  - Analogous (all within 45°)
  - Triadic (~120° apart)
  - Monochromatic (hue spread < 20°, varying L)
  - Return `harmony_type` + `confidence`
- **Color temperature** — warm/cool ratio from the LAB `b*` channel mean
- **Saturation profile** — mean + std of HSV `S`. Flag `"punchy"` (mean S > 0.55), `"muted"` (< 0.30)
- **Brightness distribution** — histogram of `L*`, plus % pixels clipped black (<5) and clipped white (>250)
- **Palette exports** — generate ready-to-paste CSS custom properties, a Tailwind color object, and an Adobe `.ase`-compatible JSON

### 3.2 — Text Detection & Placement (`analysis/text.py`)

- OCR with Tesseract at `--psm 11` (sparse text) AND `--psm 6`, merge results, dedupe
- For every detected word/line return: `text`, `bbox {x,y,w,h}`, `confidence`, `height_percent_of_image`
- Group words into **text blocks** using bbox proximity clustering
- **Word count** — the single strongest thumbnail heuristic. Score: 1–4 words = excellent, 5–6 = good, 7+ = penalized. State the reason in the output.
- **Placement quadrant** — map each block to a 3×3 grid cell (top-left … bottom-right) and to a rule-of-thirds intersection
- **Text-area ratio** — total text bbox area ÷ image area. Sweet spot 8–25%.
- **Local contrast per text block** — sample the background pixels immediately behind/around each text bbox, compute the **WCAG 2.1 contrast ratio** against the text's own dominant color. Report pass/fail at 4.5:1 and 3:1.
- **Font style classification** — do NOT claim exact font identification (impossible from a raster image without a licensed matching service, and lying here destroys trust). Instead classify: `geometric-sans / grotesque / condensed / extended / slab-serif / didone / script / handwritten / display-brush`, with stroke-weight (`light/regular/bold/black`), italic detection, and letter-case pattern. Then return **3 free Google Fonts that are visually closest** (e.g. Anton, Bebas Neue, Archivo Black, Montserrat ExtraBold, Inter Black, Oswald) each with a confidence %, clearly labelled **"Closest match — not an exact identification."**

### 3.3 — Mobile Legibility Simulation (KILLER FEATURE — build this properly)

This is the metric no competitor has. Physically downscale the thumbnail to the **actual pixel sizes YouTube renders at**, then re-measure:

| Surface | Rendered size |
|---|---|
| Mobile feed | 168×94 |
| Mobile search | 246×138 |
| Desktop home grid | 360×202 |
| Desktop sidebar / suggested | 168×94 |
| Full watch-page preview | 1280×720 |

For each surface: re-run OCR on the downscaled image and compute the **text cap-height in real pixels**. Rules:
- cap-height < 10px → **FAIL** ("your text is unreadable in the mobile feed")
- 10–14px → **WARNING**
- > 14px → **PASS**

Also render a real side-by-side preview of all five in the UI. This single feature is worth the whole product to a creator.

### 3.4 — Composition & Focal Point (`analysis/composition.py`)

- **Saliency map** — OpenCV `saliency.StaticSaliencySpectralResidual` → centroid = the focal point
- **Rule of thirds** — distance from focal centroid to the nearest of the 4 intersection points, normalized 0–1
- **Edge density (busyness)** — Sobel/Canny edge pixel ratio; flag `"cluttered"` above threshold
- **Negative space %** — low-edge, low-variance regions
- **Visual balance** — split into left/right and top/bottom halves, compare visual weight (saturation × contrast × edge density); report a balance score
- **Depth cues** — background blur estimate (Laplacian variance of background region vs subject region), which correlates with "professional" look

### 3.5 — Face & Emotion (`analysis/faces.py`)

- Detect with OpenCV DNN face detector (`res10_300x300_ssd`) — more reliable than Haar cascades
- For each face: `bbox`, `area_percent_of_image`, `position_quadrant`, whether the **eye-line sits in the upper third** (a strong engagement heuristic)
- Face count. Flag: face present + face > 15% of frame = strong hook
- Optionally run an expression classifier and report `surprise / joy / anger / neutral` with confidence. Report it as a *signal*, not a fact — clearly labelled as an estimate.

### 3.6 — Safe Zones & UI Collisions (`analysis/safezones.py`)

Overlay the real YouTube UI chrome regions and detect collisions with detected text/faces:
- **Duration pill** — bottom-right, approx `x: 84–98%, y: 82–95%` — the #1 real-world mistake creators make
- **"CC"/live badge** — bottom-left
- **Progress bar (watched)** — bottom 3–4% strip
- **Hover-preview crop** — outer 2% can be cropped on some surfaces

Return a list of collisions with severity, and render a **visual overlay** in the UI so the user actually sees the duration pill sitting on top of their text.

### 3.7 — Technical Quality (`analysis/quality.py`)
- Sharpness: variance of Laplacian
- Noise estimate
- JPEG compression artifact estimate (8×8 block edge energy)
- Aspect ratio + native resolution check against the 1280×720 / 2MB YouTube recommendation
- File size

### 3.8 — Scoring (`analysis/scoring.py`)

Produce 8 sub-scores (0–100) from the deterministic metrics ONLY — the AI does not set the numbers, it explains them:

| Score | Driven by |
|---|---|
| **Stopping Power** | saturation punch, contrast range, edge focus, face presence |
| **Text Readability** | cap-height at 168×94, WCAG contrast, word count |
| **Color Impact** | harmony type, saturation, palette distinctiveness |
| **Contrast & Legibility** | global contrast, per-text-block WCAG ratios |
| **Composition** | thirds alignment, balance, negative space, clutter |
| **Emotional Hook** | face size, eye-line, expression confidence |
| **Mobile Legibility** | the 5-surface simulation results |
| **Safe Zone Safety** | UI collision severity |

**Overall ThumbIQ Score** = weighted mean. Publish the weights in `ANALYSIS_SPEC.md` and expose them in a "How is this scored?" popover in the UI. A black-box score is worthless; a transparent one is a feature.

### 3.9 — The Claude Vision Pass (`analysis/ai.py`)

Load the Claude API skill before writing this file. Implementation requirements:

- SDK: `anthropic` (Python). **Never** hand-roll HTTP.
- Model: **`claude-opus-4-8`** (exact string, no date suffix)
- `thinking={"type": "adaptive"}` — this is a genuinely analytical task
- `output_config={"effort": "high", "format": {...json schema...}}` — structured output, so the frontend never parses prose
- Image goes in as a content block:
  ```python
  {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}}
  ```
  Downscale to max 1568px on the long edge before encoding (larger buys nothing and costs tokens).
- **Prompt-cache the system prompt** — it's the stable prefix and it's long. Put the per-thumbnail metrics JSON *after* the cache breakpoint.
- `max_tokens=8000`, non-streaming is fine here.
- Wrap in a typed error chain: `NotFoundError` → `RateLimitError` → `APIStatusError` → `APIConnectionError`. On failure, **still return the deterministic analysis** with `"ai_analysis": null` and a UI notice — the tool must stay useful when the AI call fails.

**The system prompt must instruct Claude to:**
1. Explain **why this thumbnail works (or doesn't)** in a creator's language — no design jargon dumps
2. Use ONLY the supplied measurements when citing numbers, colors, or ratios
3. Name the **psychological hook** (curiosity gap, transformation/before-after, authority, controversy, number/list, threat/warning, relatability)
4. Identify the **style archetype** (MrBeast high-saturation, minimal-editorial, documentary-still, meme/reaction, tech-clean, faceless-graphic, course/tutorial)
5. Give **5 specific, actionable improvements**, each with the concrete change ("move the word 'FREE' up 12% — it currently sits under the duration pill"), never generic advice
6. Predict the **likely niche and target audience** from visual cues
7. Return `null` for anything it cannot determine — hallucination is a bug, not a soft failure

**Output JSON schema (enforce with `output_config.format`):**
```json
{
  "verdict": "string — one punchy sentence",
  "why_it_works": ["string", "..."],
  "why_it_fails": ["string", "..."],
  "psychological_hook": {"type": "string", "explanation": "string"},
  "style_archetype": {"name": "string", "confidence": 0.0},
  "font_read": {"classification": "string", "weight": "string", "closest_google_fonts": [{"name":"string","confidence":0.0}], "disclaimer": "string"},
  "color_story": "string — what the palette communicates emotionally",
  "text_placement_critique": "string",
  "target_audience": "string",
  "likely_niche": "string",
  "improvements": [{"priority":1,"change":"string","why":"string","expected_impact":"string"}],
  "recreate_recipe": {"palette":["#hex"],"font_style":"string","layout":"string","subject_treatment":"string"}
}
```

The `recreate_recipe` field is the money feature — it tells the creator exactly how to build their own thumbnail in this style, without copying the image.

---

## PHASE 4 — API ENDPOINTS (All must be fully functional)

**POST /api/thumbnails**
```json
Request:  { "url": "https://youtube.com/watch?v=dQw4w9WgXcQ" }
Response: {
  "success": true,
  "platform": "youtube",
  "platformName": "YouTube",
  "videoId": "dQw4w9WgXcQ",
  "title": "Video title",
  "uploader": "Channel Name",
  "duration": 213,
  "views": 1600000000,
  "publishedAt": "2009-10-25",
  "native": { "url": "https://i.ytimg.com/vi/ID/maxresdefault.jpg", "width": 1280, "height": 720, "bytes": 128400 },
  "sizes": [
    { "id":"fhd","label":"Full HD","width":1920,"height":1080,"source":"upscaled","bytes":410000,"formats":["jpg","png","webp"] },
    { "id":"hd","label":"HD","width":1280,"height":720,"source":"native","bytes":128400,"formats":["jpg","png","webp"] },
    { "id":"sd","label":"SD","width":640,"height":480,"source":"native","bytes":41200,"formats":["jpg","png","webp"] }
  ],
  "resolvedVia": "tier1_youtube",
  "elapsedMs": 240
}
```

**POST /api/analyze**
```json
Request:  { "url": "...", "sizeId": "hd", "includeAI": true }
Response: {
  "success": true,
  "scores": { "overall": 78, "stoppingPower": 84, "textReadability": 61, "colorImpact": 88,
              "contrast": 72, "composition": 80, "emotionalHook": 90, "mobileLegibility": 55, "safeZone": 40 },
  "color": { "palette":[{"hex":"#FF3B30","coverage":31.2,"name":"Red","lab":[53,80,67]}],
             "harmony":{"type":"complementary","confidence":0.81},
             "temperature":"warm","saturation":{"mean":0.62,"profile":"punchy"},
             "exports":{"css":"...","tailwind":{...}} },
  "text": { "blocks":[{"text":"I QUIT","bbox":{"x":0.08,"y":0.62,"w":0.44,"h":0.18},
                       "capHeightPx":128,"wcagContrast":8.4,"passesAA":true}],
            "wordCount":2, "textAreaRatio":0.14, "fontStyle":"condensed-sans-black" },
  "mobileLegibility": [ {"surface":"mobile_feed","size":"168x94","capHeightPx":9,"verdict":"FAIL"} ],
  "composition": { "focalPoint":{"x":0.68,"y":0.41}, "ruleOfThirdsScore":0.86,
                   "edgeDensity":0.22, "negativeSpace":0.31, "balance":{"lr":0.94,"tb":0.71} },
  "faces": [ {"bbox":{...},"areaPercent":18.4,"quadrant":"right-center","eyeLineUpperThird":true} ],
  "safeZones": { "collisions":[{"zone":"duration_pill","severity":"high","overlapsText":"QUIT"}] },
  "quality": { "sharpness":412.8,"noise":0.04,"compressionArtifacts":"low","meetsYouTubeSpec":true },
  "ai": { ...schema from Phase 3.9... },
  "aiError": null
}
```

**POST /api/analyze/compare** — accepts 2–4 URLs, returns each analysis plus a `winner` object with a head-to-head breakdown per score category.

**POST /api/batch/channel** — accepts a channel/profile URL, pulls the latest N (max 24) video thumbnails via yt-dlp `extract_flat`, analyzes all in a bounded concurrency pool (max 4 at once), and returns a **channel pattern report**: recurring palette across thumbnails, dominant text placement, face-usage rate, average word count, style consistency score.

**POST /api/download** → `{ url, sizeId, format }` → streams the image with `Content-Disposition: attachment; filename="thumbiq_youtube_<id>_1280x720.jpg"`

**POST /api/download/zip** → all selected sizes/formats zipped in memory, streamed back.

**GET /api/health** → `{ "status":"ok", "yt_dlp":"2025.x.x", "tesseract":"5.x", "opencv":"4.x", "ai":"reachable", "uptime":3600 }`

### Error Handling — every case, proper code, human message
| Case | Code | Message |
|---|---|---|
| Invalid / unparseable URL | 400 | "Please enter a valid video or post link" |
| Private or age-restricted | 403 | "This content is private or restricted" |
| Deleted / not found | 404 | "This video no longer exists" |
| No thumbnail available | 404 | "No thumbnail found for this link" |
| Platform unsupported | 422 | "We can't read this platform yet — tell us about it" |
| Rate limited | 429 | "Too many requests. Please wait a moment" (+ `Retry-After`) |
| Geo-blocked | 451 | "This content isn't available in our server region" |
| Image too large | 413 | "That image is too large to process" |
| AI unavailable | 200 | Return deterministic analysis + `aiError` + UI banner |
| Extractor crash | 500 | "Could not process this link. Please try again" |

---

## PHASE 5 — FRONTEND (Next.js 14 + Tailwind + Framer Motion)

### Tech Stack
- Next.js 14 App Router, TypeScript **strict** (no `any`)
- Tailwind CSS v3
- Framer Motion
- Lucide React + React Icons (platform logos)
- Recharts (or hand-built SVG) for score gauges and the color-coverage bar
- Dark theme ONLY

### Color System — use EXACTLY these values
Deliberately different from a generic purple SaaS look — this is a *lab / analyzer*, so it reads like an instrument panel.
```css
--bg-primary:    #0A0A0D   /* page */
--bg-secondary:  #101015   /* card */
--bg-tertiary:   #16161D   /* elevated */
--border:        #232330
--border-hover:  #33334A
--text-primary:  #F2F2F7
--text-secondary:#8E8EA8
--text-muted:    #55556B
--accent:        #C8FF3D   /* electric lime — primary CTA, active states */
--accent-dim:    #9BCC26
--accent-glow:   rgba(200,255,61,0.28)
--data-cyan:     #22D3EE   /* charts, secondary data */
--data-violet:   #A78BFA   /* charts */
--score-great:   #22C55E   /* 80-100 */
--score-good:    #C8FF3D   /* 60-79  */
--score-ok:      #F59E0B   /* 40-59  */
--score-bad:     #EF4444   /* 0-39   */
```

Typography: **Inter** for UI, **JetBrains Mono** for every number, hex code and measurement. Numbers in mono is what makes it feel like a real instrument.

### Platform Colors
```js
const PLATFORM_COLORS = {
  youtube:   { accent: '#FF0000' }, tiktok:    { accent: '#FE2C55' },
  instagram: { accent: '#E1306C' }, twitter:   { accent: '#1DA1F2' },
  facebook:  { accent: '#1877F2' }, twitch:    { accent: '#9146FF' },
  vimeo:     { accent: '#1AB7EA' }, dailymotion:{accent: '#0066DC' },
  pinterest: { accent: '#E60023' }, reddit:    { accent: '#FF4500' },
  linkedin:  { accent: '#0A66C2' }, rumble:    { accent: '#85C742' },
}
```

### File Structure
```
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                        # Home: input + downloader + analyzer
│   ├── analyze/[id]/page.tsx           # Shareable analysis result page
│   ├── compare/page.tsx                # Side-by-side compare mode
│   ├── channel/page.tsx                # Channel pattern report
│   ├── (platforms)/
│   │   ├── youtube-thumbnail-downloader/page.tsx
│   │   ├── tiktok-thumbnail-downloader/page.tsx
│   │   ├── instagram-thumbnail-downloader/page.tsx
│   │   ├── vimeo-thumbnail-downloader/page.tsx
│   │   ├── twitter-thumbnail-downloader/page.tsx
│   │   └── facebook-thumbnail-downloader/page.tsx
│   ├── api/                            # thin proxy routes to FastAPI
│   └── globals.css
├── components/
│   ├── hero/{HeroSection,UrlInput,PlatformDetector,GridBackground}.tsx
│   ├── thumbnails/{ThumbnailGrid,SizeCard,FormatToggle,DownloadAllButton,UpscaledBadge}.tsx
│   ├── analysis/
│   │   ├── ScoreDial.tsx               # animated circular gauge
│   │   ├── ScoreBreakdown.tsx          # 8 sub-score bars
│   │   ├── PaletteStrip.tsx            # click-to-copy hex swatches
│   │   ├── ColorHarmonyWheel.tsx       # SVG hue wheel with plotted swatches
│   │   ├── TextOverlayCanvas.tsx       # bboxes drawn over the thumbnail
│   │   ├── SafeZoneOverlay.tsx         # YouTube UI chrome overlay
│   │   ├── MobilePreviewStrip.tsx      # the 5 real-size renders
│   │   ├── FocalPointMap.tsx           # thirds grid + saliency dot
│   │   ├── FontReadCard.tsx
│   │   ├── AIVerdict.tsx
│   │   ├── ImprovementList.tsx
│   │   └── RecreateRecipe.tsx
│   ├── compare/{CompareSlots,HeadToHeadTable,WinnerBanner}.tsx
│   ├── ui/{Toast,Spinner,Tooltip,Tabs,CopyButton,Skeleton,Badge}.tsx
│   ├── sections/{HowItWorks,SupportedPlatforms,Features,UseCases,FAQ,Footer}.tsx
│   └── layout/Navbar.tsx
├── lib/{api.ts,utils.ts,constants.ts,colors.ts}
└── public/icons/
```

---

## PHASE 6 — UI/UX IMPLEMENTATION (Read Every Word)

### Hero Section

**Background:** `#0A0A0D` with a faint technical grid (SVG background-image, 1px lines at 4% opacity), plus two very slow-drifting lime/cyan radial glows at 10% opacity. Restrained — this is an instrument, not a party.

**Headline:**
```
Steal the thumbnail.
Understand the strategy.
```
Inter 800, 68px desktop / 38px mobile. "Understand the strategy" gets the lime gradient `from-[#C8FF3D] to-[#22D3EE]`. Animate in: fade + 12px up, word-stagger 40ms.

**Sub-headline:**
`Download any thumbnail in every size — then let AI break down the colors, fonts, text placement and why it actually works.`

**URL Input Bar — the most important element:**
```tsx
<div className="relative group">
  <div className="absolute -inset-px bg-gradient-to-r from-[#C8FF3D] to-[#22D3EE]
                  rounded-2xl blur-sm opacity-0 group-focus-within:opacity-60
                  transition duration-500" />
  <div className="relative flex items-center bg-[#101015] rounded-2xl border border-[#232330]
                  focus-within:border-[#C8FF3D]/50 p-2 gap-3">
    <PlatformDetector url={value} />           {/* live platform logo fade-in */}
    <input
      placeholder="Paste a YouTube, TikTok, Instagram or any video link…"
      className="flex-1 bg-transparent text-white text-lg outline-none px-2 font-mono"
    />
    <button className="text-[#8E8EA8] hover:text-white flex items-center gap-1.5 px-3">
      <ClipboardIcon className="w-4 h-4" /> Paste
    </button>
    <button className="bg-[#C8FF3D] text-black px-7 py-3 rounded-xl font-bold
                       hover:brightness-110 hover:scale-[1.02] transition-all">
      Analyze
    </button>
  </div>
</div>
```
Below it: platform logo strip (12 logos, greyscale at 40%, the detected one snaps to full color + scale 1.15).

Also support **drag-and-drop of an image file** and **paste-image-from-clipboard** onto the page — a creator often wants to analyze their own draft thumbnail before publishing. That path skips extraction and goes straight to analysis.

### The Flow — State Machine (implement ALL states)

1. **IDLE** — input, paste button, platform strip, three example links to try
2. **DETECTING** (0–400ms) — platform logo animates in, tiny spinner in the input
3. **RESOLVING** (0.3–3s) — indeterminate bar, text cycles: "Finding thumbnail…" → "Checking available sizes…"
4. **THUMBNAILS_READY** — the download grid reveals (height animation). The analysis panel below shows skeleton loaders and keeps working. **Never block downloads on the AI call.**
5. **ANALYZING_CV** (0.5–2s) — deterministic scores stream in one by one, each dial animating from 0
6. **ANALYZING_AI** (3–12s) — AI card shows a shimmer with rotating status: "Reading the composition…" → "Judging the text placement…" → "Writing the verdict…"
7. **COMPLETE** — everything settled, share button appears
8. **ERROR** — input shakes horizontally, toast with the specific human message
9. **PARTIAL** — thumbnails + CV analysis succeeded, AI failed → amber banner: "AI analysis unavailable right now — everything else below is live."

### Thumbnail Download Grid
```
┌────────────────────────┐  ┌────────────────────────┐
│  [preview image]       │  │  [preview image]       │
│  Full HD · 1920×1080   │  │  HD · 1280×720         │
│  410 KB  ⬆ Upscaled    │  │  128 KB  ✓ Native      │
│  [JPG] [PNG] [WEBP]    │  │  [JPG] [PNG] [WEBP]    │
│  [ Download ]          │  │  [ Download ]  ★BEST   │
└────────────────────────┘  └────────────────────────┘
```
Sticky action bar at the bottom of the grid: `Select all · Download ZIP · Copy image URL`.

### The Analysis Panel

**Top row — the ThumbIQ Score.** A large animated SVG dial (0→score, spring easing, ~1.2s), color-coded by band, with the one-line verdict beside it and a "How is this scored?" popover that lists the exact weights.

**Second row — 8 sub-score bars,** each with an icon, the number in mono, and a one-line reason pulled from the deterministic layer.

**Tabbed detail area:**
- **Colors** — palette strip (click any swatch to copy hex; shift-click copies the whole palette), coverage bar chart, the harmony wheel, and Copy-as-CSS / Copy-as-Tailwind buttons
- **Text** — the thumbnail with OCR bounding boxes drawn over it, extracted text with a copy button, per-block WCAG contrast pills, the font-read card with its "closest match, not exact" disclaimer
- **Mobile Check** — the 5 real-size renders in a row with PASS/WARN/FAIL badges. This tab should be visually loud when something fails.
- **Composition** — thirds grid + saliency dot overlaid on the image, balance meters, clutter reading
- **Safe Zones** — the YouTube duration pill and progress bar drawn on top of the thumbnail in red where they collide
- **AI Verdict** — the verdict sentence, why-it-works / why-it-fails lists, psychological hook, style archetype, target audience, the 5 prioritized improvements, and the Recreate Recipe card

Every metric gets a `?` tooltip explaining what it measures and why it matters. Teaching the user *is* the retention loop.

### Compare Mode
2–4 thumbnails side by side, aligned score rows, per-category winner highlighting, and an overall winner banner with a one-line reason. Shareable URL.

### Channel Mode
Paste a channel URL → grid of the last 24 thumbnails, each with its score, plus a **pattern report**: the channel's recurring palette, most-used text position (heatmap), face-usage rate, average word count, consistency score.

---

## PHASE 7 — ANIMATIONS (Framer Motion)

**Page load sequence:**
```
0ms    grid background + glows fade in
150ms  navbar slides down
300ms  headline word-stagger up
550ms  sub-headline fades
700ms  input bar scales 0.96 → 1 with glow pulse
900ms  platform logos stagger in left→right
```

**Analysis reveal choreography (get this right — it's the "wow" moment):**
```
0ms    thumbnail grid height-animates open
200ms  score dial sweeps 0 → value (spring, stiffness 60)
400ms  the 8 sub-bars fill left→right, 60ms stagger
700ms  palette swatches pop in scale 0.8 → 1, 40ms stagger
900ms  OCR bounding boxes draw themselves (SVG pathLength 0→1)
1100ms mobile preview strip slides in
       AI card shimmers until its data lands, then crossfades
```

**Micro-interactions:** swatch hover lifts + shows hex in mono; copy shows a checkmark morph; score bars glow on hover; size cards lift 4px with an accent border; error state = 3-cycle horizontal shake; failing mobile-legibility badges get a single attention pulse.

Respect `prefers-reduced-motion` — disable transforms, keep opacity fades only.

---

## PHASE 8 — SEO, LEGAL & PRODUCTION

### Metadata
```tsx
export const metadata: Metadata = {
  title: 'ThumbIQ — Download & Analyze Any Video Thumbnail (Free AI Tool)',
  description: 'Download YouTube, TikTok, Instagram & Vimeo thumbnails in SD, HD and Full HD — then get an instant AI breakdown of colors, fonts, text placement and why the thumbnail works. Free, no signup.',
  keywords: 'youtube thumbnail downloader, thumbnail analyzer, tiktok thumbnail download, thumbnail color palette, ai thumbnail analysis, competitor thumbnail research',
  openGraph: { title: 'ThumbIQ — Download & Analyze Any Thumbnail', images: ['/og-image.png'], type: 'website' },
  twitter: { card: 'summary_large_image' },
}
```

**Structured data:** `WebApplication`, `FAQPage` (10 Qs), `HowTo` (3 steps), `BreadcrumbList` on platform pages.

**Platform landing pages** — each with a 600-word original guide, platform-specific FAQ (5 Qs), correct title tag, e.g. `"YouTube Thumbnail Downloader — HD, Full HD & 4K Sizes Free | ThumbIQ"`.

**Sitemap** (`app/sitemap.ts`) + **robots.txt** (allow all, point to sitemap).

### Legal — implement, don't hand-wave
Thumbnails are copyrighted works owned by their creators. ThumbIQ positions as an **analysis, research and educational reference tool**, not a redistribution service. Ship all of this:
- A visible line under the tool: *"Thumbnails are the property of their creators. Use for research and inspiration — don't republish someone else's thumbnail as your own."*
- **No permanent storage.** Images live only in a TTL cache (max 60 min) and are streamed to the user. Never persist to a bucket. Never build a public gallery of other people's thumbnails.
- `/privacy`, `/terms`, `/dmca` pages with a real takedown contact and a documented process
- Do not strip or bypass any platform's access controls — Tier 2 only reads publicly available metadata
- The `recreate_recipe` output is deliberately a *recipe*, not a copy — reinforce this in the UI copy: "Build your own in this style."

### Config
```js
// next.config.js
const nextConfig = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'i.ytimg.com' },
      { protocol: 'https', hostname: '*.cdninstagram.com' },
      { protocol: 'https', hostname: '*.tiktokcdn.com' },
      { protocol: 'https', hostname: '*.vimeocdn.com' },
      { protocol: 'https', hostname: '*.jtvnw.net' },
      { protocol: 'https', hostname: '*.twimg.com' },
      { protocol: 'https', hostname: '*.fbcdn.net' },
      { protocol: 'https', hostname: '*.dmcdn.net' },
    ],
    formats: ['image/avif', 'image/webp'],
  },
  compress: true,
  poweredByHeader: false,
  async headers() {
    return [{ source: '/(.*)', headers: [
      { key: 'X-Frame-Options', value: 'DENY' },
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
    ]}]
  },
}
```

### Environment
```
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=https://thumbiq.app

# backend/.env
ANTHROPIC_API_KEY=sk-ant-...
ALLOWED_ORIGINS=http://localhost:3000,https://thumbiq.app
RATE_LIMIT_THUMBNAILS_PER_MIN=30
RATE_LIMIT_ANALYZE_PER_MIN=10
RATE_LIMIT_AI_PER_HOUR=40
CACHE_TTL_SECONDS=3600
MAX_IMAGE_BYTES=20971520
AI_MODEL=claude-opus-4-8
AI_ENABLED=true
```

**Cost control (real money is involved):** AI analysis is rate-limited per IP, the deterministic analysis always runs free, results are cached by image content hash for 1 hour so re-analyzing the same thumbnail costs nothing, and the system prompt is prompt-cached. Log `usage.input_tokens` / `usage.output_tokens` per call and expose a running estimate on `/api/health`.

### requirements.txt
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
yt-dlp>=2025.1.1
anthropic>=0.40.0
pillow==10.4.0
opencv-python-headless==4.10.0.84
numpy==1.26.4
scikit-learn==1.5.1
pytesseract==0.3.13
httpx==0.27.0
pydantic==2.7.0
python-dotenv==1.0.1
slowapi==0.1.9
cachetools==5.3.3
python-multipart==0.0.9
```

---

## PHASE 9 — TESTING (Do NOT skip)

### Backend (pytest)
- Video-ID extraction: all 9 YouTube URL formats + 10 malformed URLs → correct ID or clean rejection
- `maxresdefault` fallback: a video WITH maxres and a video WITHOUT → the missing one must not appear in `sizes`
- The grey-placeholder trap: assert the 120×90 placeholder is rejected even on HTTP 200
- Tier 2 yt-dlp path on a real Vimeo, Dailymotion and Twitter URL
- Tier 3 og:image scraper against a static HTML fixture
- SSRF guard: `http://127.0.0.1:8000`, `http://169.254.169.254/`, `http://10.0.0.1` → all blocked
- Color: a synthetic 3-color image → KMeans must return those 3 hexes within ΔE tolerance
- WCAG contrast: black-on-white → 21.0, mid-grey pair → known value
- OCR: a generated image with known text at a known size → text matches, cap-height within 10%
- Scoring: fixed metric inputs → deterministic, reproducible scores (snapshot test)
- AI failure path: mock an `APIConnectionError` → response still 200 with `ai: null`, `aiError` set

### Frontend manual checklist
- [ ] YouTube standard URL → thumbnails + full analysis ✓
- [ ] YouTube Shorts URL → vertical handled correctly ✓
- [ ] `youtu.be` short link with `?si=` param ✓
- [ ] Video with no maxresdefault → no broken card, no dead image ✓
- [ ] TikTok URL → vertical thumbnail + analysis ✓
- [ ] Instagram Reel → resolves or shows the correct friendly error ✓
- [ ] Vimeo, Dailymotion, Twitter/X, Twitch, Facebook → each resolves ✓
- [ ] Drag-and-drop own image file → analysis runs, no extraction step ✓
- [ ] Paste image from clipboard → same ✓
- [ ] Deleted video → "This video no longer exists" ✓
- [ ] Private video → "private or restricted" ✓
- [ ] Garbage text in input → "valid video or post link" ✓
- [ ] AI key removed → thumbnails + CV analysis still work, amber banner shows ✓
- [ ] Download each size in JPG/PNG/WebP → correct dimensions and filename ✓
- [ ] Download ZIP → opens, contains every selected file ✓
- [ ] Copy hex / copy palette / copy CSS / copy extracted text → all land on clipboard ✓
- [ ] Compare mode with 3 URLs → winner logic correct ✓
- [ ] Channel mode → 24 thumbnails, pattern report renders ✓
- [ ] Mobile 375px → grid stacks, dials readable, touch targets ≥44px ✓
- [ ] Slow 3G throttle → every stage shows a loading state, nothing jumps ✓
- [ ] `prefers-reduced-motion` on → no transform animations ✓
- [ ] Keyboard only → full flow navigable, focus rings visible ✓

---

## PHASE 10 — DEPLOYMENT

### `Dockerfile` (backend — needed because of tesseract + opencv system deps)
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libgl1 libglib2.0-0 ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `railway.toml` (backend)
```toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
restartPolicyType = "on_failure"
```

### `vercel.json` (frontend)
```json
{ "framework": "nextjs", "regions": ["sin1", "iad1"] }
```

---

## EXECUTION ORDER — Follow EXACTLY

1. ✅ Read `frontend-design` skill + `claude-api` skill
2. ✅ Research latest package versions, verify yt-dlp / tesseract / opencv are installed
3. ✅ Write `ARCHITECTURE.md`, `PROJECT_PLAN.md`, `API_SPEC.md`, `ANALYSIS_SPEC.md`, `LEGAL.md`
4. ✅ Backend: `detector.py` → `fetcher.py` (with SSRF guard) → `extractors/youtube.py`
5. ✅ Test Tier 1 with 10 real YouTube URLs including one with no maxresdefault
6. ✅ Build Tier 2 (`ytdlp_universal.py`) and Tier 3 (`og_scraper.py`); test on Vimeo, TikTok, Twitter, Twitch, Instagram
7. ✅ Build `imaging.py` — the size ladder with honest native/upscaled tagging
8. ✅ Build the deterministic analysis modules in this order: `color` → `contrast` → `text` → `composition` → `faces` → `safezones` → `quality` → `scoring`. **Test each one against a synthetic image with a known answer before moving on.**
9. ✅ Build `ai.py` last, grounded by the metrics JSON, with structured output + full error fallback
10. ✅ Frontend: `globals.css` (CSS vars) → layout → HeroSection → ThumbnailGrid → the analysis panel components → sections
11. ✅ Implement all 9 flow states, including PARTIAL
12. ✅ Add all Framer Motion choreography + reduced-motion support
13. ✅ Build compare mode and channel mode
14. ✅ Platform landing pages, SEO meta, JSON-LD, sitemap, legal pages
15. ✅ Run the full test checklist
16. ✅ Dockerfile + deployment configs

---

## QUALITY STANDARDS — Non-Negotiable

- **Zero dummy data** — every score, hex code and pixel measurement comes from a real computation on a real image
- **Zero placeholder functions** — no `# TODO: implement`, no `return 0.5  # stub`
- **The AI never invents numbers** — it only interprets the measurements the CV layer hands it
- **Honest labeling** — upscaled sizes say upscaled; font matches say "closest match, not exact"; estimates say estimate
- **Graceful degradation** — AI down? Tool still works. Tesseract missing? Text tab shows a clear notice, everything else runs. Tier 1 fails? Tier 2 catches it.
- **TypeScript strict mode** — no `any`
- **Mobile-first** — design at 375px, then scale up
- **Lighthouse** — 90+ Performance, 100 Accessibility, 100 SEO
- **Every error has a UI state.** Every async operation has a loading state.
- **Console** — zero errors, zero warnings in the production build

---

## START COMMAND

Begin with Phase 0 immediately. Read the skill files first, then proceed phase by phase. Do not skip a phase. Do not write placeholder code. Build the real thing.

**The goal: a creator pastes a competitor's YouTube link, and within 15 seconds they have the thumbnail in 8 sizes AND a specific, measured, honest explanation of why it works — including the fact that their own text would be illegible in the mobile feed. Nothing on the internet does both today.**
