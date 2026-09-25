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
});
