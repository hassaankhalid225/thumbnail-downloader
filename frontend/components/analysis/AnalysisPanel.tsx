"use client";

import { motion } from "framer-motion";
import { Share2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge, CopyButton, Skeleton, Tabs, useReducedMotion } from "@/components/ui";
import { AIVerdict } from "./AIVerdict";
import { ColorTab } from "./ColorTab";
import { CompositionTab, SafeZoneTab } from "./CompositionTab";
import { MobileTab } from "./MobileTab";
import { ScoreBreakdown, ScoringExplainer } from "./ScoreBreakdown";
import { ScoreDial } from "./ScoreDial";
import { TextTab } from "./TextTab";
import type { AnalyzeResponse, FlowState } from "@/lib/types";
import { encodeShare } from "@/lib/utils";

const TAB_IDS = ["colors", "text", "mobile", "composition", "safezones", "ai"] as const;
type TabId = (typeof TAB_IDS)[number];

export function AnalysisPanel({
  analysis,
  previewUrl,
  state,
}: {
  analysis: AnalyzeResponse | null;
  previewUrl: string;
  state: FlowState;
}) {
  const [tab, setTab] = useState<TabId>("colors");
  const reduced = useReducedMotion();

  const aiLoading = state === "ANALYZING_CV" || state === "ANALYZING_AI";

  const shareUrl = useMemo(() => {
    if (!analysis || typeof window === "undefined") return "";
    const payload = encodeShare({
      u: analysis.sourceUrl,
      t: analysis.title,
      s: analysis.scores,
      p: analysis.color.palette.slice(0, 6).map((swatch) => swatch.hex),
    });
    return `${window.location.origin}/analyze/${payload}`;
  }, [analysis]);

  if (!analysis) {
    return <AnalysisSkeleton />;
  }

  const failingSurfaces = analysis.mobileLegibility.surfaces.filter(
    (surface) => surface.verdict === "FAIL",
  ).length;

  const tabs = [
    { id: "colors", label: "Colours" },
    {
      id: "text",
      label: "Text",
      badge:
        analysis.text.blocks.length > 0 ? (
          <Badge tone="neutral">{analysis.text.blocks.length}</Badge>
        ) : undefined,
    },
    {
      id: "mobile",
      label: "Mobile check",
      badge: failingSurfaces > 0 ? <Badge tone="bad">{failingSurfaces} fail</Badge> : undefined,
    },
    { id: "composition", label: "Composition" },
    {
      id: "safezones",
      label: "Safe zones",
      badge:
        analysis.safeZones.collisions.length > 0 ? (
          <Badge tone="ok">{analysis.safeZones.collisions.length}</Badge>
        ) : undefined,
    },
    {
      id: "ai",
      label: "AI verdict",
      badge: analysis.aiError ? <Badge tone="ok">offline</Badge> : undefined,
    },
  ];

  return (
    <section className="space-y-7" aria-label="Analysis">
      {/* ---- headline score ---- */}
      <div className="panel p-5 sm:p-7">
        <div className="flex flex-col items-center gap-7 lg:flex-row lg:items-start">
          <div className="flex flex-col items-center gap-3">
            <ScoreDial score={analysis.scores.overall} />
            <ScoringExplainer scores={analysis.scores} />
          </div>

          {/* w-full matters: in the stacked (column) layout, flex-1 governs height, so
              without it this column takes its max-content width and pushes the page
              wider than the viewport at 375px. */}
          <div className="w-full min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="eyebrow">ThumbIQ score</p>
              {analysis.cached && <Badge tone="cyan">cached</Badge>}
              <span className="mono text-[10.5px] text-[#8E8EA8]">
                measured in {analysis.timings.deterministicMs}ms
              </span>
            </div>

            <h2 className="mt-2 text-lg font-bold leading-snug text-[#F2F2F7] sm:text-xl">
              {analysis.ai?.verdict ??
                (aiLoading
                  ? "Measuring first, then writing the verdict…"
                  : "Every measurement below is live.")}
            </h2>

            {analysis.title && (
              <p className="mt-1 truncate text-sm text-[#8E8EA8]">
                {analysis.title}
                {analysis.uploader && ` · ${analysis.uploader}`}
              </p>
            )}

            <div className="mt-5">
              <ScoreBreakdown scores={analysis.scores} />
            </div>

            {shareUrl && (
              <div className="mt-4 flex items-center gap-2">
                <CopyButton value={shareUrl} label="Copy share link" compact>
                  <Share2 className="h-3.5 w-3.5" />
                </CopyButton>
                <span className="text-[11px] text-[#8E8EA8]">
                  The link carries the scores, not the image.
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ---- detail tabs ---- */}
      <div className="panel overflow-hidden">
        <Tabs items={tabs} active={tab} onChange={(id) => setTab(id as TabId)} />

        <motion.div
          key={tab}
          initial={{ opacity: 0, y: reduced ? 0 : 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          role="tabpanel"
          id={`panel-${tab}`}
          aria-labelledby={`tab-${tab}`}
          className="p-5 sm:p-6"
        >
          {tab === "colors" && <ColorTab color={analysis.color} />}
          {tab === "text" && <TextTab text={analysis.text} src={previewUrl} />}
          {tab === "mobile" && (
            <MobileTab src={previewUrl} mobile={analysis.mobileLegibility} />
          )}
          {tab === "composition" && (
            <CompositionTab
              src={previewUrl}
              composition={analysis.composition}
              faces={analysis.faces}
              quality={analysis.quality}
            />
          )}
          {tab === "safezones" && (
            <SafeZoneTab src={previewUrl} safeZones={analysis.safeZones} />
          )}
          {tab === "ai" && (
            <AIVerdict ai={analysis.ai} error={analysis.aiError} loading={aiLoading} />
          )}
        </motion.div>
      </div>
    </section>
  );
}

export function AnalysisSkeleton() {
  return (
    <section className="space-y-7" aria-busy="true" aria-label="Analysis loading">
      <div className="panel p-5 sm:p-7">
        <div className="flex flex-col items-center gap-7 lg:flex-row lg:items-start">
          <Skeleton className="h-[190px] w-[190px] shrink-0 rounded-full" />
          <div className="w-full flex-1 space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-7 w-3/4" />
            <div className="grid gap-2.5 pt-2 sm:grid-cols-2">
              {Array.from({ length: 8 }, (_, index) => (
                <Skeleton key={index} className="h-[86px] w-full" />
              ))}
            </div>
          </div>
        </div>
      </div>
      <Skeleton className="h-72 w-full" />
    </section>
  );
}
