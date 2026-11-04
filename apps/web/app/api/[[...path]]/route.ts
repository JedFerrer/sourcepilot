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
  try {
    const incoming = new URL(request.url);
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
      signal: request.signal,
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
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    console.error("API proxy request failed.");
    return new Response("Internal Server Error", { status: 500 });
  }
}

export { forward as GET, forward as HEAD, forward as POST, forward as PUT,
  forward as PATCH, forward as DELETE, forward as OPTIONS };
