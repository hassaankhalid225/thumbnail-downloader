/**
 * Content for the platform landing pages. Original copy per platform — the point of
 * these pages is that someone searching "vimeo thumbnail downloader" gets an answer
 * about Vimeo, not a find-and-replace of the YouTube page.
 */

export interface PlatformPageContent {
  slug: string;
  platform: string;
  name: string;
  title: string;
  /** Used when the analyser is switched off, so the tag never over-promises. */
  titleDownloadOnly?: string;
  description: string;
  descriptionDownloadOnly?: string;
  h1: string;
  intro: string;
  introDownloadOnly?: string;
  /** The 600-word guide, as sections. `analysisOnly` sections are dropped when off. */
  sections: { heading: string; body: string[]; analysisOnly?: boolean }[];
  sizes: { label: string; dimensions: string; note: string }[];
  faqs: { q: string; a: string; analysisOnly?: boolean }[];
  example: string;
}

export const PLATFORM_PAGES: PlatformPageContent[] = [
  {
    slug: "youtube-thumbnail-downloader",
    platform: "youtube",
    name: "YouTube",
    title: "YouTube Thumbnail Downloader — HD, Full HD & 4K Sizes Free",
    description:
      "Download any YouTube thumbnail in Max HD, HD, SD and more — then get a measured breakdown of the colours, text placement and whether the text survives at phone size. Free, no signup.",
    descriptionDownloadOnly:
      "Download any YouTube thumbnail in Max HD, HD, SD, Full HD, vertical and square — as JPG, PNG or WebP, with real file sizes. Free, no signup, no watermark.",
    h1: "YouTube thumbnail downloader",
    intro:
      "Paste any YouTube URL — a normal watch link, a Short, a live stream, an embed, a youtu.be share link with tracking parameters attached — and get every thumbnail size YouTube actually stores, plus the measurements that explain why the thumbnail performs.",
    introDownloadOnly:
      "Paste any YouTube URL — a normal watch link, a Short, a live stream, an embed, a youtu.be share link with tracking parameters attached — and get every thumbnail size YouTube actually stores, at the resolution it really has.",
    sections: [
      {
        heading: "Every URL shape works",
        body: [
          "YouTube has more link formats than any other platform, and most downloaders only handle two of them. ThumbIQ extracts the 11-character video ID from watch?v=, youtu.be/, /shorts/, /embed/, /live/, /v/, m.youtube.com, music.youtube.com and youtube-nocookie.com — with or without extra query parameters like ?si=, &t= or &list=.",
          "The ID regex is deliberately strict: exactly eleven characters from A–Z, a–z, 0–9, hyphen and underscore, with a boundary check afterwards. A loose regex is how other tools end up requesting a twelve-character ID, getting a 404, and showing you a broken card.",
        ],
      },
      {
        heading: "The maxresdefault problem, solved properly",
        body: [
          "YouTube does not generate maxresdefault.jpg for every video. Older uploads, videos published below 1280×720, and some auto-generated content simply don't have one.",
          "The trap is that YouTube doesn't always return a clean 404. Frequently it returns HTTP 200 with a grey 120×90 placeholder image. A downloader that trusts the status code shows you a broken 'Max HD' card that downloads a grey rectangle.",
          "ThumbIQ validates three ways before showing a size: the response must be 200, the content length must exceed 2 KB, and — this is the one that actually settles it — the decoded pixel dimensions read from the image header must match what the entry claims to be. A 120×90 placeholder fails the third test no matter how convincing the first two look, and the entry is dropped from the list rather than rendered as a dead card.",
        ],
      },
      {
        heading: "The sizes YouTube really stores",
        body: [
          "YouTube keeps a fixed ladder: maxresdefault (1280×720), hq720 (1280×720), sddefault (640×480), hqdefault (480×360), mqdefault (320×180) and default (120×90), plus WebP variants and three storyboard frames. hqdefault always exists — if even that fails, the video itself is gone.",
          "Anything above 1280×720 is upscaled, and ThumbIQ labels it as upscaled. There is no 4K thumbnail sitting on YouTube's servers waiting to be found; a tool offering you one is resampling 1280×720 and not telling you. The Full HD entry here is honest about what it is, applies a mild unsharp mask to counter the resampling softness, and says so in the tooltip.",
        ],
      },
      {
        heading: "What the analysis tells you that the image doesn't",
        analysisOnly: true,
        body: [
          "The mobile legibility check is the one that changes decisions. Your thumbnail renders at 168×94 in the phone feed — that is where most impressions happen. ThumbIQ physically resamples the image to that size and re-measures your text's cap height in real pixels. Under 10 pixels and it is unreadable, no matter how good it looked in your editor at 100% zoom.",
          "The safe-zone map is the other one. YouTube draws a duration pill in the bottom-right corner of every thumbnail, on every surface. If your punchline word is there, viewers never see it. ThumbIQ draws the pill on your image, in red, where it collides.",
        ],
      },
    ],
    sizes: [
      { label: "Max HD", dimensions: "1280×720", note: "maxresdefault.jpg — not present on every video" },
      { label: "HD 720", dimensions: "1280×720", note: "hq720.jpg — a reliable alternative to maxres" },
      { label: "SD", dimensions: "640×480", note: "sddefault.jpg, 4:3" },
      { label: "HQ", dimensions: "480×360", note: "hqdefault.jpg — always exists" },
      { label: "MQ", dimensions: "320×180", note: "mqdefault.jpg" },
      { label: "Default", dimensions: "120×90", note: "default.jpg" },
      { label: "Full HD", dimensions: "1920×1080", note: "Upscaled — YouTube stores nothing larger than 1280×720" },
      { label: "Vertical / Square", dimensions: "1080×1920 · 1080×1080", note: "Cropped around the measured focal point" },
    ],
    faqs: [
      {
        q: "Why is there no 4K YouTube thumbnail?",
        a: "Because YouTube doesn't store one. The largest file on their CDN is maxresdefault.jpg at 1280×720. Any tool offering you a 4K thumbnail is upscaling that file and hoping you don't check. ThumbIQ will render you a 1920×1080 version and label it upscaled, which is the honest description of what it is.",
      },
      {
        q: "Why did the Max HD size disappear for my video?",
        a: "Because YouTube never generated it for that upload — common on older videos and on anything published below 720p. Rather than showing you a card that downloads a grey placeholder, ThumbIQ validates the real pixel dimensions and drops the entry. hqdefault at 480×360 always exists as the floor.",
      },
      {
        q: "Does this work for YouTube Shorts?",
        a: "Yes. A /shorts/ URL resolves through the same fast path, and the vertical 1080×1920 export crops around the measured focal point rather than the geometric centre, so the subject survives the reframe.",
      },
      {
        q: "Can I download a private or age-restricted video's thumbnail?",
        a: "No. ThumbIQ reads publicly available images and never bypasses an access control. A private or age-gated video returns a clear message saying so rather than attempting another route.",
      },
      {
        q: "Do I need to sign in or install anything?",
        a: "No. There is no account, no extension and no API key. Paste a link and the sizes appear — usually in under a second, because the YouTube path is pure URL construction with no subprocess involved.",
      },
    ],
    example: "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  },

  {
    slug: "tiktok-thumbnail-downloader",
    platform: "tiktok",
    name: "TikTok",
    title: "TikTok Thumbnail Downloader — Vertical Covers in Full Size",
    description:
      "Download the cover image from any TikTok video in full resolution, plus a measured analysis of the colours, text placement and legibility at feed size. Free, no watermark, no signup.",
    descriptionDownloadOnly:
      "Download the cover image from any TikTok video in full resolution — vertical, square or 16:9, as JPG, PNG or WebP. Free, no watermark, no signup.",
    h1: "TikTok thumbnail downloader",
    intro:
      "Paste a TikTok link and get the video's cover image at full resolution — usually 720×1280 vertical — along with the measurements that explain why it stops a scroll.",
    introDownloadOnly:
      "Paste a TikTok link and get the video's cover image at full resolution — usually 720×1280 vertical — plus square and 16:9 crops for cross-posting.",
    sections: [
      {
        heading: "Covers are vertical, and that changes the rules",
        body: [
          "A TikTok cover is 9:16, and it competes in a feed where the whole screen is one video. The design constraints are almost the opposite of YouTube's: there is no grid of competing thumbnails, but there is a stack of interface elements — the caption, the username, the sound, the action rail — sitting on top of the lower half of your frame.",
          "That means the safe area is the upper two thirds. ThumbIQ's composition read tells you where the focal point actually landed, and the text overlay shows you exactly which of your words are in the region the UI covers.",
        ],
      },
      {
        heading: "How the cover is resolved",
        body: [
          "TikTok exposes a public oEmbed endpoint that returns the cover URL without any authentication. That is the fast path, and it usually returns in well under a second.",
          "The endpoint rate-limits aggressively, though. When it does, ThumbIQ falls through to a universal metadata extractor rather than failing — you get the cover either way, just a little slower. Nothing is ever downloaded except the image itself; the video stream is never touched.",
        ],
      },
      {
        heading: "What to measure on a vertical cover",
        analysisOnly: true,
        body: [
          "Text size matters more here than almost anywhere, because a TikTok cover is also the grid thumbnail on a profile page, where it renders at roughly a third of its height. ThumbIQ's mobile legibility check catches text that is perfectly readable full-screen and illegible in the profile grid.",
          "Saturation matters too. The TikTok feed is a high-contrast, high-motion environment, and the stopping-power score weights saturation punch and contrast range heavily for exactly that reason. A muted, low-contrast cover scores badly here and it deserves to.",
          "The palette export is the practical output: six hex codes in perceptually clustered order, ready to paste into your editor so your next cover matches the one that worked.",
        ],
      },
    ],
    sizes: [
      { label: "Native cover", dimensions: "720×1280", note: "Typical TikTok cover resolution, 9:16" },
      { label: "Vertical HD", dimensions: "1080×1920", note: "Upscaled from the native cover" },
      { label: "Square", dimensions: "1080×1080", note: "Cropped around the focal point for cross-posting" },
      { label: "HD", dimensions: "1280×720", note: "16:9 crop for YouTube repurposing" },
    ],
    faqs: [
      {
        q: "Does the downloaded cover have a TikTok watermark?",
        a: "The cover image is served by TikTok's CDN as-is. If the creator burned a watermark into the frame they chose as the cover, it will be there — ThumbIQ doesn't alter the image, and doesn't remove watermarks.",
      },
      {
        q: "Why is my TikTok cover lower resolution than expected?",
        a: "TikTok generates the cover from a video frame, so its resolution is bounded by the upload. A 720×1280 cover is typical. ThumbIQ shows the real native size and marks anything larger as upscaled.",
      },
      {
        q: "Can I download a private TikTok's cover?",
        a: "No. Private and follower-only content is not publicly served, and ThumbIQ does not authenticate against any platform. You'll get a clear message rather than a workaround.",
      },
      {
        q: "Does a vm.tiktok.com short link work?",
        a: "Yes. Short links resolve through the universal extractor, which follows the redirect and reads the public metadata at the destination.",
      },
      {
        q: "Can I analyze my own draft cover before posting?",
        analysisOnly: true,
        a: "Yes, and this is the best use of the tool. Drop the image straight onto the page — no link needed. You'll find out whether your text survives the profile grid before you commit to it.",
      },
    ],
    example: "https://www.tiktok.com/@tiktok/video/7106594312292453675",
  },

  {
    slug: "instagram-thumbnail-downloader",
    platform: "instagram",
    name: "Instagram",
    title: "Instagram Thumbnail Downloader — Reels & Post Covers",
    description:
      "Download the cover image from any public Instagram Reel or post, plus a measured breakdown of the palette, text placement and grid legibility. Free, no login.",
    descriptionDownloadOnly:
      "Download the cover image from any public Instagram Reel or post at full available resolution — square, vertical or 16:9, as JPG, PNG or WebP. Free, no login.",
    h1: "Instagram thumbnail downloader",
    intro:
      "Paste a public Reel or post link to pull its cover image at full available resolution, along with the analysis that tells you how it will read in a profile grid.",
    introDownloadOnly:
      "Paste a public Reel or post link to pull its cover image at full available resolution, with a square crop that keeps the subject rather than slicing through it.",
    sections: [
      {
        heading: "Public content only, by design",
        body: [
          "Instagram serves public post and Reel covers through its CDN without authentication. ThumbIQ reads those, and only those. It does not log in, does not accept your credentials, and does not touch private accounts, close-friends stories or follower-only content — if the content is restricted, you get a clear message instead of a workaround.",
          "That restriction is deliberate rather than technical. A tool that bypasses access controls stops being a research tool.",
        ],
      },
      {
        heading: "The grid is the real test",
        body: [
          "An Instagram cover has two lives. Full-bleed in the feed it gets a large, forgiving canvas. In a profile grid it is one of nine small squares, cropped to 1:1, competing with its own neighbours.",
          "This is where the mobile legibility check earns its keep. ThumbIQ resamples your cover down and re-measures cap height in real pixels, so you find out that the word you built the design around is eight pixels tall in the grid — before you post it, not after.",
          "The square export crops to 1:1 around the measured saliency centroid rather than the geometric centre, which means a subject sitting off to one side survives the crop instead of being sliced in half.",
        ],
      },
      {
        heading: "Reading a competitor's palette",
        analysisOnly: true,
        body: [
          "Instagram is a colour-driven platform, and consistent creators run a recognisable palette across their grid. ThumbIQ clusters the six dominant colours in LAB space — perceptually uniform, so the clusters match what your eye actually separates — and hands you the hex codes plus ready-to-paste CSS and Tailwind exports.",
          "The channel report extends this across a whole profile: paste a profile URL and see the recurring palette, how often a face appears, where the text always sits, and how consistent the whole thing is as a single number.",
        ],
      },
    ],
    sizes: [
      { label: "Native cover", dimensions: "Up to 1080×1350", note: "Instagram's largest served rendition" },
      { label: "Square", dimensions: "1080×1080", note: "1:1 grid crop, anchored on the focal point" },
      { label: "Vertical HD", dimensions: "1080×1920", note: "9:16 for Reels and Stories" },
      { label: "HD", dimensions: "1280×720", note: "16:9 for cross-posting" },
    ],
    faqs: [
      {
        q: "Can I download from a private Instagram account?",
        a: "No. ThumbIQ only reads publicly served images and never authenticates against Instagram. Private accounts return a restriction message.",
      },
      {
        q: "Why does an Instagram link sometimes fail?",
        a: "Instagram rate-limits unauthenticated requests aggressively and rotates its CDN paths. When a link doesn't resolve, ThumbIQ falls back to reading the page's Open Graph image; if that's also blocked, you get a clear error rather than a broken card.",
      },
      {
        q: "What resolution do I get?",
        a: "Whatever Instagram serves publicly — typically up to 1080 pixels on the long edge. ThumbIQ shows the real native dimensions and labels every larger export as upscaled.",
      },
      {
        q: "Does this work for carousels?",
        a: "It resolves the first image of a carousel, which is the cover that appears in the feed and in the grid — the one that does the work of getting the post opened.",
      },
      {
        q: "Can I analyze my own image without a link?",
        analysisOnly: true,
        a: "Yes. Drag it onto the page or paste it from your clipboard. There's no extraction step, so it goes straight to measurement.",
      },
    ],
    example: "https://www.instagram.com/reel/C1abcdefghi/",
  },

  {
    slug: "vimeo-thumbnail-downloader",
    platform: "vimeo",
    name: "Vimeo",
    title: "Vimeo Thumbnail Downloader — Up to Full HD, Free",
    description:
      "Download any public Vimeo video's thumbnail at up to 1920×1080, with a measured analysis of the palette, composition and text legibility. No signup.",
    descriptionDownloadOnly:
      "Download any public Vimeo video's thumbnail at up to 1920×1080 — often genuinely native, not upscaled. JPG, PNG or WebP. No signup.",
    h1: "Vimeo thumbnail downloader",
    intro:
      "Paste a Vimeo link to pull its thumbnail at the largest rendition Vimeo will serve — often genuinely Full HD, unlike most platforms — plus the measurements behind it.",
    introDownloadOnly:
      "Paste a Vimeo link to pull its thumbnail at the largest rendition Vimeo will serve — often genuinely Full HD, unlike most platforms.",
    sections: [
      {
        heading: "Vimeo actually serves large thumbnails",
        body: [
          "This is the one platform where a 1920×1080 thumbnail is frequently native rather than upscaled. Vimeo generates renditions on demand and will serve sizes well beyond what YouTube stores.",
          "The catch is that Vimeo does not 404 an oversized request — it quietly serves you the largest rendition it has and lets you believe you got what you asked for. ThumbIQ requests several sizes, reads the real pixel dimensions from each response header, deduplicates by actual size, and shows you what you genuinely received.",
        ],
      },
      {
        heading: "How the URL rewriting works",
        body: [
          "Vimeo's oEmbed endpoint returns a thumbnail URL with a size baked into the filename — a suffix like -d_295x166, or an older _295x166.jpg form, or size parameters on the query string. ThumbIQ recognises all three shapes and rewrites each to request larger renditions.",
          "Every rewrite is then validated. A rendition that comes back smaller than requested is recorded at its real size rather than its requested one, so the ladder never advertises a resolution you didn't get.",
        ],
      },
      {
        heading: "Different platform, different design language",
        analysisOnly: true,
        body: [
          "Vimeo's audience skews toward filmmakers and studios, and the thumbnails reflect it: fewer arrows and shocked faces, more cinematic stills with restrained typography and deliberate negative space.",
          "That makes the composition metrics more interesting here than the stopping-power score. The focal point map, the rule-of-thirds alignment, the left/right weight balance and the background-separation reading — how much softer the background is than the subject, which correlates with a professional look — are the numbers worth reading on a Vimeo thumbnail.",
          "The word-count heuristic still applies, but the sweet spot runs lower. Many of the strongest Vimeo thumbnails carry no text at all, in which case ThumbIQ leaves the text scores blank rather than inventing a number for something that isn't there.",
        ],
      },
    ],
    sizes: [
      { label: "Full HD", dimensions: "1920×1080", note: "Often genuinely native on Vimeo" },
      { label: "HD", dimensions: "1280×720", note: "Standard rendition" },
      { label: "SD", dimensions: "640×360", note: "Smaller rendition" },
      { label: "Square / Vertical", dimensions: "1080×1080 · 1080×1920", note: "Focal-point crops for cross-posting" },
    ],
    faqs: [
      {
        q: "Can I really get 1080p from Vimeo?",
        a: "Often, yes — Vimeo generates renditions on demand rather than storing a fixed ladder. ThumbIQ reads the real dimensions of what came back, so when a size is genuinely native it says native, and when it isn't it says upscaled.",
      },
      {
        q: "Does this work for password-protected Vimeo videos?",
        a: "No. Password-protected and private videos are not publicly served, and ThumbIQ does not attempt to work around access controls.",
      },
      {
        q: "What about Vimeo Showcase or channel URLs?",
        a: "A single video URL is the reliable path. A showcase or channel URL resolves the first video it can read; for a full sweep, use the channel report instead.",
      },
      {
        q: "Why does the thumbnail have letterboxing?",
        a: "Vimeo generates thumbnails from the source frame, so a non-16:9 upload keeps its bars. The technical quality readout reports the real aspect ratio and flags it when it isn't 16:9.",
      },
      {
        q: "Is the analysis different for Vimeo?",
        analysisOnly: true,
        a: "The measurements are identical — the same pixels get the same treatment on every platform. What differs is which numbers matter: composition and background separation carry more signal on Vimeo than raw saturation punch.",
      },
    ],
    example: "https://vimeo.com/76979871",
  },

  {
    slug: "twitter-thumbnail-downloader",
    platform: "twitter",
    name: "X (Twitter)",
    title: "X / Twitter Thumbnail Downloader — Video & Card Images",
    description:
      "Download the preview image from any public X (Twitter) video post or link card, plus a measured analysis of the palette, contrast and timeline legibility. Free.",
    descriptionDownloadOnly:
      "Download the preview image from any public X (Twitter) video post or link card, in every size and format. Free, no login.",
    h1: "X (Twitter) thumbnail downloader",
    intro:
      "Paste a public post URL to pull its video preview or link-card image, with the measurements that tell you how it will read at timeline size.",
    introDownloadOnly:
      "Paste a public post URL to pull its video preview or link-card image at the resolution X actually serves.",
    sections: [
      {
        heading: "Two different images, one URL",
        body: [
          "A post on X can carry two kinds of preview: a video poster frame generated from the upload, or a link-card image pulled from the linked page's Open Graph tags. They behave differently and they're worth telling apart.",
          "ThumbIQ resolves whichever the post actually carries. For a video post it reads the poster frame; for a link card it reads the card image, which is really the linked site's og:image and is often designed for a completely different context.",
        ],
      },
      {
        heading: "The timeline is small and it is cropped",
        body: [
          "X renders previews at a modest size in the timeline and crops aggressively on mobile. A wide 16:9 card can lose its left and right edges entirely.",
          "That makes the safe-zone read and the text measurements the useful outputs here. If your key words sit near the horizontal edges, they are at risk; if your cap height is under about 14 pixels at timeline scale, they are unreadable regardless of where they sit.",
          "The contrast measurement matters more than usual too, because X supports both a light and a dark theme. A preview that relies on a near-white background works against one theme and disappears against the other. ThumbIQ reports the WCAG ratio for every text block against the pixels actually behind it, so you can see which blocks are carried by the image and which are carried by luck.",
        ],
      },
      {
        heading: "Reading what performs on X",
        analysisOnly: true,
        body: [
          "X previews reward high contrast and very few words — the platform is text-first, so the image is competing with the post copy directly above it rather than doing all the work alone.",
          "The word-count heuristic is blunt but reliable: one to four words scores as excellent, seven or more is penalised, and the reason is stated in the output rather than left as a mystery. Most link cards that underperform on X are carrying a full headline in eleven-point type.",
        ],
      },
    ],
    sizes: [
      { label: "Native preview", dimensions: "Up to 1280×720", note: "Video poster or card image as served" },
      { label: "HD", dimensions: "1280×720", note: "Standard 16:9" },
      { label: "Square", dimensions: "1080×1080", note: "Focal-point crop, safer against timeline cropping" },
      { label: "Vertical HD", dimensions: "1080×1920", note: "For cross-posting to vertical feeds" },
    ],
    faqs: [
      {
        q: "Does this work with both x.com and twitter.com links?",
        a: "Yes, both hostnames resolve to the same extractor, along with t.co short links.",
      },
      {
        q: "Can I download from a protected account?",
        a: "No. Protected posts are not publicly served, and ThumbIQ does not authenticate against X.",
      },
      {
        q: "Why did my link return the website's image instead of the video?",
        a: "Because the post is a link card rather than a native video upload. The card image is the linked site's Open Graph image — that's genuinely what X is showing in the timeline, so it's what gets analysed.",
      },
      {
        q: "What resolution should I expect?",
        a: "Video posters are typically up to 1280×720. Card images vary widely with whatever the linked site published. The real dimensions are always shown, and larger exports are labelled upscaled.",
      },
      {
        q: "Does the analysis account for X's dark mode?",
        analysisOnly: true,
        a: "Indirectly, and usefully: the per-block WCAG contrast is measured against the pixels behind the text inside your own image, so a block that depends on the surrounding page being light shows up as low contrast.",
      },
    ],
    example: "https://x.com/Interior/status/463440424141459456",
  },

  {
    slug: "facebook-thumbnail-downloader",
    platform: "facebook",
    name: "Facebook",
    title: "Facebook Thumbnail Downloader — Video & Reel Covers",
    description:
      "Download the cover image from any public Facebook video, Reel or post, plus a measured breakdown of the colours, text placement and feed legibility. Free, no login.",
    descriptionDownloadOnly:
      "Download the cover image from any public Facebook video, Reel or post — feed, Reel and square sizes, as JPG, PNG or WebP. Free, no login.",
    h1: "Facebook thumbnail downloader",
    intro:
      "Paste a public Facebook video, Reel or post link to pull its cover image, along with the measurements that explain how it will perform in the feed.",
    introDownloadOnly:
      "Paste a public Facebook video, Reel or post link to pull its cover image at the resolution Facebook actually serves.",
    sections: [
      {
        heading: "Public posts only",
        body: [
          "Facebook serves public video covers and post images without authentication, and those are what ThumbIQ reads. Friends-only, group-restricted and private content is not publicly served, and ThumbIQ does not log in, accept credentials, or attempt to route around a restriction — you get a clear message instead.",
          "fb.watch short links work, as do standard facebook.com video and reel URLs.",
        ],
      },
      {
        heading: "A feed that punishes small type",
        body: [
          "Facebook's feed renders video covers at a wide range of sizes depending on surface and device, and the smallest of them are unforgiving. Text that reads comfortably on your monitor frequently collapses into a smudge in a mobile feed.",
          "ThumbIQ's mobile legibility check is calibrated against YouTube's render sizes, but the physics are identical everywhere: below roughly ten pixels of cap height, text stops being readable and becomes texture. The five-surface strip shows you the actual rendered result at true scale rather than describing it.",
          "Facebook also historically penalised covers that were mostly text, and while the specific rule has changed over the years, the underlying design lesson has not: the text-area ratio measurement here has a sweet spot of 8 to 25 percent of the frame, and a cover well above that range is doing too much work with words.",
        ],
      },
      {
        heading: "Using the analysis on your own drafts",
        analysisOnly: true,
        body: [
          "The most valuable workflow on Facebook is checking your own cover before publishing. Drag your draft onto the page — no link required, no extraction step — and read the eight sub-scores.",
          "The two that usually change a decision are mobile legibility, which tells you whether the words survive, and safe-zone safety, which tells you whether anything important is sitting where an interface element will land. Both are measurements of your specific image rather than general advice, and both are things no design tool shows you at edit time.",
        ],
      },
    ],
    sizes: [
      { label: "Native cover", dimensions: "Up to 1280×720", note: "As served by Facebook's CDN" },
      { label: "HD", dimensions: "1280×720", note: "Standard 16:9 feed cover" },
      { label: "Vertical HD", dimensions: "1080×1920", note: "9:16 for Reels" },
      { label: "Square", dimensions: "1080×1080", note: "1:1, cropped around the focal point" },
    ],
    faqs: [
      {
        q: "Can I download from a private Facebook group or profile?",
        a: "No. That content isn't publicly served, and ThumbIQ doesn't authenticate against Facebook or work around access controls.",
      },
      {
        q: "Do fb.watch links work?",
        a: "Yes. Short links are followed to their destination and the public metadata is read there.",
      },
      {
        q: "Why does a Facebook link sometimes fail?",
        a: "Facebook rate-limits unauthenticated requests and changes its markup often. When the primary path fails, ThumbIQ falls back to reading the page's Open Graph image, and reports a clear error if that's blocked too.",
      },
      {
        q: "What size are Facebook video covers?",
        a: "Usually up to 1280×720 for feed video, and 1080×1920 for Reels. The real native size is always shown, and any larger export is labelled upscaled.",
      },
      {
        q: "Is there a text limit on Facebook covers?",
        analysisOnly: true,
        a: "The old hard 20% text rule is gone, but heavy text still hurts readability. ThumbIQ measures your actual text-area ratio and flags it outside the 8–25% range, which is a measurement rather than a policy guess.",
      },
    ],
    example: "https://www.facebook.com/watch/?v=10153231379946729",
  },
];

export function getPlatformPage(slug: string): PlatformPageContent | undefined {
  return PLATFORM_PAGES.find((page) => page.slug === slug);
}

/**
 * The page content as it should actually render right now.
 *
 * With the analyser off, the analysis-specific sections and questions are dropped and the
 * title, description and intro fall back to their download-only wording — so the page
 * never describes a feature the visitor can't use, and the meta tag never promises one.
 */
export function resolvePlatformPage(
  page: PlatformPageContent,
  analysisEnabled: boolean,
): PlatformPageContent {
  if (analysisEnabled) return page;
  return {
    ...page,
    title: page.titleDownloadOnly ?? page.title,
    description: page.descriptionDownloadOnly ?? page.description,
    intro: page.introDownloadOnly ?? page.intro,
    sections: page.sections.filter((section) => !section.analysisOnly),
    faqs: page.faqs.filter((faq) => !faq.analysisOnly),
  };
}
