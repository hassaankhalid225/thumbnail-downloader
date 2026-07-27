"use client";

import { motion } from "framer-motion";

import { useReducedMotion } from "@/components/ui";
import { severityColor } from "@/lib/colors";
import type {
  CompositionAnalysis,
  FaceAnalysis,
  QualityAnalysis,
  SafeZoneAnalysis,
} from "@/lib/types";
import { formatBytes, formatPercent } from "@/lib/utils";
import { Metric, SectionHead } from "./ColorTab";

/* ============================= FocalPointMap ========================== */

export function FocalPointMap({
  src,
  composition,
  faces,
}: {
  src: string;
  composition: CompositionAnalysis;
  faces: FaceAnalysis;
}) {
  const reduced = useReducedMotion();

  return (
    <div className="relative overflow-hidden rounded-xl border border-[#232330] bg-[#0F0F14]">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="Thumbnail with the rule-of-thirds grid and focal point" className="w-full" />
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 h-full w-full"
        aria-hidden="true"
      >
        {[33.333, 66.667].map((position) => (
          <g key={position}>
            <line x1={position} y1="0" x2={position} y2="100" stroke="#F2F2F7" strokeOpacity="0.25" strokeWidth="0.25" vectorEffect="non-scaling-stroke" />
            <line x1="0" y1={position} x2="100" y2={position} stroke="#F2F2F7" strokeOpacity="0.25" strokeWidth="0.25" vectorEffect="non-scaling-stroke" />
          </g>
        ))}
        {[33.333, 66.667].flatMap((x) =>
          [33.333, 66.667].map((y) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="0.7" fill="#F2F2F7" fillOpacity="0.45" />
          )),
        )}

        {faces.faces.map((face, index) => (
          <rect
            key={index}
            x={face.bbox.x * 100}
            y={face.bbox.y * 100}
            width={face.bbox.w * 100}
            height={face.bbox.h * 100}
            fill="none"
            stroke="#22D3EE"
            strokeWidth="0.35"
            vectorEffect="non-scaling-stroke"
            strokeDasharray="2 1.5"
          />
        ))}
      </svg>

      <motion.span
        initial={{ scale: reduced ? 1 : 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ type: "spring", stiffness: 240, damping: 18, delay: reduced ? 0 : 0.3 }}
        className="pointer-events-none absolute h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[#C8FF3D] bg-[#C8FF3D]/25"
        style={{
          left: `${composition.focalPoint.x * 100}%`,
          top: `${composition.focalPoint.y * 100}%`,
          boxShadow: "0 0 18px rgba(200,255,61,0.55)",
        }}
        title={`Focal point (${composition.focalPoint.x.toFixed(2)}, ${composition.focalPoint.y.toFixed(2)})`}
      />
    </div>
  );
}

/* ============================== BalanceMeters ========================= */

export function BalanceMeters({ composition }: { composition: CompositionAnalysis }) {
  const rows: { label: string; value: number; hint: string }[] = [
    {
      label: "Left / right balance",
      value: composition.balance.lr,
      hint: "1.00 means the visual weight either side of centre is equal",
    },
    {
      label: "Top / bottom balance",
      value: composition.balance.tb,
      hint: "Weight = saturation × local contrast × edge density",
    },
    {
      label: "Thirds alignment",
      value: composition.ruleOfThirdsScore,
      hint: "How close the focal point sits to a thirds intersection",
    },
    {
      label: "Background separation",
      value: composition.depth.backgroundBlur,
      hint: "How much softer the background is than the subject",
    },
    {
      label: "Subject focus",
      value: composition.saliencyConcentration,
      hint: "Share of visual attention held by the busiest fifth of the frame",
    },
  ];

  return (
    <ul className="space-y-3">
      {rows.map((row) => (
        <li key={row.label}>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[12.5px] text-[#8E8EA8]" title={row.hint}>
              {row.label}
            </span>
            <span className="mono text-[12.5px] font-bold text-[#F2F2F7]">
              {row.value.toFixed(2)}
            </span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-[#232330]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#22D3EE] to-[#C8FF3D]"
              style={{ width: `${Math.max(0, Math.min(1, row.value)) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}

/* ============================ CompositionTab ========================== */

export function CompositionTab({
  src,
  composition,
  faces,
  quality,
}: {
  src: string;
  composition: CompositionAnalysis;
  faces: FaceAnalysis;
  quality: QualityAnalysis;
}) {
  return (
    <div className="space-y-7">
      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <section className="min-w-0">
          <SectionHead
            title="Where the eye lands"
            hint="The lime dot is the centroid of the saliency map, thresholded at its 80th percentile. Cyan boxes are detected faces. The grid is the rule of thirds."
          />
          <FocalPointMap src={src} composition={composition} faces={faces} />
        </section>

        <section className="min-w-0 space-y-4">
          <SectionHead title="Structure" hint="Balance compares visual weight across the two halves of the frame in each axis." />
          <BalanceMeters composition={composition} />

          <dl className="grid grid-cols-2 gap-2.5">
            <Metric
              label="Busyness"
              value={composition.edgeDensity.toFixed(3)}
              detail={composition.cluttered ? "Cluttered — above 0.18" : "Clean"}
            />
            <Metric
              label="Negative space"
              value={formatPercent(composition.negativeSpace)}
              detail="Quiet, flat, edge-free tiles"
            />
          </dl>
        </section>
      </div>

      <section>
        <SectionHead
          title="Faces"
          hint="Detector is named honestly — a YuNet detection and a Haar detection are not the same evidence. Expression is a geometric estimate, never a trained classifier."
        />
        {faces.count === 0 ? (
          <p className="panel-raised p-4 text-sm text-[#8E8EA8]">
            No face detected. Emotional hook was scored on visual energy alone and capped
            at 65 — a human face is the strongest hook a thumbnail has.
            {faces.note && <span className="mt-2 block text-[#8E8EA8]">{faces.note}</span>}
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {faces.faces.map((face, index) => (
              <div key={index} className="panel-raised p-3">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-bold text-[#F2F2F7]">Face {index + 1}</span>
                  <span className="mono text-sm font-bold text-[#22D3EE]">
                    {face.areaPercent.toFixed(1)}%
                  </span>
                </div>
                <dl className="mono mt-2 space-y-1 text-[11px] text-[#8E8EA8]">
                  <div>position · {face.quadrant}</div>
                  <div>
                    eye-line ·{" "}
                    {face.eyeLineUpperThird === null
                      ? "not resolvable"
                      : face.eyeLineUpperThird
                        ? `upper third (y ${face.eyeLineY?.toFixed(2)})`
                        : `below upper third (y ${face.eyeLineY?.toFixed(2)})`}
                  </div>
                  <div>
                    expression · {face.expression.label ?? "—"}{" "}
                    {face.expression.label &&
                      `(${formatPercent(face.expression.confidence)}, estimate)`}
                  </div>
                </dl>
              </div>
            ))}
          </div>
        )}
        <p className="mono mt-2 text-[10.5px] text-[#8E8EA8]">
          detector: {faces.detector}
        </p>
      </section>

      <section>
        <SectionHead
          title="Technical quality"
          hint="Sharpness is the variance of the Laplacian. Compression is the ratio of gradient energy on 8-pixel block boundaries to everywhere else — a re-compressed image prefers multiples of 8."
        />
        <dl className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            label="Sharpness"
            value={quality.sharpness.toFixed(0)}
            detail={quality.sharpnessVerdict}
          />
          <Metric
            label="Noise"
            value={quality.noise.toFixed(3)}
            detail="Immerkær estimator, 0–1"
          />
          <Metric
            label="Compression"
            value={quality.compressionArtifacts}
            detail={`block ratio ${quality.blockRatio}`}
          />
          <Metric
            label="Source"
            value={`${quality.width}×${quality.height}`}
            detail={`${formatBytes(quality.bytes)} · ${quality.aspect}`}
          />
        </dl>
        {quality.specNotes.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {quality.specNotes.map((note) => (
              <li key={note} className="text-[12px] text-[#F59E0B]">
                • {note}
              </li>
            ))}
          </ul>
        )}
        {quality.meetsYouTubeSpec && (
          <p className="mt-3 text-[12px] text-[#22C55E]">
            • Meets YouTube&apos;s thumbnail spec: at least 1280×720, 16:9, under 2 MB.
          </p>
        )}
      </section>
    </div>
  );
}

/* ============================ SafeZoneOverlay ========================= */

export function SafeZoneTab({
  src,
  safeZones,
}: {
  src: string;
  safeZones: SafeZoneAnalysis;
}) {
  const collidingZones = new Set(safeZones.collisions.map((collision) => collision.zone));

  return (
    <div className="space-y-6">
      <SectionHead
        title="YouTube's own UI, drawn on your thumbnail"
        hint="The duration pill is the mistake creators make most: the punchline word goes bottom-right, and a black rounded rectangle lands on top of it in every feed. Nothing in your editor shows you this."
      />

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <div className="relative min-w-0 overflow-hidden rounded-xl border border-[#232330] bg-[#0F0F14]">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt="Thumbnail with YouTube UI chrome overlaid" className="w-full" />
          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            className="pointer-events-none absolute inset-0 h-full w-full"
            aria-hidden="true"
          >
            {safeZones.zones
              .filter((zone) => zone.id !== "hover_crop")
              .map((zone) => {
                const hit = collidingZones.has(zone.id);
                return (
                  <rect
                    key={zone.id}
                    x={zone.x * 100}
                    y={zone.y * 100}
                    width={zone.w * 100}
                    height={zone.h * 100}
                    fill={hit ? "rgba(239,68,68,0.35)" : "rgba(10,10,13,0.62)"}
                    stroke={hit ? "#EF4444" : "#55556B"}
                    strokeWidth="0.3"
                    vectorEffect="non-scaling-stroke"
                    rx="0.8"
                  />
                );
              })}
            {/* The hover crop is a border, not a box. */}
            <rect
              x="2"
              y="2"
              width="96"
              height="96"
              fill="none"
              stroke={collidingZones.has("hover_crop") ? "#EF4444" : "#33334A"}
              strokeWidth="0.3"
              strokeDasharray="2 2"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
        </div>

        <div className="min-w-0 space-y-3">
          {safeZones.clean ? (
            <div className="rounded-xl border border-[#22C55E]/30 bg-[#22C55E]/8 p-4">
              <p className="text-sm font-bold text-[#22C55E]">Nothing collides</p>
              <p className="mt-1 text-sm text-[#8E8EA8]">
                No text or face sits under the duration pill, the CC badge, the progress
                bar, or the hover crop.
              </p>
            </div>
          ) : (
            <ul className="space-y-2.5">
              {safeZones.collisions.map((collision, index) => {
                const color = severityColor(collision.severity);
                return (
                  <li
                    key={index}
                    className="rounded-xl border p-3.5"
                    style={{ borderColor: `${color}55`, background: `${color}12` }}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="text-sm font-bold" style={{ color }}>
                        {collision.zoneLabel}
                      </span>
                      <span className="mono text-[11px] font-bold uppercase" style={{ color }}>
                        {collision.severity} · {formatPercent(collision.overlapFraction)} covered
                      </span>
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-[#F2F2F7]">
                      {collision.advice}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}

          <ul className="space-y-1.5 pt-2">
            {safeZones.zones.map((zone) => (
              <li key={zone.id} className="text-[11px] leading-relaxed text-[#8E8EA8]">
                <span className="mono text-[#8E8EA8]">{zone.label}</span> — {zone.note}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
