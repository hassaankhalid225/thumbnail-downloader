"use client";

import { motion } from "framer-motion";
import { Sparkles, ThumbsDown, ThumbsUp, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { CopyButton, Skeleton } from "@/components/ui";
import type { AiAnalysis, AiError } from "@/lib/types";
import { formatPercent } from "@/lib/utils";
import { SectionHead } from "./ColorTab";

const STATUS_MESSAGES = [
  "Reading the composition…",
  "Judging the text placement…",
  "Naming the psychological hook…",
  "Writing the verdict…",
];

/* ============================ ImprovementList ========================= */

export function ImprovementList({ improvements }: { improvements: AiAnalysis["improvements"] }) {
  if (improvements.length === 0) return null;

  return (
    <ol className="space-y-2.5">
      {improvements.map((improvement) => (
        <li key={improvement.priority} className="panel-raised p-4">
          <div className="flex gap-3">
            <span className="mono flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-[#C8FF3D] text-[12px] font-black text-black">
              {improvement.priority}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold leading-relaxed text-[#F2F2F7]">
                {improvement.change}
              </p>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-[#8E8EA8]">
                {improvement.why}
              </p>
              <p className="mt-1 text-[12px] leading-relaxed text-[#22D3EE]">
                {improvement.expected_impact}
              </p>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

/* ============================ RecreateRecipe ========================== */

export function RecreateRecipe({ recipe }: { recipe: NonNullable<AiAnalysis["recreate_recipe"]> }) {
  const summary = [
    recipe.font_style && `Type: ${recipe.font_style}`,
    recipe.layout && `Layout: ${recipe.layout}`,
    recipe.subject_treatment && `Subject: ${recipe.subject_treatment}`,
    recipe.palette.length > 0 && `Palette: ${recipe.palette.join(", ")}`,
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <div className="rounded-2xl border border-[#C8FF3D]/25 bg-gradient-to-br from-[#C8FF3D]/8 to-[#22D3EE]/5 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-bold text-[#C8FF3D]">
          <Sparkles className="h-4 w-4" />
          Build your own in this style
        </h3>
        <CopyButton value={summary} label="Copy recipe" compact />
      </div>

      <p className="mt-1.5 text-[12px] leading-relaxed text-[#8E8EA8]">
        A recipe, not a copy. These are the ingredients that make the style work, so you
        can make your own thumbnail — not republish someone else&apos;s.
      </p>

      {recipe.palette.length > 0 && (
        <div className="mt-4">
          <p className="eyebrow">Palette</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {recipe.palette.map((hex) => (
              <span
                key={hex}
                className="mono flex items-center gap-1.5 rounded-lg border border-[#232330] bg-[#101015] px-2 py-1 text-[11px] font-bold text-[#F2F2F7]"
              >
                <i
                  className="inline-block h-3.5 w-3.5 rounded-sm border border-[#33334A]"
                  style={{ background: hex }}
                />
                {hex}
              </span>
            ))}
          </div>
        </div>
      )}

      <dl className="mt-4 space-y-3">
        {recipe.font_style && <RecipeRow label="Type treatment" value={recipe.font_style} />}
        {recipe.layout && <RecipeRow label="Layout" value={recipe.layout} />}
        {recipe.subject_treatment && (
          <RecipeRow label="Subject treatment" value={recipe.subject_treatment} />
        )}
      </dl>
    </div>
  );
}

function RecipeRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="eyebrow">{label}</dt>
      <dd className="mt-1 text-[13px] leading-relaxed text-[#F2F2F7]">{value}</dd>
    </div>
  );
}

/* =============================== AIVerdict ============================ */

export function AIVerdict({
  ai,
  error,
  loading,
}: {
  ai: AiAnalysis | null;
  error: AiError | null;
  loading: boolean;
}) {
  const [statusIndex, setStatusIndex] = useState(0);

  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(
      () => setStatusIndex((index) => (index + 1) % STATUS_MESSAGES.length),
      2600,
    );
    return () => clearInterval(timer);
  }, [loading]);

  if (loading) {
    return (
      <div className="space-y-4">
        <p className="flex items-center gap-2 text-sm text-[#8E8EA8]">
          <Sparkles className="h-4 w-4 animate-pulse text-[#C8FF3D]" />
          {STATUS_MESSAGES[statusIndex]}
        </p>
        <Skeleton className="h-16 w-full" />
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
        <Skeleton className="h-44 w-full" />
      </div>
    );
  }

  if (error || !ai) {
    return (
      <div className="rounded-xl border border-[#F59E0B]/35 bg-[#F59E0B]/8 p-5">
        <p className="flex items-center gap-2 text-sm font-bold text-[#F59E0B]">
          <TriangleAlert className="h-4 w-4" />
          AI verdict unavailable
        </p>
        <p className="mt-1.5 text-sm leading-relaxed text-[#8E8EA8]">
          {error?.message ??
            "The AI pass didn't run. Every measurement in the other tabs is live."}
        </p>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      <div className="rounded-2xl border border-[#232330] bg-gradient-to-br from-[#16161D] to-[#101015] p-5">
        <p className="eyebrow">Verdict</p>
        <p className="mt-2 text-xl font-bold leading-snug text-[#F2F2F7] sm:text-2xl">
          {ai.verdict}
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          {ai.style_archetype && (
            <span className="rounded-lg border border-[#A78BFA]/30 bg-[#A78BFA]/10 px-2.5 py-1 text-[12px] font-semibold text-[#A78BFA]">
              {ai.style_archetype.name} · {formatPercent(ai.style_archetype.confidence)}
            </span>
          )}
          {ai.psychological_hook && (
            <span className="rounded-lg border border-[#22D3EE]/30 bg-[#22D3EE]/10 px-2.5 py-1 text-[12px] font-semibold text-[#22D3EE]">
              Hook: {ai.psychological_hook.type}
            </span>
          )}
          {ai.likely_niche && (
            <span className="rounded-lg border border-[#232330] bg-[#0F0F14] px-2.5 py-1 text-[12px] font-semibold text-[#8E8EA8]">
              {ai.likely_niche}
            </span>
          )}
        </div>

        {ai.psychological_hook && (
          <p className="mt-3 text-[13px] leading-relaxed text-[#8E8EA8]">
            {ai.psychological_hook.explanation}
          </p>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <VerdictList
          title="What's working"
          items={ai.why_it_works}
          icon={<ThumbsUp className="h-4 w-4" />}
          tone="#22C55E"
        />
        <VerdictList
          title="What's costing you"
          items={ai.why_it_fails}
          icon={<ThumbsDown className="h-4 w-4" />}
          tone="#EF4444"
        />
      </div>

      {(ai.color_story || ai.text_placement_critique || ai.target_audience) && (
        <div className="grid gap-3 md:grid-cols-3">
          {ai.color_story && <Note label="Colour story" body={ai.color_story} />}
          {ai.text_placement_critique && (
            <Note label="Text placement" body={ai.text_placement_critique} />
          )}
          {ai.target_audience && <Note label="Target audience" body={ai.target_audience} />}
        </div>
      )}

      {ai.improvements.length > 0 && (
        <section>
          <SectionHead
            title="Five specific changes"
            hint="Ordered by impact. Each one names the element, the direction and the distance — generic advice isn't actionable."
          />
          <ImprovementList improvements={ai.improvements} />
        </section>
      )}

      {ai.recreate_recipe && <RecreateRecipe recipe={ai.recreate_recipe} />}
    </motion.div>
  );
}

function VerdictList({
  title,
  items,
  icon,
  tone,
}: {
  title: string;
  items: string[];
  icon: React.ReactNode;
  tone: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="panel-raised p-4">
      <p className="flex items-center gap-2 text-sm font-bold" style={{ color: tone }}>
        {icon} {title}
      </p>
      <ul className="mt-3 space-y-2">
        {items.map((item, index) => (
          <li key={index} className="flex gap-2 text-[13px] leading-relaxed text-[#8E8EA8]">
            <span style={{ color: tone }}>•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Note({ label, body }: { label: string; body: string }) {
  return (
    <div className="panel-raised p-4">
      <p className="eyebrow">{label}</p>
      <p className="mt-2 text-[13px] leading-relaxed text-[#8E8EA8]">{body}</p>
    </div>
  );
}
