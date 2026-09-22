import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

describe("ProjectWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows the saved request and a presentation-only five-stage shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          id: "project-1",
          name: "Travel Bag",
          original_request: "Source recycled travel bags.",
          stage: "BRIEF",
        }),
      }),
    );
    render(<ProjectWorkspace projectId="project-1" />);

    expect(await screen.findByText("Travel Bag")).toBeInTheDocument();
    expect(screen.getByText("Source recycled travel bags.")).toBeInTheDocument();
    expect(screen.getByText("Brief").closest("li")).toHaveAttribute("aria-current", "step");
    for (const stage of ["Suppliers", "Quotes", "Comparison", "Decision"]) {
      expect(screen.getByText(stage).closest("li")).toHaveAttribute("data-unavailable", "true");
    }
  });

  it("persists a project rename", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "project-1", name: "Travel Bag", original_request: "Source bags" }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "project-1", name: "Renamed Bag", original_request: "Source bags" }),
        }),
    );
    render(<ProjectWorkspace projectId="project-1" />);

    await screen.findByText("Travel Bag");
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Renamed Bag" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByText("Renamed Bag")).toBeInTheDocument();
    expect(fetch).toHaveBeenLastCalledWith("/api/projects/project-1", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Renamed Bag" }),
    });
  });

  it("does not expose a project outside the current session", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 404, ok: false }));
    render(<ProjectWorkspace projectId="foreign-project" />);

    expect(await screen.findByText("Project not found in this demo session.")).toBeInTheDocument();
  });
});
