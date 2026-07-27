"use client";

import { motion } from "framer-motion";
import {
  Contrast,
  Crosshair,
  Palette,
  ShieldAlert,
  Smartphone,
  Smile,
  Type,
  Zap,
} from "lucide-react";
import { useState } from "react";

import { Tooltip, useReducedMotion } from "@/components/ui";
import { scoreColor } from "@/lib/colors";
import { SCORE_META, SCORE_ORDER } from "@/lib/constants";
import type { ScoreKey, Scores } from "@/lib/types";

const ICONS: Record<
  string,
  React.ComponentType<{ className?: string; style?: React.CSSProperties }>
> = {
  Zap,
  Type,
  Smartphone,
  Palette,
  Contrast,
  Crosshair,
  Smile,
  ShieldAlert,
};

export function ScoreBreakdown({ scores }: { scores: Scores }) {
  const reduced = useReducedMotion();

  return (
    <div className="grid gap-2.5 sm:grid-cols-2">
      {SCORE_ORDER.map((key, index) => {
        const value = scores[key];
        const meta = SCORE_META[key];
        const Icon = ICONS[meta.icon] ?? Zap;
        const color = scoreColor(value);

        return (
          <div key={key} className="panel-raised p-3.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex min-w-0 items-center gap-2">
                <Icon className="h-3.5 w-3.5 shrink-0" style={{ color }} />
                <span className="truncate text-[13px] font-semibold text-[#F2F2F7]">
                  {scores.labels[key]}
                </span>
                <Tooltip content={meta.tooltip} />
              </div>
              <span className="mono shrink-0 text-lg font-bold" style={{ color }}>
                {value === null ? "—" : value}
              </span>
            </div>

            <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-[#232330]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${value ?? 0}%` }}
                transition={{
                  duration: reduced ? 0 : 0.7,
                  delay: reduced ? 0 : 0.4 + index * 0.06,
                  ease: [0.22, 1, 0.36, 1],
                }}
                className="h-full rounded-full"
                style={{ background: color, boxShadow: `0 0 8px ${color}66` }}
              />
            </div>

            <p className="mt-2 text-[11.5px] leading-relaxed text-[#8E8EA8]">
              {scores.reasons[key]}
            </p>
          </div>
        );
      })}
    </div>
  );
}

/**
 * A black-box score is worthless. This popover publishes the exact weights the overall
 * number is built from, and names anything that was excluded and why.
 */
export function ScoringExplainer({ scores }: { scores: Scores }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="text-xs font-semibold text-[#8E8EA8] underline decoration-dotted underline-offset-4 transition-colors hover:text-[#C8FF3D]"
      >
        How is this scored?
      </button>

      {open && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          // Centred on the trigger rather than anchored to its left edge: the trigger
          // itself is centred under the dial on narrow screens, so a left-anchored
          // popover runs off the right of a 375px viewport.
          className="absolute left-1/2 top-full z-40 mt-2 w-[min(24rem,86vw)] -translate-x-1/2 rounded-xl border border-[#33334A] bg-[#16161D] p-4 shadow-2xl"
        >
          <p className="text-sm font-bold text-[#F2F2F7]">The weights</p>
          <p className="mt-1 text-xs leading-relaxed text-[#8E8EA8]">
            The overall score is a weighted mean of the eight sub-scores. Every sub-score
            comes from a measurement of real pixels — the AI writes the verdict, it never
            sets a number.
          </p>

          <ul className="mt-3 space-y-1.5">
            {SCORE_ORDER.map((key) => (
              <li key={key} className="flex items-center justify-between gap-3 text-xs">
                <span className="text-[#8E8EA8]">{scores.labels[key]}</span>
                <span className="mono font-bold text-[#F2F2F7]">
                  {(scores.weights[key] * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>

          {scores.excludedNote && (
            <p className="mt-3 rounded-lg border border-[#F59E0B]/25 bg-[#F59E0B]/10 p-2.5 text-[11px] leading-relaxed text-[#F59E0B]">
              {scores.excludedNote}
            </p>
          )}

          <p className="mt-3 text-[11px] leading-relaxed text-[#8E8EA8]">
            Excluded scores don&apos;t get a placeholder value — their weight is
            redistributed across the ones that were measurable.
          </p>
        </motion.div>
      )}
    </div>
  );
}

export type { ScoreKey };
