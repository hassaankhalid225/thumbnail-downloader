/** Score banding and colour helpers. The bands are published in ANALYSIS_SPEC.md. */

export type ScoreBand = "great" | "good" | "ok" | "bad" | "none";

export function scoreBand(score: number | null): ScoreBand {
  if (score === null) return "none";
  if (score >= 80) return "great";
  if (score >= 60) return "good";
  if (score >= 40) return "ok";
  return "bad";
}

const BAND_COLORS: Record<ScoreBand, string> = {
  great: "#22C55E",
  good: "#C8FF3D",
  ok: "#F59E0B",
  bad: "#EF4444",
  none: "#55556B",
};

const BAND_LABELS: Record<ScoreBand, string> = {
  great: "Strong",
  good: "Solid",
  ok: "Needs work",
  bad: "Weak",
  none: "Not measured",
};

export function scoreColor(score: number | null): string {
  return BAND_COLORS[scoreBand(score)];
}

export function scoreLabel(score: number | null): string {
  return BAND_LABELS[scoreBand(score)];
}

export function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const full =
    clean.length === 3
      ? clean
          .split("")
          .map((c) => c + c)
          .join("")
      : clean;
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16),
  ];
}

/** WCAG relative luminance — the same formula the backend uses, so labels agree. */
function relativeLuminance([r, g, b]: [number, number, number]): number {
  const channel = (value: number) => {
    const v = value / 255;
    return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/** Black or white, whichever is legible on the given background. */
export function readableOn(hex: string): string {
  return relativeLuminance(hexToRgb(hex)) > 0.45 ? "#0A0A0D" : "#F2F2F7";
}

export function verdictColor(verdict: string): string {
  if (verdict === "PASS") return "#22C55E";
  if (verdict === "WARNING") return "#F59E0B";
  return "#EF4444";
}

export function severityColor(severity: string): string {
  if (severity === "high") return "#EF4444";
  if (severity === "medium") return "#F59E0B";
  return "#8E8EA8";
}
