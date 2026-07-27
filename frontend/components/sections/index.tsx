import {
  Crosshair,
  Download,
  Eye,
  FileSearch,
  Palette,
  Ruler,
  ShieldAlert,
  Smartphone,
} from "lucide-react";

import { ANALYSIS_ENABLED, SUPPORTED_PLATFORMS } from "@/lib/constants";

/* ============================== HowItWorks ============================ */

const ANALYZER_STEPS = [
  {
    title: "Paste a link",
    body: "Any video or post URL — YouTube, TikTok, Instagram, Vimeo, X, Twitch, or 1,800 other sites. Or drop your own draft image straight onto the page.",
  },
  {
    title: "Take the downloads",
    body: "Eight sizes in three formats, each with its real byte count, each labelled native or upscaled. The grid appears before the analysis finishes — it never waits.",
  },
  {
    title: "Read why it works",
    body: "Eight measured sub-scores, the palette in hex, the text placement, and the one check nobody else does: whether your words survive at phone size.",
  },
];

const DOWNLOADER_STEPS = [
  {
    title: "Paste a link",
    body: "Any video or post URL — YouTube, TikTok, Instagram, Vimeo, X, Twitch, or 1,800 other sites. No account, no extension, nothing to install.",
  },
  {
    title: "Pick a size",
    body: "Eight sizes in JPG, PNG and WebP, each showing the real file size for the format you picked. Sizes the platform doesn't actually store are never listed.",
  },
  {
    title: "Download",
    body: "One file, or select several and take them as a ZIP. Vertical and square exports crop around the subject rather than slicing through it.",
  },
];

const STEPS = ANALYSIS_ENABLED ? ANALYZER_STEPS : DOWNLOADER_STEPS;

export function HowItWorks() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
      <p className="eyebrow">How it works</p>
      <h2 className="mt-2 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl">
        {ANALYSIS_ENABLED ? "Three steps. Fifteen seconds." : "Three steps. Five seconds."}
      </h2>

      {/* Numbered because this genuinely is a sequence — step two cannot precede step one. */}
      <ol className="mt-10 grid gap-5 md:grid-cols-3">
        {STEPS.map((step, index) => (
          <li key={step.title} className="panel relative p-6">
            <span className="mono text-3xl font-black text-[#232330]">
              {String(index + 1).padStart(2, "0")}
            </span>
            <h3 className="mt-3 text-lg font-bold text-[#F2F2F7]">{step.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-[#8E8EA8]">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* =============================== Features ============================= */

const ANALYZER_FEATURES = [
  {
    icon: Smartphone,
    title: "Mobile legibility simulation",
    body: "The thumbnail is physically resampled to the five sizes YouTube renders at, and the text is re-measured on each. Cap height under 10px fails. No other tool checks this.",
  },
  {
    icon: ShieldAlert,
    title: "Safe-zone collision map",
    body: "YouTube's duration pill, CC badge and progress bar drawn on top of your image, in red where they land on something that matters.",
  },
  {
    icon: Palette,
    title: "Palette in LAB, not RGB",
    body: "Six clusters found in perceptually uniform colour space, with harmony type, temperature and ready-to-paste CSS, Tailwind and ASE exports.",
  },
  {
    icon: Ruler,
    title: "Measured, not estimated",
    body: "Every byte count is from a real encode. Every cap height is from a real ink profile. Every contrast ratio is WCAG 2.1 against the pixels actually behind the letters.",
  },
  {
    icon: Crosshair,
    title: "Focal point and balance",
    body: "Spectral-residual saliency finds where the eye lands, then measures it against the rule of thirds, left/right weight, negative space and clutter.",
  },
  {
    icon: Download,
    title: "Eight sizes, three formats",
    body: "Including 9:16 and 1:1 crops anchored on the measured focal point, so a vertical export keeps the subject instead of slicing through it.",
  },
  {
    icon: Eye,
    title: "Honest labels",
    body: "Upscaled sizes say upscaled. Font matches say closest match, never identification. Expression says estimate. A score with no basis says nothing at all.",
  },
  {
    icon: FileSearch,
    title: "AI that can't invent numbers",
    body: "Claude gets the image and the measurements, and is instructed that those are the only permitted source of any figure. It writes the insight; the code produces the facts.",
  },
];

const DOWNLOADER_FEATURES = [
  {
    icon: Download,
    title: "Eight sizes, three formats",
    body: "Full HD down to 120×90, plus 9:16 and 1:1 exports — each available as JPG, PNG or WebP, with the real file size shown for the format you picked.",
  },
  {
    icon: Ruler,
    title: "Real file sizes, not estimates",
    body: "Every byte count comes from a real encode of that exact size in that exact format. Nothing on the card is a guess or a rounded placeholder.",
  },
  {
    icon: Eye,
    title: "No broken cards",
    body: "YouTube serves a grey placeholder with HTTP 200 when a size doesn't exist. Each candidate is checked by status, byte count and decoded pixel dimensions — if it isn't real, it isn't listed.",
  },
  {
    icon: FileSearch,
    title: "Upscales say upscaled",
    body: "YouTube stores nothing above 1280×720. The Full HD export is interpolated, it's labelled as interpolated, and no one is sold a fake 1080p.",
  },
  {
    icon: Crosshair,
    title: "Crops that keep the subject",
    body: "Vertical and square exports crop around the measured focal point rather than the geometric centre, so an off-centre subject survives the reframe.",
  },
  {
    icon: Palette,
    title: "1,800+ sites",
    body: "YouTube, TikTok, Vimeo and Dailymotion get a dedicated fast path. Instagram, Facebook, X, Twitch, Reddit, Pinterest, LinkedIn and the rest resolve through a universal extractor.",
  },
  {
    icon: ShieldAlert,
    title: "Nothing stored",
    body: "No account, no signup, no database. Images live in a 60-minute memory cache and are then gone. There's no gallery of other people's thumbnails.",
  },
  {
    icon: Smartphone,
    title: "Take them all at once",
    body: "Select the sizes you want and download them as a single ZIP, with correct filenames and the creator-copyright notice included.",
  },
];

const FEATURES = ANALYSIS_ENABLED ? ANALYZER_FEATURES : DOWNLOADER_FEATURES;

export function Features() {
  return (
    <section className="border-y border-[#232330] bg-[#0C0C10]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <p className="eyebrow">{ANALYSIS_ENABLED ? "What it measures" : "What you get"}</p>
        <h2 className="mt-2 max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl">
          {ANALYSIS_ENABLED ? "An instrument, not an opinion" : "Accurate, or not shown"}
        </h2>
        <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8]">
          {ANALYSIS_ENABLED
            ? "Every number on this site comes from a computation on a real pixel. Where something cannot be measured, it is left blank rather than filled in."
            : "Every file size on this page comes from a real encode, and every size listed has been verified to actually exist. A size that isn't real doesn't get a card."}
        </p>

        <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => (
            <div key={feature.title} className="panel p-5">
              <feature.icon className="h-5 w-5 text-[#C8FF3D]" />
              <h3 className="mt-3 text-[15px] font-bold text-[#F2F2F7]">{feature.title}</h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-[#8E8EA8]">
                {feature.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* =========================== SupportedPlatforms ======================= */

export function SupportedPlatforms() {
  return (
    <section className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
      <p className="eyebrow">Coverage</p>
      <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
        Where it works
      </h2>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8]">
        Four platforms get a dedicated fast path that resolves in under a second. The rest
        go through a universal extractor that covers most of the video web.
      </p>

      <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {SUPPORTED_PLATFORMS.map((platform) => (
          <div key={platform.name} className="panel-raised px-4 py-3">
            <p className="text-sm font-bold text-[#F2F2F7]">{platform.name}</p>
            <p className="mt-0.5 text-[12.5px] text-[#8E8EA8]">{platform.note}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/* =============================== UseCases ============================= */

const ANALYZER_USE_CASES = [
  {
    who: "Studying a competitor",
    what: "Pull their thumbnail, read the palette in hex, see where the text sits and which psychological hook it uses — then build your own in that style with the recreate recipe.",
  },
  {
    who: "Checking your own draft",
    what: "Drop your unpublished thumbnail on the page. Before you upload, find out that the word you built the whole design around is 8 pixels tall in the mobile feed.",
  },
  {
    who: "Auditing a channel",
    what: "Paste a channel URL and get the last 24 thumbnails scored, plus the pattern: recurring palette, where the text always goes, how often a face appears, how consistent it all is.",
  },
  {
    who: "Picking between two options",
    what: "Compare mode puts 2–4 thumbnails side by side with aligned score rows and a per-category winner, so the choice stops being a coin flip.",
  },
];

const DOWNLOADER_USE_CASES = [
  {
    who: "Building a moodboard",
    what: "Grab the thumbnails you keep coming back to at full resolution, in one ZIP, with filenames that tell you where each one came from.",
  },
  {
    who: "Reposting your own video",
    what: "Take your published thumbnail back down in the exact size the next platform wants — 9:16 for Shorts and Reels, 1:1 for a grid, cropped around the subject.",
  },
  {
    who: "Replacing a lost original",
    what: "The source file is gone but the video is live. Pull the largest version the platform actually stores, and see plainly whether anything bigger is real or interpolated.",
  },
  {
    who: "Writing about a video",
    what: "A clean, correctly sized still for a blog post, a newsletter or a deck — in WebP if you care about page weight, PNG if you need it lossless.",
  },
];

const USE_CASES = ANALYSIS_ENABLED ? ANALYZER_USE_CASES : DOWNLOADER_USE_CASES;

export function UseCases() {
  return (
    <section className="border-y border-[#232330] bg-[#0C0C10]">
      <div className="mx-auto max-w-7xl px-5 py-20 sm:px-8">
        <p className="eyebrow">Who it's for</p>
        <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
          Four jobs it does well
        </h2>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          {USE_CASES.map((useCase) => (
            <div key={useCase.who} className="panel p-6">
              <h3 className="text-lg font-bold text-[#C8FF3D]">{useCase.who}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#8E8EA8]">{useCase.what}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ================================== FAQ =============================== */

/** Questions that hold regardless of whether the analyser is switched on. */
const CORE_FAQ = [
  {
    q: "Is ThumbIQ free?",
    a: "Yes, and there's no signup. Paste a link, take the sizes you want. There's no account, no extension and nothing to install.",
  },
  {
    q: "Why does the Full HD size say 'upscaled'?",
    a: "Because it is. YouTube stores thumbnails at 1280×720 at most, so a 1920×1080 export is interpolated — the pixels are invented by the resampler, not recovered from the source. We apply a mild unsharp mask to counter the softening and we label it, because selling you a fake 1080p would be a lie.",
  },
  {
    q: "Why do some sizes not appear for my video?",
    a: "Because the platform never generated them. YouTube doesn't create maxresdefault for every upload, and it doesn't always 404 when a size is missing — it often returns a grey placeholder with HTTP 200. Every candidate is checked by status, byte count and decoded pixel dimensions, and anything that fails is dropped rather than shown as a card that downloads a grey rectangle.",
  },
  {
    q: "Which platforms are supported?",
    a: "YouTube, TikTok, Vimeo and Dailymotion have dedicated fast paths. Instagram, Facebook, X, Twitch, Reddit, Pinterest, LinkedIn, Rumble, Odysee, Kick, Bilibili, VK and around 1,800 other sites resolve through a universal extractor. Anything else falls back to reading the page's Open Graph image.",
  },
  {
    q: "Do you store the thumbnails I look up?",
    a: "No. Images live in an in-memory cache for at most 60 minutes and are then evicted. There's no database, no object store, and no gallery of other people's thumbnails — a gallery would turn a research tool into a redistribution service.",
  },
  {
    q: "Is downloading someone else's thumbnail legal?",
    a: "Thumbnails are copyrighted works owned by their creators. ThumbIQ is built for research, study and commentary. Copying someone's thumbnail and publishing it as your own is not one of those uses — see the terms and DMCA pages for the full position.",
  },
  {
    q: "Can I download from a private or age-restricted video?",
    a: "No. ThumbIQ reads publicly served images and never bypasses an access control, logs in, or accepts credentials for any platform. Restricted content returns a clear message instead of a workaround.",
  },
  {
    q: "What's the difference between the formats?",
    a: "JPG is the smallest and what the platforms serve natively. WebP is usually smaller again at the same quality and is well supported everywhere modern. PNG is lossless and much larger — worth it only when you're going to edit the file. The real size of each is shown on the card before you pick.",
  },
];

/** Questions that only make sense while the analyser is switched on. */
const ANALYZER_FAQ = [
  {
    q: "Is the analysis free too?",
    a: "The full measured analysis is free. The AI verdict is rate-limited per hour because it costs real money to run — when you hit that limit, every measurement still works and the app tells you when to come back.",
  },
  {
    q: "Can you tell me the exact font a thumbnail uses?",
    a: "No, and neither can anyone else from a raster image without a licensed matching service. What ThumbIQ does instead is measurable: it classifies the letterform family from stroke geometry, measures the weight and width, and returns the three free Google Fonts whose own measured signature is closest — labelled as a closest match, never an identification.",
  },
  {
    q: "What is the mobile legibility check actually doing?",
    a: "It physically resamples your thumbnail to 168×94, 246×138, 360×202 and 1280×720 — the sizes YouTube really renders at — and re-measures the cap height of your text in real pixels at each one. Under 10px is a fail, 10 to 14 is a warning. It also re-runs OCR on the shrunken render to report how many of your words a reader could still recover.",
  },
  {
    q: "Why is a score sometimes shown as a dash?",
    a: "Because it couldn't be measured. A thumbnail with no text has no text readability — filling in 70 'to be safe' would be a fabricated measurement. Null scores are excluded from the overall and their weight is redistributed, and the scoring popover names exactly what was left out.",
  },
  {
    q: "Does the AI decide the scores?",
    a: "No. Scoring runs before the AI call, and its output is part of the AI's input. Claude receives the image and the measurements and is instructed that those are the only permitted source of any number, hex code or ratio. It writes the interpretation; the code produces the facts.",
  },
  {
    q: "What happens if the AI is down?",
    a: "You get an amber banner and everything else. The download grid, all eight sub-scores, the palette, the text measurements, the mobile check and the safe-zone map are all deterministic and run locally — the tool is designed to be useful with the AI switched off entirely.",
  },
];

/**
 * The list rendered on the page *and* the source of the FAQPage structured data. Both
 * read from here, so search results can never advertise an answer the page doesn't show.
 */
export const FAQ_ITEMS = ANALYSIS_ENABLED ? [...CORE_FAQ, ...ANALYZER_FAQ] : CORE_FAQ;

export function FAQ() {
  return (
    <section id="faq" className="mx-auto max-w-4xl px-5 py-20 sm:px-8">
      <p className="eyebrow">Questions</p>
      <h2 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
        The things people actually ask
      </h2>

      <div className="mt-10 space-y-3">
        {FAQ_ITEMS.map((item) => (
          <details key={item.q} className="panel group p-5 [&_summary::-webkit-details-marker]:hidden">
            <summary className="flex cursor-pointer items-start justify-between gap-4 text-[15px] font-bold text-[#F2F2F7]">
              {item.q}
              <span className="mt-0.5 shrink-0 text-[#C8FF3D] transition-transform group-open:rotate-45">
                +
              </span>
            </summary>
            <p className="mt-3 text-sm leading-relaxed text-[#8E8EA8]">{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
