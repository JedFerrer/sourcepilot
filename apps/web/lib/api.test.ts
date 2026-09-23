import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClientError, apiRequest } from "./api";
import { jsonResponse } from "../test/api-responses";

describe("apiRequest", () => {
  afterEach(() => vi.restoreAllMocks());

  it("returns JSON and includes same-origin credentials", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));

    await expect(apiRequest<{ status: string }>("/api/health")).resolves.toEqual({ status: "ok" });
    expect(fetch).toHaveBeenCalledWith("/api/health", { credentials: "same-origin" });
  });

  it("exposes structured API errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          {
            error: {
              code: "VALIDATION_ERROR",
              message: "Request validation failed.",
              fields: [{ field: "body.name", message: "must not be blank" }],
            },
          },
          422,
        ),
      ),
    );

    await expect(apiRequest("/api/projects")).rejects.toMatchObject({
      code: "VALIDATION_ERROR",
      message: "Request validation failed.",
      status: 422,
      fields: [{ field: "body.name", message: "must not be blank" }],
    } satisfies Partial<ApiClientError>);
  });

  it("uses safe errors for malformed responses and network failures", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ detail: "legacy" }, 500)));
    await expect(apiRequest("/api/projects")).rejects.toMatchObject({ code: "INVALID_RESPONSE" });

    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(apiRequest("/api/projects")).rejects.toMatchObject({ code: "NETWORK_ERROR" });
  });
});
