"use client";

import { motion } from "framer-motion";
import { useState } from "react";

import { CopyButton, Tooltip, useReducedMotion, useToast } from "@/components/ui";
import { readableOn } from "@/lib/colors";
import type { ColorAnalysis } from "@/lib/types";
import { copyToClipboard, formatPercent } from "@/lib/utils";

/* ============================= PaletteStrip ============================ */

export function PaletteStrip({ palette }: { palette: ColorAnalysis["palette"] }) {
  const toast = useToast();
  const reduced = useReducedMotion();

  const handleClick = async (hex: string, event: React.MouseEvent) => {
    // Shift-click takes the whole palette — the thing a designer actually wants once
    // they've decided they like it.
    const value = event.shiftKey ? palette.map((s) => s.hex).join(", ") : hex;
    const ok = await copyToClipboard(value);
    if (ok) toast.push(event.shiftKey ? "Whole palette copied" : `${hex} copied`, "success");
  };

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
      {palette.map((swatch, index) => (
        <motion.button
          key={swatch.hex + index}
          type="button"
          initial={{ opacity: 0, scale: reduced ? 1 : 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: reduced ? 0 : 0.7 + index * 0.04, duration: 0.28 }}
          onClick={(event) => handleClick(swatch.hex, event)}
          title={`${swatch.hex} · ${swatch.name} · ${swatch.coverage}% — click to copy, shift-click for the whole palette`}
          className="group overflow-hidden rounded-xl border border-[#232330] text-left transition-all hover:-translate-y-1 hover:border-[#33334A]"
        >
          <div
            className="flex h-20 items-end justify-end p-2"
            style={{ background: swatch.hex }}
          >
            <span
              className="mono text-[11px] font-bold opacity-0 transition-opacity group-hover:opacity-100"
              style={{ color: readableOn(swatch.hex) }}
            >
              {swatch.hex}
            </span>
          </div>
          <div className="bg-[#101015] p-2">
            <p className="mono text-[11px] font-bold text-[#F2F2F7]">{swatch.hex}</p>
            <p className="truncate text-[11px] text-[#8E8EA8]">{swatch.name}</p>
            <p className="mono mt-0.5 text-[10px] text-[#8E8EA8]">{swatch.coverage}% of frame</p>
          </div>
        </motion.button>
      ))}
    </div>
  );
}

/* ============================== CoverageBar =========================== */

export function CoverageBar({ palette }: { palette: ColorAnalysis["palette"] }) {
  return (
    <div className="flex h-7 overflow-hidden rounded-lg border border-[#232330]">
      {palette.map((swatch, index) => (
        <div
          key={swatch.hex + index}
          style={{ background: swatch.hex, width: `${swatch.coverage}%` }}
          title={`${swatch.name} — ${swatch.coverage}%`}
        />
      ))}
    </div>
  );
}

/* =========================== ColorHarmonyWheel =========================
   Swatches plotted at their measured hue and saturation. The wheel is not
   decoration: the distance between the plotted dots is literally the harmony
   the classifier read.                                                     */

export function ColorHarmonyWheel({
  palette,
  harmony,
}: {
  palette: ColorAnalysis["palette"];
  harmony: ColorAnalysis["harmony"];
}) {
  const size = 210;
  const center = size / 2;
  const outer = center - 14;

  const chromatic = palette.filter((swatch) => swatch.hsv[1] >= 0.15);

  return (
    <div className="flex flex-col items-center gap-3">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img"
           aria-label={`Hue wheel showing a ${harmony.type} relationship`}>
        <defs>
          <radialGradient id="wheel-fade">
            <stop offset="0%" stopColor="#0A0A0D" stopOpacity="0.95" />
            <stop offset="62%" stopColor="#0A0A0D" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#0A0A0D" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* 72 hue wedges — enough to read as continuous, few enough to stay light. */}
        {Array.from({ length: 72 }, (_, index) => {
          const start = (index * 5 - 90) * (Math.PI / 180);
          const end = ((index + 1) * 5 - 90) * (Math.PI / 180);
          const x1 = center + outer * Math.cos(start);
          const y1 = center + outer * Math.sin(start);
          const x2 = center + outer * Math.cos(end);
          const y2 = center + outer * Math.sin(end);
          return (
            <path
              key={index}
              d={`M ${center} ${center} L ${x1} ${y1} A ${outer} ${outer} 0 0 1 ${x2} ${y2} Z`}
              fill={`hsl(${index * 5} 85% 55%)`}
              opacity={0.5}
            />
          );
        })}
        <circle cx={center} cy={center} r={outer} fill="url(#wheel-fade)" />
        <circle cx={center} cy={center} r={outer} fill="none" stroke="#232330" strokeWidth="1" />

        {chromatic.map((swatch, index) => {
          const angle = (swatch.hsv[0] - 90) * (Math.PI / 180);
          const distance = outer * Math.min(1, Math.max(0.22, swatch.hsv[1]));
          const x = center + distance * Math.cos(angle);
          const y = center + distance * Math.sin(angle);
          const r = 6 + (swatch.coverage / 100) * 12;
          return (
            <g key={swatch.hex + index}>
              <line x1={center} y1={center} x2={x} y2={y} stroke="#33334A" strokeWidth="1" />
              <circle cx={x} cy={y} r={r} fill={swatch.hex} stroke="#0A0A0D" strokeWidth="2.5" />
            </g>
          );
        })}
      </svg>

      <div className="text-center">
        <p className="text-sm font-bold capitalize text-[#F2F2F7]">
          {harmony.type.replace(/-/g, " ")}
        </p>
        <p className="mono text-[11px] text-[#8E8EA8]">
          {formatPercent(harmony.confidence)} confidence
        </p>
        <p className="mt-1 max-w-xs text-[11px] leading-relaxed text-[#8E8EA8]">
          {harmony.reason}
        </p>
      </div>
    </div>
  );
}

/* ================================ ColorTab ============================ */

export function ColorTab({ color }: { color: ColorAnalysis }) {
  const [exportKind, setExportKind] = useState<"css" | "tailwind" | "ase">("css");

  const exportValue =
    exportKind === "css"
      ? color.exports.css
      : JSON.stringify(
          exportKind === "tailwind" ? color.exports.tailwind : color.exports.ase,
          null,
          2,
        );

  return (
    <div className="space-y-7">
      <section>
        <SectionHead
          title="Dominant palette"
          hint="Six clusters found with KMeans in LAB colour space, not RGB — LAB is perceptually uniform, so the clusters match what your eye separates. Click a swatch to copy its hex; shift-click copies the set."
        />
        <PaletteStrip palette={color.palette} />
        <div className="mt-3">
          <CoverageBar palette={color.palette} />
          <p className="mt-1.5 text-[11px] text-[#8E8EA8]">
            Bar widths are measured coverage of the frame.
          </p>
        </div>
      </section>

      {/* min-w-0 on the grid children is load-bearing: the <pre> below has
          white-space: pre, so its min-content width is its longest line, and an auto
          grid track will happily grow past its container to accommodate that. */}
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_auto]">
        <section className="min-w-0 space-y-4">
          <SectionHead
            title="Colour behaviour"
            hint="Temperature comes from the mean b* channel in LAB — the yellow/blue axis. Saturation is the mean HSV S across the whole frame."
          />
          <dl className="grid grid-cols-2 gap-2.5">
            <Metric
              label="Temperature"
              value={color.temperature.profile}
              detail={`mean b* ${color.temperature.meanB} · ${formatPercent(color.temperature.warmRatio)} warm pixels`}
            />
            <Metric
              label="Saturation"
              value={color.saturation.profile}
              detail={`mean ${color.saturation.mean.toFixed(2)} · σ ${color.saturation.std.toFixed(2)}`}
            />
            <Metric
              label="Mean lightness"
              value={`L* ${color.brightness.meanL.toFixed(0)}`}
              detail={`${formatPercent(color.brightness.clippedBlack, 1)} crushed · ${formatPercent(color.brightness.clippedWhite, 1)} blown`}
            />
            <Metric
              label="Palette spread"
              value={`ΔE ${color.distinctiveness.toFixed(0)}`}
              detail="Mean perceptual distance between swatches"
            />
          </dl>

          <div className="panel-raised overflow-hidden">
            <div className="flex items-center justify-between border-b border-[#232330] px-3 py-2">
              <div className="flex gap-1">
                {(["css", "tailwind", "ase"] as const).map((kind) => (
                  <button
                    key={kind}
                    type="button"
                    onClick={() => setExportKind(kind)}
                    className={
                      exportKind === kind
                        ? "mono rounded-md bg-[#C8FF3D] px-2 py-1 text-[11px] font-bold uppercase text-black"
                        : "mono rounded-md px-2 py-1 text-[11px] font-bold uppercase text-[#8E8EA8] hover:text-white"
                    }
                  >
                    {kind}
                  </button>
                ))}
              </div>
              <CopyButton value={exportValue} compact label="Copy" />
            </div>
            <pre className="mono max-h-48 overflow-auto p-3 text-[11px] leading-relaxed text-[#8E8EA8]">
              {exportValue}
            </pre>
          </div>
        </section>

        <section className="panel-raised min-w-0 p-4">
          <SectionHead title="Harmony" hint="Hue relationships between the swatches that cover at least 5% of the frame and carry real chroma. Greys are excluded — they have no hue to relate." />
          <ColorHarmonyWheel palette={color.palette} harmony={color.harmony} />
        </section>
      </div>
    </div>
  );
}

export function SectionHead({ title, hint }: { title: string; hint: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <h3 className="text-sm font-bold text-[#F2F2F7]">{title}</h3>
      <Tooltip content={hint} />
    </div>
  );
}

export function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string;
}) {
  return (
    <div className="panel-raised p-3">
      <dt className="eyebrow">{label}</dt>
      <dd className="mono mt-1 text-base font-bold capitalize text-[#F2F2F7]">{value}</dd>
      {detail && <p className="mono mt-0.5 text-[10.5px] text-[#8E8EA8]">{detail}</p>}
    </div>
  );
}
