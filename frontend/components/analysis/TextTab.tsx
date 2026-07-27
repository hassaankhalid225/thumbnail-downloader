"use client";

import { motion } from "framer-motion";
import { AlertTriangle } from "lucide-react";

import { CopyButton, useReducedMotion } from "@/components/ui";
import { Metric, SectionHead } from "./ColorTab";
import type { FontRead, TextAnalysis, TextBlock } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

/* =========================== TextOverlayCanvas ========================
   The bounding boxes draw themselves onto the thumbnail. Seeing the boxes is
   what makes "your text sits in the bottom-left" land — a number never does. */

export function TextOverlayCanvas({
  src,
  blocks,
}: {
  src: string;
  blocks: TextBlock[];
}) {
  const reduced = useReducedMotion();

  return (
    <div className="relative overflow-hidden rounded-xl border border-[#232330] bg-[#0F0F14]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="Thumbnail with detected text outlined" className="w-full" />
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
      >
        {blocks.map((block, index) => (
          <motion.rect
            key={index}
            x={block.bbox.x * 100}
            y={block.bbox.y * 100}
            width={block.bbox.w * 100}
            height={block.bbox.h * 100}
            fill="rgba(200,255,61,0.07)"
            stroke={block.passesAA ? "#C8FF3D" : "#F59E0B"}
            strokeWidth={0.35}
            vectorEffect="non-scaling-stroke"
            initial={{ pathLength: reduced ? 1 : 0, opacity: reduced ? 1 : 0 }}
            animate={{ pathLength: 1, opacity: 1 }}
            transition={{
              duration: reduced ? 0 : 0.6,
              delay: reduced ? 0 : 0.9 + index * 0.1,
              ease: "easeOut",
            }}
          />
        ))}
      </svg>
    </div>
  );
}

/* ============================== ContrastPill ========================== */

export function ContrastPill({ ratio, passesAA }: { ratio: number; passesAA: boolean }) {
  return (
    <span
      className={
        passesAA
          ? "mono inline-flex items-center gap-1 rounded-md border border-[#22C55E]/30 bg-[#22C55E]/10 px-2 py-0.5 text-[11px] font-bold text-[#22C55E]"
          : "mono inline-flex items-center gap-1 rounded-md border border-[#EF4444]/30 bg-[#EF4444]/10 px-2 py-0.5 text-[11px] font-bold text-[#EF4444]"
      }
      title={
        passesAA
          ? "Meets WCAG AA (4.5:1) against the background actually behind the letters"
          : "Below WCAG AA (4.5:1) — the text is fighting its own background"
      }
    >
      {ratio.toFixed(1)}:1 {passesAA ? "AA" : "fails AA"}
    </span>
  );
}

/* ============================== FontReadCard ========================== */

export function FontReadCard({ fontRead }: { fontRead: FontRead }) {
  if (!fontRead.classification) {
    return (
      <div className="panel-raised p-4">
        <SectionHead title="Letterform read" hint="Measured from stroke geometry." />
        <p className="text-sm text-[#8E8EA8]">{fontRead.disclaimer}</p>
      </div>
    );
  }

  return (
    <div className="panel-raised p-4">
      <SectionHead
        title="Letterform read"
        hint="Classified from measured geometry: stroke width and its variation, glyph width relative to cap height, ink density at the terminals, and slant. This is a classification, never an identification."
      />

      <div className="flex flex-wrap items-baseline gap-2">
        <span className="text-lg font-bold capitalize text-[#F2F2F7]">
          {fontRead.classification.replace(/-/g, " ")}
        </span>
        <span className="mono rounded-md border border-[#232330] bg-[#0F0F14] px-2 py-0.5 text-[11px] font-bold uppercase text-[#C8FF3D]">
          {fontRead.weight}
        </span>
        {fontRead.italic && (
          <span className="mono rounded-md border border-[#232330] px-2 py-0.5 text-[11px] italic text-[#8E8EA8]">
            italic {fontRead.slantDeg}°
          </span>
        )}
        {fontRead.casePattern && (
          <span className="mono text-[11px] text-[#8E8EA8]">{fontRead.casePattern}</span>
        )}
      </div>

      <dl className="mono mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] text-[#8E8EA8] sm:grid-cols-4">
        <Pair label="stroke" value={fontRead.strokeWidth} suffix="px" />
        <Pair label="modulation" value={fontRead.strokeContrast} />
        <Pair label="width/cap" value={fontRead.widthRatio} />
        <Pair label="serif score" value={fontRead.serifScore} />
      </dl>

      <p className="eyebrow mt-4">Closest free fonts</p>
      <ul className="mt-2 space-y-1.5">
        {fontRead.closestGoogleFonts.map((font) => (
          <li key={font.name} className="flex items-center gap-3">
            <span className="w-40 shrink-0 text-sm font-semibold text-[#F2F2F7]">
              {font.name}
            </span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#232330]">
              <div
                className="h-full rounded-full bg-[#22D3EE]"
                style={{ width: `${font.confidence * 100}%` }}
              />
            </div>
            <span className="mono w-10 shrink-0 text-right text-[11px] text-[#8E8EA8]">
              {formatPercent(font.confidence)}
            </span>
          </li>
        ))}
      </ul>

      <p className="mt-3 flex items-start gap-1.5 text-[11px] leading-relaxed text-[#F59E0B]">
        <AlertTriangle className="mt-px h-3 w-3 shrink-0" />
        {fontRead.disclaimer}
      </p>
    </div>
  );
}

function Pair({ label, value, suffix = "" }: { label: string; value: number | null; suffix?: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider">{label}</dt>
      <dd className="text-[#8E8EA8]">{value === null ? "—" : `${value}${suffix}`}</dd>
    </div>
  );
}

/* ================================ TextTab ============================= */

export function TextTab({ text, src }: { text: TextAnalysis; src: string }) {
  const extracted = text.blocks
    .map((block) => block.text)
    .filter(Boolean)
    .join("\n");

  return (
    <div className="space-y-7">
      {!text.recognitionAvailable && text.recognitionNote && (
        <div className="rounded-xl border border-[#F59E0B]/30 bg-[#F59E0B]/8 p-3.5">
          <p className="flex items-start gap-2 text-sm leading-relaxed text-[#F59E0B]">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {text.recognitionNote}
          </p>
        </div>
      )}

      {text.blocks.length === 0 ? (
        <div className="panel-raised p-8 text-center">
          <p className="text-sm font-semibold text-[#F2F2F7]">No text detected</p>
          <p className="mt-1 text-sm text-[#8E8EA8]">
            Text readability and mobile legibility were left unscored rather than filled
            in with a guess.
          </p>
        </div>
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
            <section className="min-w-0">
              <SectionHead
                title="Where the text sits"
                hint="Boxes are the detected text regions. Lime means the block clears WCAG AA against what's behind it; amber means it doesn't."
              />
              <TextOverlayCanvas src={src} blocks={text.blocks} />
            </section>

            <section className="min-w-0 space-y-3">
              <SectionHead
                title="Per-block measurements"
                hint="Cap height is measured from the ink row profile — the baseline is the lowest row still carrying 15% of peak ink, so descenders don't inflate it."
              />
              <ul className="space-y-2">
                {text.blocks.map((block, index) => (
                  <li key={index} className="panel-raised p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-bold text-[#F2F2F7]">
                        {block.text ?? (
                          <span className="italic text-[#8E8EA8]">
                            text region (not transcribed)
                          </span>
                        )}
                      </span>
                      <ContrastPill ratio={block.wcagContrast} passesAA={block.passesAA} />
                    </div>
                    <dl className="mono mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#8E8EA8]">
                      <span>cap {block.capHeightPx.toFixed(0)}px</span>
                      <span>{block.heightPercent.toFixed(1)}% of frame height</span>
                      <span>{block.quadrant}</span>
                      <span
                        className="flex items-center gap-1"
                        title="Text colour / background colour, sampled from the ink and from what sits immediately behind it"
                      >
                        <i
                          className="inline-block h-2.5 w-2.5 rounded-sm border border-[#33334A]"
                          style={{ background: block.textColor }}
                        />
                        on
                        <i
                          className="inline-block h-2.5 w-2.5 rounded-sm border border-[#33334A]"
                          style={{ background: block.backgroundColor }}
                        />
                      </span>
                    </dl>
                  </li>
                ))}
              </ul>

              {extracted && (
                <div className="flex justify-end">
                  <CopyButton value={extracted} label="Copy extracted text" />
                </div>
              )}
            </section>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <Metric
              label="Word count"
              value={String(text.wordCount)}
              detail={`${text.wordCountVerdict}${text.wordCountEstimated ? " (estimated — no OCR)" : ""}`}
            />
            <Metric
              label="Text area"
              value={formatPercent(text.textAreaRatio, 1)}
              detail="Sweet spot is 8–25% of the frame"
            />
            <Metric
              label="Detected via"
              value={text.textSource === "ocr" ? "OCR" : "Geometry"}
              detail={text.engine}
            />
          </div>

          <FontReadCard fontRead={text.fontRead} />
        </>
      )}
    </div>
  );
}
