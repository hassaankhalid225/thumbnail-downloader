# ThumbIQ — Legal position

## What ThumbIQ is

An analysis, research and educational reference tool. It reads a publicly available
thumbnail, measures it, and explains what it measured. It is not a redistribution
service, a hosting service, or an archive.

## Copyright

Thumbnails are copyrighted works owned by the creators who made them. ThumbIQ does not
claim any right in them, does not license them onward, and does not present them as
available for reuse.

The product is built for the uses that fall within research, commentary, criticism and
study — a creator studying why a competitor's thumbnail performs, a designer reading a
palette, an editor checking their own draft against the mobile feed. Those uses are
transformative in purpose: the value ThumbIQ adds is the measurement, not the image.

Copying someone else's thumbnail and publishing it as your own is not one of those uses,
and the product says so in the interface rather than staying quiet about it.

### Shipped in the product, not just in this file

- A visible line under the tool on every page that renders a thumbnail:
  *"Thumbnails are the property of their creators. Use for research and inspiration —
  don't republish someone else's thumbnail as your own."*
- The same line, as `README.txt`, inside every ZIP download.
- `recreate_recipe` is deliberately a recipe — palette, font style, layout, subject
  treatment — and never an image. The UI frames it as *"Build your own in this style."*

## Retention

**Nothing user-facing is written to disk. There is no object store and no database.**

| Data | Where it lives | How long |
|---|---|---|
| Resolved thumbnail URLs | in-memory TTL cache | 60 minutes, then evicted |
| Downloaded image bytes | in-memory TTL cache | 60 minutes |
| Generated renditions | in-memory TTL cache | 60 minutes |
| Analysis results | in-memory TTL cache, keyed by image content hash | 60 minutes |
| Uploaded draft thumbnails | request memory only | the life of the request |
| Request logs | URL host + status + latency. **No full URLs, no IP addresses, no images.** | 14 days |

A process restart clears everything. There is no public gallery of other people's
thumbnails and there will not be one — a gallery would convert a research tool into a
redistribution service, which is the line this product does not cross.

## Access controls

ThumbIQ reads publicly available metadata and publicly served images. It does not:

- bypass, strip or work around any platform's authentication, paywall, age gate or
  geo-restriction
- log into any platform, or accept user credentials for any platform
- scrape private, unlisted or follower-only content

Where a platform restricts content, ThumbIQ returns the restriction to the user as an
error (`403 This content is private or restricted`) rather than attempting another route.
yt-dlp is run in metadata-only mode (`skip_download=True`); the video stream is never
touched.

## Personal data

ThumbIQ has no accounts, no signup, no email collection and no advertising or analytics
cookies. IP addresses are used transiently and in memory for rate limiting only, and are
not written to logs or storage.

Thumbnails may contain images of people. ThumbIQ's face module measures geometry —
position, size, eye-line — to score composition. It does not perform face recognition,
identity matching, or biometric templating, and it stores nothing.

## DMCA / takedown

Because ThumbIQ stores nothing, there is normally nothing to take down: a cached entry
expires within 60 minutes and a restart clears it immediately. Where a rights holder wants
their content excluded from processing entirely, the process is:

1. Send a notice to **dmca@thumbiq.app** including: the work, the URL that produces it,
   your relationship to the work, contact details, a good-faith statement, and a statement
   under penalty of perjury that you are authorised to act.
2. Acknowledgement within **2 business days**.
3. On a valid notice, the cache is purged immediately and the source URL or channel is
   added to a permanent processing blocklist — ThumbIQ will refuse to resolve it and
   returns a clear message to the user.
4. Counter-notice at the same address, handled under the same timeline.

The `/dmca` page in the app carries this process verbatim, with the contact address live.

## Third-party services

| Service | What it receives | Why |
|---|---|---|
| Anthropic (Claude API) | the thumbnail image, downscaled to a 1568 px long edge, plus the measured metrics | writes the qualitative verdict |
| Platform CDNs (`i.ytimg.com`, `*.vimeocdn.com`, …) | a standard HTTP request for a public image | resolution |

Anthropic's API is not used to train models on this data under its standard commercial
terms. The AI pass can be disabled entirely with `AI_ENABLED=false`, and every other
feature keeps working — the tool is designed to be useful with the AI turned off.

## Warranty

Scores are measurements and heuristics, not predictions of performance. The font read is
explicitly a closest-match classification, never an identification. Expression detection is
labelled an estimate everywhere it appears. ThumbIQ makes no guarantee that acting on its
advice changes any metric on any platform, and says so on `/terms`.
