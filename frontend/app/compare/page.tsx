"use client";

import { motion } from "framer-motion";
import { Crown, Plus, Trophy, X } from "lucide-react";
import { useCallback, useState } from "react";

import { ScoreDial } from "@/components/analysis/ScoreDial";
import { AnalyzerOffNotice } from "@/components/AnalyzerOffNotice";
import { IndeterminateBar, Spinner, ToastProvider, useToast } from "@/components/ui";
import { compare } from "@/lib/api";
import { scoreColor } from "@/lib/colors";
import { ANALYSIS_ENABLED, SCORE_ORDER } from "@/lib/constants";
import { ApiError, type CompareResponse } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function ComparePage() {
  if (!ANALYSIS_ENABLED) return <AnalyzerOffNotice feature="Compare mode" />;

  return (
    <ToastProvider>
      <CompareTool />
    </ToastProvider>
  );
}

function CompareTool() {
  const [urls, setUrls] = useState<string[]>(["", ""]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const filled = urls.filter((url) => url.trim().length > 0);

  const run = useCallback(async () => {
    if (filled.length < 2) {
      toast.push("Paste at least two links to compare.", "error");
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      setResult(await compare(filled, false));
    } catch (error) {
      toast.push(
        error instanceof ApiError ? error.message : "Couldn't run the comparison.",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [filled, toast]);

  return (
    <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8">
      <p className="eyebrow">Compare mode</p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
        Put them side by side
      </h1>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8]">
        Two to four thumbnails, the same eight measurements each, and a winner per
        category. Deterministic only — no AI call, so this stays free and fast.
      </p>

      <div className="mt-8 space-y-2.5">
        {urls.map((url, index) => (
          <div key={index} className="flex items-center gap-2">
            <span className="mono w-6 shrink-0 text-sm text-[#8E8EA8]">
              {String.fromCharCode(65 + index)}
            </span>
            <input
              type="url"
              value={url}
              placeholder={`Thumbnail ${index + 1} — paste a video link`}
              onChange={(event) =>
                setUrls((current) =>
                  current.map((value, i) => (i === index ? event.target.value : value)),
                )
              }
              className="mono min-w-0 flex-1 rounded-xl border border-[#232330] bg-[#101015] px-4 py-3 text-sm text-white outline-none transition-colors placeholder:text-[#8E8EA8] focus:border-[#C8FF3D]/50"
            />
            {urls.length > 2 && (
              <button
                type="button"
                aria-label={`Remove slot ${index + 1}`}
                onClick={() => setUrls((current) => current.filter((_, i) => i !== index))}
                className="rounded-lg border border-[#232330] p-2.5 text-[#8E8EA8] transition-colors hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {urls.length < 4 && (
          <button
            type="button"
            onClick={() => setUrls((current) => [...current, ""])}
            className="flex items-center gap-1.5 rounded-lg border border-[#232330] bg-[#16161D] px-3.5 py-2.5 text-sm font-semibold text-[#8E8EA8] transition-colors hover:text-white"
          >
            <Plus className="h-4 w-4" /> Add another
          </button>
        )}
        <button
          type="button"
          onClick={run}
          disabled={loading || filled.length < 2}
          className="flex items-center gap-2 rounded-lg bg-[#C8FF3D] px-5 py-2.5 text-sm font-bold text-black transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading && <Spinner size={15} />}
          Compare {filled.length > 0 && `(${filled.length})`}
        </button>
      </div>

      {loading && (
        <div className="mt-8 max-w-md">
          <IndeterminateBar label="Resolving and measuring each thumbnail…" />
        </div>
      )}

      {result && <CompareResults result={result} />}
    </div>
  );
}

function CompareResults({ result }: { result: CompareResponse }) {
  const successful = result.results.filter((item) => item.ok && item.analysis);

  if (successful.length === 0) {
    return (
      <div className="mt-10 rounded-xl border border-[#EF4444]/35 bg-[#EF4444]/8 p-5">
        <p className="text-sm font-bold text-[#EF4444]">Nothing could be compared</p>
        <ul className="mt-2 space-y-1">
          {result.results.map((item, index) => (
            <li key={index} className="text-[13px] text-[#8E8EA8]">
              {item.url} — {item.error?.message}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-10 space-y-8"
    >
      {result.winner && (
        <div className="rounded-2xl border border-[#C8FF3D]/30 bg-gradient-to-br from-[#C8FF3D]/10 to-transparent p-5">
          <p className="flex items-center gap-2 text-sm font-bold text-[#C8FF3D]">
            <Trophy className="h-4 w-4" />
            Winner: thumbnail {String.fromCharCode(65 + result.winner.index)}
          </p>
          <p className="mt-1.5 text-[14px] leading-relaxed text-[#F2F2F7]">
            {result.winner.reason}
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {result.results.map((item, index) => (
          <div
            key={index}
            className={cn(
              "panel flex flex-col overflow-hidden",
              result.winner?.index === index && "border-[#C8FF3D]/50",
            )}
          >
            {item.thumbnailUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={item.thumbnailUrl}
                alt={item.title ?? `Thumbnail ${index + 1}`}
                className="aspect-video w-full border-b border-[#232330] object-cover"
              />
            )}
            <div className="flex flex-1 flex-col items-center gap-2 p-4">
              <div className="flex w-full items-center justify-between">
                <span className="mono text-sm font-bold text-[#8E8EA8]">
                  {String.fromCharCode(65 + index)}
                </span>
                {result.winner?.index === index && (
                  <Crown className="h-4 w-4 text-[#C8FF3D]" />
                )}
              </div>
              {item.ok && item.analysis ? (
                <>
                  <ScoreDial score={item.analysis.scores.overall} size={120} />
                  <p className="line-clamp-2 text-center text-[12px] text-[#8E8EA8]">
                    {item.title ?? item.url}
                  </p>
                </>
              ) : (
                <p className="py-8 text-center text-[12.5px] text-[#EF4444]">
                  {item.error?.message}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="panel overflow-x-auto">
        <table className="w-full min-w-[640px] text-sm">
          <caption className="sr-only">Score comparison by category</caption>
          <thead>
            <tr className="border-b border-[#232330]">
              <th scope="col" className="p-3 text-left text-[12px] font-bold text-[#8E8EA8]">
                Category
              </th>
              {result.results.map((_, index) => (
                <th
                  key={index}
                  scope="col"
                  className="mono p-3 text-center text-[12px] font-bold text-[#8E8EA8]"
                >
                  {String.fromCharCode(65 + index)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-[#232330] bg-[#16161D]">
              <th scope="row" className="p-3 text-left text-[13px] font-bold text-[#F2F2F7]">
                Overall
              </th>
              {result.results.map((item, index) => {
                const score = item.analysis?.scores.overall ?? null;
                return (
                  <td key={index} className="p-3 text-center">
                    <span
                      className="mono text-lg font-black"
                      style={{ color: scoreColor(score) }}
                    >
                      {score ?? "—"}
                    </span>
                  </td>
                );
              })}
            </tr>

            {SCORE_ORDER.map((key) => {
              const category = result.winner?.categories[key];
              const label =
                successful[0]?.analysis?.scores.labels[key] ?? key;
              return (
                <tr key={key} className="border-b border-[#232330] last:border-0">
                  <th scope="row" className="p-3 text-left text-[13px] text-[#8E8EA8]">
                    {label}
                  </th>
                  {result.results.map((item, index) => {
                    const score = item.analysis?.scores[key] ?? null;
                    const isWinner = category?.winnerIndex === index;
                    return (
                      <td
                        key={index}
                        className={cn(
                          "p-3 text-center",
                          isWinner && "bg-[#C8FF3D]/8",
                        )}
                      >
                        <span
                          className="mono text-[13px] font-bold"
                          style={{ color: scoreColor(score) }}
                        >
                          {score ?? "—"}
                        </span>
                        {isWinner && category?.margin ? (
                          <span className="mono ml-1 text-[10px] text-[#C8FF3D]">
                            +{category.margin}
                          </span>
                        ) : null}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mono text-[11px] text-[#8E8EA8]">
        Measured in {result.elapsedMs}ms. Highlighted cells win their category; the margin
        is the gap to the runner-up.
      </p>
    </motion.div>
  );
}
