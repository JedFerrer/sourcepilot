import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { HealthStatus } from "./health-status";
import { jsonResponse } from "../test/api-responses";

describe("HealthStatus", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows that the API is connected after the health request succeeds", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ status: "ok" })));

    render(<HealthStatus />);

    expect(await screen.findByText("API connected")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/health", { credentials: "same-origin" });
  });

  it("shows an unavailable state when the health request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("unavailable")));

    render(<HealthStatus />);

    expect(await screen.findByText("We could not reach SourcePilot. Please try again.")).toBeInTheDocument();
  });
});
