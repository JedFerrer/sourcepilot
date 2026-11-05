// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { GET, HEAD, OPTIONS, PATCH, POST } from "./route";

describe("same-site streaming API proxy", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); });

  it("returns a safe analysis envelope for an interrupted connection without retry", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("private-sentinel"));
    vi.stubGlobal("fetch", fetchMock);
    vi.spyOn(console, "error").mockImplementation(() => {});
    const response = await POST(new Request("https://app.test/api/projects/p/comparison/advice", { method: "POST" }));
    expect(response.status).toBe(502);
    expect(await response.json()).toMatchObject({ error: { code: "ANALYSIS_CONNECTION_LOST" } });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it.each(["headers", "body"])("bounds analysis %s consumption with a JSON timeout", async (phase) => {
    const controller = new AbortController();
    vi.spyOn(AbortSignal, "timeout").mockReturnValue(controller.signal);
    vi.spyOn(console, "error").mockImplementation(() => {});
    const waitForAbort = () => new Promise<never>((_, reject) => {
      controller.signal.addEventListener("abort", () => reject(controller.signal.reason), { once: true });
    });
    vi.stubGlobal("fetch", vi.fn(() => phase === "headers" ? waitForAbort() : Promise.resolve({
      headers: new Headers(), status: 200, statusText: "OK", arrayBuffer: waitForAbort,
    })));
    const request = POST(new Request("https://app.test/api/projects/p/comparison/advice", { method: "POST" }));
    await Promise.resolve();
    controller.abort(new DOMException("deadline", "TimeoutError"));
    const response = await request;
    expect(response.status).toBe(504);
    expect(await response.json()).toMatchObject({ error: { code: "ANALYSIS_WAIT_TIMEOUT" } });
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("forwards normal requests and queries only to the configured backend", async () => {
    vi.stubEnv("API_ORIGIN", "http://backend.test/base");
    const call = vi.fn().mockResolvedValue(new Response('{"status":"ok"}', {
      headers: { "content-type": "application/json", "x-request-id": "safe-id" },
    }));
    vi.stubGlobal("fetch", call);
    const result = await GET(new Request("https://app.test/api//evil.test/projects?next=https://evil.test", {
      headers: { host: "evil.test", "x-forwarded-host": "evil.test", cookie: "sourcepilot_demo_session=opaque" },
    }));
    const [url, options] = call.mock.calls[0];
    expect(url.origin).toBe("http://backend.test");
    expect(url.pathname).toBe("/base//evil.test/projects");
    expect(url.search).toBe("?next=https://evil.test");
    expect(options.headers.get("host")).toBeNull();
    expect(options.headers.get("x-forwarded-host")).toBe("app.test");
    expect(options.headers.get("cookie")).toBe("sourcepilot_demo_session=opaque");
    expect(options).toMatchObject({ method: "GET", body: undefined, cache: "no-store", redirect: "manual" });
    expect(result.headers.get("x-request-id")).toBe("safe-id");
    expect(result.headers.has("connection")).toBe(false);
    expect(await result.json()).toEqual({ status: "ok" });
  });

  it("also forwards the API root rather than returning a Next.js page", async () => {
    const call = vi.fn().mockResolvedValue(new Response('{"detail":"Not Found"}', { status: 404 }));
    vi.stubGlobal("fetch", call);
    expect((await GET(new Request("https://app.test/api"))).status).toBe(404);
    expect(call.mock.calls[0][0].pathname).toBe("/");
  });

  it.each([401, 403, 404, 413, 422, 503])("preserves backend status %s and its safe error body", async (status) => {
    const body = JSON.stringify({ error: { code: status === 413 ? "REQUEST_TOO_LARGE" : "TEST_ERROR", message: "Safe message." } });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body, { status,
      headers: { "content-type": "application/json", "retry-after": "10" } })));
    const result = await PATCH(new Request("https://app.test/api/projects/id", { method: "PATCH", body: "{}" }));
    expect(result.status).toBe(status);
    expect(result.headers.get("content-type")).toBe("application/json");
    expect(result.headers.get("retry-after")).toBe("10");
    expect(result.headers.get("connection")).toBe(status === 413 ? "close" : null);
    expect(await result.text()).toBe(body);
  });

  it("preserves session cookies separately and removes hop-by-hop response headers", async () => {
    const cookies = ["sourcepilot_demo_session=opaque; Path=/; HttpOnly; SameSite=Lax; Secure",
      "second=value; Expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/"];
    const headers = new Headers({ connection: "x-hop", "x-hop": "private", "transfer-encoding": "chunked" });
    cookies.forEach((cookie) => headers.append("set-cookie", cookie));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204, headers })));
    const result = await POST(new Request("https://app.test/api/demo-session", { method: "POST" }));
    expect(result.status).toBe(204);
    expect(result.headers.getSetCookie()).toEqual(cookies);
    expect(result.headers.has("connection")).toBe(false);
    expect(result.headers.has("x-hop")).toBe(false);
    expect(result.headers.has("transfer-encoding")).toBe(false);
    expect(await result.text()).toBe("");
  });

  it.each([false, true])("streams multipart PDF bytes unchanged (Expect header: %s)", async (withExpect) => {
    const body = new TextEncoder().encode('--boundary\r\nContent-Disposition: form-data; name="file"; filename="quote.pdf"\r\nContent-Type: application/pdf\r\n\r\n%PDF-original\r\n--boundary--\r\n');
    const request = new Request("https://app.test/api/projects/id/quotes/upload", { method: "POST", body,
      headers: { "content-type": "multipart/form-data; boundary=boundary", "content-length": String(body.length),
        connection: "close, x-hop", "x-hop": "remove", cookie: "sourcepilot_demo_session=opaque",
        ...(withExpect ? { expect: "100-continue" } : {}) } });
    vi.stubGlobal("fetch", vi.fn(async (_url: URL, options: RequestInit) => {
      expect(options.body).toBe(request.body);
      expect(request.bodyUsed).toBe(false);
      const headers = new Headers(options.headers);
      expect(headers.get("content-type")).toBe("multipart/form-data; boundary=boundary");
      expect(headers.get("content-length")).toBe(String(body.length));
      expect(headers.get("cookie")).toBe("sourcepilot_demo_session=opaque");
      expect(headers.has("expect")).toBe(false);
      expect(headers.has("connection")).toBe(false);
      expect(headers.has("x-hop")).toBe(false);
      expect(new Uint8Array(await new Response(options.body).arrayBuffer())).toEqual(body);
      return new Response('{"quote":{}}', { status: 201 });
    }));
    expect((await POST(request)).status).toBe(201);
  });

  it("returns an early 413 without waiting for the incoming stream to end", async () => {
    const body = new ReadableStream<Uint8Array>();
    const request = new Request("https://app.test/api/projects", { method: "POST", body,
      duplex: "half" } as RequestInit);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response('{"error":{"code":"REQUEST_TOO_LARGE"}}', { status: 413 })));
    const result = await POST(request);
    expect(result.status).toBe(413);
    expect(result.headers.get("connection")).toBe("close");
    expect(request.bodyUsed).toBe(false);
    await body.cancel();
  });

  it("propagates client aborts to the upstream request", async () => {
    const controller = new AbortController();
    const request = new Request("https://app.test/api/projects", { signal: controller.signal });
    vi.stubGlobal("fetch", vi.fn(async (_url: URL, options: RequestInit) => {
      controller.abort();
      expect(options.signal?.aborted).toBe(true);
      return new Response(null, { status: 204 });
    }));
    await GET(request);
  });

  it("preserves response streaming and cancellation", async () => {
    const cancel = vi.fn();
    const body = new ReadableStream<Uint8Array>({ cancel });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(body)));
    const result = await GET(new Request("https://app.test/api/projects"));
    expect(result.body).toBe(body);
    await result.body?.cancel();
    expect(cancel).toHaveBeenCalledOnce();
  });

  it("does not follow redirects or lose Location, HEAD and OPTIONS responses", async () => {
    const call = vi.fn().mockResolvedValueOnce(new Response(null, { status: 307, headers: { location: "/projects/" } }))
      .mockResolvedValueOnce(new Response(null, { headers: { "content-length": "50" } }))
      .mockResolvedValueOnce(new Response(null, { status: 405, headers: { allow: "GET" } }));
    vi.stubGlobal("fetch", call);
    const redirect = await GET(new Request("https://app.test/api/projects"));
    expect(redirect.status).toBe(307);
    expect(redirect.headers.get("location")).toBe("/projects/");
    expect((await HEAD(new Request("https://app.test/api/projects", { method: "HEAD" }))).headers.get("content-length")).toBe("50");
    expect((await OPTIONS(new Request("https://app.test/api/projects", { method: "OPTIONS" }))).headers.get("allow")).toBe("GET");
    expect(call.mock.calls.every(([, options]) => options.redirect === "manual")).toBe(true);
  });

  it("does not relay stale compression headers after fetch decoding", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("decoded", { headers: {
      "content-encoding": "gzip", "content-length": "100", "content-type": "application/json",
    } })));
    const result = await GET(new Request("https://app.test/api/health"));
    expect(result.headers.has("content-encoding")).toBe(false);
    expect(result.headers.has("content-length")).toBe(false);
    expect(await result.text()).toBe("decoded");
  });

  it("retains an encoding that fetch has not decoded", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("opaque", { headers: {
      "content-encoding": "custom", "content-length": "6",
    } })));
    const result = await GET(new Request("https://app.test/api/health"));
    expect(result.headers.get("content-encoding")).toBe("custom");
    expect(result.headers.get("content-length")).toBe("6");
    expect(await result.text()).toBe("opaque");
  });

  it("keeps transport exceptions out of public responses and logs", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("SECRET_SENTINEL")));
    const log = vi.spyOn(console, "error").mockImplementation(() => undefined);
    const result = await GET(new Request("https://app.test/api/health"));
    expect(result.status).toBe(500);
    expect(await result.text()).toBe("Internal Server Error");
    expect(log).toHaveBeenCalledExactlyOnceWith("API proxy request failed.");
  });
});
