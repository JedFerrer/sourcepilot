import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DemoSessionInitializer } from "./demo-session-initializer";

describe("DemoSessionInitializer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("automatically initializes an anonymous session without exposing a token", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));

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

    expect(await screen.findByText("Demo session unavailable. Refresh to try again.")).toBeInTheDocument();
  });

  it("can initialize again safely when mounted again", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
    const firstRender = render(<DemoSessionInitializer />);

    await screen.findByText("Demo session ready");
    firstRender.unmount();
    render(<DemoSessionInitializer />);

    expect(await screen.findByText("Demo session ready")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
