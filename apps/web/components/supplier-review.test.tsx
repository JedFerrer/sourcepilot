import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SupplierReview } from "./supplier-review";
import { jsonResponse } from "../test/api-responses";

const supplier = {
  id: "supplier-1", name: "Harbor Pouch Works", country: "Vietnam", description: "Bags",
  capabilities: [{ kind: "MATERIAL", value: "recycled polyester" }],
  general_moq: 1000, general_lead_time_days: 30,
  indicative_price_amount: null, indicative_price_currency: null,
  shortlisted: false, dismissed: false, notes: null, stale: false,
  evaluated_against_brief_revision: 1,
  evaluations: [{ requirement_id: "req-1", kind: "MATERIAL", importance: "REQUIRED",
    expected_value: { value: "recycled polyester" }, status: "MEETS", evidence_ids: ["evidence-1"] }],
  derived_context: [{ kind: "MOQ", status: "MEETS", evidence_ids: [] }],
  informational_requirements: [],
  evidence: [{ id: "evidence-1", claim_key: "material:recycled polyester", source_label: "Catalog record",
    source_reference: null, evidence_text: "Uses recycled polyester", evidence_state: "SUPPORTS" }],
};

describe("SupplierReview", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it("explains successful empty discovery, links to Brief without writing, and recovers candidates", async () => {
    let candidates = false;
    let fail = false;
    const fetchMock = vi.fn((path: string) => Promise.resolve(
      fail && path.endsWith("/discover") ? jsonResponse({ error: { code: "UNAVAILABLE", message: "Try again." } }, 503) :
        jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: candidates ? [supplier] : [] }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText(/No supplier candidates to review yet/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Discover Suppliers" }));
    expect(await screen.findByText(/No supplier candidates were found in the curated dataset/)).toBeInTheDocument();
    const calls = fetchMock.mock.calls.length;
    const link = screen.getByRole("link", { name: "Review Brief" });
    expect(link).toHaveAttribute("href", "#brief-complete");
    fireEvent.click(link);
    expect(fetchMock).toHaveBeenCalledTimes(calls);
    fail = true;
    fireEvent.click(screen.getByRole("button", { name: "Discover Suppliers" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again.");
    expect(screen.queryByText(/No supplier candidates were found/)).not.toBeInTheDocument();
    fail = false;
    candidates = true;
    fireEvent.click(screen.getByRole("button", { name: "Discover Suppliers" }));
    expect(await screen.findByText(supplier.name)).toBeInTheDocument();
    expect(screen.queryByText(/No supplier candidates/)).not.toBeInTheDocument();
  });

  it.each(["refresh", "project"])("clears an empty outcome on %s and preserves Brief approval gating", async (change) => {
    let approved = true;
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      brief_revision: approved ? 1 : 2, brief_approved: approved, suppliers: [],
    }))));
    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Discover Suppliers" }));
    expect(await screen.findByText(/No supplier candidates were found/)).toBeInTheDocument();
    approved = false;
    view.rerender(<SupplierReview projectId={change === "project" ? "project-2" : "project-1"} refreshKey={1} />);
    expect(await screen.findByText(/No supplier candidates to review yet/)).toBeInTheDocument();
    expect(screen.queryByText(/No supplier candidates were found/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Discover Suppliers" })).not.toBeInTheDocument();
    expect(screen.getByText("Approve the Brief to discover or re-evaluate suppliers.")).toBeInTheDocument();
  });

  it("does not publish a late empty discovery after a Brief refresh", async () => {
    let resolveDiscovery: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveDiscovery = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/discover") ? pending :
      Promise.resolve(jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [] }))));
    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Discover Suppliers" }));
    view.rerender(<SupplierReview projectId="project-1" refreshKey={1} />);
    await act(async () => { resolveDiscovery!(jsonResponse({ brief_revision: 1, suppliers: [] })); });
    expect(screen.queryByText(/No supplier candidates were found/)).not.toBeInTheDocument();
    expect(screen.getByText(/No supplier candidates to review yet/)).toBeInTheDocument();
  });

  it("shows current requirement findings and evidence and saves review choices", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => Promise.resolve(
      jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [
        path.endsWith("/supplier-1") && init?.method === "PATCH" ? { ...supplier, shortlisted: true } : supplier,
      ] }),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Harbor Pouch Works")).toBeInTheDocument();
    expect(screen.getByText("MEETS", { selector: "strong" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("Available evidence"));
    expect(screen.getByText(/Uses recycled polyester/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add to shortlist" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/suppliers/supplier-1", expect.objectContaining({ method: "PATCH" }),
    ));
    expect(await screen.findByRole("button", { name: "Remove from shortlist" })).toBeInTheDocument();
  });

  it("hides old requirement findings, warns, and refreshes the candidates", async () => {
    let refreshed = false;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/discover") && init?.method === "POST") {
        refreshed = true;
        return Promise.resolve(jsonResponse({ brief_revision: 2, suppliers: [] }));
      }
      return Promise.resolve(jsonResponse({ brief_revision: 2, brief_approved: true, suppliers: [
        { ...supplier, stale: !refreshed },
      ] }));
    }));
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText(/Your sourcing requirements changed/)).toBeInTheDocument();
    expect(screen.queryByText("MEETS", { selector: "strong" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Explain this supplier" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Re-discover and re-evaluate" }));
    expect(await screen.findByText("MEETS", { selector: "strong" })).toBeInTheDocument();
  });

  it("never presents old findings as current when a Brief-triggered reload fails", async () => {
    let rejectReload: (reason: Error) => void;
    const failedReload = new Promise<Response>((_, reject) => { rejectReload = reject; });
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [supplier] }))
      .mockReturnValueOnce(failedReload);
    vi.stubGlobal("fetch", fetchMock);

    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("MEETS", { selector: "strong" })).toBeInTheDocument();

    view.rerender(<SupplierReview projectId="project-1" refreshKey={1} />);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("MEETS", { selector: "strong" })).not.toBeInTheDocument();

    await act(async () => { rejectReload!(new Error("Network unavailable")); });
    expect(await screen.findByRole("alert")).toHaveTextContent("We could not reach SourcePilot. Please try again.");
    expect(screen.queryByText("MEETS", { selector: "strong" })).not.toBeInTheDocument();
    expect(screen.queryByText("Harbor Pouch Works")).not.toBeInTheDocument();
  });

  it("keeps the newest supplier response when reloads resolve out of order", async () => {
    const pending: Array<(value: Response) => void> = [];
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => pending.push(resolve))));
    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(pending).toHaveLength(1);

    view.rerender(<SupplierReview projectId="project-1" refreshKey={1} />);
    expect(pending).toHaveLength(2);
    await act(async () => {
      pending[1](jsonResponse({ brief_revision: 2, brief_approved: true, suppliers: [
        { ...supplier, name: "Current Supplier", stale: true, evaluations: [] },
      ] }));
    });
    expect(screen.getByText("Current Supplier")).toBeInTheDocument();
    expect(screen.getByText(/Your sourcing requirements changed/)).toBeInTheDocument();

    await act(async () => {
      pending[0](jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [supplier] }));
    });
    expect(screen.getByText("Current Supplier")).toBeInTheDocument();
    expect(screen.queryByText("Harbor Pouch Works")).not.toBeInTheDocument();
    expect(screen.getByText(/Your sourcing requirements changed/)).toBeInTheDocument();
  });

  it("generates an on-demand explanation with cited evidence and no internal trace", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/explanation") && init?.method === "POST") {
        return Promise.resolve(jsonResponse({ run_id: "run-1", explanation: {
          supplier_id: supplier.id,
          strengths: [{ text: "Recycled polyester is supported.", requirement_id: "req-1", evidence_ids: ["evidence-1"] }],
          required_failures: [], preferred_findings: [], unknowns: [], conflicts: [], concerns: [],
          evidence_ids: ["evidence-1"],
        } }));
      }
      return Promise.resolve(jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [supplier] }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Explain this supplier" }));
    expect(await screen.findByText(/Recycled polyester is supported/)).toBeInTheDocument();
    expect(screen.getAllByText(/Evidence: Catalog record/)).toHaveLength(2);
    expect(screen.queryByText("run-1")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/projects/project-1/suppliers/supplier-1/explanation",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("offers retry on explanation failure and clears the result after a Brief refresh", async () => {
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/explanation") && init?.method === "POST") {
        attempts += 1;
        if (attempts === 1) return Promise.resolve(jsonResponse({ error: { code: "SUPPLIER_EXPLANATION_UNAVAILABLE", message: "Try again." } }, 503));
        return Promise.resolve(jsonResponse({ run_id: "run-2", explanation: {
          supplier_id: supplier.id, strengths: [{ text: "Supported material.", requirement_id: "req-1", evidence_ids: ["evidence-1"] }],
          required_failures: [], preferred_findings: [], unknowns: [], conflicts: [], concerns: [], evidence_ids: ["evidence-1"],
        } }));
      }
      return Promise.resolve(jsonResponse({ brief_revision: 1, brief_approved: true, suppliers: [supplier] }));
    }));
    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Explain this supplier" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again.");
    fireEvent.click(screen.getByRole("button", { name: "Retry explanation" }));
    expect(await screen.findByText(/Supported material/)).toBeInTheDocument();
    view.rerender(<SupplierReview projectId="project-1" refreshKey={1} />);
    await waitFor(() => expect(screen.queryByText(/Supported material/)).not.toBeInTheDocument());
    expect(await screen.findByRole("button", { name: "Explain this supplier" })).toBeInTheDocument();
  });

  it("shows loading and does not reveal an in-flight result after the Brief becomes stale", async () => {
    let resolveExplanation: (value: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveExplanation = resolve; });
    let revision = 1;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/explanation") && init?.method === "POST") return pending;
      return Promise.resolve(jsonResponse({
        brief_revision: revision, brief_approved: true,
        suppliers: [{ ...supplier, stale: revision > 1 }],
      }));
    }));
    const view = render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Explain this supplier" }));
    expect(screen.getByText(/Preparing an evidence-backed explanation/)).toBeInTheDocument();
    revision = 2;
    view.rerender(<SupplierReview projectId="project-1" refreshKey={1} />);
    expect(await screen.findByText(/Your sourcing requirements changed/)).toBeInTheDocument();
    await act(async () => { resolveExplanation!(jsonResponse({ run_id: "old-run", explanation: {
      supplier_id: supplier.id, strengths: [{ text: "Old result", requirement_id: "req-1", evidence_ids: [] }],
      required_failures: [], preferred_findings: [], unknowns: [], conflicts: [], concerns: [], evidence_ids: [],
    } })); });
    expect(screen.queryByText("Old result")).not.toBeInTheDocument();
  });

  it("refreshes supplier staleness when explanation request detects a changed Brief", async () => {
    let stale = false;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/explanation") && init?.method === "POST") {
        stale = true;
        return Promise.resolve(jsonResponse({ error: {
          code: "SUPPLIER_EVALUATION_STALE", message: "Refresh supplier evaluations.",
        } }, 409));
      }
      return Promise.resolve(jsonResponse({
        brief_revision: stale ? 2 : 1, brief_approved: true,
        suppliers: [{ ...supplier, stale }],
      }));
    }));
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Explain this supplier" }));
    expect(await screen.findByText(/Your sourcing requirements changed/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Explain this supplier" })).not.toBeInTheDocument();
    expect(screen.queryByText("Supplier explanation")).not.toBeInTheDocument();
  });

  it("reviews current findings and requires explicit approval after dismiss and restore", async () => {
    let shortlisted = false;
    let dismissed = false;
    let approved = false;
    const onStageChange = vi.fn().mockResolvedValue(undefined);
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/shortlist/approve") && init?.method === "POST") approved = true;
      if (path.endsWith("/supplier-1") && init?.method === "PATCH") {
        const change = JSON.parse(String(init.body));
        if ("shortlisted" in change) shortlisted = change.shortlisted;
        if ("dismissed" in change) {
          dismissed = change.dismissed;
          if (dismissed) shortlisted = false;
        }
        if (!shortlisted) approved = false;
      }
      return Promise.resolve(jsonResponse({
        brief_revision: 1, brief_approved: true, shortlist_approved: approved,
        suppliers: [{ ...supplier, shortlisted, dismissed }],
      }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SupplierReview projectId="project-1" refreshKey={0} onStageChange={onStageChange} />);
    await screen.findByText("Harbor Pouch Works");
    fireEvent.click(screen.getByRole("button", { name: "Add to shortlist" }));
    expect(await screen.findByText(/1 selected/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review selected suppliers" }));
    expect(screen.getByLabelText("Harbor Pouch Works approval details")).toHaveTextContent("REQUIRED: MATERIAL recycled polyester — MEETS");
    fireEvent.click(screen.getByRole("button", { name: "Continue Reviewing" }));
    expect(screen.queryByText("Review before approval")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review selected suppliers" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve Shortlist" }));
    expect(await screen.findByText(/Shortlist approved/)).toBeInTheDocument();
    expect(onStageChange).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(await screen.findByRole("button", { name: "Restore" })).toBeInTheDocument();
    expect(screen.queryByText(/Shortlist approved/)).not.toBeInTheDocument();
    expect(onStageChange).toHaveBeenCalledTimes(2);
    fireEvent.click(screen.getByRole("button", { name: "Restore" }));
    expect(await screen.findByRole("button", { name: "Add to shortlist" })).toBeInTheDocument();
    expect(screen.queryByText(/Shortlist approved/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Add to shortlist" }));
    expect(await screen.findByRole("button", { name: "Remove from shortlist" })).toBeInTheDocument();
    expect(screen.queryByText(/Shortlist approved/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review selected suppliers" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve Shortlist" }));
    expect(await screen.findByText(/Shortlist approved/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/shortlist/approve"))).toHaveLength(2);
  });

  it("labels only an in-flight approval as Approving while re-discovery keeps approval disabled", async () => {
    let resolveDiscovery!: (value: Response) => void;
    let resolveApproval!: (value: Response) => void;
    const discovery = new Promise<Response>((resolve) => { resolveDiscovery = resolve; });
    const approval = new Promise<Response>((resolve) => { resolveApproval = resolve; });
    const list = { brief_revision: 1, brief_approved: true, shortlist_approved: false,
      suppliers: [{ ...supplier, shortlisted: true }] };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/discover") && init?.method === "POST") return discovery;
      if (path.endsWith("/shortlist/approve") && init?.method === "POST") return approval;
      return Promise.resolve(jsonResponse(list));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Review selected suppliers" }));
    fireEvent.click(screen.getByRole("button", { name: "Re-discover and re-evaluate" }));
    expect(screen.getByRole("button", { name: "Approve Shortlist" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Approving…" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/shortlist/approve"))).toHaveLength(0);

    await act(async () => { resolveDiscovery(jsonResponse({})); });
    expect(screen.getByRole("button", { name: "Approve Shortlist" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Approve Shortlist" }));
    expect(screen.getByRole("button", { name: "Approving…" })).toBeDisabled();
    await act(async () => { resolveApproval(jsonResponse({ ...list, shortlist_approved: true })); });
    expect(screen.getByText(/Shortlist approved/)).toBeInTheDocument();
  });

  it("blocks approval when four suppliers are selected", async () => {
    const selectedSuppliers = Array.from({ length: 4 }, (_, index) => ({
      ...supplier, id: `supplier-${index}`, name: `Supplier ${index}`, shortlisted: true,
    }));
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse({
      brief_revision: 1, brief_approved: true, shortlist_approved: false, suppliers: selectedSuppliers,
    }))));
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText(/4 selected/)).toBeInTheDocument();
    expect(screen.getByText(/Remove suppliers until no more than three remain/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review selected suppliers" }));
    expect(screen.getByRole("button", { name: "Approve Shortlist" })).toBeDisabled();
  });

  it("refreshes stale findings and explains a rejected approval", async () => {
    let stale = false;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/shortlist/approve") && init?.method === "POST") {
        stale = true;
        return Promise.resolve(jsonResponse({ error: {
          code: "SHORTLIST_NOT_READY", message: "Re-discover and re-evaluate suppliers before approval.",
        } }, 409));
      }
      return Promise.resolve(jsonResponse({
        brief_revision: stale ? 2 : 1, brief_approved: true, shortlist_approved: false,
        suppliers: [{ ...supplier, shortlisted: true, stale, evaluations: stale ? [] : supplier.evaluations }],
      }));
    }));
    render(<SupplierReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Review selected suppliers" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve Shortlist" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Re-discover and re-evaluate suppliers before approval.");
    expect(screen.getByText(/Your sourcing requirements changed/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve Shortlist" })).toBeDisabled();
    expect(screen.queryByText(/Shortlist approved/)).not.toBeInTheDocument();
  });
});
