/**
 * Server-side proxy to the FastAPI backend.
 *
 * The browser never talks to the analyzer directly. That keeps the API origin private,
 * puts one timeout in front of every call, and guarantees the client only ever sees the
 * error envelope shape it knows how to render — a proxy failure looks exactly like an
 * API failure.
 */

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

const TIMEOUTS: Record<string, number> = {
  "/api/thumbnails": 45_000,
  "/api/analyze": 180_000,
  "/api/analyze/upload": 180_000,
  "/api/analyze/compare": 300_000,
  "/api/batch/channel": 420_000,
  "/api/download": 60_000,
  "/api/download/zip": 120_000,
  "/api/health": 10_000,
};

function envelope(code: string, message: string) {
  return { success: false, error: { code, message, detail: null } };
}

export async function proxy(request: Request, path: string): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), TIMEOUTS[path] ?? 60_000);

  try {
    const headers = new Headers();
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);

    // Preserve the caller's address so the backend rate-limits the real client and not
    // this server.
    const forwarded =
      request.headers.get("x-forwarded-for") ?? request.headers.get("x-real-ip");
    if (forwarded) headers.set("x-forwarded-for", forwarded);

    const method = request.method.toUpperCase();
    const upstream = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: method === "GET" || method === "HEAD" ? undefined : request.body,
      // Required by undici whenever a streaming body is forwarded.
      duplex: "half",
      signal: controller.signal,
      cache: "no-store",
    } as RequestInit & { duplex: "half" });

    const responseHeaders = new Headers();
    for (const key of [
      "content-type",
      "content-disposition",
      "content-length",
      "retry-after",
      "cache-control",
    ]) {
      const value = upstream.headers.get(key);
      if (value) responseHeaders.set(key, value);
    }

    // On an error status, make sure what comes back is actually a ThumbIQ error
    // envelope. If something else is listening on API_URL — another project's server on
    // a shared port is the usual culprit — it answers with its own shape or with HTML,
    // and the client would surface a bare "Something went wrong". Buffering here costs
    // nothing (error bodies are tiny) and turns that into a message that names the cause.
    if (upstream.status >= 400) {
      const raw = await upstream.text();
      let parsed: unknown = null;
      try {
        parsed = JSON.parse(raw);
      } catch {
        parsed = null;
      }

      const isThumbIQError =
        typeof parsed === "object" &&
        parsed !== null &&
        typeof (parsed as { error?: { code?: unknown } }).error?.code === "string";

      if (!isThumbIQError) {
        responseHeaders.set("content-type", "application/json");
        responseHeaders.delete("content-length");
        return new Response(
          JSON.stringify(
            envelope(
              "upstream_mismatch",
              `Got a ${upstream.status} from ${API_URL} that isn't a ThumbIQ response. ` +
                "Check that the ThumbIQ backend — not another service — is running on that address.",
            ),
          ),
          { status: 502, headers: responseHeaders },
        );
      }

      responseHeaders.delete("content-length");
      return new Response(raw, { status: upstream.status, headers: responseHeaders });
    }

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === "AbortError";
    return Response.json(
      aborted
        ? envelope("timeout", "That took too long to process. Try again in a moment.")
        : envelope("upstream_unreachable", "The analyzer is unavailable right now."),
      { status: aborted ? 504 : 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}
