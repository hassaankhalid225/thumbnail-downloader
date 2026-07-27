"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ClipboardPaste, ImagePlus, Search } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  SiDailymotion,
  SiFacebook,
  SiInstagram,
  SiPinterest,
  SiReddit,
  SiRumble,
  SiTiktok,
  SiTwitch,
  SiVimeo,
  SiX,
  SiYoutube,
} from "react-icons/si";

import { ANALYSIS_ENABLED, PLATFORM_COLORS, PLATFORM_STRIP } from "@/lib/constants";
import type { FlowState } from "@/lib/types";
import { cn, isImageFile } from "@/lib/utils";
import { useReducedMotion } from "@/components/ui";

type IconProps = { className?: string; style?: React.CSSProperties };

/**
 * simple-icons no longer ships a LinkedIn mark, so platforms without an icon get a
 * monogram instead of being quietly dropped from the strip — the backend resolves them
 * either way, and a missing logo shouldn't imply a missing capability.
 */
function Monogram({ letter }: { letter: string }) {
  return function MonogramIcon({ className, style }: IconProps) {
    return (
      <span
        className={cn(
          "inline-flex items-center justify-center rounded-[3px] border border-current text-[9px] font-black leading-none",
          className,
        )}
        style={style}
        aria-hidden="true"
      >
        {letter}
      </span>
    );
  };
}

const ICONS: Record<string, React.ComponentType<IconProps>> = {
  youtube: SiYoutube,
  tiktok: SiTiktok,
  instagram: SiInstagram,
  twitter: SiX,
  facebook: SiFacebook,
  twitch: SiTwitch,
  vimeo: SiVimeo,
  dailymotion: SiDailymotion,
  pinterest: SiPinterest,
  reddit: SiReddit,
  linkedin: Monogram({ letter: "in" }),
  rumble: SiRumble,
};

/* ========================== GridBackground ========================== */

export function GridBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="grid-bg absolute inset-0" />
      <div className="glow-lime left-[8%] top-[-8rem] h-[26rem] w-[26rem]" />
      <div className="glow-cyan right-[4%] top-[6rem] h-[22rem] w-[22rem]" />
    </div>
  );
}

/* ========================= PlatformDetector ========================= */

export function PlatformDetector({ platform }: { platform: string | null }) {
  const Icon = platform ? ICONS[platform] : undefined;
  const accent = platform ? (PLATFORM_COLORS[platform]?.accent ?? "#8E8EA8") : "#55556B";

  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center">
      <AnimatePresence mode="wait" initial={false}>
        {Icon ? (
          <motion.span
            key={platform}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={{ duration: 0.18 }}
            style={{ color: accent }}
            title={PLATFORM_COLORS[platform ?? "generic"]?.name}
          >
            <Icon className="h-5 w-5" />
          </motion.span>
        ) : (
          <motion.span
            key="idle"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-[#8E8EA8]"
          >
            <Search className="h-5 w-5" />
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

/* =========================== PlatformStrip ========================== */

export function PlatformStrip({ active }: { active: string | null }) {
  const reduced = useReducedMotion();
  return (
    <ul className="mt-8 flex flex-wrap items-center justify-center gap-x-7 gap-y-4">
      {PLATFORM_STRIP.map((platform, index) => {
        const Icon = ICONS[platform];
        if (!Icon) return null;
        const isActive = active === platform;
        return (
          <motion.li
            key={platform}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: reduced ? 0 : 0.9 + index * 0.035, duration: 0.3 }}
            title={PLATFORM_COLORS[platform]?.name}
          >
            <Icon
              className={cn(
                "h-5 w-5 transition-all duration-300",
                isActive ? "scale-115 opacity-100" : "opacity-40 grayscale",
              )}
              // The detected platform snaps to its own brand colour. Everything else
              // stays grey, so the strip reads as a state indicator, not decoration.
              {...(isActive ? { style: { color: PLATFORM_COLORS[platform]?.accent } } : {})}
            />
          </motion.li>
        );
      })}
    </ul>
  );
}

/* ============================== UrlInput ============================ */

export function UrlInput({
  value,
  platform,
  state,
  hasError,
  onChange,
  onSubmit,
  onFile,
}: {
  value: string;
  platform: string | null;
  state: FlowState;
  hasError: boolean;
  onChange: (value: string) => void;
  onSubmit: (value: string) => void;
  onFile: (file: File) => void;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const busy = state === "RESOLVING" || state === "ANALYZING_CV" || state === "ANALYZING_AI";

  // Paste an image straight onto the page — a creator checking their own draft
  // shouldn't have to save it somewhere first.
  useEffect(() => {
    // Only meaningful while the analyser is on — there is nothing to download from an
    // image the user already has on their machine.
    if (!ANALYSIS_ENABLED) return;
    const onPaste = (event: ClipboardEvent) => {
      const items = event.clipboardData?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) {
            event.preventDefault();
            onFile(file);
            return;
          }
        }
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [onFile]);

  const pasteFromClipboard = useCallback(async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        onChange(text.trim());
        inputRef.current?.focus();
      }
    } catch {
      inputRef.current?.focus();
    }
  }, [onChange]);

  const handleDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragging(false);
      if (!ANALYSIS_ENABLED) return;
      const file = event.dataTransfer.files?.[0];
      if (file && isImageFile(file)) onFile(file);
    },
    [onFile],
  );

  return (
    <div className="w-full">
      <div
        className={cn("group relative", hasError && "shake")}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
      >
        <div
          className={cn(
            "absolute -inset-px rounded-2xl bg-gradient-to-r from-[#C8FF3D] to-[#22D3EE] blur-sm transition duration-500",
            dragging ? "opacity-70" : "opacity-0 group-focus-within:opacity-60",
          )}
        />
        <form
          onSubmit={(event) => {
            event.preventDefault();
            onSubmit(value);
          }}
          className={cn(
            "relative flex items-center gap-2 rounded-2xl border bg-[#101015] p-2 transition-colors",
            dragging
              ? "border-[#C8FF3D]"
              : hasError
                ? "border-[#EF4444]/60"
                : "border-[#232330] focus-within:border-[#C8FF3D]/50",
          )}
        >
          <PlatformDetector platform={platform} />

          <input
            ref={inputRef}
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            aria-label="Video or post link"
            aria-invalid={hasError}
            placeholder="Paste a YouTube, TikTok, Instagram or any video link…"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            className="mono min-w-0 flex-1 bg-transparent px-1 text-[15px] text-white outline-none placeholder:text-[#8E8EA8] sm:text-base"
          />

          <button
            type="button"
            onClick={pasteFromClipboard}
            className="hidden items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-[#8E8EA8] transition-colors hover:text-white sm:flex"
          >
            <ClipboardPaste className="h-4 w-4" /> Paste
          </button>

          {ANALYSIS_ENABLED && (
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              title="Analyze your own image"
              aria-label="Analyze your own image"
              className="flex items-center rounded-lg px-2 py-2 text-[#8E8EA8] transition-colors hover:text-white"
            >
              <ImagePlus className="h-4 w-4" />
            </button>
          )}

          <button
            type="submit"
            disabled={busy || value.trim().length === 0}
            className="shrink-0 rounded-xl bg-[#C8FF3D] px-5 py-3 text-sm font-bold text-black transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40 sm:px-7 sm:text-base"
          >
            {busy ? "Working…" : ANALYSIS_ENABLED ? "Analyze" : "Get sizes"}
          </button>
        </form>

        {ANALYSIS_ENABLED && (
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            // Visually hidden and driven by the button above, but it still needs an
            // accessible name — a screen reader that lands on it otherwise announces
            // nothing at all.
            aria-label="Upload your own thumbnail image to analyze"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) onFile(file);
              event.target.value = "";
            }}
          />
        )}
      </div>

      <p className="mt-3 text-center text-xs text-[#8E8EA8]">
        {ANALYSIS_ENABLED
          ? "Or drop an image here — or just paste one — to check your own draft before you publish."
          : "Every size YouTube actually stores, in JPG, PNG and WebP. No signup, no watermark."}
      </p>
    </div>
  );
}
