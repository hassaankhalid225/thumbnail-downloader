"use client";

import { motion } from "framer-motion";
import { Check, TriangleAlert, X } from "lucide-react";

import { useReducedMotion } from "@/components/ui";
import { verdictColor } from "@/lib/colors";
import { SURFACE_META } from "@/lib/constants";
import type { MobileLegibility } from "@/lib/types";
import { cn, formatPercent } from "@/lib/utils";
import { SectionHead } from "./ColorTab";

const ICONS = { PASS: Check, WARNING: TriangleAlert, FAIL: X } as const;

/**
 * The feature no competitor has, and the reason this tab is allowed to be loud.
 *
 * The renders are shown at their true CSS pixel size — 168×94 really is 168×94 on
 * screen. Scaling them up "so you can see them better" would destroy the entire point.
 */
export function MobilePreviewStrip({
  src,
  mobile,
}: {
  src: string;
  mobile: MobileLegibility;
}) {
  const reduced = useReducedMotion();

  if (!mobile.available) {
    return (
      <div className="panel-raised p-8 text-center">
        <p className="text-sm font-semibold text-[#F2F2F7]">Nothing to check</p>
        <p className="mt-1 text-sm text-[#8E8EA8]">{mobile.reason}</p>
      </div>
    );
  }

  const failing = mobile.surfaces.filter((surface) => surface.verdict === "FAIL");

  return (
    <div className="space-y-5">
      {failing.length > 0 && (
        <div className="rounded-xl border border-[#EF4444]/40 bg-[#EF4444]/8 p-4">
          <p className="text-sm font-bold text-[#EF4444]">
            Your text is unreadable on {failing.length} of {mobile.surfaces.length} surfaces
          </p>
          <p className="mt-1 text-sm leading-relaxed text-[#FCA5A5]">
            {failing.map((surface) => surface.label).join(", ")} —{" "}
            {failing[0]?.reason.toLowerCase()}
          </p>
        </div>
      )}

      {/* The renders are shown at true pixel scale, so on a narrow screen this row has
          to scroll rather than shrink — shrinking them would falsify the whole check. */}
      <div className="-mx-1 flex items-start gap-5 overflow-x-auto px-1 pb-2 lg:flex-wrap lg:overflow-x-visible">
        {mobile.surfaces.map((surface, index) => {
          const Icon = ICONS[surface.verdict];
          const color = verdictColor(surface.verdict);
          const meta = SURFACE_META[surface.surface];
          // The watch-page render is 1280px wide; show it capped so the row stays usable.
          const displayWidth = Math.min(surface.width, 380);

          return (
            <motion.figure
              key={surface.surface}
              initial={{ opacity: 0, x: reduced ? 0 : 18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: reduced ? 0 : 1.1 + index * 0.08, duration: 0.35 }}
              className="shrink-0 space-y-2"
            >
              <div
                className={cn(
                  "overflow-hidden rounded-lg border-2",
                  surface.verdict === "FAIL" && "attention-pulse",
                )}
                style={{ width: displayWidth, borderColor: `${color}66` }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={src}
                  alt={`${surface.label} render, ${surface.width} by ${surface.height} pixels`}
                  width={displayWidth}
                  height={Math.round((displayWidth / surface.width) * surface.height)}
                  className="block h-auto w-full"
                />
              </div>

              <figcaption style={{ width: displayWidth }}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[12px] font-bold text-[#F2F2F7]">{surface.label}</span>
                  <span
                    className="mono flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-black"
                    style={{ background: `${color}1f`, color }}
                  >
                    <Icon className="h-3 w-3" />
                    {surface.verdict}
                  </span>
                </div>
                <p className="mono mt-0.5 text-[10.5px] text-[#8E8EA8]">
                  {surface.width}×{surface.height} · cap {surface.capHeightPx.toFixed(0)}px
                  {surface.ocrRecoveryRatio !== null &&
                    ` · ${formatPercent(surface.ocrRecoveryRatio)} of words still readable by OCR`}
                </p>
                {meta && <p className="mt-1 text-[10.5px] text-[#8E8EA8]">{meta.note}</p>}
              </figcaption>
            </motion.figure>
          );
        })}
      </div>

      <p className="text-[11px] leading-relaxed text-[#8E8EA8]">
        Each panel is the thumbnail physically resampled to the size YouTube renders it
        at, shown at true scale. Cap height under 10px fails, 10–14px is a warning, above
        14px passes.
      </p>
    </div>
  );
}

export function MobileTab({ src, mobile }: { src: string; mobile: MobileLegibility }) {
  return (
    <div className="space-y-5">
      <SectionHead
        title="What it actually looks like in the feed"
        hint="The thumbnail is downscaled to the five sizes YouTube really renders at, and the text is re-measured on each one. This is the check that catches a thumbnail that looks great in the editor and reads as a smudge on a phone."
      />
      <MobilePreviewStrip src={src} mobile={mobile} />
    </div>
  );
}
