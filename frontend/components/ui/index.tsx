"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Check, Copy, HelpCircle, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";

import { cn, copyToClipboard } from "@/lib/utils";

/* ============================ reduced motion ============================ */

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const listener = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, []);
  return reduced;
}

/* ================================ Spinner =============================== */

export function Spinner({ size = 16, className }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={cn("animate-spin", className)}
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" fill="none" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}

/* ================================ Skeleton ============================== */

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("shimmer rounded-lg", className)} aria-hidden="true" />;
}

/* ================================= Badge ================================ */

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: React.ReactNode;
  tone?: "neutral" | "accent" | "great" | "ok" | "bad" | "cyan";
  className?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "bg-[#16161D] text-[#8E8EA8] border-[#232330]",
    accent: "bg-[#C8FF3D]/12 text-[#C8FF3D] border-[#C8FF3D]/30",
    great: "bg-[#22C55E]/12 text-[#22C55E] border-[#22C55E]/30",
    ok: "bg-[#F59E0B]/12 text-[#F59E0B] border-[#F59E0B]/30",
    bad: "bg-[#EF4444]/12 text-[#EF4444] border-[#EF4444]/30",
    cyan: "bg-[#22D3EE]/12 text-[#22D3EE] border-[#22D3EE]/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/* ================================ Tooltip ===============================
   Opens on hover and on focus, closes on Escape. A tooltip that only opens on
   hover is invisible to a keyboard, and every metric here needs one.          */

export function Tooltip({
  content,
  children,
  side = "top",
}: {
  content: React.ReactNode;
  children?: React.ReactNode;
  side?: "top" | "bottom";
}) {
  const [open, setOpen] = useState(false);
  const id = useId();

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        aria-label={typeof content === "string" ? content : "More information"}
        className="inline-flex items-center text-[#8E8EA8] transition-colors hover:text-[#C8FF3D]"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(event) => {
          event.preventDefault();
          setOpen((value) => !value);
        }}
      >
        {children ?? <HelpCircle className="h-3.5 w-3.5" />}
      </button>
      <AnimatePresence>
        {open && (
          <motion.span
            id={id}
            role="tooltip"
            initial={{ opacity: 0, y: side === "top" ? 4 : -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.14 }}
            className={cn(
              "pointer-events-none absolute left-1/2 z-50 w-64 -translate-x-1/2 rounded-lg border border-[#33334A] bg-[#16161D] px-3 py-2 text-xs leading-relaxed text-[#F2F2F7] shadow-xl",
              side === "top" ? "bottom-full mb-2" : "top-full mt-2",
            )}
          >
            {content}
          </motion.span>
        )}
      </AnimatePresence>
    </span>
  );
}

/* ============================== CopyButton ============================== */

export function CopyButton({
  value,
  label = "Copy",
  copiedLabel = "Copied",
  className,
  compact = false,
  children,
}: {
  value: string;
  label?: string;
  copiedLabel?: string;
  className?: string;
  compact?: boolean;
  /** Replaces the default copy glyph. The checkmark morph still takes over on success. */
  children?: React.ReactNode;
}) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  const handle = useCallback(async () => {
    const ok = await copyToClipboard(value);
    if (!ok) return;
    setCopied(true);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setCopied(false), 1600);
  }, [value]);

  return (
    <button
      type="button"
      onClick={handle}
      aria-live="polite"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border border-[#232330] bg-[#16161D] font-medium text-[#8E8EA8] transition-all hover:border-[#33334A] hover:text-[#F2F2F7]",
        compact ? "px-2 py-1 text-[11px]" : "px-3 py-1.5 text-xs",
        className,
      )}
    >
      <AnimatePresence mode="wait" initial={false}>
        {copied ? (
          <motion.span
            key="done"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.14 }}
            className="flex items-center gap-1.5 text-[#C8FF3D]"
          >
            <Check className="h-3.5 w-3.5" /> {copiedLabel}
          </motion.span>
        ) : (
          <motion.span
            key="idle"
            initial={{ scale: 0.6, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.6, opacity: 0 }}
            transition={{ duration: 0.14 }}
            className="flex items-center gap-1.5"
          >
            {children ?? <Copy className="h-3.5 w-3.5" />} {label}
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
}

/* ================================= Tabs =================================
   Roving tabindex with arrow-key navigation, per the WAI-ARIA tabs pattern.   */

export interface TabItem {
  id: string;
  label: string;
  badge?: React.ReactNode;
}

export function Tabs({
  items,
  active,
  onChange,
}: {
  items: TabItem[];
  active: string;
  onChange: (id: string) => void;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  const onKeyDown = (event: React.KeyboardEvent) => {
    const index = items.findIndex((item) => item.id === active);
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % items.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = items.length - 1;
    else return;
    event.preventDefault();
    const target = items[next];
    if (!target) return;
    onChange(target.id);
    refs.current[target.id]?.focus();
  };

  return (
    <div
      role="tablist"
      aria-label="Analysis sections"
      onKeyDown={onKeyDown}
      className="flex gap-1 overflow-x-auto border-b border-[#232330] pb-px"
    >
      {items.map((item) => {
        const selected = item.id === active;
        return (
          <button
            key={item.id}
            ref={(node) => {
              refs.current[item.id] = node;
            }}
            role="tab"
            id={`tab-${item.id}`}
            aria-selected={selected}
            aria-controls={`panel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(item.id)}
            className={cn(
              "relative shrink-0 px-4 py-3 text-sm font-semibold transition-colors",
              selected ? "text-[#F2F2F7]" : "text-[#8E8EA8] hover:text-[#F2F2F7]",
            )}
          >
            <span className="flex items-center gap-2">
              {item.label}
              {item.badge}
            </span>
            {selected && (
              <motion.span
                layoutId="tab-underline"
                className="absolute inset-x-2 -bottom-px h-0.5 rounded-full bg-[#C8FF3D]"
                transition={{ type: "spring", stiffness: 380, damping: 32 }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ================================= Toast ================================ */

interface Toast {
  id: number;
  message: string;
  tone: "info" | "error" | "success";
}

interface ToastApi {
  push: (message: string, tone?: Toast["tone"]) => void;
}

const ToastContext = createContext<ToastApi>({ push: () => undefined });

export function useToast(): ToastApi {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const counter = useRef(0);

  const push = useCallback((message: string, tone: Toast["tone"] = "info") => {
    counter.current += 1;
    const id = counter.current;
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 5200);
  }, []);

  const api = useMemo(() => ({ push }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        className="pointer-events-none fixed bottom-5 left-1/2 z-[100] flex w-[min(92vw,26rem)] -translate-x-1/2 flex-col gap-2"
        role="status"
        aria-live="polite"
      >
        <AnimatePresence initial={false}>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 16, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.97 }}
              transition={{ type: "spring", stiffness: 420, damping: 34 }}
              className={cn(
                "pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur",
                toast.tone === "error"
                  ? "border-[#EF4444]/40 bg-[#1a1114]/95 text-[#FCA5A5]"
                  : toast.tone === "success"
                    ? "border-[#C8FF3D]/40 bg-[#12160c]/95 text-[#C8FF3D]"
                    : "border-[#33334A] bg-[#16161D]/95 text-[#F2F2F7]",
              )}
            >
              <span className="flex-1 leading-relaxed">{toast.message}</span>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setToasts((c) => c.filter((t) => t.id !== toast.id))}
                className="mt-0.5 opacity-60 transition-opacity hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

/* =============================== Progress =============================== */

export function IndeterminateBar({ label }: { label: string }) {
  return (
    <div className="space-y-2" role="status" aria-live="polite">
      <div className="flex items-center gap-2 text-xs text-[#8E8EA8]">
        <Spinner size={13} />
        <span>{label}</span>
      </div>
      <div className="h-0.5 overflow-hidden rounded-full bg-[#232330]">
        <motion.div
          className="h-full w-1/3 rounded-full bg-gradient-to-r from-[#C8FF3D] to-[#22D3EE]"
          animate={{ x: ["-100%", "300%"] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    </div>
  );
}
