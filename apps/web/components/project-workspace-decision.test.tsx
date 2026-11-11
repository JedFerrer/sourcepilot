import { viewStage } from "../test/workspace-navigation";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";
import { workspaceFixtureResponse as jsonResponse } from "../test/workflow-fixtures";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("./brief-editor", () => ({ BriefEditor: () => null }));
vi.mock("./supplier-review", () => ({ SupplierReview: () => null }));
vi.mock("./quote-review", () => ({ QuoteReview: () => null }));

const supplier = (id: string, name: string) => ({
  supplier_id: id, supplier_name: name, quote_id: `quote-${id}`, quote_fields: [],
  resolved_facts: {}, evaluation: { results: [], informational_requirement_ids: [], warnings: [] },
  completeness: [], supplier_facts: { evidence: [] },
});
const comparison = {
  id: "snapshot", stale: false, generated_at: "2026-10-03T00:00:00Z",
  comparison_payload: { brief: { requirements: [] }, suppliers: [supplier("a", "Supplier A"), supplier("c", "Supplier C")] },
};
const point = { text: "Review Supplier A's tradeoffs.", supplier_ids: ["a"], requirement_ids: [], quote_fields: [], evidence_ids: [] };
const advice = {
  run_id: "run", snapshot_id: "snapshot",
  analysis: { supplier_summaries: [point], key_tradeoffs: [], important_unknowns: [], important_conflicts: [] },
  suggestion: { supplier_id: "a", supporting_reasons: [point], tradeoffs: [], uncertainties: [], evidence_ids: [] },
};

describe("Workspace decision with existing ComparisonReview", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("allows disagreement with advice and retains it through selection, notes save, and clear", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/comparison/advice")) return Promise.resolve(jsonResponse(advice));
      if (path.endsWith("/comparison")) return Promise.resolve(jsonResponse(comparison));
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [
        { id: "a", name: "Supplier A", shortlisted: true }, { id: "c", name: "Supplier C", shortlisted: true },
      ] }));
      const project = { id: "p", name: "Project", original_request: "Source", stage: "QUOTES", preferred_supplier_id: null, preferred_supplier_name: null, decision_notes: null };
      if (init?.method === "PUT") {
        const body = JSON.parse(String(init.body)) as { supplier_id: string | null; decision_notes: string };
        return Promise.resolve(jsonResponse({ ...project, preferred_supplier_id: body.supplier_id,
          preferred_supplier_name: body.supplier_id === "c" ? "Supplier C" : null,
          decision_notes: body.decision_notes || null }));
      }
      return Promise.resolve(jsonResponse(project));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProjectWorkspace projectId="p" />);
    await viewStage("Comparison");
    await screen.findByText("Comparison is current.");
    fireEvent.click(screen.getByRole("button", { name: "Analyze Comparison" }));
    const region = await screen.findByRole("region", { name: "Comparison analysis" });
    expect(within(region).getByText("Supplier A", { selector: "strong" })).toBeInTheDocument();
    await viewStage("Decision");
    expect(screen.getByLabelText("Preferred supplier")).toHaveValue("");
    const reads = fetchMock.mock.calls.filter(([path]) => path.endsWith("/comparison")).length;
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "c" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    fireEvent.click(screen.getByRole("button", { name: "Save preferred supplier" }));
    await screen.findByText("Supplier C", { selector: ".project-context strong" });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "My own choice" } });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    fireEvent.click(screen.getByRole("button", { name: "Clear preferred supplier" }));
    await screen.findByText("Preferred supplier cleared.");
    await viewStage("Comparison");
    await waitFor(() => expect(screen.getByRole("region", { name: "Comparison analysis" })).toBe(region));
    expect(within(region).getByText("Supplier A", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByText("Comparison is current.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/comparison"))).toHaveLength(reads);
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/comparison/advice"))).toHaveLength(1);
  });
});
