import { viewStage } from "../test/workspace-navigation";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { workspaceFixtureResponse as jsonResponse } from "../test/workflow-fixtures";
import { ProjectWorkspace } from "./project-workspace";

const brief = {
  product_name: "Desk lamp", category: "Lighting", quantity: 100, destination: "Manila",
  delivery_target: { kind: "DATE", date: "2027-01-01" }, target_unit_price: null,
  requirements: [], status: "APPROVED", missing_fields: [], uncertainties: [],
  brief_revision: 1, can_analyze: false, approved_at: "2026-09-24T00:00:00Z",
};

const supplier = {
  id: "supplier-1", name: "Willow", country: "PH", description: "Lamp supplier",
  capabilities: [], general_moq: null, general_lead_time_days: null,
  indicative_price_amount: null, indicative_price_currency: null,
  shortlisted: true, dismissed: false, notes: null, stale: false,
  evaluated_against_brief_revision: 1, evaluations: [], derived_context: [],
  informational_requirements: [], evidence: [],
};

const supplierList = (shortlistApproved: boolean) => ({
  brief_revision: 1, brief_approved: true, shortlist_approved: shortlistApproved,
  suppliers: [{ ...supplier, shortlisted: shortlistApproved }],
});

const comparisonNotFound = () => jsonResponse({
  error: { code: "COMPARISON_NOT_FOUND", message: "No comparison exists." },
}, 404);
const projectUnavailable = () => jsonResponse({
  error: { code: "PROJECT_UNAVAILABLE", message: "Project unavailable." },
}, 503);
const generationNotReady = () => jsonResponse({
  error: { code: "COMPARISON_NOT_READY", message: "Comparison inputs need approval." },
}, 409);

async function showSettledGenerationError() {
  await viewStage("Comparison");
  const generate = await screen.findByRole("button", { name: "Generate Comparison" });
  await waitFor(() => expect(generate).toBeEnabled());
  fireEvent.click(generate);
  expect(await screen.findByText("Comparison inputs need approval.")).toBeInTheDocument();
}

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>,
}));
vi.mock("./quote-review", () => ({ QuoteReview: () => null }));

describe("ProjectWorkspace comparison refresh after upstream changes", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("reloads comparison after a successful Brief edit even when the project reload fails", async () => {
    let projectReads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/comparison/generate") && init?.method === "POST") return Promise.resolve(generationNotReady());
      if (path.endsWith("/comparison")) return Promise.resolve(comparisonNotFound());
      if (path.endsWith("/brief") && init?.method === "PATCH") return Promise.resolve(jsonResponse({ ...brief, quantity: 101, brief_revision: 2 }));
      if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(brief));
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse(supplierList(true)));
      if (path === "/api/projects/project-1") {
        projectReads += 1;
        return Promise.resolve(projectReads === 1
          ? jsonResponse({ id: "project-1", name: "Lamp", original_request: "Source lamps.", stage: "QUOTES" })
          : projectUnavailable());
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProjectWorkspace projectId="project-1" />);

    await viewStage("Brief");
    fireEvent.click(await screen.findByRole("button", { name: "Edit Brief" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/comparison", expect.anything()));
    await showSettledGenerationError();
    await viewStage("Brief");
    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "101" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));

    expect(await screen.findByText("The project stage could not be refreshed. Try again.")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => path === "/api/projects/project-1/comparison")).toHaveLength(2));
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief", expect.objectContaining({ method: "PATCH" }));
    expect(projectReads).toBe(2);
    expect(screen.queryByText("Comparison inputs need approval.")).not.toBeInTheDocument();
  });

  it("reloads comparison after a successful shortlist change even when the project reload fails", async () => {
    let projectReads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/comparison/generate") && init?.method === "POST") return Promise.resolve(generationNotReady());
      if (path.endsWith("/comparison")) return Promise.resolve(comparisonNotFound());
      if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(brief));
      if (path.endsWith("/suppliers/supplier-1") && init?.method === "PATCH") return Promise.resolve(jsonResponse(supplierList(false)));
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse(supplierList(true)));
      if (path === "/api/projects/project-1") {
        projectReads += 1;
        return Promise.resolve(projectReads === 1
          ? jsonResponse({ id: "project-1", name: "Lamp", original_request: "Source lamps.", stage: "QUOTES" })
          : projectUnavailable());
      }
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProjectWorkspace projectId="project-1" />);

    await showSettledGenerationError();
    await viewStage("Suppliers");
    fireEvent.click(await screen.findByRole("button", { name: "Remove from shortlist" }));

    expect(await screen.findByText("The project stage could not be refreshed. Try again.")).toBeInTheDocument();
    await waitFor(() => expect(fetchMock.mock.calls.filter(([path]) => path === "/api/projects/project-1/comparison")).toHaveLength(2));
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/suppliers/supplier-1", expect.objectContaining({ method: "PATCH" }));
    expect(projectReads).toBe(2);
    expect(screen.queryByText("Comparison inputs need approval.")).not.toBeInTheDocument();
  });

  it("clears settled generation feedback after shortlist approval", async () => {
    let comparisonReads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/comparison/generate") && init?.method === "POST") return Promise.resolve(generationNotReady());
      if (path.endsWith("/comparison")) { comparisonReads += 1; return Promise.resolve(comparisonNotFound()); }
      if (path.endsWith("/shortlist/approve") && init?.method === "POST") return Promise.resolve(jsonResponse(supplierList(true)));
      if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(brief));
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ ...supplierList(false), suppliers: [supplier] }));
      if (path === "/api/projects/project-1") return Promise.resolve(jsonResponse({
        id: "project-1", name: "Lamp", original_request: "Source lamps.", stage: "SUPPLIERS",
      }));
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ProjectWorkspace projectId="project-1" />);

    await showSettledGenerationError();
    await viewStage("Suppliers");
    fireEvent.click(await screen.findByRole("button", { name: "Review selected suppliers" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve Shortlist" }));

    await waitFor(() => expect(comparisonReads).toBe(2));
    expect(screen.queryByText("Comparison inputs need approval.")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/shortlist/approve", expect.objectContaining({ method: "POST" }));
  });
});
