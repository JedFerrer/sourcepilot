import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";
import { ProjectDashboard } from "./project-dashboard";
import { WorkflowSummary, workflowActions, WorkflowAction } from "../lib/workflow";
import { jsonResponse } from "../test/api-responses";
import { workflowFixture } from "../test/workflow-fixtures";

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

const brief = { product_name: "Desk lamp", category: "Lighting", quantity: 100,
  destination: "Manila", delivery_target: { kind: "DATE", date: "2027-01-01" }, target_unit_price: null,
  requirements: [], status: "APPROVED", missing_fields: [], uncertainties: [], brief_revision: 1,
  approved_at: "2026-10-04T00:00:00Z", can_analyze: false };
const supplier = { id: "a", name: "Supplier A", country: "PH", description: "Lighting",
  capabilities: [], general_moq: null, general_lead_time_days: null, indicative_price_amount: null,
  indicative_price_currency: null, shortlisted: true, dismissed: false, notes: null,
  stale: false, evaluated_against_brief_revision: 1, evaluations: [], derived_context: [],
  informational_requirements: [], evidence: [] };
const snapshot = { id: "snapshot", stale: false, generated_at: "2026-10-04T00:00:00Z",
  comparison_payload: { brief: { requirements: [] }, suppliers: [] } };
const project = (workflow: WorkflowSummary) => ({ id: "p", name: "Lamps", original_request: "Source lamps",
  stage: "QUOTES", preferred_supplier_id: null, preferred_supplier_name: null, decision_notes: null,
  created_at: "2026-10-04T00:00:00Z", updated_at: "2026-10-04T00:00:00Z", workflow });

function fixture(initial: WorkflowSummary) {
  let current = project(initial);
  const fetchMock = vi.fn((path: string, init?: RequestInit): Promise<Response> => {
    if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(brief));
    if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ brief_revision: 1,
      brief_approved: true, shortlist_approved: true, suppliers: [supplier] }));
    if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([]));
    if (path.endsWith("/comparison/generate")) {
      current = project({ ...initial, current_stage: "DECISION", comparison_present: true,
        next_action: { code: "RECORD_PREFERENCE", reason_code: "PREFERENCE_NOT_RECORDED", target_stage: "DECISION" } });
      return Promise.resolve(jsonResponse(snapshot));
    }
    if (path.endsWith("/comparison")) return Promise.resolve(jsonResponse(snapshot));
    if (path.endsWith("/preferred-supplier") && init?.method === "PUT") {
      const body = JSON.parse(String(init.body));
      return Promise.resolve(jsonResponse({ ...current, preferred_supplier_id: body.supplier_id,
        preferred_supplier_name: "Supplier A", decision_notes: body.decision_notes,
        workflow: { ...current.workflow, next_action: { code: "MANAGE_PREFERENCE",
          reason_code: "PREFERENCE_RECORDED", target_stage: "DECISION" } } }));
    }
    return Promise.resolve(jsonResponse(path === "/api/projects" ? [current] : current));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("M5-U2 workflow integration", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it.each(["COMPLETE_BRIEF", "APPROVE_BRIEF"] as const)("refreshes guidance to %s after request analysis without a reload", async (action) => {
    const empty = { ...brief, product_name: null, category: null, quantity: null,
      destination: null, delivery_target: null, status: "IN_PROGRESS", brief_revision: 0,
      approved_at: null, can_analyze: true, missing_fields: [] };
    const extracted = { ...brief, status: action === "COMPLETE_BRIEF" ? "IN_PROGRESS" : "READY_FOR_REVIEW",
      brief_revision: 1, approved_at: null, can_analyze: false,
      delivery_target: action === "COMPLETE_BRIEF" ? null : brief.delivery_target };
    const updated: WorkflowSummary = { ...workflowFixture("BRIEF"), next_action: {
      code: action, reason_code: action === "COMPLETE_BRIEF" ? "BRIEF_INCOMPLETE" : "BRIEF_APPROVAL_REQUIRED",
      target_stage: "BRIEF",
    } };
    let analyzed = false;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/brief/analyze") && init?.method === "POST") {
        analyzed = true;
        return Promise.resolve(jsonResponse(extracted));
      }
      return Promise.resolve(jsonResponse(
        path.endsWith("/brief") ? analyzed ? extracted : empty :
          path.endsWith("/suppliers") ? { suppliers: [], brief_approved: false, shortlist_approved: false } :
            path.endsWith("/quotes") ? [] : path.endsWith("/comparison") ? snapshot :
              project(analyzed ? updated : workflowFixture("BRIEF")),
      ));
    }));
    render(<ProjectWorkspace projectId="p" />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze request" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Analyze request" })).not.toBeInTheDocument());
    const next = within(screen.getByLabelText("Next action")).getByRole("link");
    await waitFor(() => expect(next).toHaveTextContent(`Next: ${workflowActions[action].label}`));
    expect(next).toHaveAttribute("href", `#${workflowActions[action].anchor}`);
    expect(document.getElementById(workflowActions[action].anchor)).toBeInTheDocument();
  });

  it("preserves quote drafts through focus prerequisite updates and isolates project visits", async () => {
    let summary = workflowFixture("QUOTES");
    const fetchMock = fixture(summary);
    const ordinary = fetchMock.getMockImplementation()!;
    const quote = { id: "quote-a", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
      revision: 1, confirmed_at: null, notes: "Saved A", values: {} };
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p") return Promise.resolve(jsonResponse(project(summary)));
      if (path === "/api/projects/other") return Promise.resolve(jsonResponse({ ...project(workflowFixture("QUOTES")), id: "other", name: "Other lamps" }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([{ ...quote,
        notes: path.includes("/other/") ? "Saved B" : "Saved A" }]));
      return ordinary(path, init);
    });
    const view = render(<ProjectWorkspace projectId="p" />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    const notes = screen.getByLabelText("Quote notes");
    fireEvent.change(notes, { target: { value: "UNSAVED FOCUS QUOTE" } });
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.75" } });
    summary = workflowFixture("BRIEF");
    fireEvent(window, new Event("focus"));
    await screen.findByText("Current stage: Brief");
    expect(screen.getByText("Approve the current shortlist before adding or reviewing quotes.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Quote notes" })).not.toBeInTheDocument();
    expect(within(screen.getByRole("navigation")).getByRole("link", { name: "Quotes" }).closest("li"))
      .toHaveAttribute("data-unavailable", "true");
    summary = workflowFixture("QUOTES");
    fireEvent(window, new Event("focus"));
    await screen.findByText("Current stage: Quotes");
    await waitFor(() => expect(screen.queryByText("Loading quotes…")).not.toBeInTheDocument());
    expect(screen.getByRole("textbox", { name: "Quote notes" })).toBe(notes);
    expect(notes).toHaveValue("UNSAVED FOCUS QUOTE");
    expect(screen.getByLabelText("Unit price")).toHaveValue(4.75);
    expect(screen.queryByText("Approve the current shortlist before adding or reviewing quotes.")).not.toBeInTheDocument();
    fireEvent(window, new Event("focus"));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => path === "/api/projects/p")).toHaveLength(4));
    expect(notes).toHaveValue("UNSAVED FOCUS QUOTE");

    view.rerender(<ProjectWorkspace projectId="other" />);
    await screen.findByRole("heading", { name: "Other lamps" });
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Saved B");
    expect(screen.getByLabelText("Unit price")).toHaveValue(null);
    view.rerender(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("heading", { name: "Lamps" });
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Saved A");
  });

  it("uses the server's five-stage summary and links to mounted existing controls without submitting", async () => {
    const summary = { ...workflowFixture("COMPARISON"), shortlist_count: 3, confirmed_quote_count: 2 };
    const fetchMock = fixture(summary);
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("Current stage: Comparison");
    const next = within(screen.getByLabelText("Next action")).getByRole("link");
    expect(next).toHaveAttribute("href", "#comparison-generate");
    expect(await screen.findByRole("button", { name: "Regenerate Comparison" })).toHaveAttribute("id", "comparison-generate");
    const stages = within(screen.getByRole("navigation", { name: "Sourcing workflow stages" }));
    for (const label of ["Brief", "Suppliers", "Quotes", "Comparison", "Decision"]) {
      const link = stages.getByRole("link", { name: label });
      const anchor = link.getAttribute("href")!;
      expect(document.querySelector(anchor)).toBeInTheDocument();
      fireEvent.click(link);
    }
    fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "Unsaved lamp" } });
    fireEvent.click(next);
    expect(screen.getByLabelText("Product name")).toHaveValue("Unsaved lamp");
    expect(fetchMock.mock.calls.every(([, init]) => !init?.method)).toBe(true);
  });

  it.each([
    ["ANALYZE_BRIEF", "BRIEF_ANALYSIS_AVAILABLE", "brief-analyze"],
    ["COMPLETE_BRIEF", "BRIEF_INCOMPLETE", "brief-complete"],
    ["APPROVE_BRIEF", "BRIEF_APPROVAL_REQUIRED", "brief-approve"],
  ] as const)("targets the existing Brief control for %s", async (code, reason, anchor) => {
    const summary = { ...workflowFixture(), next_action: { code, reason_code: reason, target_stage: "BRIEF" as const } };
    const fetchMock = fixture(summary);
    fetchMock.mockImplementation((path: string) => Promise.resolve(jsonResponse(
      path.endsWith("/brief") ? { ...brief, can_analyze: code === "ANALYZE_BRIEF",
        status: code === "APPROVE_BRIEF" ? "READY_FOR_REVIEW" : "IN_PROGRESS" } :
      path.endsWith("/suppliers") ? { suppliers: [], brief_approved: false } :
      path.endsWith("/quotes") ? [] : path.endsWith("/comparison") ? snapshot : project(summary),
    )));
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("Current stage: Brief");
    expect(within(screen.getByLabelText("Next action")).getByRole("link")).toHaveAttribute("href", `#${anchor}`);
    await waitFor(() => expect(document.getElementById(anchor)).toBeInTheDocument());
  });

  it("blocks generation from server prerequisites without blocking the human choice", async () => {
    const summary = { ...workflowFixture("QUOTES"), comparison_ready: false,
      stage_prerequisites: { ...workflowFixture("QUOTES").stage_prerequisites,
        COMPARISON: "INSUFFICIENT_CONFIRMED_QUOTES" as const } };
    fixture(summary);
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    await waitFor(() => expect(screen.getByRole("button", { name: "Regenerate Comparison" })).toBeDisabled());
    expect(within(screen.getByRole("navigation")).getByRole("link", { name: "Comparison" }).closest("li"))
      .toHaveAttribute("data-unavailable", "true");
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    expect(screen.getByRole("button", { name: "Mark as Preferred Supplier" })).toBeEnabled();
  });

  it("refreshes summary after generation while preserving unsaved Brief edits", async () => {
    fixture(workflowFixture("COMPARISON"));
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("Current stage: Comparison");
    fireEvent.change(await screen.findByLabelText("Product name"), { target: { value: "Draft" } });
    fireEvent.click(await screen.findByRole("button", { name: "Regenerate Comparison" }));
    await screen.findByText("Current stage: Decision");
    expect(screen.getByLabelText("Product name")).toHaveValue("Draft");
  });

  it("ignores older summary reads, preserves drafts on failure, and retries guidance", async () => {
    const initial = workflowFixture("QUOTES");
    const fetchMock = fixture(initial);
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveOlder!: (response: Response) => void;
    let resolveNewer!: (response: Response) => void;
    const older = new Promise<Response>((resolve) => { resolveOlder = resolve; });
    const newer = new Promise<Response>((resolve) => { resolveNewer = resolve; });
    let reads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p" && !init?.method) {
        reads += 1;
        if (reads === 2) return older;
        if (reads === 3) return newer;
        if (reads === 4) return Promise.resolve(jsonResponse({ error: { code: "UNAVAILABLE", message: "Unavailable" } }, 503));
      }
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("Current stage: Quotes");
    fireEvent.change(await screen.findByLabelText("Product name"), { target: { value: "Keep draft" } });
    fireEvent(window, new Event("focus"));
    fireEvent(window, new Event("focus"));
    await act(async () => resolveNewer(jsonResponse(project(workflowFixture("DECISION")))));
    await screen.findByText("Current stage: Decision");
    await act(async () => resolveOlder(jsonResponse(project(initial))));
    expect(screen.getByText("Current stage: Decision")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));
    await screen.findByText(/Progress guidance may be outdated/);
    expect(screen.queryByLabelText("Next action")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Product name")).toHaveValue("Keep draft");
    fireEvent.click(screen.getByRole("button", { name: "Refresh stage" }));
    await screen.findByLabelText("Next action");
  });

  it("renders dashboard counts and Comparison stage supplied by the server", async () => {
    fixture({ ...workflowFixture("COMPARISON"), shortlist_count: 3, confirmed_quote_count: 2 });
    render(<ProjectDashboard />);
    await screen.findByText("Lamps");
    expect(screen.getByText("Comparison", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("Shortlisted: 3 · Confirmed quotes: 2")).toBeInTheDocument();
    expect(screen.getByText("Comparison ready")).toBeInTheDocument();
    expect(screen.getByText("Next: Generate Comparison")).toBeInTheDocument();
  });

  it("does not let an initial read overwrite a newer focus refresh", async () => {
    const fetchMock = fixture(workflowFixture("QUOTES"));
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveInitial!: (response: Response) => void;
    const initial = new Promise<Response>((resolve) => { resolveInitial = resolve; });
    let reads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p") {
        reads += 1;
        return reads === 1 ? initial : Promise.resolve(jsonResponse(project(workflowFixture("DECISION"))));
      }
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    expect(screen.getByText("Loading project…")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));
    await screen.findByText("Current stage: Decision");
    await act(async () => resolveInitial(jsonResponse(project(workflowFixture("QUOTES")))));
    expect(screen.getByText("Current stage: Decision")).toBeInTheDocument();
  });

  it("defines one presentation anchor for every approved action", () => {
    const codes: WorkflowAction[] = ["ANALYZE_BRIEF", "COMPLETE_BRIEF", "APPROVE_BRIEF",
      "DISCOVER_SUPPLIERS", "REFRESH_SUPPLIERS", "REVIEW_SHORTLIST", "APPROVE_SHORTLIST",
      "COMPLETE_QUOTES", "GENERATE_COMPARISON", "REGENERATE_COMPARISON", "RECORD_PREFERENCE", "MANAGE_PREFERENCE"];
    expect(Object.keys(workflowActions).sort()).toEqual(codes.sort());
  });

  it("ignores A's late rename while B loads, including a superseding focus refresh", async () => {
    const fetchMock = fixture(workflowFixture("QUOTES"));
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveRename!: (response: Response) => void;
    const bReads: ((response: Response) => void)[] = [];
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p" && init?.method === "PATCH") {
        return new Promise<Response>((resolve) => { resolveRename = resolve; });
      }
      if (path === "/api/projects/b" && !init?.method) {
        return new Promise<Response>((resolve) => { bReads.push(resolve); });
      }
      return ordinary(path, init);
    });
    const { rerender } = render(<ProjectWorkspace projectId="p" />);
    await screen.findByText("Current stage: Quotes");
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Renamed A" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    rerender(<ProjectWorkspace projectId="b" />);
    await act(async () => resolveRename(jsonResponse({ ...project(workflowFixture("QUOTES")), name: "Renamed A" })));
    expect(screen.getByText("Loading project…")).toBeInTheDocument();
    fireEvent(window, new Event("focus"));
    const b = { ...project(workflowFixture("BRIEF")), id: "b", name: "Project B" };
    await act(async () => bReads[1](jsonResponse(b)));
    await screen.findByRole("heading", { name: "Project B" });
    expect(screen.getByText("Current stage: Brief")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save name" })).toBeEnabled();
    await act(async () => bReads[0](jsonResponse({ ...b, name: "Older B" })));
    expect(screen.getByRole("heading", { name: "Project B" })).toBeInTheDocument();
    expect(screen.queryByText("Renamed A")).not.toBeInTheDocument();
  });

  it("keeps newer upstream Brief guidance when an older decision response arrives", async () => {
    const fetchMock = fixture(workflowFixture("DECISION"));
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveDecision!: (response: Response) => void;
    let reads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path.endsWith("/preferred-supplier")) {
        return new Promise<Response>((resolve) => { resolveDecision = resolve; });
      }
      if (path === "/api/projects/p" && !init?.method && ++reads > 1) {
        return Promise.resolve(jsonResponse({ ...project(workflowFixture("BRIEF")),
          ...(reads > 2 ? { preferred_supplier_id: "a", preferred_supplier_name: "Supplier A", decision_notes: "Saved choice" } : {}) }));
      }
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Saved choice" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    fireEvent(window, new Event("focus"));
    await screen.findByText("Current stage: Brief");
    await act(async () => resolveDecision(jsonResponse({ ...project(workflowFixture("DECISION")),
      preferred_supplier_id: "a", preferred_supplier_name: "Supplier A", decision_notes: "Saved choice" })));
    expect(screen.getByText("Current stage: Brief")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Next action")).getByRole("link")).toHaveAttribute("href", "#brief-analyze");
    expect(screen.getByText("Preferred supplier: Supplier A")).toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Saved choice");
    expect(screen.getByText("Preferred supplier saved.")).toBeInTheDocument();
  });
  it.each(["DECISION", "BRIEF"] as const)("reconciles decision-save-before-focus-read with %s guidance", async (stage) => {
    const fetchMock = fixture(workflowFixture("DECISION"));
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveDecision!: (response: Response) => void;
    const reads: ((response: Response) => void)[] = [];
    let projectReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path.endsWith("/preferred-supplier")) return new Promise<Response>((resolve) => { resolveDecision = resolve; });
      if (path === "/api/projects/p" && !init?.method && ++projectReads > 1) {
        return new Promise<Response>((resolve) => { reads.push(resolve); });
      }
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Saved choice" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    fireEvent(window, new Event("focus"));
    const workflow = stage === "BRIEF" ? workflowFixture("BRIEF") : {
      ...workflowFixture("DECISION"), next_action: { code: "MANAGE_PREFERENCE" as const,
        reason_code: "PREFERENCE_RECORDED" as const, target_stage: "DECISION" as const },
    };
    const saved = { ...project(workflow), preferred_supplier_id: "a", preferred_supplier_name: "Supplier A", decision_notes: "Saved choice" };
    await act(async () => resolveDecision(jsonResponse(saved)));
    expect(screen.getByText(/Progress guidance may be outdated/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Next action")).not.toBeInTheDocument();
    // The overlapping GET can still contain a pre-save snapshot.
    await act(async () => reads[0](jsonResponse(project(workflowFixture(stage)))));
    expect(screen.getByText(/Progress guidance may be outdated/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Next action")).not.toBeInTheDocument();
    expect(reads).toHaveLength(2);
    await act(async () => reads[1](jsonResponse(saved)));
    expect(screen.getByText(`Current stage: ${stage === "BRIEF" ? "Brief" : "Decision"}`)).toBeInTheDocument();
    expect(within(screen.getByLabelText("Next action")).getByRole("link")).toHaveAttribute("href", stage === "BRIEF" ? "#brief-analyze" : "#decision-choice");
    expect(screen.queryByText(/Progress guidance may be outdated/)).not.toBeInTheDocument();
    expect(screen.getByText("Preferred supplier: Supplier A")).toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Saved choice");
  });

  it.each(["select", "change", "clear"] as const)("reconciles pre-save focus guidance before a delayed decision %s completes", async (operation) => {
    const initialWorkflow = workflowFixture("DECISION");
    const managedWorkflow: WorkflowSummary = { ...initialWorkflow, next_action: {
      code: "MANAGE_PREFERENCE", reason_code: "PREFERENCE_RECORDED", target_stage: "DECISION",
    } };
    const initial = operation === "select" ? project(initialWorkflow) : {
      ...project(managedWorkflow), preferred_supplier_id: "old", preferred_supplier_name: "Old supplier", decision_notes: "Old notes",
    };
    const saved = { ...initial, preferred_supplier_id: operation === "clear" ? null : "a",
      preferred_supplier_name: operation === "clear" ? null : "Supplier A", decision_notes: "Saved choice",
      workflow: operation === "clear" ? initialWorkflow : managedWorkflow };
    const fetchMock = fixture(initial.workflow);
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveDecision!: (response: Response) => void;
    const reads: ((response: Response) => void)[] = [];
    let projectReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path.endsWith("/preferred-supplier")) return new Promise<Response>((resolve) => { resolveDecision = resolve; });
      if (path === "/api/projects/p" && !init?.method) {
        if (++projectReads === 1) return Promise.resolve(jsonResponse(initial));
        return new Promise<Response>((resolve) => { reads.push(resolve); });
      }
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("option", { name: "Supplier A" });
    if (operation !== "clear") fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Saved choice" } });
    fireEvent.click(screen.getByRole("button", { name: operation === "clear" ? "Clear preferred supplier" : "Mark as Preferred Supplier" }));
    fireEvent(window, new Event("focus"));
    await act(async () => reads[0](jsonResponse(initial)));
    expect(screen.getByLabelText("Next action")).toBeInTheDocument();
    await act(async () => resolveDecision(jsonResponse(saved)));
    expect(screen.getByText(/Progress guidance may be outdated/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Next action")).not.toBeInTheDocument();
    expect(screen.getByText(`Preferred supplier: ${saved.preferred_supplier_name ?? "No Decision Yet"}`)).toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Saved choice");
    expect(reads).toHaveLength(2);
    await act(async () => reads[1](jsonResponse(saved)));
    expect(within(screen.getByLabelText("Next action")).getByRole("link")).toHaveTextContent(
      workflowActions[saved.workflow.next_action.code].label,
    );
    expect(screen.queryByText(/Progress guidance may be outdated/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Saved choice");
  });

  it.each(["rename-first", "read-first"] as const)("applies a successful rename after an unchanged pre-save read with %s request start", async (order) => {
    const summary = workflowFixture("QUOTES");
    const fetchMock = fixture(summary);
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveRename!: (response: Response) => void;
    let resolveRead!: (response: Response) => void;
    let projectReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p" && init?.method === "PATCH") return new Promise<Response>((resolve) => { resolveRename = resolve; });
      if (path === "/api/projects/p" && !init?.method && ++projectReads > 1) return new Promise<Response>((resolve) => { resolveRead = resolve; });
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("heading", { name: "Lamps" });
    if (order === "read-first") fireEvent(window, new Event("focus"));
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Renamed lamps" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    if (order === "rename-first") fireEvent(window, new Event("focus"));
    await act(async () => resolveRead(jsonResponse(project(summary))));
    expect(screen.getByRole("heading", { name: "Lamps" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Saving/ })).toBeDisabled();
    await act(async () => resolveRename(jsonResponse({ ...project(summary), name: "Renamed lamps" })));
    expect(screen.getByRole("heading", { name: "Renamed lamps" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save name" })).toBeEnabled();
  });

  it.each(["rename-first", "refresh-first"] as const)("protects accepted same-visit names with %s completion", async (order) => {
    const summary = workflowFixture("QUOTES");
    const fetchMock = fixture(summary);
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveRename!: (response: Response) => void;
    const reads: ((response: Response) => void)[] = [];
    let projectReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p" && init?.method === "PATCH") return new Promise<Response>((resolve) => { resolveRename = resolve; });
      if (path === "/api/projects/p" && !init?.method && ++projectReads > 1) return new Promise<Response>((resolve) => { reads.push(resolve); });
      return ordinary(path, init);
    });
    render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("heading", { name: "Lamps" });
    if (order === "rename-first") fireEvent(window, new Event("focus"));
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Renamed lamps" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    if (order === "refresh-first") fireEvent(window, new Event("focus"));
    const rename = jsonResponse({ ...project(summary), name: "Renamed lamps" });
    const refresh = jsonResponse({ ...project(summary), name: order === "rename-first" ? "Lamps" : "Newer external name" });
    if (order === "rename-first") {
      await act(async () => resolveRename(rename));
      await screen.findByRole("heading", { name: "Renamed lamps" });
      await act(async () => reads[0](refresh));
    } else {
      await act(async () => reads[0](refresh));
      await screen.findByRole("heading", { name: "Newer external name" });
      await act(async () => resolveRename(rename));
    }
    expect(screen.getByRole("heading", { name: order === "rename-first" ? "Renamed lamps" : "Newer external name" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save name" })).toBeEnabled();
    // A read started after the accepted name data is legitimate and must still apply.
    fireEvent(window, new Event("focus"));
    await act(async () => reads[1](jsonResponse({ ...project(summary), name: "Latest refreshed name" })));
    expect(screen.getByRole("heading", { name: "Latest refreshed name" })).toBeInTheDocument();
  });

  it.each(["initial", "focus"])("ignores A's delayed Brief callback while B's %s read is pending", async (read) => {
    const fetchMock = fixture(workflowFixture("QUOTES"));
    const ordinary = fetchMock.getMockImplementation()!;
    let resolveSave!: (response: Response) => void;
    let resolveB!: (response: Response) => void;
    const b = { ...project(workflowFixture("BRIEF")), id: "b", name: "Project B" };
    let bReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p/brief" && init?.method === "PATCH") return new Promise<Response>((resolve) => { resolveSave = resolve; });
      if (path === "/api/projects/b" && !init?.method) {
        bReads += 1;
        if (read === "focus" && bReads === 1) return Promise.resolve(jsonResponse(b));
        return new Promise<Response>((resolve) => { resolveB = resolve; });
      }
      return ordinary(path, init);
    });
    const { rerender } = render(<ProjectWorkspace projectId="p" />);
    fireEvent.click(await screen.findByRole("button", { name: "Save Brief" }));
    rerender(<ProjectWorkspace projectId="b" />);
    if (read === "focus") {
      await screen.findByRole("heading", { name: "Project B" });
      fireEvent(window, new Event("focus"));
    }
    const requestsBefore = fetchMock.mock.calls.length;
    await act(async () => resolveSave(jsonResponse({ ...brief, brief_revision: 2 })));
    expect(fetchMock.mock.calls).toHaveLength(requestsBefore);
    await act(async () => resolveB(jsonResponse(b)));
    expect(screen.getByRole("heading", { name: "Project B" })).toBeInTheDocument();
    expect(screen.getByText("Current stage: Brief")).toBeInTheDocument();
  });

  it.each(["success", "error"])("isolates an old A rename %s after A to B to A with a newer rename pending", async (outcome) => {
    const fetchMock = fixture(workflowFixture("QUOTES"));
    const ordinary = fetchMock.getMockImplementation()!;
    const renames: ((response: Response) => void)[] = [];
    let aReads = 0;
    fetchMock.mockImplementation((path, init) => {
      if (path === "/api/projects/p" && init?.method === "PATCH") return new Promise<Response>((resolve) => { renames.push(resolve); });
      if (path === "/api/projects/p" && !init?.method && ++aReads > 1) return Promise.resolve(jsonResponse({ ...project(workflowFixture("QUOTES")), name: "Reloaded A" }));
      if (path === "/api/projects/b" && !init?.method) return Promise.resolve(jsonResponse({ ...project(workflowFixture("BRIEF")), id: "b", name: "Project B" }));
      return ordinary(path, init);
    });
    const { rerender } = render(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("heading", { name: "Lamps" });
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Old A" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    rerender(<ProjectWorkspace projectId="b" />);
    await screen.findByRole("heading", { name: "Project B" });
    rerender(<ProjectWorkspace projectId="p" />);
    await screen.findByRole("heading", { name: "Reloaded A" });
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "New A" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));
    await act(async () => renames[0](outcome === "success"
      ? jsonResponse({ ...project(workflowFixture("QUOTES")), name: "Old A" })
      : jsonResponse({ error: { code: "UNAVAILABLE", message: "Old rename error" } }, 503)));
    expect(screen.getByRole("heading", { name: "Reloaded A" })).toBeInTheDocument();
    expect(screen.queryByText("Old rename error")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Saving/ })).toBeDisabled();
    expect(renames).toHaveLength(2);
    await act(async () => renames[1](jsonResponse({ ...project(workflowFixture("QUOTES")), name: "New A" })));
    expect(screen.getByRole("heading", { name: "New A" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save name" })).toBeEnabled();
  });

});
