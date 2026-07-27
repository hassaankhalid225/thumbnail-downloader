"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo } from "react";

import { ScoreDial } from "@/components/analysis/ScoreDial";
import { AnalyzerOffNotice } from "@/components/AnalyzerOffNotice";
import { scoreColor } from "@/lib/colors";
import { ANALYSIS_ENABLED, SCORE_ORDER } from "@/lib/constants";
import type { Scores } from "@/lib/types";
import { decodeShare } from "@/lib/utils";

interface SharedPayload {
  u: string | null;
  t: string | null;
  s: Scores;
  p: string[];
}

/**
 * A shared result page.
 *
 * The payload travels in the URL, not in a database. There is no server-side result
 * store, so a share link cannot outlive the person who made it or leak anyone else's
 * lookups — and it carries scores, never the image.
 */
export default function SharedAnalysisPage() {
  const params = useParams<{ id: string }>();
  const payload = useMemo(
    () => (params?.id ? decodeShare<SharedPayload>(params.id) : null),
    [params?.id],
  );

  // Old share links stay readable if the analyser is later switched off — the scores are
  // in the URL, not on a server — but there's no point rendering a scoreboard for a
  // feature that currently can't produce one.
  if (!ANALYSIS_ENABLED) return <AnalyzerOffNotice feature="Shared analysis" />;

  if (!payload?.s) {
    return (
      <div className="mx-auto max-w-2xl px-5 py-24 text-center sm:px-8">
        <h1 className="text-2xl font-bold">That share link isn&apos;t readable</h1>
        <p className="mt-3 text-[15px] text-[#8E8EA8]">
          It may have been truncated in transit. Run the analysis again to get a fresh one.
        </p>
        <Link
          href="/"
          className="mt-6 inline-block rounded-xl bg-[#C8FF3D] px-6 py-3 text-sm font-bold text-black"
        >
          Analyze a thumbnail
        </Link>
      </div>
    );
  }

  const scores = payload.s;

  return (
    <div className="mx-auto max-w-4xl px-5 py-14 sm:px-8">
      <p className="eyebrow">Shared analysis</p>
      <h1 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
        {payload.t ?? "Thumbnail analysis"}
      </h1>
      {payload.u && (
        <a
          href={payload.u}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mono mt-1 block truncate text-[12px] text-[#8E8EA8] hover:text-[#C8FF3D]"
        >
          {payload.u}
        </a>
      )}

      <div className="panel mt-8 flex flex-col items-center gap-8 p-6 sm:flex-row sm:items-start">
        <ScoreDial score={scores.overall} />

        <div className="w-full flex-1 space-y-2.5">
          {SCORE_ORDER.map((key) => {
            const value = scores[key];
            return (
              <div key={key}>
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[13px] text-[#8E8EA8]">
                    {scores.labels?.[key] ?? key}
                  </span>
                  <span
                    className="mono text-[13px] font-bold"
                    style={{ color: scoreColor(value) }}
                  >
                    {value ?? "—"}
                  </span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#232330]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${value ?? 0}%`, background: scoreColor(value) }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {payload.p?.length > 0 && (
        <section className="mt-8">
          <p className="eyebrow">Palette</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {payload.p.map((hex) => (
              <span
                key={hex}
                className="mono flex items-center gap-2 rounded-lg border border-[#232330] bg-[#101015] px-2.5 py-1.5 text-[12px] font-bold"
              >
                <i
                  className="inline-block h-4 w-4 rounded-sm border border-[#33334A]"
                  style={{ background: hex }}
                />
                {hex}
              </span>
            ))}
          </div>
        </section>
      )}

      <div className="mt-10 rounded-xl border border-[#232330] bg-[#101015] p-5">
        <p className="text-sm font-bold text-[#F2F2F7]">Want the full breakdown?</p>
        <p className="mt-1 text-[13.5px] leading-relaxed text-[#8E8EA8]">
          This link carries the scores only. Run it yourself for the palette exports, the
          text overlay, the mobile legibility check and the safe-zone map.
        </p>
        <Link
          href="/"
          className="mt-4 inline-block rounded-xl bg-[#C8FF3D] px-5 py-2.5 text-sm font-bold text-black transition-all hover:brightness-110"
        >
          Open ThumbIQ
        </Link>
      </div>
    </div>
  );
}
