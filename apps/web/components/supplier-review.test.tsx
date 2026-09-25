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
});
