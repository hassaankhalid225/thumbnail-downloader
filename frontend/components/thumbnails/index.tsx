"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowUpRight, Check, Download, Link2, Package } from "lucide-react";
import { useCallback, useMemo, useState } from "react";

import { CopyButton, Spinner, Tooltip, useReducedMotion, useToast } from "@/components/ui";
import { downloadSize, downloadZip } from "@/lib/api";
import { ApiError, type ImageFormat, type SizeId, type ThumbnailResponse, type ThumbnailSize } from "@/lib/types";
import { cn, formatBytes } from "@/lib/utils";

const FORMATS: ImageFormat[] = ["jpg", "png", "webp"];

/**
 * Translate the backend's measured crop region into a CSS object-position, so the card
 * preview frames the same part of the image the download will contain.
 *
 * For an `object-fit: cover` box, a position of P% aligns the P% point of the overflow
 * with the P% point of the box — so the crop's left offset as a share of the total
 * overflow is exactly the percentage needed.
 */
function cropPosition(crop: ThumbnailSize["crop"]): string {
  if (!crop) return "50% 50%";
  const axis = (offset: number, extent: number) =>
    extent >= 0.999 ? 50 : (offset / (1 - extent)) * 100;
  return `${axis(crop.x, crop.w).toFixed(2)}% ${axis(crop.y, crop.h).toFixed(2)}%`;
}

/* ============================ UpscaledBadge =========================== */

export function UpscaledBadge({ note }: { note: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-[#F59E0B]/30 bg-[#F59E0B]/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#F59E0B]">
      <ArrowUpRight className="h-3 w-3" />
      Upscaled
      <Tooltip content={note} />
    </span>
  );
}

/* ============================= FormatToggle =========================== */

export function FormatToggle({
  value,
  onChange,
  bytesByFormat,
}: {
  value: ImageFormat;
  onChange: (format: ImageFormat) => void;
  bytesByFormat: Record<ImageFormat, number>;
}) {
  return (
    <div
      className="flex gap-1 rounded-lg border border-[#232330] bg-[#0F0F14] p-0.5"
      role="group"
      aria-label="Download format"
    >
      {FORMATS.map((format) => (
        <button
          key={format}
          type="button"
          onClick={() => onChange(format)}
          aria-pressed={value === format}
          title={`${format.toUpperCase()} — ${formatBytes(bytesByFormat[format])}`}
          className={cn(
            "mono flex-1 rounded-md px-2 py-1 text-[11px] font-bold uppercase transition-colors",
            value === format
              ? "bg-[#C8FF3D] text-black"
              : "text-[#8E8EA8] hover:bg-[#16161D] hover:text-white",
          )}
        >
          {format}
        </button>
      ))}
    </div>
  );
}

/* ================================ SizeCard ============================ */

export function SizeCard({
  size,
  sourceUrl,
  previewUrl,
  isBest,
  selected,
  onToggle,
  index,
}: {
  size: ThumbnailSize;
  sourceUrl: string;
  previewUrl: string;
  isBest: boolean;
  selected: boolean;
  onToggle: (sizeId: SizeId, format: ImageFormat) => void;
  index: number;
}) {
  const [format, setFormat] = useState<ImageFormat>("jpg");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const reduced = useReducedMotion();

  const handleDownload = useCallback(async () => {
    setBusy(true);
    try {
      await downloadSize(sourceUrl, size.id, format);
    } catch (error) {
      toast.push(
        error instanceof ApiError ? error.message : "That download didn't start. Try again.",
        "error",
      );
    } finally {
      setBusy(false);
    }
  }, [format, size.id, sourceUrl, toast]);

  return (
    <motion.article
      initial={{ opacity: 0, y: reduced ? 0 : 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: reduced ? 0 : index * 0.045, duration: 0.32 }}
      className={cn(
        "panel group flex flex-col overflow-hidden transition-all duration-200",
        "hover:-translate-y-1 hover:border-[#33334A]",
        selected && "border-[#C8FF3D]/50",
      )}
    >
      <div className="checker relative flex aspect-video items-center justify-center overflow-hidden border-b border-[#232330] bg-[#0F0F14] p-1.5">
        {/* The preview shows the shape you will actually download. A 9:16 entry that
            previews as 16:9 is a small lie that only surfaces after the download —
            so the inner box takes the target aspect, and object-position reproduces
            the exact crop origin the backend measured. */}
        <div
          className="relative max-h-full max-w-full overflow-hidden rounded-sm"
          style={{
            aspectRatio: `${size.width} / ${size.height}`,
            height: size.height > size.width ? "100%" : undefined,
            width: size.height > size.width ? undefined : "100%",
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={previewUrl}
            alt={`${size.label} preview — ${size.width} by ${size.height} pixels`}
            loading={index < 4 ? "eager" : "lazy"}
            className="h-full w-full object-cover"
            style={{ objectPosition: cropPosition(size.crop) }}
          />
        </div>
        <label className="absolute left-2 top-2 flex cursor-pointer items-center gap-1.5 rounded-md border border-[#232330] bg-[#0A0A0D]/85 px-2 py-1 text-[11px] font-semibold backdrop-blur">
          <input
            type="checkbox"
            checked={selected}
            onChange={() => onToggle(size.id, format)}
            className="h-3 w-3 accent-[#C8FF3D]"
          />
          Select
        </label>
        {isBest && (
          <span className="absolute right-2 top-2 rounded-md bg-[#C8FF3D] px-2 py-1 text-[10px] font-black uppercase tracking-wide text-black">
            ★ Best
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-3.5">
        <div>
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-bold text-[#F2F2F7]">{size.label}</h3>
            <span className="mono text-xs text-[#8E8EA8]">
              {size.width}×{size.height}
            </span>
          </div>
          <div className="mt-1.5 flex flex-wrap items-center gap-2">
            <span className="mono text-xs text-[#8E8EA8]">
              {formatBytes(size.bytesByFormat[format])}
            </span>
            {size.source === "upscaled" ? (
              <UpscaledBadge note={size.note} />
            ) : (
              <span className="inline-flex items-center gap-1 rounded-md border border-[#22C55E]/25 bg-[#22C55E]/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-[#22C55E]">
                <Check className="h-3 w-3" /> Native
              </span>
            )}
            {size.crop && (
              <span className="text-[10px] text-[#8E8EA8]" title={size.note}>
                {size.aspect} crop
              </span>
            )}
          </div>
        </div>

        <FormatToggle value={format} onChange={setFormat} bytesByFormat={size.bytesByFormat} />

        <button
          type="button"
          onClick={handleDownload}
          disabled={busy}
          className="mt-auto flex items-center justify-center gap-2 rounded-lg border border-[#232330] bg-[#16161D] py-2.5 text-sm font-semibold text-[#F2F2F7] transition-all hover:border-[#C8FF3D]/40 hover:bg-[#1b1b24] disabled:opacity-50"
        >
          {busy ? <Spinner size={15} /> : <Download className="h-4 w-4" />}
          Download
        </button>
      </div>
    </motion.article>
  );
}

/* ============================ ThumbnailGrid =========================== */

export function ThumbnailGrid({ data }: { data: ThumbnailResponse }) {
  const [selected, setSelected] = useState<Record<string, ImageFormat>>({});
  const [zipping, setZipping] = useState(false);
  const toast = useToast();
  const reduced = useReducedMotion();

  const selectedItems = useMemo(
    () =>
      Object.entries(selected).map(([sizeId, format]) => ({
        sizeId: sizeId as SizeId,
        format,
      })),
    [selected],
  );

  const toggle = useCallback((sizeId: SizeId, format: ImageFormat) => {
    setSelected((current) => {
      const next = { ...current };
      if (next[sizeId]) delete next[sizeId];
      else next[sizeId] = format;
      return next;
    });
  }, []);

  const selectAll = useCallback(() => {
    setSelected((current) =>
      Object.keys(current).length === data.sizes.length
        ? {}
        : Object.fromEntries(data.sizes.map((size) => [size.id, "jpg" as ImageFormat])),
    );
  }, [data.sizes]);

  const handleZip = useCallback(async () => {
    if (selectedItems.length === 0) return;
    setZipping(true);
    try {
      await downloadZip(data.sourceUrl, selectedItems);
      toast.push(`Zipped ${selectedItems.length} file(s).`, "success");
    } catch (error) {
      toast.push(
        error instanceof ApiError ? error.message : "Couldn't build the archive.",
        "error",
      );
    } finally {
      setZipping(false);
    }
  }, [data.sourceUrl, selectedItems, toast]);

  return (
    <motion.section
      initial={{ opacity: 0, height: reduced ? "auto" : 0 }}
      animate={{ opacity: 1, height: "auto" }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="overflow-hidden"
      aria-label="Download sizes"
    >
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="eyebrow">Download</p>
          <h2 className="mt-1 text-xl font-bold">Every size, measured</h2>
          <p className="mt-1 text-sm text-[#8E8EA8]">
            Native source is{" "}
            <span className="mono text-[#F2F2F7]">
              {data.native.width}×{data.native.height}
            </span>{" "}
            · {formatBytes(data.native.bytes)} · resolved via{" "}
            <span className="mono">{data.resolvedVia}</span> in{" "}
            <span className="mono">{data.elapsedMs}ms</span>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={selectAll}
            className="rounded-lg border border-[#232330] bg-[#16161D] px-3 py-2 text-xs font-semibold text-[#8E8EA8] transition-colors hover:text-white"
          >
            {Object.keys(selected).length === data.sizes.length ? "Clear selection" : "Select all"}
          </button>
          <CopyButton value={data.native.url} label="Copy image URL" className="!py-2">
            <Link2 className="h-3.5 w-3.5" />
          </CopyButton>
          <button
            type="button"
            onClick={handleZip}
            disabled={selectedItems.length === 0 || zipping}
            className="flex items-center gap-2 rounded-lg bg-[#C8FF3D] px-3.5 py-2 text-xs font-bold text-black transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-35"
          >
            {zipping ? <Spinner size={14} /> : <Package className="h-3.5 w-3.5" />}
            Download ZIP
            {selectedItems.length > 0 && ` (${selectedItems.length})`}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <AnimatePresence>
          {data.sizes.map((size, index) => (
            <SizeCard
              key={size.id}
              size={size}
              index={index}
              sourceUrl={data.sourceUrl}
              previewUrl={data.native.url}
              isBest={size.id === data.bestSizeId}
              selected={Boolean(selected[size.id])}
              onToggle={toggle}
            />
          ))}
        </AnimatePresence>
      </div>
    </motion.section>
  );
}
