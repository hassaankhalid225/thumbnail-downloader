import {
  ApiError,
  type AnalyzeResponse,
  type ChannelResponse,
  type CompareResponse,
  type HealthResponse,
  type ImageFormat,
  type SizeId,
  type ThumbnailResponse,
} from "./types";

/**
 * Every request goes through the Next route handlers under /api, which proxy to
 * FastAPI. That keeps the API origin out of the browser and gives one place to
 * normalise the error envelope.
 */
const BASE = "/api";

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      { code: "network", message: "Couldn't reach the analyzer. Check your connection." },
      0,
    );
  }
  return handle<T>(response);
}

async function handle<T>(response: Response): Promise<T> {
  const retryAfterHeader = response.headers.get("retry-after");
  const retryAfter = retryAfterHeader ? Number(retryAfterHeader) : null;

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const envelope = payload as { error?: { code: string; message: string } } | null;
    throw new ApiError(
      envelope?.error ?? {
        // Reaching here means the response wasn't a ThumbIQ error envelope at all.
        // Say that, rather than "something went wrong" — the cause is almost always
        // the backend being down or a different service answering on its address.
        code: "bad_response",
        message:
          "The analyzer didn't respond properly. It may be down, or another service " +
          "may be running on its address.",
      },
      response.status,
      retryAfter,
    );
  }
  return payload as T;
}

export function getThumbnails(url: string, signal?: AbortSignal): Promise<ThumbnailResponse> {
  return post<ThumbnailResponse>("/thumbnails", { url }, signal);
}

export function analyze(
  url: string,
  options: { sizeId?: string; includeAI?: boolean } = {},
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse>(
    "/analyze",
    { url, sizeId: options.sizeId ?? "native", includeAI: options.includeAI ?? true },
    signal,
  );
}

export async function analyzeUpload(
  file: File,
  includeAI = true,
  signal?: AbortSignal,
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("image", file);
  form.append("includeAI", String(includeAI));

  let response: Response;
  try {
    response = await fetch(`${BASE}/analyze-upload`, { method: "POST", body: form, signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(
      { code: "network", message: "Couldn't reach the analyzer. Check your connection." },
      0,
    );
  }
  return handle<AnalyzeResponse>(response);
}

export function compare(
  urls: string[],
  includeAI = false,
  signal?: AbortSignal,
): Promise<CompareResponse> {
  return post<CompareResponse>("/compare", { urls, includeAI }, signal);
}

export function channel(
  url: string,
  limit = 24,
  signal?: AbortSignal,
): Promise<ChannelResponse> {
  return post<ChannelResponse>("/channel", { url, limit }, signal);
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${BASE}/health`, { cache: "no-store" });
  return handle<HealthResponse>(response);
}

/**
 * Downloads are a POST that streams a file, so they can't be a plain link. Build the
 * blob, click it, revoke it.
 */
export async function downloadSize(
  url: string,
  sizeId: SizeId,
  format: ImageFormat,
): Promise<void> {
  const response = await fetch(`${BASE}/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, sizeId, format }),
  });
  if (!response.ok) {
    await handle(response);
    return;
  }
  await saveBlob(response, `thumbiq_${sizeId}.${format}`);
}

export async function downloadZip(
  url: string,
  items: { sizeId: SizeId; format: ImageFormat }[],
): Promise<void> {
  const response = await fetch(`${BASE}/download-zip`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, items }),
  });
  if (!response.ok) {
    await handle(response);
    return;
  }
  await saveBlob(response, "thumbiq.zip");
}

async function saveBlob(response: Response, fallbackName: string): Promise<void> {
  const disposition = response.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? fallbackName;

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  // Give the browser a tick to start the download before releasing the object URL.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
}
