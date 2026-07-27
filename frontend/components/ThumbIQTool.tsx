"use client";

import { AnimatePresence, motion } from "framer-motion";
import { TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { AnalysisPanel, AnalysisSkeleton } from "@/components/analysis/AnalysisPanel";
import { PlatformStrip, UrlInput } from "@/components/hero";
import { ThumbnailGrid } from "@/components/thumbnails";
import { IndeterminateBar, ToastProvider, useToast } from "@/components/ui";
import { ANALYSIS_ENABLED, COPYRIGHT_LINE, EXAMPLE_URLS } from "@/lib/constants";
import { useThumbIQ } from "@/lib/useThumbIQ";

const RESOLVING_MESSAGES = [
  "Finding the thumbnail…",
  "Checking which sizes really exist…",
  "Rendering the download ladder…",
];

/**
 * The tool, with its own toast context.
 *
 * The provider lives here rather than around the page so the marketing sections stay
 * server components. Wrapping the whole page in a client provider would drag the FAQ,
 * the feature grid and the footer into the client bundle for no reason.
 */
export function ThumbIQTool() {
  return (
    <ToastProvider>
      <ThumbIQToolInner />
    </ToastProvider>
  );
}

function ThumbIQToolInner() {
  const flow = useThumbIQ();
  const toast = useToast();
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    if (flow.state !== "RESOLVING") return;
    const timer = setInterval(
      () => setMessageIndex((index) => (index + 1) % RESOLVING_MESSAGES.length),
      1400,
    );
    return () => clearInterval(timer);
  }, [flow.state]);

  useEffect(() => {
    if (flow.state === "ERROR" && flow.error) toast.push(flow.error.message, "error");
  }, [flow.state, flow.error, toast]);

  const previewUrl = flow.uploadPreview ?? flow.thumbnails?.native.url ?? "";
  const busy =
    flow.state === "RESOLVING" ||
    flow.state === "ANALYZING_CV" ||
    flow.state === "ANALYZING_AI";

  return (
    <div id="tool" className="space-y-9">
      <UrlInput
        value={flow.url}
        platform={flow.platform}
        state={flow.state}
        hasError={flow.state === "ERROR"}
        onChange={flow.setUrl}
        onSubmit={flow.submit}
        onFile={flow.submitFile}
      />

      <PlatformStrip active={flow.platform} />

      {flow.state === "IDLE" && (
        <div className="flex flex-wrap items-center justify-center gap-2">
          <span className="text-xs text-[#8E8EA8]">Try one:</span>
          {EXAMPLE_URLS.map((example) => (
            <button
              key={example.url}
              type="button"
              onClick={() => {
                flow.setUrl(example.url);
                void flow.submit(example.url);
              }}
              className="rounded-lg border border-[#232330] bg-[#101015] px-3 py-1.5 text-xs font-medium text-[#8E8EA8] transition-all hover:border-[#33334A] hover:text-[#F2F2F7]"
            >
              {example.label}
            </button>
          ))}
        </div>
      )}

      <AnimatePresence>
        {flow.state === "RESOLVING" && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="mx-auto max-w-md"
          >
            <IndeterminateBar label={RESOLVING_MESSAGES[messageIndex] ?? ""} />
          </motion.div>
        )}
      </AnimatePresence>

      {flow.state === "ERROR" && flow.error && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto max-w-2xl rounded-xl border border-[#EF4444]/35 bg-[#EF4444]/8 p-4"
          role="alert"
        >
          <p className="flex items-center gap-2 text-sm font-bold text-[#EF4444]">
            <TriangleAlert className="h-4 w-4" />
            {flow.error.message}
          </p>
          <p className="mono mt-1 text-[11px] text-[#8E8EA8]">
            {flow.error.code}
            {flow.error.retryAfter ? ` · retry in ${flow.error.retryAfter}s` : ""}
          </p>
        </motion.div>
      )}

      {ANALYSIS_ENABLED && flow.state === "PARTIAL" && (flow.analysisError ?? flow.analysis?.aiError) && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-xl border border-[#F59E0B]/35 bg-[#F59E0B]/8 p-4"
          role="status"
        >
          <p className="flex items-center gap-2 text-sm font-bold text-[#F59E0B]">
            <TriangleAlert className="h-4 w-4" />
            {flow.analysisError
              ? "Analysis unavailable right now — your downloads below are ready."
              : "AI verdict unavailable right now — everything else below is live."}
          </p>
          <p className="mt-1 text-[12.5px] leading-relaxed text-[#8E8EA8]">
            {(flow.analysisError ?? flow.analysis?.aiError)?.message}
          </p>
        </motion.div>
      )}

      {flow.thumbnails && <ThumbnailGrid data={flow.thumbnails} />}

      {ANALYSIS_ENABLED && (flow.analysis || busy) && (
        <>
          {flow.thumbnails && <div className="hairline" />}
          {flow.analysis ? (
            <AnalysisPanel
              analysis={flow.analysis}
              previewUrl={previewUrl}
              state={flow.state}
            />
          ) : (
            <AnalysisSkeleton />
          )}
        </>
      )}

      {(flow.thumbnails || flow.analysis) && (
        <p className="text-center text-[11.5px] leading-relaxed text-[#8E8EA8]">
          {COPYRIGHT_LINE}
        </p>
      )}
    </div>
  );
}
