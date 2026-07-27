import { PLATFORM_COLORS } from "./constants";

export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatViews(views: number | null): string {
  if (views === null || !Number.isFinite(views)) return "—";
  if (views < 1000) return String(views);
  if (views < 1_000_000) return `${(views / 1000).toFixed(1)}K`;
  if (views < 1_000_000_000) return `${(views / 1_000_000).toFixed(1)}M`;
  return `${(views / 1_000_000_000).toFixed(2)}B`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds)) return "—";
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  const secs = total % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${minutes}:${pad(secs)}`;
}

export function formatPercent(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/**
 * Client-side platform guess, purely so the input can show a logo before the request
 * lands. The backend's detector is authoritative; this is a 120ms affordance.
 */
export function detectPlatform(raw: string): string | null {
  const url = raw.trim();
  if (url.length < 4) return null;

  let host: string;
  try {
    host = new URL(url.includes("://") ? url : `https://${url}`).hostname.toLowerCase();
  } catch {
    return null;
  }

  const map: [string, string][] = [
    ["youtube.", "youtube"],
    ["youtu.be", "youtube"],
    ["tiktok.", "tiktok"],
    ["instagram.", "instagram"],
    ["instagr.am", "instagram"],
    ["twitter.", "twitter"],
    ["x.com", "twitter"],
    ["facebook.", "facebook"],
    ["fb.watch", "facebook"],
    ["twitch.", "twitch"],
    ["vimeo.", "vimeo"],
    ["dailymotion.", "dailymotion"],
    ["dai.ly", "dailymotion"],
    ["pinterest.", "pinterest"],
    ["pin.it", "pinterest"],
    ["reddit.", "reddit"],
    ["redd.it", "reddit"],
    ["linkedin.", "linkedin"],
    ["rumble.", "rumble"],
  ];

  for (const [needle, platform] of map) {
    if (host === needle.replace(/\.$/, "") || host.includes(needle)) return platform;
  }
  return host.includes(".") ? "generic" : null;
}

export function platformAccent(platform: string | null): string {
  if (!platform) return PLATFORM_COLORS.generic.accent;
  return (PLATFORM_COLORS[platform] ?? PLATFORM_COLORS.generic).accent;
}

export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Clipboard API needs a secure context; fall back to the old selection trick so
    // copy still works over plain http on a LAN address.
    try {
      const area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(area);
      return ok;
    } catch {
      return false;
    }
  }
}

export function isImageFile(file: File): boolean {
  return file.type.startsWith("image/");
}

/** Compresses an analysis payload into a URL-safe string for the share link. */
export function encodeShare(payload: unknown): string {
  const json = JSON.stringify(payload);
  const bytes = new TextEncoder().encode(json);
  let binary = "";
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function decodeShare<T>(encoded: string): T | null {
  try {
    const base64 = encoded.replace(/-/g, "+").replace(/_/g, "/");
    const binary = atob(base64);
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    return JSON.parse(new TextDecoder().decode(bytes)) as T;
  } catch {
    return null;
  }
}
