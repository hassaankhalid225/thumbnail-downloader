import type { ScoreKey, SizeId } from "./types";

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://thumbiq.app";

/**
 * Master switch for the analyzer.
 *
 * Off = pure thumbnail downloader: no analysis request is fired, no scores or AI verdict
 * render, compare/channel are closed, the upload-your-own-draft path is hidden, and the
 * marketing copy stops promising an analysis the product isn't doing.
 *
 * Nothing is deleted. The whole analysis stack — backend modules, scoring, the Claude
 * pass, every component under `components/analysis/` — is intact and untouched. Set
 * `NEXT_PUBLIC_ENABLE_ANALYSIS=true` in `.env.local` and it all comes back.
 */
export const ANALYSIS_ENABLED = process.env.NEXT_PUBLIC_ENABLE_ANALYSIS === "true";

export const PLATFORM_COLORS: Record<string, { accent: string; name: string }> = {
  youtube: { accent: "#FF0000", name: "YouTube" },
  tiktok: { accent: "#FE2C55", name: "TikTok" },
  instagram: { accent: "#E1306C", name: "Instagram" },
  twitter: { accent: "#1DA1F2", name: "X" },
  facebook: { accent: "#1877F2", name: "Facebook" },
  twitch: { accent: "#9146FF", name: "Twitch" },
  vimeo: { accent: "#1AB7EA", name: "Vimeo" },
  dailymotion: { accent: "#0066DC", name: "Dailymotion" },
  pinterest: { accent: "#E60023", name: "Pinterest" },
  reddit: { accent: "#FF4500", name: "Reddit" },
  linkedin: { accent: "#0A66C2", name: "LinkedIn" },
  rumble: { accent: "#85C742", name: "Rumble" },
  generic: { accent: "#8E8EA8", name: "Web page" },
  upload: { accent: "#C8FF3D", name: "Your upload" },
};

export const PLATFORM_STRIP: readonly string[] = [
  "youtube",
  "tiktok",
  "instagram",
  "twitter",
  "facebook",
  "twitch",
  "vimeo",
  "dailymotion",
  "pinterest",
  "reddit",
  "linkedin",
  "rumble",
];

/** Ladder display order. Matches services/imaging.py. */
export const SIZE_ORDER: readonly SizeId[] = [
  "fhd",
  "hd",
  "sd",
  "hq",
  "mq",
  "tiny",
  "vertical",
  "square",
];

export const SCORE_ORDER: readonly ScoreKey[] = [
  "stoppingPower",
  "textReadability",
  "mobileLegibility",
  "colorImpact",
  "contrast",
  "composition",
  "emotionalHook",
  "safeZone",
];

/**
 * What each score measures, in the words a creator would use. These strings are the
 * `?` tooltips — teaching what the number means is the retention loop.
 */
export const SCORE_META: Record<ScoreKey, { icon: string; tooltip: string }> = {
  stoppingPower: {
    icon: "Zap",
    tooltip:
      "How hard this image pulls the eye out of a scroll. Built from colour punch, contrast range, how focused the busy areas are, and whether there's a face.",
  },
  textReadability: {
    icon: "Type",
    tooltip:
      "Whether the words can actually be read. Cap height at phone size, WCAG contrast against what sits behind each block, and word count.",
  },
  mobileLegibility: {
    icon: "Smartphone",
    tooltip:
      "The thumbnail is physically shrunk to the five sizes YouTube renders at, and the text is re-measured on each. Under 10px cap height is unreadable.",
  },
  colorImpact: {
    icon: "Palette",
    tooltip:
      "Palette strength: which harmony the hues form, how saturated they are, and how far apart the swatches sit perceptually.",
  },
  contrast: {
    icon: "Contrast",
    tooltip:
      "Global range between the darkest and brightest 5% of the frame, local contrast inside 16px tiles, and the WCAG ratio behind every text block.",
  },
  composition: {
    icon: "Crosshair",
    tooltip:
      "Where the eye lands relative to the rule-of-thirds intersections, left/right and top/bottom weight balance, breathing room, and clutter.",
  },
  emotionalHook: {
    icon: "Smile",
    tooltip:
      "Face size in frame, whether the eye-line sits in the upper third, and an estimated expression. No face caps this at 65.",
  },
  safeZone: {
    icon: "ShieldAlert",
    tooltip:
      "Whether YouTube's own UI — the duration pill, the CC badge, the progress bar — lands on top of anything that matters.",
  },
};

export const SURFACE_META: Record<string, { device: string; note: string }> = {
  mobile_feed: { device: "Phone", note: "The home feed. Where most impressions happen." },
  mobile_search: { device: "Phone", note: "Search results on mobile." },
  desktop_grid: { device: "Desktop", note: "The desktop home grid." },
  desktop_sidebar: { device: "Desktop", note: "Suggested videos beside a playing video." },
  watch_page: { device: "Desktop", note: "The full-size preview before playback." },
};

export const EXAMPLE_URLS: readonly { label: string; url: string }[] = [
  { label: "A YouTube classic", url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ" },
  { label: "A Vimeo staff pick", url: "https://vimeo.com/76979871" },
  { label: "A YouTube Short", url: "https://www.youtube.com/shorts/tPEE9ZwTmy0" },
];

export const SUPPORTED_PLATFORMS: readonly { name: string; note: string }[] = [
  { name: "YouTube", note: "Videos, Shorts, Live, embeds — every URL shape" },
  { name: "TikTok", note: "Vertical covers via oEmbed" },
  { name: "Instagram", note: "Reels and posts" },
  { name: "Vimeo", note: "Up to Full HD renditions" },
  { name: "X (Twitter)", note: "Video posts and cards" },
  { name: "Facebook", note: "Videos and Reels" },
  { name: "Twitch", note: "Clips and VODs" },
  { name: "Dailymotion", note: "All rendition sizes" },
  { name: "Reddit", note: "Hosted video posts" },
  { name: "Pinterest", note: "Pin images" },
  { name: "LinkedIn", note: "Native video posts" },
  { name: "Rumble, Odysee, Kick, Bilibili, VK…", note: "1,800+ more via yt-dlp" },
];

export const COPYRIGHT_LINE =
  "Thumbnails are the property of their creators. Use for research and inspiration — don't republish someone else's thumbnail as your own.";
