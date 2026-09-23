import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DemoSessionInitializer } from "./demo-session-initializer";
import { emptyResponse, jsonResponse } from "../test/api-responses";

describe("DemoSessionInitializer", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("automatically initializes an anonymous session without exposing a token", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(emptyResponse()));

    render(<DemoSessionInitializer />);

    expect(await screen.findByText("Demo session ready")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/demo-session", {
      method: "POST",
      credentials: "same-origin",
    });
    expect(document.body.textContent).not.toContain("sourcepilot_demo_session");
  });

  it("shows a retry message when initialization fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("unavailable")));

    render(<DemoSessionInitializer />);

    expect(await screen.findByText("We could not reach SourcePilot. Please try again.")).toBeInTheDocument();
  });

  it("can initialize again safely when mounted again", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(emptyResponse()));
    const firstRender = render(<DemoSessionInitializer />);

    await screen.findByText("Demo session ready");
    firstRender.unmount();
    render(<DemoSessionInitializer />);

    expect(await screen.findByText("Demo session ready")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(2);
  });

  it("retries a recoverable initialization failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse({ error: { code: "HTTP_ERROR", message: "Try again." } }, 503))
        .mockResolvedValueOnce(emptyResponse()),
    );

    render(<DemoSessionInitializer />);
    await screen.findByText("Try again.");
    screen.getByRole("button", { name: "Try again" }).click();

    expect(await screen.findByText("Demo session ready")).toBeInTheDocument();
  });
});
