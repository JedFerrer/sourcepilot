import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectDashboard } from "./project-dashboard";
import Link from "next/link";
import { workflowFixture } from "../test/workflow-fixtures";
import { jsonResponse } from "../test/api-responses";

const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));

describe("ProjectDashboard", () => {
  it.each(["project", "header"])("guards %s navigation with a retained uncertain request and preserves it on Stay", async (destination) => {
    let writes = 0;
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => {
      if (init?.method === "POST") { writes++; return Promise.reject(new TypeError("Disconnected")); }
      return Promise.resolve(jsonResponse([{ id: "existing", name: "Existing project", updated_at: "2026-11-10T00:00:00Z" }]));
    }));
    render(<><Link href="/">Dashboard home</Link><ProjectDashboard /></>);
    await screen.findByRole("link", { name: /Existing project/ });
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Retained name" } });
    fireEvent.change(screen.getByLabelText("What do you want to source?"), { target: { value: "Retained request" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);
    fireEvent.click(await screen.findByRole("button", { name: "Check saved projects" }));
    await screen.findByRole("button", { name: "Return to retained request" });
    const name = destination === "project" ? /Existing project/ : /Dashboard home/;
    expect(fireEvent.click(screen.getByRole("link", { name }))).toBe(false);
    expect(screen.getByRole("button", { name: "Stay" })).toHaveFocus();
    expect(push).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Stay" }));
    expect(screen.getByLabelText("Project name")).toHaveValue("Retained name");
    expect(screen.getByLabelText("What do you want to source?")).toHaveValue("Retained request");
    expect(screen.getByRole("button", { name: "Create project" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Check saved projects" }));
    await screen.findByRole("button", { name: "Return to retained request" });
    fireEvent.click(screen.getByRole("link", { name }));
    fireEvent.click(screen.getByRole("button", { name: "Leave anyway" }));
    expect(push).toHaveBeenCalledExactlyOnceWith(destination === "project" ? "/projects/existing" : "/");
    expect(writes).toBe(1);
    const reload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(reload);
    expect(reload.defaultPrevented).toBe(false);
  });

  it.each(["success", "failure"])("does not redirect or restore an abandoned creation on late %s", async (outcome) => {
    let finish!: (value: Response) => void;
    let fail!: (reason: Error) => void;
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => init?.method === "POST"
      ? new Promise<Response>((resolve, reject) => { finish = resolve; fail = reject; }) : Promise.resolve(jsonResponse([]))));
    render(<ProjectDashboard />);
    await screen.findByText("No projects yet.");
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Departed" } });
    fireEvent.change(screen.getByLabelText("What do you want to source?"), { target: { value: "Request" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.click(screen.getByRole("button", { name: "Leave anyway" }));
    await act(async () => { if (outcome === "success") finish(jsonResponse({ id: "departed" })); else fail(new TypeError("Disconnected")); });
    expect(push).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    expect(screen.getByLabelText("Project name")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Create project" })).toBeEnabled();
    expect(screen.queryByText(/Creation outcome is uncertain/)).not.toBeInTheDocument();
  });
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    push.mockReset();
  });

  it("shows the persisted preferred supplier and no-decision projects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse([
      { id: "chosen", name: "Chosen project", preferred_supplier_name: "Supplier C", updated_at: "2026-10-03T00:00:00Z" },
      { id: "pending", name: "Pending project", preferred_supplier_name: null, updated_at: "2026-10-03T00:00:00Z" },
    ])));
    render(<ProjectDashboard />);
    expect(await screen.findByRole("link", { name: /Chosen project.*Preferred supplier: Supplier C/ })).toHaveAttribute("href", "/projects/chosen");
    expect(screen.getByRole("link", { name: /Pending project.*No Decision Yet/ })).toHaveAttribute("href", "/projects/pending");
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
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Travel Bag" } });
    fireEvent.change(screen.getByLabelText("What do you want to source?"), { target: { value: "Source bags" } });
    if (!screen.queryByRole("button", { name: "Create project" })) fireEvent.click(screen.getByRole("button", { name: "New project" }));
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
            workflow: workflowFixture(),
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
    if (!screen.queryByRole("button", { name: "Create project" })) fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);

    expect(screen.getByText("Enter a project name and sourcing request.")).toBeInTheDocument();
  });
  it("retains the request while checking an uncertain creation without replaying it", async () => {
    let writes = 0;
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => {
      if (init?.method === "POST") { writes += 1; return Promise.reject(new TypeError("Disconnected")); }
      return Promise.resolve(jsonResponse([]));
    }));
    render(<ProjectDashboard />);
    await screen.findByText("No projects yet.");
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Retained name" } });
    fireEvent.change(screen.getByLabelText("What do you want to source?"), { target: { value: "Retained sourcing request" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create project" }).closest("form")!);
    fireEvent.click(await screen.findByRole("button", { name: "Check saved projects" }));
    const reload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(reload);
    expect(reload.defaultPrevented).toBe(true);
    fireEvent.click(await screen.findByRole("button", { name: "Return to retained request" }));
    expect(screen.getByLabelText("Project name")).toHaveValue("Retained name");
    expect(screen.getByLabelText("What do you want to source?")).toHaveValue("Retained sourcing request");
    expect(screen.getByRole("button", { name: "Create project" })).toBeDisabled();
    expect(writes).toBe(1);

    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.click(screen.getByRole("button", { name: "Leave anyway" }));
    const discardedReload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(discardedReload);
    expect(discardedReload.defaultPrevented).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "New project" }));
    expect(screen.getByLabelText("Project name")).toHaveValue("");
    expect(screen.getByLabelText("What do you want to source?")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Create project" })).toBeEnabled();
    expect(writes).toBe(1);
    fireEvent.change(screen.getByLabelText("Project name"), { target: { value: "Different project" } });
    const newDraftReload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(newDraftReload);
    expect(newDraftReload.defaultPrevented).toBe(true);
  });

});
