import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useDraftRegistration, useWorkspaceDrafts, WorkspaceDraftProvider } from "./workspace-drafts";

function Editor({ pending = false, check, leave }: { pending?: boolean; check: () => Promise<void>; leave: () => void }) {
  const [dirty, setDirty] = useState(true);
  const registry = useWorkspaceDrafts();
  useDraftRegistration("quote", { label: "Quote · Harbor", stage: "QUOTES", dirty, pending, check });
  return <><button onClick={() => registry?.leave(leave)}>All projects</button><button onClick={() => setDirty(false)}>Settle save</button></>;
}
describe("workspace departure", () => {
  afterEach(() => { cleanup(); vi.useRealTimers(); });
  it("defaults to Stay, names dirty records and leaves only on explicit discard", () => {
    const leave = vi.fn(); const check = vi.fn().mockResolvedValue(undefined);
    render(<WorkspaceDraftProvider><Editor leave={leave} check={check} /></WorkspaceDraftProvider>);
    fireEvent.click(screen.getByRole("button", { name: "All projects" }));
    expect(screen.getByRole("button", { name: "Stay" })).toHaveFocus();
    expect(screen.getByText("Quote · Harbor: Unsaved changes")).toBeInTheDocument();
    expect(screen.queryByText("Stay and save")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Discard unsaved changes and leave" }));
    expect(leave).toHaveBeenCalledTimes(1); expect(check).not.toHaveBeenCalled();
  });
  it("allows immediate departure while a write is pending", () => {
    const leave = vi.fn();
    render(<WorkspaceDraftProvider><Editor pending leave={leave} check={vi.fn()} /></WorkspaceDraftProvider>);
    fireEvent.click(screen.getByRole("button", { name: "All projects" }));
    expect(screen.getByText(/does not cancel a request/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Leave anyway" }));
    expect(leave).toHaveBeenCalledTimes(1);
  });
  it("offers a bounded read after ten seconds, keeps leave available, and never writes", async () => {
    vi.useFakeTimers(); const leave = vi.fn(); const check = vi.fn(() => new Promise<void>(() => {}));
    render(<WorkspaceDraftProvider><Editor pending leave={leave} check={check} /></WorkspaceDraftProvider>);
    fireEvent.click(screen.getByRole("button", { name: "All projects" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(screen.getByText("Save outcome not yet confirmed.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Check saved state" }));
    expect(screen.getByRole("button", { name: "Leave anyway" })).toBeEnabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(screen.getByText(/Saved state could not be confirmed/)).toBeInTheDocument();
    expect(check).toHaveBeenCalledTimes(1); expect(leave).not.toHaveBeenCalled();
  });
  it("does not navigate on late success and retains the choice to stay", async () => {
    vi.useFakeTimers(); const leave = vi.fn(); const check = vi.fn().mockResolvedValue(undefined);
    const view = render(<WorkspaceDraftProvider><Editor pending leave={leave} check={check} /></WorkspaceDraftProvider>);
    fireEvent.click(screen.getByRole("button", { name: "All projects" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    fireEvent.click(screen.getByRole("button", { name: "Check saved state" }));
    await act(async () => {});
    view.rerender(<WorkspaceDraftProvider><Editor leave={leave} check={check} /></WorkspaceDraftProvider>);
    expect(leave).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
  it("registers a native reload warning for unsaved drafts", () => {
    render(<WorkspaceDraftProvider><Editor leave={vi.fn()} check={vi.fn()} /></WorkspaceDraftProvider>);
    const event = new Event("beforeunload", { cancelable: true }); window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });
});
