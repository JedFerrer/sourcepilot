import { analysisProxyMs } from "../../../lib/analysis-timeouts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function endToEndHeaders(source: Headers): Headers {
  const headers = new Headers(source);
  const connectionHeaders = (headers.get("connection") ?? "").split(",");
  for (const name of [...connectionHeaders, "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "proxy-connection", "te", "trailer", "transfer-encoding", "upgrade"]) {
    if (name.trim()) headers.delete(name.trim());
  }
  return headers;
}

async function forward(request: Request): Promise<Response> {
  const incoming = new URL(request.url);
  const analysis = request.method === "POST" && /^\/api\/projects\/[^/]+\/comparison\/(advice|analysis)$/.test(incoming.pathname);
  const deadline = analysis ? AbortSignal.timeout(analysisProxyMs) : undefined;
  try {
    const upstream = new URL(process.env.API_ORIGIN ?? "http://localhost:8000");
    // Assign a pathname, never resolve a user-supplied URL against the backend origin.
    upstream.pathname = upstream.pathname.replace(/\/$/, "") + incoming.pathname.slice(4);
    upstream.search = incoming.search;
    const headers = endToEndHeaders(request.headers);
    headers.delete("host");
    // The incoming HTTP server handled this expectation; fetch does not support it.
    headers.delete("expect");
    headers.set("x-forwarded-host", incoming.host);
    headers.set("accept-encoding", "identity");
    const options: RequestInit & { duplex: "half" } = {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      duplex: "half",
      cache: "no-store",
      redirect: "manual",
      signal: deadline ? AbortSignal.any([request.signal, deadline]) : request.signal,
    };
    const response = await fetch(upstream, options);
    const responseHeaders = endToEndHeaders(response.headers);
    // An early rejection can leave the incoming upload incomplete and paused.
    if (response.status === 413) responseHeaders.set("connection", "close");
    // Fetch decodes compressed responses, even if an upstream ignores identity encoding.
    const encodings = responseHeaders.get("content-encoding")?.toLowerCase().split(",").map((value) => value.trim());
    if (encodings?.length && encodings.every((value) => ["gzip", "deflate", "br"].includes(value))) {
      responseHeaders.delete("content-encoding");
      responseHeaders.delete("content-length");
    }
    // Analysis is one JSON result, not a stream. Include body consumption in the
    // proxy deadline so a stalled body still gets a structured error envelope.
    const body = analysis ? await response.arrayBuffer() : response.body;
    return new Response(body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    console.error("API proxy request failed.");
    if (analysis) {
      return Response.json({ error: {
        code: deadline?.aborted ? "ANALYSIS_WAIT_TIMEOUT" : "ANALYSIS_CONNECTION_LOST",
        message: deadline?.aborted ? "Analysis took too long. Please retry."
          : "The connection was interrupted. Analysis may still be finishing. Please wait before retrying.",
      } }, { status: deadline?.aborted ? 504 : 502 });
    }
    return new Response("Internal Server Error", { status: 500 });
  }
}

export { forward as GET, forward as HEAD, forward as POST, forward as PUT,
  forward as PATCH, forward as DELETE, forward as OPTIONS };
