import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ProjectWorkspace } from "./project-workspace";
import { jsonResponse } from "../test/api-responses";

const emptyBrief = {
  product_name: null, category: null, quantity: null, destination: null,
  delivery_target: null, target_unit_price: null, requirements: [],
  status: "IN_PROGRESS", missing_fields: [], uncertainties: [], brief_revision: 0, can_analyze: true,
};

const readyBrief = {
  ...emptyBrief, product_name: "Desk lamp", category: "Lighting", quantity: 100,
  destination: "Manila", delivery_target: { kind: "DATE", date: "2027-01-01" },
  status: "READY_FOR_REVIEW", brief_revision: 1, can_analyze: false,
  approved_at: null,
};

vi.mock("next/link", () => ({ default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }));
vi.mock("./supplier-review", () => ({ SupplierReview: () => null }));
vi.mock("./quote-review", () => ({ QuoteReview: () => null }));
const comparisonRender = vi.hoisted(() => vi.fn());
vi.mock("./comparison-review", () => ({ ComparisonReview: (props: { refreshKey: number }) => {
  comparisonRender(props.refreshKey);
  return <p>Existing comparison advice</p>;
} }));

describe("ProjectWorkspace", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
    comparisonRender.mockClear();
  });

  it("updates preference without replacing comparison advice or refreshing its inputs", async () => {
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(emptyBrief));
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [{ id: "c", name: "Supplier C", shortlisted: true }] }));
      const project = { id: "project-1", name: "Travel Bag", original_request: "Source bags", stage: "QUOTES", preferred_supplier_id: null, preferred_supplier_name: null, decision_notes: null };
      if (init?.method === "PUT") return Promise.resolve(jsonResponse({ ...project, preferred_supplier_id: "c", preferred_supplier_name: "Supplier C", decision_notes: "Choice" }));
      reads += 1;
      return Promise.resolve(jsonResponse(project));
    }));
    render(<ProjectWorkspace projectId="project-1" />);
    await screen.findByRole("option", { name: "Supplier C" });
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "c" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Choice" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    expect(await screen.findByText("Preferred supplier: Supplier C")).toBeInTheDocument();
    expect(screen.getByText("Existing comparison advice")).toBeInTheDocument();
    expect(comparisonRender.mock.calls.every(([refreshKey]) => refreshKey === 0)).toBe(true);
    expect(reads).toBe(1);
  });

  it("shows the saved request and a presentation-only five-stage shell", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string) => Promise.resolve(path.endsWith("/brief") ? jsonResponse(emptyBrief) : jsonResponse({
          id: "project-1",
          name: "Travel Bag",
          original_request: "Source recycled travel bags.",
          stage: "BRIEF",
        }))),
    );
    render(<ProjectWorkspace projectId="project-1" />);

    expect(await screen.findByText("Travel Bag")).toBeInTheDocument();
    expect(screen.getByText("Source recycled travel bags.")).toBeInTheDocument();
    expect(screen.getByText("Brief").closest("li")).toHaveAttribute("aria-current", "step");
    for (const stage of ["Suppliers", "Quotes"]) {
      expect(screen.getByText(stage).closest("li")).toHaveAttribute("data-unavailable", "true");
    }
    expect(screen.getByText("Comparison").closest("li")).not.toHaveAttribute("data-unavailable");
    const decision = within(screen.getByRole("navigation", { name: "Sourcing workflow stages" })).getByText("Decision");
    expect(decision.closest("li")).not.toHaveAttribute("data-unavailable");
    expect(screen.getByRole("heading", { name: "Decision" })).toBeInTheDocument();
  });

  it("synchronizes project stage after approval and an approval-revoking edit", async () => {
    let stage = "BRIEF";
    let brief = {
      ...readyBrief, quantity: readyBrief.quantity as number | null,
      approved_at: null as string | null,
      missing_fields: [] as { field_key: string; reason: string }[],
    };
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/brief/approve")) {
        stage = "SUPPLIERS";
        brief = { ...brief, status: "APPROVED", approved_at: "2026-09-24T00:00:00Z" };
        return Promise.resolve(jsonResponse(brief));
      }
      if (path.endsWith("/brief") && init?.method === "PATCH") {
        stage = "BRIEF";
        brief = { ...brief, quantity: null, status: "IN_PROGRESS", approved_at: null, brief_revision: 2,
          missing_fields: [{ field_key: "quantity", reason: "Enter a positive requested quantity." }] };
        return Promise.resolve(jsonResponse(brief));
      }
      if (path.endsWith("/brief")) return Promise.resolve(jsonResponse(brief));
      return Promise.resolve(jsonResponse({ id: "project-1", name: "Lamp", original_request: "Source lamps.", stage }));
    }));
    render(<ProjectWorkspace projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve Brief" }));
    expect(await screen.findByText("Current stage: Suppliers")).toBeInTheDocument();
    const suppliers = screen.getByText("Suppliers").closest("li");
    expect(suppliers).toHaveAttribute("aria-current", "step");
    expect(suppliers).not.toHaveAttribute("data-unavailable");
    expect(suppliers).toHaveTextContent("Review discovered suppliers above.");
    expect(suppliers).not.toHaveTextContent("Available in a later step.");
    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    expect(await screen.findByText("Current stage: Brief")).toBeInTheDocument();
  });

  it("persists a project rename", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((path: string, init?: RequestInit) => Promise.resolve(
        path.endsWith("/brief") ? jsonResponse(emptyBrief) :
        init?.method === "PATCH" ? jsonResponse({ id: "project-1", name: "Renamed Bag", original_request: "Source bags" }) :
        jsonResponse({ id: "project-1", name: "Travel Bag", original_request: "Source bags" }),
      )),
    );
    render(<ProjectWorkspace projectId="project-1" />);

    await screen.findByText("Travel Bag");
    fireEvent.change(screen.getByLabelText("Rename project"), { target: { value: "Renamed Bag" } });
    fireEvent.click(screen.getByRole("button", { name: "Save name" }));

    expect(await screen.findByText("Renamed Bag")).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/projects/project-1", {
      method: "PATCH",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Renamed Bag" }),
    });
  });

  it("shows Quotes as the current stage after shortlist approval", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/brief") ? jsonResponse(emptyBrief) : jsonResponse({
        id: "project-1", name: "Travel Bag", original_request: "Source bags.", stage: "QUOTES",
      }),
    )));
    render(<ProjectWorkspace projectId="project-1" />);
    expect(await screen.findByText("Current stage: Quotes")).toBeInTheDocument();
    expect(screen.getByText("Quotes").closest("li")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Quotes").closest("li")).not.toHaveAttribute("data-unavailable");
    expect(screen.getByText("Quotes").closest("li")).toHaveTextContent("Add and confirm manual quotes above.");
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
      vi.fn((path: string) => path.endsWith("/brief") ? Promise.resolve(jsonResponse(emptyBrief)) : (path.endsWith("project-a") ? projectAResponse : projectBResponse)),
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
