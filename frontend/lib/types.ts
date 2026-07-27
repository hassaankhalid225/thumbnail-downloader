/**
 * Mirrors API_SPEC.md exactly. No `any` anywhere in this file or downstream of it —
 * if the backend adds a field, it gets typed here first.
 */

export type ImageFormat = "jpg" | "png" | "webp";
export type SizeId = "fhd" | "hd" | "sd" | "hq" | "mq" | "tiny" | "vertical" | "square";

export interface ApiErrorBody {
  code: string;
  message: string;
  detail?: unknown;
}

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly retryAfter: number | null;

  constructor(body: ApiErrorBody, status: number, retryAfter: number | null = null) {
    super(body.message);
    this.name = "ApiError";
    this.code = body.code;
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

/* ---------- thumbnails ---------- */

export interface CropRegion {
  x: number;
  y: number;
  w: number;
  h: number;
  anchoredTo: string;
}

export interface ThumbnailSize {
  id: SizeId;
  label: string;
  width: number;
  height: number;
  aspect: string;
  source: "native" | "upscaled";
  bytes: number;
  bytesByFormat: Record<ImageFormat, number>;
  formats: ImageFormat[];
  crop: CropRegion | null;
  note: string;
}

export interface NativeThumbnail {
  url: string;
  label: string;
  width: number;
  height: number;
  bytes: number;
  aspect: string;
}

export interface ThumbnailCandidate {
  label: string;
  url: string;
  width: number | null;
  height: number | null;
  bytes: number | null;
}

export interface ThumbnailResponse {
  success: true;
  platform: string;
  platformName: string;
  videoId: string | null;
  title: string | null;
  uploader: string | null;
  duration: number | null;
  views: number | null;
  publishedAt: string | null;
  sourceUrl: string;
  webpageUrl: string | null;
  imageHash: string;
  native: NativeThumbnail;
  candidates: ThumbnailCandidate[];
  sizes: ThumbnailSize[];
  bestSizeId: SizeId;
  resolvedVia: string;
  elapsedMs: number;
}

/* ---------- analysis ---------- */

export type ScoreKey =
  | "stoppingPower"
  | "textReadability"
  | "mobileLegibility"
  | "colorImpact"
  | "contrast"
  | "composition"
  | "emotionalHook"
  | "safeZone";

export type Scores = {
  overall: number;
  reasons: Record<string, string>;
  labels: Record<ScoreKey, string>;
  weights: Record<ScoreKey, number>;
  excluded: ScoreKey[];
  excludedNote: string | null;
} & { [K in ScoreKey]: number | null };

export interface Swatch {
  hex: string;
  rgb: [number, number, number];
  lab: [number, number, number];
  hsv: [number, number, number];
  coverage: number;
  name: string;
}

export interface ColorAnalysis {
  palette: Swatch[];
  harmony: { type: string; confidence: number; hues: number[]; reason: string };
  temperature: { profile: string; meanB: number; warmRatio: number };
  saturation: { mean: number; std: number; profile: string };
  brightness: {
    histogram: number[];
    meanL: number;
    clippedBlack: number;
    clippedWhite: number;
  };
  distinctiveness: number;
  exports: {
    css: string;
    tailwind: Record<string, unknown>;
    ase: Record<string, unknown>;
    json: string;
  };
}

export interface ContrastAnalysis {
  globalContrast: number;
  rmsContrast: number;
  localContrast: { mean: number; max: number; p90: number };
  luminance: { mean: number; p5: number; p95: number };
}

export interface BBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface TextBlock {
  text: string | null;
  words: string[];
  confidence: number;
  bbox: BBox;
  bboxPx: BBox;
  capHeightPx: number;
  heightPercent: number;
  wcagContrast: number;
  passesAA: boolean;
  passesAALarge: boolean;
  textColor: string;
  backgroundColor: string;
  quadrant: string;
  thirdsDistance: number;
}

export interface FontRead {
  classification: string | null;
  weight: string | null;
  italic: boolean | null;
  casePattern: string | null;
  strokeWidth: number | null;
  strokeContrast: number | null;
  widthRatio: number | null;
  serifScore: number | null;
  slantDeg: number | null;
  closestGoogleFonts: { name: string; confidence: number; note?: string }[];
  disclaimer: string;
}

export interface TextAnalysis {
  available: boolean;
  textSource: "ocr" | "geometric";
  engine: string;
  recognitionAvailable: boolean;
  recognitionNote: string | null;
  blocks: TextBlock[];
  wordCount: number;
  wordCountVerdict: string;
  wordCountEstimated: boolean;
  textAreaRatio: number;
  fontRead: FontRead;
}

export type SurfaceVerdict = "PASS" | "WARNING" | "FAIL";

export interface MobileSurface {
  surface: string;
  label: string;
  width: number;
  height: number;
  capHeightPx: number;
  verdict: SurfaceVerdict;
  reason: string;
  ocrRecoveryRatio: number | null;
}

export interface MobileLegibility {
  available: boolean;
  reason: string | null;
  surfaces: MobileSurface[];
}

export interface CompositionAnalysis {
  focalPoint: { x: number; y: number };
  ruleOfThirdsScore: number;
  thirdsDistance: number;
  edgeDensity: number;
  cluttered: boolean;
  negativeSpace: number;
  balance: { lr: number; tb: number };
  depth: { backgroundBlur: number; subjectLapVar: number; backgroundLapVar: number };
  saliencyConcentration: number;
  saliencyBackend: string;
}

export interface Expression {
  label: string | null;
  confidence: number;
  method: string;
  signals: Record<string, number | boolean>;
  disclaimer: string;
}

export interface Face {
  bbox: BBox;
  bboxPx: BBox;
  confidence: number;
  areaPercent: number;
  quadrant: string;
  eyeLineY: number | null;
  eyeLineUpperThird: boolean | null;
  eyeLineSource: string | null;
  landmarks: Record<string, [number, number]> | null;
  expression: Expression;
}

export interface FaceAnalysis {
  available: boolean;
  detector: string;
  count: number;
  faces: Face[];
  note: string | null;
}

export interface SafeZone {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  note: string;
}

export interface Collision {
  zone: string;
  zoneLabel: string;
  severity: "high" | "medium" | "low";
  overlapFraction: number;
  element: "text" | "face";
  elementLabel: string;
  region: BBox;
  advice: string;
}

export interface SafeZoneAnalysis {
  collisions: Collision[];
  zones: SafeZone[];
  clean: boolean;
}

export interface QualityAnalysis {
  sharpness: number;
  sharpnessVerdict: string;
  noise: number;
  compressionArtifacts: string;
  blockRatio: number;
  width: number;
  height: number;
  bytes: number;
  format: string | null;
  aspect: string;
  aspectIs16x9: boolean;
  meetsYouTubeSpec: boolean;
  specNotes: string[];
}

export interface Improvement {
  priority: number;
  change: string;
  why: string;
  expected_impact: string;
}

export interface AiAnalysis {
  verdict: string;
  why_it_works: string[];
  why_it_fails: string[];
  psychological_hook: { type: string; explanation: string } | null;
  style_archetype: { name: string; confidence: number } | null;
  font_read: {
    classification: string | null;
    weight: string | null;
    closest_google_fonts: { name: string; confidence: number }[];
    disclaimer: string;
  } | null;
  color_story: string | null;
  text_placement_critique: string | null;
  target_audience: string | null;
  likely_niche: string | null;
  improvements: Improvement[];
  recreate_recipe: {
    palette: string[];
    font_style: string | null;
    layout: string | null;
    subject_treatment: string | null;
  } | null;
}

export interface AiError {
  code: string;
  message: string;
  retryable: boolean;
}

export interface AnalyzeResponse {
  success: true;
  imageHash: string;
  image: { width: number; height: number; bytes: number; format: string; analysedAt: string };
  scores: Scores;
  color: ColorAnalysis;
  contrast: ContrastAnalysis;
  text: TextAnalysis;
  mobileLegibility: MobileLegibility;
  composition: CompositionAnalysis;
  faces: FaceAnalysis;
  safeZones: SafeZoneAnalysis;
  quality: QualityAnalysis;
  ai: AiAnalysis | null;
  aiError: AiError | null;
  aiUsage: {
    inputTokens: number;
    outputTokens: number;
    cacheReadTokens: number;
    estimatedCostUsd: number;
  } | null;
  cached: boolean;
  timings: { deterministicMs: number };
  elapsedMs: number;
  platform: string;
  platformName: string;
  videoId: string | null;
  title: string | null;
  uploader: string | null;
  sourceUrl: string | null;
  sizeId: string;
}

/* ---------- compare & channel ---------- */

export interface CompareResult {
  url: string;
  ok: boolean;
  platform?: string;
  platformName?: string;
  title?: string | null;
  uploader?: string | null;
  thumbnailUrl?: string | null;
  analysis: AnalyzeResponse | null;
  error: ApiErrorBody | null;
}

export interface CompareWinner {
  url: string;
  index: number;
  overall: number;
  reason: string;
  categories: Record<
    ScoreKey,
    { winnerIndex: number | null; values: (number | null)[]; margin: number | null }
  >;
}

export interface CompareResponse {
  success: true;
  results: CompareResult[];
  winner: CompareWinner | null;
  elapsedMs: number;
}

export interface ChannelItem {
  ok: boolean;
  videoId: string | null;
  title: string | null;
  url: string;
  thumbnailUrl?: string | null;
  scores?: Scores;
  color?: { palette: Swatch[] };
  text?: { wordCount: number; blocks: { quadrant: string; capHeightPx: number }[] };
  faces?: { count: number };
  error: ApiErrorBody | null;
}

export interface ChannelPattern {
  recurringPalette: { hex: string; name: string; frequency: number; meanCoverage: number }[];
  dominantTextPlacement: { quadrant: string; share: number; heatmap: number[][] } | null;
  faceUsageRate: number;
  averageWordCount: number;
  wordCountStdDev: number;
  averageScores: Record<string, number>;
  consistencyScore: number;
  consistencyBasis: string;
}

export interface ChannelResponse {
  success: true;
  channel: { name: string | null; url: string; videoCount: number; requested: number };
  items: ChannelItem[];
  pattern: ChannelPattern;
  elapsedMs: number;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  uptime: number;
  ytDlp: string | null;
  tesseract: string | null;
  opencv: string;
  faceDetector: string;
  saliency: string;
  ai: { enabled: boolean; model: string; configured: boolean };
  aiUsage: Record<string, number>;
  cache: Record<string, number>;
  limits: Record<string, number>;
  degraded: string[];
}

/* ---------- flow ---------- */

export type FlowState =
  | "IDLE"
  | "DETECTING"
  | "RESOLVING"
  | "THUMBNAILS_READY"
  | "ANALYZING_CV"
  | "ANALYZING_AI"
  | "COMPLETE"
  | "ERROR"
  | "PARTIAL";
