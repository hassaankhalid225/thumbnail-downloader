"use client";

import { useCallback, useRef, useState } from "react";

import { analyze, analyzeUpload, getThumbnails } from "./api";
import { ANALYSIS_ENABLED } from "./constants";
import {
  ApiError,
  type AnalyzeResponse,
  type FlowState,
  type ThumbnailResponse,
} from "./types";
import { detectPlatform } from "./utils";

interface ThumbIQState {
  state: FlowState;
  url: string;
  platform: string | null;
  thumbnails: ThumbnailResponse | null;
  analysis: AnalyzeResponse | null;
  error: ApiError | null;
  /** Set when the download path worked but the analysis path did not. */
  analysisError: ApiError | null;
  uploadPreview: string | null;
}

const INITIAL: ThumbIQState = {
  state: "IDLE",
  url: "",
  platform: null,
  thumbnails: null,
  analysis: null,
  error: null,
  analysisError: null,
  uploadPreview: null,
};

/**
 * Owns the whole flow.
 *
 * The one structural rule: the two requests are independent. `/api/thumbnails` and
 * `/api/analyze` fire together, and the download grid renders the moment the first
 * lands — a slow or failed AI call can never stand between a user and their image.
 */
export function useThumbIQ() {
  const [state, setState] = useState<ThumbIQState>(INITIAL);
  const abort = useRef<AbortController | null>(null);
  const previewUrl = useRef<string | null>(null);

  const reset = useCallback(() => {
    abort.current?.abort();
    if (previewUrl.current) {
      URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = null;
    }
    setState(INITIAL);
  }, []);

  const setUrl = useCallback((url: string) => {
    setState((current) => ({
      ...current,
      url,
      platform: detectPlatform(url),
      state: current.state === "ERROR" ? "IDLE" : current.state,
      error: current.state === "ERROR" ? null : current.error,
    }));
  }, []);

  const submit = useCallback(async (raw: string) => {
    const url = raw.trim();
    if (!url) return;

    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;

    if (previewUrl.current) {
      URL.revokeObjectURL(previewUrl.current);
      previewUrl.current = null;
    }

    setState({
      ...INITIAL,
      url,
      platform: detectPlatform(url),
      state: "RESOLVING",
    });

    // Both requests start now. Neither waits for the other.
    const thumbnailsPromise = getThumbnails(url, controller.signal);
    // Analyser off: don't fire the request at all. Starting it and discarding the result
    // would still cost the user a round trip and the server a full CV pass.
    const analysisPromise = ANALYSIS_ENABLED
      ? analyze(url, { includeAI: true }, controller.signal)
      : null;

    let resolved = false;

    try {
      const thumbnails = await thumbnailsPromise;
      resolved = true;
      setState((current) => ({
        ...current,
        thumbnails,
        state: analysisPromise ? "ANALYZING_CV" : "COMPLETE",
      }));
    } catch (error) {
      if (isAbort(error)) return;
      setState((current) => ({
        ...current,
        state: "ERROR",
        error: asApiError(error),
      }));
      // The analysis request is now pointless; stop it rather than leaving it running.
      controller.abort();
      return;
    }

    if (!analysisPromise) return;

    try {
      const analysis = await analysisPromise;
      setState((current) => ({
        ...current,
        analysis,
        analysisError: null,
        state: analysis.aiError ? "PARTIAL" : "COMPLETE",
      }));
    } catch (error) {
      if (isAbort(error)) return;
      // Thumbnails are on screen and downloadable. This is a partial success, and the
      // UI says so rather than throwing away work the user can already use.
      setState((current) => ({
        ...current,
        analysisError: asApiError(error),
        state: resolved ? "PARTIAL" : "ERROR",
        error: resolved ? null : asApiError(error),
      }));
    }
  }, []);

  const submitFile = useCallback(async (file: File) => {
    // The upload path exists only to analyse your own draft — there is nothing to
    // download from it. With the analyser off it is a no-op, and the UI hides its entry
    // point so this is unreachable rather than silently ignored.
    if (!ANALYSIS_ENABLED) return;

    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;

    if (previewUrl.current) URL.revokeObjectURL(previewUrl.current);
    const preview = URL.createObjectURL(file);
    previewUrl.current = preview;

    setState({
      ...INITIAL,
      url: file.name,
      platform: "upload",
      uploadPreview: preview,
      state: "ANALYZING_CV",
    });

    try {
      const analysis = await analyzeUpload(file, true, controller.signal);
      setState((current) => ({
        ...current,
        analysis,
        state: analysis.aiError ? "PARTIAL" : "COMPLETE",
      }));
    } catch (error) {
      if (isAbort(error)) return;
      setState((current) => ({
        ...current,
        state: "ERROR",
        error: asApiError(error),
      }));
    }
  }, []);

  return { ...state, setUrl, submit, submitFile, reset };
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function asApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  return new ApiError(
    { code: "unknown", message: "Something went wrong. Please try again." },
    0,
  );
}
