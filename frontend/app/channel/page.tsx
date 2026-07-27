"use client";

import { motion } from "framer-motion";
import { useCallback, useState } from "react";

import { AnalyzerOffNotice } from "@/components/AnalyzerOffNotice";
import { IndeterminateBar, Spinner, ToastProvider, Tooltip, useToast } from "@/components/ui";
import { channel } from "@/lib/api";
import { scoreColor } from "@/lib/colors";
import { ANALYSIS_ENABLED } from "@/lib/constants";
import { ApiError, type ChannelPattern, type ChannelResponse } from "@/lib/types";
import { formatPercent } from "@/lib/utils";

export default function ChannelPage() {
  if (!ANALYSIS_ENABLED) return <AnalyzerOffNotice feature="The channel report" />;

  return (
    <ToastProvider>
      <ChannelTool />
    </ToastProvider>
  );
}

function ChannelTool() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState<ChannelResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const run = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      setResult(await channel(url.trim(), 24));
    } catch (error) {
      toast.push(
        error instanceof ApiError ? error.message : "Couldn't read that channel.",
        "error",
      );
    } finally {
      setLoading(false);
    }
  }, [url, toast]);

  return (
    <div className="mx-auto max-w-7xl px-5 py-14 sm:px-8">
      <p className="eyebrow">Channel report</p>
      <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">
        The pattern one thumbnail can&apos;t show you
      </h1>
      <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[#8E8EA8]">
        Paste a channel or profile URL. ThumbIQ pulls the last 24 thumbnails, scores each
        one, and reports what the channel does <em>repeatedly</em>: the recurring palette,
        where the text always goes, how often a face appears, and how consistent it is.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
        className="mt-8 flex flex-col gap-2 sm:flex-row"
      >
        <input
          type="url"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          placeholder="https://www.youtube.com/@channelname"
          className="mono min-w-0 flex-1 rounded-xl border border-[#232330] bg-[#101015] px-4 py-3 text-sm text-white outline-none transition-colors placeholder:text-[#8E8EA8] focus:border-[#C8FF3D]/50"
        />
        <button
          type="submit"
          disabled={loading || url.trim().length === 0}
          className="flex items-center justify-center gap-2 rounded-xl bg-[#C8FF3D] px-6 py-3 text-sm font-bold text-black transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {loading && <Spinner size={15} />}
          Analyze channel
        </button>
      </form>

      {loading && (
        <div className="mt-8 max-w-md">
          <IndeterminateBar label="Listing videos, then measuring each thumbnail (4 at a time)…" />
        </div>
      )}

      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-10 space-y-9"
        >
          <div>
            <h2 className="text-xl font-bold">{result.channel.name ?? "Channel"}</h2>
            <p className="mono mt-1 text-[12px] text-[#8E8EA8]">
              {result.channel.videoCount} of {result.channel.requested} thumbnails
              analysed · {result.elapsedMs}ms
            </p>
          </div>

          <PatternReport pattern={result.pattern} />

          <section>
            <h3 className="text-sm font-bold text-[#F2F2F7]">Every thumbnail, scored</h3>
            <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
              {result.items.map((item, index) => (
                <div key={index} className="panel overflow-hidden">
                  {item.thumbnailUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.thumbnailUrl}
                      alt={item.title ?? "Thumbnail"}
                      loading="lazy"
                      className="aspect-video w-full object-cover"
                    />
                  ) : (
                    <div className="aspect-video w-full bg-[#16161D]" />
                  )}
                  <div className="p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className="mono text-lg font-black"
                        style={{ color: scoreColor(item.scores?.overall ?? null) }}
                      >
                        {item.scores?.overall ?? "—"}
                      </span>
                      {item.text && (
                        <span className="mono text-[10px] text-[#8E8EA8]">
                          {item.text.wordCount}w
                          {item.faces && item.faces.count > 0 ? " · face" : ""}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-[#8E8EA8]">
                      {item.title ?? item.error?.message ?? "Untitled"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </motion.div>
      )}
    </div>
  );
}

function PatternReport({ pattern }: { pattern: ChannelPattern }) {
  const heatmap = pattern.dominantTextPlacement?.heatmap ?? [
    [0, 0, 0],
    [0, 0, 0],
    [0, 0, 0],
  ];
  const peak = Math.max(...heatmap.flat(), 0.0001);

  return (
    <section className="grid gap-4 lg:grid-cols-4">
      <div className="panel p-5 lg:col-span-2">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-[#F2F2F7]">Recurring palette</h3>
          <Tooltip content="Every swatch from every thumbnail clustered together in LAB space. Frequency is the share of thumbnails that carry a colour from that cluster." />
        </div>
        <ul className="mt-4 space-y-2.5">
          {pattern.recurringPalette.map((entry) => (
            <li key={entry.hex} className="flex items-center gap-3">
              <span
                className="h-8 w-8 shrink-0 rounded-lg border border-[#33334A]"
                style={{ background: entry.hex }}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="mono text-[12px] font-bold text-[#F2F2F7]">
                    {entry.hex}
                  </span>
                  <span className="mono text-[11px] text-[#8E8EA8]">
                    {formatPercent(entry.frequency)} of thumbnails
                  </span>
                </div>
                <div className="mt-1 h-1 overflow-hidden rounded-full bg-[#232330]">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${entry.frequency * 100}%`, background: entry.hex }}
                  />
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <div className="panel p-5">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-bold text-[#F2F2F7]">Text placement</h3>
          <Tooltip content="A 3×3 heatmap of where text blocks land across every thumbnail. A hot single cell means a strong, repeatable layout." />
        </div>
        <div className="mt-4 grid aspect-video grid-cols-3 grid-rows-3 gap-1">
          {heatmap.flat().map((value, index) => (
            <div
              key={index}
              className="flex items-center justify-center rounded-md border border-[#232330]"
              style={{ background: `rgba(200,255,61,${(value / peak) * 0.75})` }}
              title={`${formatPercent(value)}`}
            >
              {value > 0.02 && (
                <span className="mono text-[10px] font-bold text-[#0A0A0D]">
                  {Math.round(value * 100)}
                </span>
              )}
            </div>
          ))}
        </div>
        <p className="mt-3 text-[12px] text-[#8E8EA8]">
          Most used:{" "}
          <span className="font-bold text-[#F2F2F7]">
            {pattern.dominantTextPlacement?.quadrant ?? "—"}
          </span>
        </p>
      </div>

      <div className="panel space-y-4 p-5">
        <div>
          <p className="eyebrow">Consistency</p>
          <p
            className="mono mt-1 text-4xl font-black"
            style={{ color: scoreColor(pattern.consistencyScore) }}
          >
            {pattern.consistencyScore}
          </p>
          <p className="mt-2 text-[11.5px] leading-relaxed text-[#8E8EA8]">
            {pattern.consistencyBasis}
          </p>
        </div>
        <dl className="space-y-2 border-t border-[#232330] pt-3">
          <Row label="Face usage" value={formatPercent(pattern.faceUsageRate)} />
          <Row
            label="Avg word count"
            value={`${pattern.averageWordCount} ±${pattern.wordCountStdDev}`}
          />
          <Row
            label="Avg overall score"
            value={String(pattern.averageScores.overall ?? "—")}
          />
        </dl>
      </div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2">
      <dt className="text-[12px] text-[#8E8EA8]">{label}</dt>
      <dd className="mono text-[12px] font-bold text-[#F2F2F7]">{value}</dd>
    </div>
  );
}
