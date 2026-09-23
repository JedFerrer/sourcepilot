import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectDashboard } from "./project-dashboard";
import { jsonResponse } from "../test/api-responses";

const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

describe("ProjectDashboard", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    push.mockReset();
  });

  it("creates a project with its original request and opens its workspace", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(jsonResponse([]))
        .mockResolvedValueOnce(jsonResponse({ id: "project-1", name: "Travel Bag", original_request: "Source bags" })),
    );
    render(<ProjectDashboard />);

    await screen.findByText("No projects yet.");
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Travel Bag" } });
    fireEvent.change(screen.getByLabelText("What do you want to source?"), { target: { value: "Source bags" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);

    await vi.waitFor(() => expect(push).toHaveBeenCalledWith("/projects/project-1"));
    expect(fetch).toHaveBeenLastCalledWith("/api/projects", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Travel Bag", original_request: "Source bags" }),
    });
  });

  it("shows current-session projects for reopening", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse(
        [
          {
            id: "project-1",
            name: "Recycled Cosmetic Travel Bag",
            original_request: "Source bags",
            stage: "BRIEF",
            updated_at: "2026-09-22T00:00:00Z",
          },
        ],
      )),
    );
    render(<ProjectDashboard />);

    const projectLink = await screen.findByRole("link", { name: /Recycled Cosmetic Travel Bag/ });
    expect(projectLink).toHaveAttribute("href", "/projects/project-1");
    expect(screen.getByText("Brief")).toBeInTheDocument();
  });

  it("validates required local input before creating a project", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([])));
    render(<ProjectDashboard />);

    await screen.findByText("No projects yet.");
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);

    expect(screen.getByText("Enter a project name and sourcing request.")).toBeInTheDocument();
  });
});
