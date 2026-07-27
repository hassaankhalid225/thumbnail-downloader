# ThumbIQ — Project Plan

Build order, with the exit condition for each step. Nothing moves on until its exit
condition is met. Status is kept current as the build progresses.

| # | Step | Exit condition | Status |
|---|---|---|---|
| 0 | Environment + docs | yt-dlp, OpenCV, deps verified; six docs written | ✅ done |
| 1 | `services/detector.py` | all 9 YouTube URL shapes → correct ID; 10 malformed → clean reject | ✅ done |
| 2 | `services/fetcher.py` | SSRF guard blocks loopback/private/link-local/CGNAT incl. per redirect hop; 20 MB cap aborts mid-stream | ✅ done |
| 3 | `extractors/youtube.py` | 10 ladder entries HEAD-validated concurrently; grey 120×90 placeholder rejected on HTTP 200 | ✅ done |
| 4 | `extractors/` tier 2 + tier 3 | Vimeo, Dailymotion, TikTok, X, Twitch resolve; og scraper passes the HTML fixture | ✅ done |
| 5 | `services/imaging.py` | 8 sizes × 3 formats, real byte counts, honest native/upscaled tag, saliency-anchored crop | ✅ done |
| 6 | `analysis/color.py` | synthetic 3-color image → the 3 hexes within ΔE tolerance | ✅ done |
| 7 | `analysis/contrast.py` | black↔white = 21.00; `#767676`↔white = 4.54 | ✅ done |
| 8 | `analysis/text.py` | generated image with known text at a known size → cap height within 10 % | ✅ done |
| 9 | `analysis/composition.py` | synthetic image with a bright blob → focal point lands on the blob | ✅ done |
| 10 | `analysis/faces.py` | detector reports which backend ran; no face → empty list, not a guess | ✅ done |
| 11 | `analysis/safezones.py` | text placed in the duration pill → high-severity collision | ✅ done |
| 12 | `analysis/quality.py` | blurred copy of an image scores lower sharpness than the original | ✅ done |
| 13 | `analysis/scoring.py` | fixed metric input → byte-identical scores (snapshot test) | ✅ done |
| 14 | `analysis/ai.py` | structured output parsed; `APIConnectionError` → 200 with `ai: null` | ✅ done |
| 15 | Routers + error map | every row of the error table reachable and correct | ✅ done |
| 16 | Frontend shell + design system | tokens, layout, navbar, hero render at 375 px and 1440 px | ✅ done |
| 17 | Thumbnail grid + downloads | every size/format downloads with correct dimensions and filename | ✅ done |
| 18 | Analysis panel | all six tabs render from live data; every metric has a tooltip | ✅ done |
| 19 | Flow states | all 9 states reachable, including PARTIAL | ✅ done |
| 20 | Motion choreography | the reveal sequence runs; `prefers-reduced-motion` kills transforms | ✅ done |
| 21 | Compare + channel modes | 3-URL compare picks the right winner; channel report renders | ✅ done |
| 22 | SEO, landing pages, legal | sitemap, robots, JSON-LD, 6 platform pages, privacy/terms/dmca | ✅ done |
| 23 | Tests | backend suite green | ✅ done |
| 24 | Deployment | Dockerfile, railway.toml, vercel.json, compose | ✅ done |

---

## Sequencing rationale

**Backend before frontend, deterministic before AI.** The frontend renders whatever the
analyzer measures; building it first would mean designing around imagined data. Within the
analyzer, the deterministic layer is built and tested first because the AI layer consumes
its output — the reverse order would leave Claude ungrounded.

**Each analysis module is validated against a synthetic image with a known answer before
the next one starts.** A KMeans palette that looks plausible is not evidence; a
three-color test image whose exact hexes come back is.

**The download path never depends on the analysis path.** They are separate endpoints and
separate frontend requests specifically so a slow or failed AI call can never stop a user
getting their image. This is a structural decision, not an optimisation.

## Risks tracked during the build

| Risk | Mitigation |
|---|---|
| `maxresdefault.jpg` grey-placeholder trap | three-part validation (status + content-length + decoded dimensions) |
| Tesseract absent on the host | Connected-component text localisation runs regardless; only transcription needs Tesseract, and `textSource` says which ran |
| `res10` DNN model needs a download | `scripts/fetch_models.py` + the Dockerfile fetch it; `detector` field always reports which backend ran |
| `cv2.saliency` only in contrib builds | NumPy spectral-residual implementation of the identical algorithm as fallback |
| Claude cost | analysis cached by image content hash, system prompt prompt-cached, per-IP hourly AI limit, usage logged to `/api/health` |
| CPU-bound CV blocking the event loop | every analysis runs in `asyncio.to_thread` behind a bounded semaphore |

## Corrections made during the build

Three things the original plan got wrong, found by testing rather than by reading:

| Assumed | Actual | What changed |
|---|---|---|
| MSER would localise text | OpenCV 5's MSER returns **zero** regions on flat high-contrast input — exactly what a thumbnail headline is | Replaced with connected components over four binarisations, which behave the same on a poster and a photograph |
| `res10` Caffe DNN for faces | OpenCV 5 removed the Caffe importer entirely | YuNet ONNX as primary (better, and it returns eye landmarks); res10 kept for 4.x; Haar as the floor |
| Thread pool would parallelise the CV | Two Python loops held the GIL and serialised everything | Vectorised both; a full analysis went from ~2.7 s to ~750 ms and the pool actually runs in parallel |
