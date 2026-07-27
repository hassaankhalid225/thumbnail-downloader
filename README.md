# ThumbIQ

Download any video thumbnail in every size, then find out — with real measurements —
why it works.

> ### ⚙️ The analyzer is currently switched OFF
>
> `NEXT_PUBLIC_ENABLE_ANALYSIS=false` in `frontend/.env.local`. The app runs as a pure
> thumbnail downloader: no analysis request is fired, no scores or AI verdict render,
> `/compare` and `/channel` show a "switched off" notice, the upload-your-own-image path
> is hidden, and every piece of copy and metadata drops its analysis claims so the page
> never promises something it isn't doing.
>
> **Nothing was deleted.** The backend analysis modules, the scoring engine, the Claude
> pass and every component under `components/analysis/` are intact and untouched — they
> are simply not reached. Set the flag to `true`, restart, and the full product below
> comes back exactly as documented.

Right now a creator uses two tools: a janky site to grab a competitor's thumbnail, and
their own eye to guess why it performs. ThumbIQ is one tool that does both, and the
second half is the point: it tells you the colour science, the text placement, the
mobile legibility and the focal point, as numbers taken from real pixels.

```
┌ backend/   FastAPI · yt-dlp · OpenCV · scikit-learn · Tesseract · Claude
└ frontend/  Next.js 16 · React 19 · Tailwind v4 · Framer Motion · TypeScript strict
```

---

## Run it

### Docker (everything, one command)

```bash
ANTHROPIC_API_KEY=sk-ant-... docker compose up --build
# web  → http://localhost:3000
# api  → http://localhost:8000/api/docs
```

The key is optional. Without it the AI verdict shows an amber banner and **every
measurement still runs** — that degradation path is a designed feature, not an accident.

### Local

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate      # or: source .venv/bin/activate
pip install -r requirements.txt
python scripts/fetch_models.py                      # face-detection models, one time
cp .env.example .env                                # add your key if you have one
uvicorn main:app --reload --port 8000

# frontend
cd frontend
npm install
cp .env.example .env.local                          # analyzer flag lives here
npm run dev                                         # http://localhost:3000
```

**Turning the analyzer back on:** set `NEXT_PUBLIC_ENABLE_ANALYSIS=true` in
`frontend/.env.local` and restart. That single flag controls the whole feature — the
analysis request, the score panel, compare, channel, the shared-result page, the
upload-your-own-draft path, the nav links, the sitemap entries, and every line of copy
and metadata that mentions analysis.

**Tesseract is optional.** Install it (`apt-get install tesseract-ocr`, or the
UB-Mannheim build on Windows) to get the actual transcribed words. Without it, ThumbIQ
still *locates* every text block geometrically and measures its size, placement,
contrast and mobile legibility — only the transcription is missing, and the response
says so via `textSource`.

---

## What it actually measures

Every number in the UI comes from a computation on a real pixel. The full formula for
each one is in [`ANALYSIS_SPEC.md`](ANALYSIS_SPEC.md), including the exact scoring
weights, which are also published in the app's "How is this scored?" popover.

| | |
|---|---|
| **Palette** | KMeans k=6 in **LAB**, not RGB — RGB distance isn't perceptual, so clustering there merges colours your eye separates. Plus harmony classification, temperature from LAB b\*, and CSS/Tailwind/ASE exports. |
| **Text** | Connected-component localisation over four binarisations, then Tesseract for transcription if available. Cap height is measured from the ink row profile, so descenders don't inflate it. |
| **Mobile legibility** | The thumbnail is physically resampled to the five sizes YouTube renders at, and the text is re-measured on each. Under 10px cap height fails. **No other tool checks this.** |
| **Composition** | Spectral-residual saliency → focal point, thirds alignment, edge density, negative space, L/R and T/B weight balance, background separation. |
| **Faces** | YuNet ONNX (with eye landmarks), falling back to res10 Caffe on OpenCV 4.x, then Haar cascades. The response always names which one ran. |
| **Safe zones** | YouTube's duration pill, CC badge, progress bar and hover crop, drawn on your image in red where they collide. |
| **Quality** | Laplacian sharpness, Immerkær noise, 8×8 block artifact ratio, spec compliance. |
| **AI verdict** | Claude Opus 4.8 receives the image *and* the measurements, and is instructed those are the only permitted source of any number. It writes the insight; the code produces the facts. |

---

## The rules this is built on

**Zero fabricated numbers.** Byte counts come from real encodes. Cap heights come from
real ink profiles. Contrast ratios are WCAG 2.1 against the pixels actually behind the
letters.

**A score with no basis is `null`, not a guess.** A thumbnail with no text has no text
readability. Returning 70 "to be safe" would be a fabricated measurement — instead the
score shows `—`, is excluded from the overall, and its weight is redistributed. The
popover names what was left out and why.

**Honest labels everywhere.** Upscaled sizes say upscaled. The font read is a
classification of letterform geometry with closest-match suggestions, never an
identification. Expression detection says estimate. The download card previews the
actual crop shape you'll receive, not a stand-in.

**The AI can never set a number.** Scoring runs before the Claude call, and its output
is part of Claude's input.

**Graceful degradation is a feature.** AI down → everything else works. Tesseract
missing → text is located but not read, and the UI says so. YuNet missing → Haar
fallback, named in the response. Tier 1 fails → tier 2 catches it.

**Nothing is stored.** No database, no object store, no gallery. Images live in a
60-minute in-memory cache and are then gone. See [`LEGAL.md`](LEGAL.md).

---

## Verified

Measured on this build, not asserted:

| Check | Result |
|---|---|
| Backend test suite | **118 passing** |
| Lighthouse (production build) | Accessibility **100** · Best Practices **100** · SEO **100** · Performance **85–88** (noisy on a loaded dev machine) |
| Console on the production build | **zero** errors, **zero** warnings across all 12 routes plus a full analysis run |
| Horizontal overflow at 375 px | none (`scrollWidth == clientWidth`) |
| Keyboard-only flow | every stop interactive, every focus ring visible, submit works from the keyboard alone |
| `prefers-reduced-motion` | dial lands on its final value, no transform animations left running |
| Steady-state analysis | ~750 ms for a 1280×720 thumbnail |
| Live platform sweep | YouTube (watch/Shorts/youtu.be), TikTok, Vimeo, X, Twitch resolve; deleted → 404, private → 403, garbage → 400, SSRF → 400 |

Performance lands in the mid-80s rather than 90+. Only the tool is a client island — the
hero copy, feature grid, platform list, use cases and FAQ are all server-rendered and
ship no JavaScript — and Framer Motion, Lucide and react-icons are tree-shaken via
`optimizePackageImports`. The remaining gap is the motion library plus the analysis panel
on the home route, and closing it means replacing Framer Motion or deferring the panel
behind a dynamic import. That's a real trade-off, not a config tweak. It isn't fixed, and
it isn't being reported as fixed.

## Tests

```bash
cd backend && python -m pytest        # 118 tests
```

Each analysis module is validated against a synthetic image whose answer is known before
the code runs: a three-colour image whose exact hexes must come back within ΔE 6, a
black/white pair that must produce exactly 21.00, glyphs drawn at a known cap height that
must be measured within 10%, a bright blob whose position the focal point must find.

The scoring snapshot was hand-computed from the published formulas before being asserted
— if a formula changes, the test fails and `ANALYSIS_SPEC.md` has to change with it.

Also covered: all 9 YouTube URL shapes plus 10 malformed ones, the grey-placeholder trap
(rejected even on HTTP 200), the SSRF guard across loopback / private / link-local /
CGNAT / IPv4-mapped-IPv6, the og:image scraper against an HTML fixture, and every AI
failure mode returning 200 with the deterministic analysis intact.

---

## Docs

| File | What's in it |
|---|---|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | The 3-tier resolution ladder, the analysis pipeline, caching, data flow |
| [`ANALYSIS_SPEC.md`](ANALYSIS_SPEC.md) | Every metric: exact formula, range, meaning, and the scoring weights |
| [`API_SPEC.md`](API_SPEC.md) | Every endpoint with request/response schemas and the full error table |
| [`COMPONENT_MAP.md`](COMPONENT_MAP.md) | Every UI component, its props and who owns state |
| [`PROJECT_PLAN.md`](PROJECT_PLAN.md) | Build order with the exit condition for each step |
| [`LEGAL.md`](LEGAL.md) | Copyright position, retention policy, DMCA process |

---

## Deploy

Backend needs a container — Tesseract is a system binary and OpenCV needs libGL, so
`pip install` alone produces an image that imports `cv2` and then dies.

```bash
# backend  → Railway (railway.toml), Fly, Render, or any Docker host
# frontend → Vercel (vercel.json), set API_URL to the backend origin
```

Set `API_URL` server-side only. The browser never learns the analyzer's address — every
request goes through the Next route handlers under `/api`.
