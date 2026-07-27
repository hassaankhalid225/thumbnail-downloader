# ThumbIQ — Architecture

ThumbIQ resolves a thumbnail from any video URL, renders it into a full download ladder,
and measures it. Two halves, one request path:

```
                     ┌──────────────────────────────────────────────┐
  browser  ─────────▶│  Next.js 16 (App Router, RSC + client isles) │
                     │  app/api/* = thin proxy (hides API origin,   │
                     │              adds timeouts, normalises errs) │
                     └───────────────────┬──────────────────────────┘
                                         │ JSON over HTTP
                     ┌───────────────────▼──────────────────────────┐
                     │  FastAPI (async)                             │
                     │                                              │
                     │  routers/  thumbnails · analyze · batch      │
                     │            download   · health               │
                     │                                              │
                     │  ┌ RESOLUTION LADDER ───────────────────┐    │
                     │  │ tier 1 platform fast path (<300ms)   │    │
                     │  │ tier 2 yt-dlp metadata-only          │    │
                     │  │ tier 3 og:image scrape               │    │
                     │  └──────────────────────────────────────┘    │
                     │  ┌ ANALYSIS PIPELINE ───────────────────┐    │
                     │  │ deterministic CV (numpy/opencv/PIL)  │    │
                     │  │        ↓ facts as JSON               │    │
                     │  │ Claude vision pass (opinion only)    │    │
                     │  └──────────────────────────────────────┘    │
                     └──────────────────────────────────────────────┘
```

---

## 1. The three-tier resolution ladder

Every URL enters `services/detector.py`, which classifies the platform from the hostname
and path. The ladder then runs top-down and **stops at the first tier that yields a
validated image**. Each tier records how it resolved so the response can report
`resolvedVia`.

### Tier 1 — platform fast path (`extractors/youtube.py`, `vimeo.py`, `dailymotion.py`, `tiktok.py`)

No subprocess, no third-party API key. For YouTube this is pure URL construction: extract
the 11-character ID, build the ten known `i.ytimg.com` paths, and `HEAD` all of them
concurrently with `asyncio.gather`.

**Validation is three-part**, because YouTube lies:

| Check | Why |
|---|---|
| `status == 200` | obvious |
| `content-length > 2000` | `maxresdefault.jpg` often 200s with a grey 120×90 placeholder |
| decoded `(w, h)` within tolerance of the expected size | catches placeholders that pass the byte check |

`hqdefault.jpg` always exists and acts as the guaranteed floor. Anything failing
validation is dropped from the set — a broken card is never rendered.

Vimeo and TikTok go through oEmbed; Dailymotion uses its direct thumbnail host plus
oEmbed for metadata. Vimeo's oEmbed returns a `_295x166`-suffixed URL, which is rewritten
to larger renditions and re-validated.

### Tier 2 — yt-dlp universal (`extractors/ytdlp_universal.py`)

`skip_download=True`, metadata only, never touches the video stream. Runs inside
`asyncio.to_thread` so the event loop stays free. `info["thumbnails"]` is sorted by
`width × height` descending, deduped by URL, and each candidate is HEAD-validated.
This one path covers Instagram, Facebook, X, Twitch, Reddit, Pinterest, LinkedIn,
Rumble, Odysee, Bilibili, Kick, Streamable, Bitchute, VK and ~1800 other extractors.

### Tier 3 — Open Graph scrape (`extractors/og_scraper.py`)

Real browser User-Agent, HTML only, capped at 2 MB. Priority order:
`og:image:secure_url` → `og:image` → `twitter:image` → `twitter:image:src` →
`<link rel="image_src">` → largest `<img>` in the document.

All three tiers exhausted → `404 "No thumbnail found for this link"`. Never a stack trace.

### Fetch safety (`services/fetcher.py`)

Every outbound fetch — tier 1, 2, 3 and the image download itself — goes through one
guarded client:

- DNS-resolve the host first, then reject private, loopback, link-local, multicast,
  reserved and CGNAT ranges (SSRF guard, applied per redirect hop too)
- 20 MB hard cap, enforced by streaming and aborting mid-body
- 15 s connect / 30 s total
- `Content-Type` must be `image/*` for image fetches
- EXIF stripped on every re-encode

---

## 2. The size ladder, and honesty about it

`services/imaging.py` takes the best validated native source and renders eight standard
sizes with Lanczos resampling. Every entry is tagged:

- `source: "native"` — the target is ≤ the native resolution on both axes; pure downscale
- `source: "upscaled"` — the target exceeds native on some axis; a mild unsharp mask
  (radius 1.2, percent 55, threshold 3) is applied and the UI shows an **Upscaled** badge

Non-16:9 targets (SD 4:3, Vertical 9:16, Square 1:1) are produced by **cover-crop around
the measured saliency centroid**, not a naive centre crop, so the subject survives the
reframe. The crop origin is reported in the response.

Each size is encoded to JPG, PNG and WebP up-front so the byte counts shown in the UI are
measured, not estimated. All 24 renditions live in the rendition cache keyed by
`sha256(native bytes)`, so `/api/download` is a cache read.

---

## 3. The analysis pipeline

`analysis/pipeline.py` orchestrates. The ordering rule that makes the product
trustworthy: **deterministic first, AI second, and the AI never produces a number.**

```
image bytes
   │
   ├─ decode once → RGB ndarray (+ LAB, HSV, grey derivatives computed once and shared)
   │
   ├─ color.py        palette (KMeans k=6 in LAB), harmony, temperature, saturation,
   │                  brightness distribution, CSS/Tailwind/ASE exports
   ├─ contrast.py     WCAG 2.1 relative luminance + ratio, global contrast, local maps
   ├─ text.py         connected-component localisation over 4 binarisations (always on),
   │                  Tesseract psm 11 + psm 6 for transcription (optional), block
   │                  clustering, word count, quadrant mapping, text-area ratio,
   │                  per-block WCAG, font-style class
   ├─ mobile          text.py re-runs OCR on 5 physically downscaled renders
   ├─ composition.py  spectral-residual saliency → focal point, thirds, edge density,
   │                  negative space, L/R + T/B balance, background-blur depth cue
   ├─ faces.py        YuNet ONNX (→ res10 Caffe on cv2 4.x → Haar) → bbox, area %,
   │                  quadrant, eye-line from landmarks
   ├─ safezones.py    duration pill / CC badge / progress bar / hover crop collisions
   ├─ quality.py      Laplacian sharpness, noise σ, 8×8 block artifact energy, spec check
   │
   ├─ scoring.py      the eight sub-scores + weighted overall — pure function of the above
   │
   └─ ai.py           Claude opus 4.8 vision pass. Receives the image AND the metrics
                      JSON. Writes prose, hooks, archetype, improvements, recreate recipe.
                      Fails → ai: null + aiError, everything above still returned.
```

The CV work is CPU-bound, so `pipeline.py` runs it inside `asyncio.to_thread` with a
bounded semaphore (`ANALYSIS_CONCURRENCY`, default 4) to keep the event loop responsive
under load.

**Why the hot loops are vectorised.** Threads only help if the work releases the GIL.
NumPy and OpenCV do; Python loops do not. Two loops originally didn't: the negative-space
tile scan (3,600 iterations on a 1280×720 frame) and the connected-component shape filter
(tens of thousands of iterations on a photograph). Both held the GIL long enough to
serialise every concurrent analysis in the pool, which is what turned a 24-thumbnail
channel report into a multi-minute request. Rewritten as array operations, a full
analysis is ~750 ms and the pool genuinely runs in parallel.

The first KMeans and the first DNN forward pass cost over a second of one-time library
initialisation, so `main.py` runs one throwaway analysis at startup. The first real
request is then as fast as the hundredth.

### Why the AI is last and constrained

Claude receives the measured facts as a JSON block and is instructed to use only those
numbers. It has no ability to overwrite a score. If it is unavailable, rate-limited, or
the key is missing, the endpoint still returns HTTP 200 with the full deterministic
analysis and a populated `aiError`. The tool degrades, it does not fail.

---

## 4. Caching and cost control

Three caches, all in-memory TTL (`cachetools`), all bounded, nothing on disk:

| Cache | Key | TTL | Purpose |
|---|---|---|---|
| `resolution` | normalised URL | 60 min | skip re-running the ladder |
| `image` | source URL | 60 min | raw bytes, so re-analysis costs no bandwidth |
| `rendition` | `(sha256, sizeId, format)` | 60 min | download + measured byte counts |
| `analysis` | `sha256(image bytes) + flags` | 60 min | **an identical thumbnail never costs a second Claude call** |

The Claude system prompt is a frozen string with a `cache_control` breakpoint; the
per-thumbnail metrics JSON goes after it, so the ~2.5k-token prefix is a cache read on
every call after the first. Token usage is accumulated per process and exposed on
`/api/health`.

Nothing user-facing is ever written to disk. There is no bucket, no gallery, no
persistence layer. This is a deliberate legal position, documented in `LEGAL.md`.

---

## 5. Frontend data flow

The page is a state machine (`IDLE → DETECTING → RESOLVING → THUMBNAILS_READY →
ANALYZING_CV → ANALYZING_AI → COMPLETE`, plus `ERROR` and `PARTIAL`). Two independent
requests fire so the AI never blocks a download:

1. `POST /api/thumbnails` → grid renders as soon as it lands
2. `POST /api/analyze` → deterministic scores render, then the AI card resolves

Server components render the static marketing shell and the platform landing pages; the
tool itself is a client island. Analysis results are shareable via a compressed
URL-encoded payload on `/analyze/[id]` — no server-side result storage.

---

## 6. Deviation from the brief's pinned versions

The brief pins Next 14 / Tailwind v3 and also instructs to research current versions.
Built on **Next 16.2 / React 19.2 / Tailwind v4.3 / framer-motion 12.42**, which are the
current stable releases. The App Router paradigm, all the class names and the design
system in the brief carry over unchanged; Tailwind v4 moves config from `tailwind.config.js`
into a CSS `@theme` block, which is the only structural difference.
