import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";
import { jsonResponse } from "../test/api-responses";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

describe("ProjectWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows the saved request and a presentation-only five-stage shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({
          id: "project-1",
          name: "Travel Bag",
          original_request: "Source recycled travel bags.",
          stage: "BRIEF",
        })),
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
        .mockResolvedValueOnce(jsonResponse({ id: "project-1", name: "Travel Bag", original_request: "Source bags" }))
        .mockResolvedValueOnce(jsonResponse({ id: "project-1", name: "Renamed Bag", original_request: "Source bags" })),
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
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ error: { code: "NOT_FOUND", message: "Project not found." } }, 404)),
    );
    render(<ProjectWorkspace projectId="foreign-project" />);

    expect(await screen.findByText("Project not found in this demo session.")).toBeInTheDocument();
  });

  it("keeps the newer project when an earlier request resolves last", async () => {
    let resolveProjectA: (response: Response) => void;
    let resolveProjectB: (response: Response) => void;
    const projectAResponse = new Promise<Response>((resolve) => {
      resolveProjectA = resolve;
    });
    const projectBResponse = new Promise<Response>((resolve) => {
      resolveProjectB = resolve;
    });
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => (path.endsWith("project-a") ? projectAResponse : projectBResponse)),
    );

    const { rerender } = render(<ProjectWorkspace projectId="project-a" />);
    rerender(<ProjectWorkspace projectId="project-b" />);

    await act(async () => {
      resolveProjectB!(jsonResponse({ id: "project-b", name: "Project B", original_request: "New request" }));
    });
    expect(await screen.findByText("Project B")).toBeInTheDocument();

    await act(async () => {
      resolveProjectA!(jsonResponse({ id: "project-a", name: "Project A", original_request: "Old request" }));
    });
    expect(screen.getByText("Project B")).toBeInTheDocument();
    expect(screen.queryByText("Project A")).not.toBeInTheDocument();
  });
});
