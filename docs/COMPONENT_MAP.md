# ThumbIQ — Component Map

Next.js 16 App Router. Server components by default; `"use client"` only where a component
owns state, motion, or a browser API. Every prop below is typed in
`frontend/lib/types.ts` — no `any` anywhere in the tree.

---

## Routes

| Route | Rendering | Purpose |
|---|---|---|
| `/` | server shell + `<ThumbIQTool />` client island | the product |
| `/analyze/[id]` | client | a shared analysis, rehydrated from the URL payload — no server storage |
| `/compare` | client | 2–4 thumbnails head to head |
| `/channel` | client | last 24 thumbnails of a channel + pattern report |
| `/(platforms)/youtube-thumbnail-downloader` … ×6 | server | SEO landing pages, 600-word guide + 5 FAQs each |
| `/privacy`, `/terms`, `/dmca` | server | legal |
| `/api/{thumbnails,analyze,analyze-upload,compare,channel,download,download-zip,health}` | route handlers | thin proxy to FastAPI: hides the origin, sets timeouts, normalises errors |
| `/sitemap.xml`, `/robots.txt` | generated | `app/sitemap.ts`, `app/robots.ts` |

---

## State ownership

One hook owns the entire flow: **`useThumbIQ()`** (`lib/useThumbIQ.ts`).

```ts
type FlowState =
  | "IDLE" | "DETECTING" | "RESOLVING" | "THUMBNAILS_READY"
  | "ANALYZING_CV" | "ANALYZING_AI" | "COMPLETE" | "ERROR" | "PARTIAL";
```

It holds `url`, `platform`, `thumbnails`, `analysis`, `error`, `aiError`, and exposes
`submit(url)`, `submitFile(file)`, `reset()`. It fires the two backend requests
independently — the thumbnail grid renders the moment `/api/thumbnails` lands, regardless
of what `/api/analyze` is doing. Every component below is a pure function of that state;
nothing else fetches.

---

## `components/hero/`

| Component | Client | Props | Notes |
|---|---|---|---|
| `HeroSection` | no | `—` | headline, sub-headline, slot for `UrlInput` |
| `UrlInput` | yes | `{ state, onSubmit, onFile, error }` | the primary control. Paste button (`navigator.clipboard.readText`), Enter to submit, drag-and-drop and clipboard-image paste both routed to `onFile`. Shakes on `ERROR`. |
| `PlatformDetector` | yes | `{ url }` | debounced 120 ms; fades in the detected platform's logo in its brand color |
| `PlatformStrip` | yes | `{ active }` | 12 logos at 40 % grayscale; the active one snaps to full color + `scale(1.15)` |
| `GridBackground` | no | `—` | pure CSS/SVG: 1px technical grid at 4 % opacity, two slow-drifting radial glows |

## `components/thumbnails/`

| Component | Client | Props | Notes |
|---|---|---|---|
| `ThumbnailGrid` | yes | `{ data, selected, onToggle }` | height-animates open; renders one `SizeCard` per ladder entry |
| `SizeCard` | yes | `{ size, sourceUrl, platform, selected, onToggle, best }` | preview, label, measured byte count for the active format, format toggle, download button, `★ BEST` on the largest native entry |
| `FormatToggle` | yes | `{ value, onChange, bytesByFormat }` | JPG / PNG / WEBP; the byte count under the card updates to the selected format's real size |
| `UpscaledBadge` | no | `{ from, to }` | `⬆ Upscaled` chip with the tooltip explaining Lanczos + unsharp |
| `DownloadAllButton` | yes | `{ selected, url }` | sticky bar: select all · download ZIP · copy image URL |

## `components/analysis/`

| Component | Client | Props | Notes |
|---|---|---|---|
| `ScoreDial` | yes | `{ score, size, label }` | SVG arc, spring 0→score over ~1.2 s, band-colored |
| `ScoreBreakdown` | yes | `{ scores, weights }` | the 8 sub-bars, mono numbers, one-line deterministic reason each, `?` tooltips |
| `ScoringExplainer` | yes | `{ weights }` | the "How is this scored?" popover — publishes the exact weights |
| `PaletteStrip` | yes | `{ palette }` | click a swatch → copy hex; shift-click → copy the whole palette |
| `ColorHarmonyWheel` | yes | `{ palette, harmony }` | SVG hue wheel with the swatches plotted at their measured hue/saturation |
| `CoverageBar` | no | `{ palette }` | single stacked bar, widths = measured coverage % |
| `TextOverlayCanvas` | yes | `{ src, blocks }` | OCR bboxes drawn over the thumbnail; SVG `pathLength` 0→1 draw-on |
| `ContrastPill` | no | `{ ratio, passesAA }` | mono ratio + AA/AAA state |
| `FontReadCard` | no | `{ fontRead }` | classification, weight, 3 closest Google fonts with confidence, disclaimer always visible |
| `MobilePreviewStrip` | yes | `{ src, surfaces }` | the 5 renders at their true pixel sizes, PASS/WARN/FAIL badges; failing badges pulse once |
| `FocalPointMap` | yes | `{ src, focalPoint, thirdsScore }` | thirds grid + saliency dot |
| `SafeZoneOverlay` | yes | `{ src, zones, collisions }` | YouTube chrome drawn on the thumbnail; colliding zones in red |
| `BalanceMeters` | no | `{ balance, negativeSpace, edgeDensity }` | |
| `QualityReadout` | no | `{ quality }` | mono table |
| `AIVerdict` | yes | `{ ai, loading, error }` | shimmer with rotating status while loading; amber banner on `error` |
| `ImprovementList` | no | `{ improvements }` | the 5 prioritised changes |
| `RecreateRecipe` | yes | `{ recipe }` | palette chips, font style, layout, subject treatment — framed "build your own in this style" |
| `AnalysisTabs` | yes | `{ analysis, src }` | Colors · Text · Mobile Check · Composition · Safe Zones · AI Verdict |

## `components/compare/` and `components/channel/`

| Component | Props |
|---|---|
| `CompareSlots` | `{ urls, onChange, onRun }` — 2–4 inputs |
| `HeadToHeadTable` | `{ results, winner }` — aligned score rows, per-category winner highlight |
| `WinnerBanner` | `{ winner }` |
| `ChannelGrid` | `{ items }` — 24 thumbnails, each with its score |
| `PatternReport` | `{ pattern }` — recurring palette, placement heatmap, face rate, avg word count, consistency |

## `components/ui/`

`Toast` (queue + auto-dismiss) · `Spinner` · `Tooltip` (hover + focus, Escape to close) ·
`Tabs` (roving tabindex, arrow keys) · `CopyButton` (checkmark morph, 1.6 s revert) ·
`Skeleton` · `Badge` · `Progress`.

## `components/sections/` and `components/layout/`

`HowItWorks` · `SupportedPlatforms` · `Features` · `UseCases` · `FAQ` (10 Qs, also the
`FAQPage` JSON-LD source) · `Footer` (carries the copyright line) · `Navbar`.

---

## `lib/`

| File | Exports |
|---|---|
| `api.ts` | `getThumbnails`, `analyze`, `analyzeUpload`, `compare`, `channel`, `downloadUrl`, `downloadZip` — all typed, all normalise the error envelope into `ApiError` |
| `types.ts` | every response type, mirroring `API_SPEC.md` |
| `constants.ts` | `PLATFORM_COLORS`, `PLATFORMS`, `SIZE_LABELS`, `SURFACE_LABELS`, `EXAMPLE_URLS`, `SCORE_META` (icon + tooltip per sub-score) |
| `colors.ts` | `scoreBand()`, `scoreColor()`, `hexToRgb()`, `readableOn()` |
| `utils.ts` | `cn()`, `formatBytes()`, `formatViews()`, `formatDuration()`, `detectPlatform()`, `copyToClipboard()` |
| `useThumbIQ.ts` | the flow hook above |
| `useReducedMotion.ts` | wraps the media query; every motion component reads it |

## Design tokens

Defined once as CSS custom properties in `app/globals.css` and exposed to Tailwind v4 via
`@theme`. Inter for UI, JetBrains Mono for every number, hex and measurement — the mono
numerals are what make the panel read as an instrument rather than a marketing page.
