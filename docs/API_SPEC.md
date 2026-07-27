# ThumbIQ — API Spec

Base URL `http://localhost:8000`. All request and response bodies are JSON unless noted.
Every endpoint is rate-limited per IP (see `.env.example`) and returns `Retry-After` on 429.

---

## `POST /api/thumbnails`

Resolve a URL to its native thumbnail plus the full download ladder.

**Request**
```json
{ "url": "https://youtube.com/watch?v=dQw4w9WgXcQ" }
```

**200**
```json
{
  "success": true,
  "platform": "youtube",
  "platformName": "YouTube",
  "videoId": "dQw4w9WgXcQ",
  "title": "Rick Astley - Never Gonna Give You Up",
  "uploader": "Rick Astley",
  "duration": 213,
  "views": 1600000000,
  "publishedAt": "2009-10-25",
  "sourceUrl": "https://youtube.com/watch?v=dQw4w9WgXcQ",
  "imageHash": "9f2c…",
  "native": {
    "url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    "width": 1280, "height": 720, "bytes": 128400,
    "label": "Max HD", "aspect": "16:9"
  },
  "candidates": [
    { "label": "Max HD", "url": "…/maxresdefault.jpg", "width": 1280, "height": 720, "bytes": 128400 }
  ],
  "sizes": [
    {
      "id": "fhd", "label": "Full HD", "width": 1920, "height": 1080, "aspect": "16:9",
      "source": "upscaled", "bytes": 410000,
      "bytesByFormat": { "jpg": 410000, "png": 2840000, "webp": 288000 },
      "formats": ["jpg", "png", "webp"],
      "crop": null,
      "note": "Upscaled from 1280×720 with Lanczos + unsharp mask."
    },
    {
      "id": "vertical", "label": "Vertical HD", "width": 1080, "height": 1920, "aspect": "9:16",
      "source": "upscaled", "bytes": 512000,
      "bytesByFormat": { "jpg": 512000, "png": 3120000, "webp": 361000 },
      "formats": ["jpg", "png", "webp"],
      "crop": { "x": 0.31, "y": 0.0, "w": 0.38, "h": 1.0, "anchoredTo": "saliency" },
      "note": "Cropped to 9:16 around the measured focal point, then upscaled."
    }
  ],
  "resolvedVia": "tier1_youtube",
  "elapsedMs": 240
}
```

The eight ladder entries are `fhd, hd, sd, hq, mq, tiny, vertical, square`.
`source` is `"native"` when the target is ≤ native on both axes, `"upscaled"` otherwise.
`bytes` is the measured JPG size; `bytesByFormat` carries all three, measured.
`crop` is non-null only for aspect changes and reports the region actually taken.

`resolvedVia` ∈ `tier1_youtube | tier1_vimeo | tier1_dailymotion | tier1_tiktok |
tier2_ytdlp | tier3_opengraph | upload`.

---

## `POST /api/analyze`

**Request**
```json
{ "url": "https://youtube.com/watch?v=…", "sizeId": "hd", "includeAI": true }
```

Or, for a user's own draft, `POST /api/analyze/upload` as `multipart/form-data` with an
`image` file field and an `includeAI` form field. Same response shape, `platform: "upload"`.

**200** (abridged — full field list in `ANALYSIS_SPEC.md`)
```json
{
  "success": true,
  "imageHash": "9f2c…",
  "image": { "width": 1280, "height": 720, "bytes": 128400, "format": "JPEG" },
  "scores": {
    "overall": 78,
    "stoppingPower": 84, "textReadability": 61, "colorImpact": 88, "contrast": 72,
    "composition": 80, "emotionalHook": 90, "mobileLegibility": 55, "safeZone": 40,
    "reasons": {
      "mobileLegibility": "Largest cap height is 9 px in the 168×94 mobile feed — under the 10 px readability floor."
    },
    "weights": { "stoppingPower": 0.20, "textReadability": 0.15, "…": 0 },
    "excluded": []
  },
  "color": {
    "palette": [{ "hex": "#FF3B30", "rgb": [255,59,48], "lab": [53.2,80.1,67.2], "coverage": 31.2, "name": "Tomato" }],
    "harmony": { "type": "complementary", "confidence": 0.81, "hues": [4.2, 187.5] },
    "temperature": { "profile": "warm", "meanB": 14.2, "warmRatio": 0.78 },
    "saturation": { "mean": 0.62, "std": 0.21, "profile": "punchy" },
    "brightness": { "histogram": [], "clippedBlack": 0.012, "clippedWhite": 0.004, "meanL": 51.8 },
    "exports": { "css": ":root { --thumbiq-1: #FF3B30; }", "tailwind": {}, "ase": {} }
  },
  "text": {
    "available": true, "textSource": "ocr", "engine": "tesseract 5.4.0",
    "blocks": [{
      "text": "I QUIT", "words": ["I","QUIT"], "confidence": 91.4,
      "bbox": { "x": 0.08, "y": 0.62, "w": 0.44, "h": 0.18 },
      "capHeightPx": 128, "heightPercent": 17.8,
      "wcagContrast": 8.4, "passesAA": true, "passesAALarge": true,
      "textColor": "#FFFFFF", "backgroundColor": "#12121A",
      "quadrant": "bottom-left", "thirdsDistance": 0.09
    }],
    "wordCount": 2, "wordCountVerdict": "excellent",
    "textAreaRatio": 0.14,
    "fontRead": {
      "classification": "condensed", "weight": "black", "italic": false, "casePattern": "ALL CAPS",
      "strokeWidth": 21.4, "strokeContrast": 0.08, "widthRatio": 0.49, "serifScore": 0.94, "slantDeg": 0.7,
      "closestGoogleFonts": [{ "name": "Anton", "confidence": 0.88 }],
      "disclaimer": "Closest match — not an exact identification."
    }
  },
  "mobileLegibility": {
    "available": true,
    "surfaces": [{
      "surface": "mobile_feed", "label": "Mobile feed", "width": 168, "height": 94,
      "capHeightPx": 9.4, "verdict": "FAIL", "ocrRecoveryRatio": 0.0,
      "reason": "Cap height 9 px — under the 10 px floor."
    }]
  },
  "composition": {
    "focalPoint": { "x": 0.68, "y": 0.41 }, "ruleOfThirdsScore": 0.86,
    "edgeDensity": 0.22, "cluttered": true, "negativeSpace": 0.31,
    "balance": { "lr": 0.94, "tb": 0.71 },
    "depth": { "backgroundBlur": 0.61, "subjectLapVar": 812.4, "backgroundLapVar": 316.9 },
    "saliencyConcentration": 0.58
  },
  "faces": {
    "detector": "haar_cascade", "count": 1,
    "faces": [{
      "bbox": { "x": 0.55, "y": 0.18, "w": 0.3, "h": 0.53 }, "areaPercent": 18.4,
      "quadrant": "right-center", "eyeLineUpperThird": true, "eyeLineY": 0.31,
      "expression": { "label": "surprise", "confidence": 0.62, "method": "geometric-estimate",
                      "disclaimer": "Estimated from facial geometry, not a trained classifier." }
    }]
  },
  "safeZones": {
    "collisions": [{
      "zone": "duration_pill", "zoneLabel": "Duration pill",
      "severity": "high", "overlapFraction": 0.41,
      "element": "text", "elementLabel": "QUIT",
      "region": { "x": 0.84, "y": 0.82, "w": 0.14, "h": 0.13 }
    }],
    "zones": [{ "id": "duration_pill", "x": 0.84, "y": 0.82, "w": 0.14, "h": 0.13 }]
  },
  "quality": {
    "sharpness": 412.8, "noise": 0.041, "compressionArtifacts": "low", "blockRatio": 1.08,
    "width": 1280, "height": 720, "bytes": 128400, "aspect": "16:9", "meetsYouTubeSpec": true,
    "specNotes": []
  },
  "ai": { "verdict": "…", "…": null },
  "aiError": null,
  "aiUsage": { "inputTokens": 2914, "outputTokens": 1180, "cacheReadTokens": 2610, "estimatedCostUsd": 0.0334 },
  "cached": false,
  "elapsedMs": 6120
}
```

`ai` follows the Phase 3.9 schema exactly (`verdict`, `why_it_works`, `why_it_fails`,
`psychological_hook`, `style_archetype`, `font_read`, `color_story`,
`text_placement_critique`, `target_audience`, `likely_niche`, `improvements`,
`recreate_recipe`).

When the AI call fails, the whole response is still 200; `ai` is `null` and `aiError` is
`{ "code": "rate_limited", "message": "…", "retryable": true }`.

---

## `POST /api/analyze/compare`

**Request** — 2 to 4 URLs.
```json
{ "urls": ["…", "…", "…"], "includeAI": false }
```

**200**
```json
{
  "success": true,
  "results": [{ "url": "…", "ok": true, "analysis": { }, "thumbnail": { } }],
  "winner": {
    "url": "…", "index": 1, "overall": 84,
    "reason": "Highest overall, and the only one that stays legible in the mobile feed.",
    "categories": {
      "stoppingPower": { "winnerIndex": 0, "values": [84, 71, 66], "margin": 13 }
    }
  },
  "elapsedMs": 14200
}
```

Individual failures do not fail the request: that entry gets `ok: false` and an `error`
object, and the winner is computed from the successful ones.

---

## `POST /api/batch/channel`

**Request**
```json
{ "url": "https://youtube.com/@channelname", "limit": 24 }
```

`limit` is clamped to 24. yt-dlp runs with `extract_flat` to list videos, then each
thumbnail is resolved and analysed (deterministic only — no AI, to keep it free) in a
bounded pool of 4.

**200**
```json
{
  "success": true,
  "channel": { "name": "Channel Name", "url": "…", "videoCount": 24 },
  "items": [{ "videoId": "…", "title": "…", "thumbnailUrl": "…", "scores": {}, "ok": true }],
  "pattern": {
    "recurringPalette": [{ "hex": "#FF3B30", "frequency": 0.71, "name": "Tomato" }],
    "dominantTextPlacement": { "quadrant": "bottom-left", "share": 0.58,
                               "heatmap": [[0,0,0],[0,0.1,0],[0.58,0.2,0.12]] },
    "faceUsageRate": 0.83,
    "averageWordCount": 3.2,
    "averageScores": { "overall": 74.1 },
    "consistencyScore": 81,
    "consistencyBasis": "Palette ΔE spread, text-placement entropy and face-rate variance across 24 thumbnails."
  },
  "elapsedMs": 38400
}
```

---

## `POST /api/download`

```json
{ "url": "…", "sizeId": "hd", "format": "webp" }
```

Streams the encoded image with
`Content-Disposition: attachment; filename="thumbiq_youtube_dQw4w9WgXcQ_1280x720.webp"`.
Served from the rendition cache, so no re-encode and no second upstream fetch.

## `POST /api/download/zip`

```json
{ "url": "…", "items": [{ "sizeId": "hd", "format": "jpg" }, { "sizeId": "fhd", "format": "png" }] }
```

Builds the archive in `io.BytesIO` and streams it as
`thumbiq_youtube_dQw4w9WgXcQ.zip`. Nothing touches disk. A `README.txt` is included
stating that the thumbnails belong to their creators.

## `GET /api/health`

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime": 3600,
  "ytDlp": "2026.07.04",
  "tesseract": "5.4.0",
  "opencv": "5.0.0",
  "ai": { "enabled": true, "model": "claude-opus-4-8", "reachable": true },
  "faceDetector": "haar_cascade",
  "saliency": "cv2.saliency",
  "cache": { "resolution": 12, "image": 8, "rendition": 96, "analysis": 5 },
  "aiUsage": { "calls": 41, "inputTokens": 119474, "outputTokens": 48310, "estimatedCostUsd": 1.804 }
}
```

`status` is `"degraded"` when a non-fatal dependency is missing (no Tesseract, no AI key);
the body always names what is missing. Never 503 for a degraded dependency.

---

## Errors

Every error body is `{ "success": false, "error": { "code": "...", "message": "...", "detail": null } }`.

| Case | HTTP | `code` | Message |
|---|---|---|---|
| Invalid / unparseable URL | 400 | `invalid_url` | Please enter a valid video or post link |
| Private or age-restricted | 403 | `restricted` | This content is private or restricted |
| Deleted / not found | 404 | `not_found` | This video no longer exists |
| No thumbnail available | 404 | `no_thumbnail` | No thumbnail found for this link |
| Platform unsupported | 422 | `unsupported_platform` | We can't read this platform yet — tell us about it |
| Rate limited | 429 | `rate_limited` | Too many requests. Please wait a moment (+ `Retry-After`) |
| Geo-blocked | 451 | `geo_blocked` | This content isn't available in our server region |
| Image too large | 413 | `image_too_large` | That image is too large to process |
| Blocked host (SSRF) | 400 | `blocked_host` | That address can't be fetched |
| AI unavailable | **200** | — | deterministic analysis returned, `aiError` populated |
| Extractor crash | 500 | `extractor_failed` | Could not process this link. Please try again |
