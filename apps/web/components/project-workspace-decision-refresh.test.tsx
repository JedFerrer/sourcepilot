import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";
import { workspaceFixtureResponse as jsonResponse } from "../test/workflow-fixtures";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("./brief-editor", () => ({ BriefEditor: ({ onProjectChange }: { onProjectChange: () => Promise<void> }) => <button onClick={() => void onProjectChange()}>Refresh project fixture</button> }));
vi.mock("./quote-review", () => ({ QuoteReview: () => null }));
vi.mock("./comparison-review", () => ({ ComparisonReview: () => <p>Existing comparison</p> }));

const emptyProject = {
  id: "p", name: "Project", original_request: "Source", stage: "SUPPLIERS",
  preferred_supplier_id: null as string | null, preferred_supplier_name: null as string | null,
  decision_notes: null as string | null,
};
const supplier = {
  id: "a", name: "Supplier A", country: "Vietnam", description: "Bags", capabilities: [],
  general_moq: 1000, general_lead_time_days: 30, indicative_price_amount: null,
  indicative_price_currency: null, shortlisted: false, dismissed: false, notes: null,
  stale: false, evaluated_against_brief_revision: 1, evaluations: [], derived_context: [],
  informational_requirements: [], evidence: [],
};

function fixture({ shortlisted = false, preferred = false } = {}) {
  let project = preferred ? { ...emptyProject, preferred_supplier_id: "a", preferred_supplier_name: "Supplier A", decision_notes: "Original" } : { ...emptyProject };
  let pendingPath: "rename" | "refresh" | null = null;
  let resolveOlder!: (response: Response) => void;
  const pending = new Promise<Response>((resolve) => { resolveOlder = resolve; });
  const list = () => ({ brief_revision: 1, brief_approved: true, shortlist_approved: false, suppliers: [{ ...supplier, shortlisted }] });
  const fetchMock = vi.fn((path: string, init?: RequestInit): Promise<Response> => {
    if (path.endsWith("/suppliers/a") && init?.method === "PATCH") {
      const body = JSON.parse(String(init.body)) as { shortlisted: boolean };
      shortlisted = body.shortlisted;
      return Promise.resolve(jsonResponse(list()));
    }
    if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse(list()));
    if (init?.method === "PUT") {
      const body = JSON.parse(String(init.body)) as { supplier_id: string | null; decision_notes: string };
      project = { ...project, preferred_supplier_id: body.supplier_id,
        preferred_supplier_name: body.supplier_id === "a" ? "Supplier A" : null,
        decision_notes: body.decision_notes.trim() || null };
      return Promise.resolve(jsonResponse(project));
    }
    if ((pendingPath === "rename" && init?.method === "PATCH") || (pendingPath === "refresh" && path === "/api/projects/p" && !init?.method)) {
      pendingPath = null;
      return pending;
    }
    return Promise.resolve(jsonResponse(project));
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, startOlder: (path: "rename" | "refresh") => { pendingPath = path; },
    finishOlder: () => resolveOlder(jsonResponse({ ...emptyProject, name: "Older response project", stage: "QUOTES" })) };
}

describe("Workspace decision review regressions", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("updates Decision options after ordinary shortlist addition and removal before approval", async () => {
    fixture();
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("No shortlisted suppliers are available for a new selection.");
    fireEvent.click(screen.getByRole("button", { name: "Add to shortlist" }));
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.click(screen.getByRole("button", { name: "Remove from shortlist" }));
    await waitFor(() => expect(screen.queryByRole("option", { name: "Supplier A" })).not.toBeInTheDocument());
    expect(screen.getByText("No shortlisted suppliers are available for a new selection.")).toBeInTheDocument();
    expect(screen.getByText("Current stage: Suppliers")).toBeInTheDocument();
  });

  it("warns after removing the saved preference and retains notes editing with an empty shortlist", async () => {
    const { fetchMock } = fixture({ shortlisted: true, preferred: true });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.click(screen.getByRole("button", { name: "Remove from shortlist" }));
    await screen.findByText(/saved preferred supplier is no longer shortlisted/);
    expect(screen.queryByRole("option", { name: "Supplier A" })).not.toBeInTheDocument();
    expect(screen.getByText("Preferred supplier: Supplier A")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Retained notes" } });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    expect(fetchMock).toHaveBeenLastCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ body: JSON.stringify({ supplier_id: "a", decision_notes: "Retained notes" }) }));
  });

  it.each(["rename", "refresh"] as const)("preserves a newer decision and notes save after an older %s response", async (path) => {
    const { fetchMock, startOlder, finishOlder } = fixture({ shortlisted: true });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    startOlder(path);
    fireEvent.click(screen.getByRole("button", { name: path === "rename" ? "Save name" : "Refresh project fixture" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([url, init]) => url === "/api/projects/p" && (path === "rename" ? init?.method === "PATCH" : !init?.method))).toHaveLength(path === "rename" ? 1 : 2));
    await waitFor(() => expect(screen.getByLabelText("Preferred supplier")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "New decision notes" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await screen.findByText("Preferred supplier: Supplier A");
    await act(async () => finishOlder());
    expect(screen.getByRole("heading", { name: path === "refresh" ? "Project" : "Older response project" })).toBeInTheDocument();
    expect(screen.getByText("Current stage: Suppliers")).toBeInTheDocument();
    expect(screen.getByText("Preferred supplier: Supplier A")).toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("New decision notes");
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    expect(fetchMock).toHaveBeenLastCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ body: JSON.stringify({ supplier_id: "a", decision_notes: "New decision notes" }) }));
  });
});
