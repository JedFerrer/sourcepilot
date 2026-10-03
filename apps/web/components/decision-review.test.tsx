import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DecisionProject, DecisionReview } from "./decision-review";
import { jsonResponse } from "../test/api-responses";

const empty: DecisionProject = { id: "p", preferred_supplier_id: null, preferred_supplier_name: null, decision_notes: null };
const choices = [
  { id: "a", name: "Supplier A", shortlisted: true },
  { id: "c", name: "Supplier C", shortlisted: true },
  { id: "x", name: "Unselected supplier", shortlisted: false },
];
const saved = { ...empty, preferred_supplier_id: "a", preferred_supplier_name: "Supplier A", decision_notes: "Original" };

function Host({ initial = empty }: { initial?: DecisionProject }) {
  const [project, setProject] = useState(initial);
  return <DecisionReview project={project} refreshKey={0} onSaved={setProject} />;
}

function server(suppliers = choices) {
  return vi.fn((path: string, init?: RequestInit) => {
    if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers }));
    const body = JSON.parse(String(init?.body)) as { supplier_id: string | null; decision_notes: string };
    return Promise.resolve(jsonResponse({ ...empty, preferred_supplier_id: body.supplier_id,
      preferred_supplier_name: choices.find((supplier) => supplier.id === body.supplier_id)?.name ?? null,
      decision_notes: body.decision_notes.trim() || null }));
  });
}

describe("DecisionReview", () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

  it("selects, changes, edits notes, and clears through explicit user actions", async () => {
    const fetchMock = server();
    vi.stubGlobal("fetch", fetchMock);
    render(<Host />);
    await screen.findByRole("option", { name: "Supplier A" });
    expect(screen.getByLabelText("Preferred supplier")).toHaveValue("");
    expect(screen.queryByRole("option", { name: "Unselected supplier" })).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.every(([, init]) => !init?.method)).toBe(true);
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "  First choice  " } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await screen.findByText("Preferred supplier saved.");
    expect(fetchMock).toHaveBeenLastCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ method: "PUT", body: JSON.stringify({ supplier_id: "a", decision_notes: "  First choice  " }) }));
    expect(screen.getByLabelText("Decision notes")).toHaveValue("First choice");
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "c" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await waitFor(() => expect(screen.getByText("Supplier C", { selector: "strong" })).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Changed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    expect(fetchMock).toHaveBeenLastCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ body: JSON.stringify({ supplier_id: "c", decision_notes: "Changed" }) }));
    fireEvent.click(screen.getByRole("button", { name: "Clear preferred supplier" }));
    await screen.findByText("Preferred supplier cleared.");
    expect(screen.getByText("No Decision Yet")).toBeInTheDocument();
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Changed");
  });

  it("reopens the saved choice without automatically selecting a replacement", async () => {
    vi.stubGlobal("fetch", server());
    render(<Host initial={saved} />);
    await screen.findByRole("option", { name: "Supplier C" });
    expect(screen.getByText("Supplier A", { selector: "strong" })).toBeInTheDocument();
    expect(screen.getByLabelText("Preferred supplier")).toHaveValue("");
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Original");
  });

  it("saves retained-choice notes and clears with no remaining shortlist", async () => {
    const fetchMock = server([]);
    vi.stubGlobal("fetch", fetchMock);
    render(<Host initial={saved} />);
    await screen.findByText(/saved preferred supplier is no longer shortlisted/);
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Retained" } });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    expect(fetchMock).toHaveBeenLastCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ body: JSON.stringify({ supplier_id: "a", decision_notes: "Retained" }) }));
    fireEvent.click(screen.getByRole("button", { name: "Clear preferred supplier" }));
    await screen.findByText("Preferred supplier cleared.");
    expect(screen.getByText("No Decision Yet")).toBeInTheDocument();
  });

  it("allows notes before a choice and clears blank notes", async () => {
    const fetchMock = server([]);
    vi.stubGlobal("fetch", fetchMock);
    render(<Host initial={{ ...empty, decision_notes: "Old" }} />);
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    await screen.findByText("Decision notes saved.");
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/p/preferred-supplier", expect.objectContaining({ body: JSON.stringify({ supplier_id: null, decision_notes: "  " }) }));
    expect(screen.getByLabelText("Decision notes")).toHaveValue("");
  });

  it("preserves draft selection and notes after network failure and supports retry", async () => {
    const base = server();
    let fail = true;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PUT" && fail) return Promise.reject(new Error("network"));
      return base(path, init);
    }));
    render(<Host />);
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await screen.findByRole("alert");
    expect(screen.getByLabelText("Preferred supplier")).toHaveValue("a");
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Draft");
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await screen.findByText("Preferred supplier saved.");
  });

  it("refreshes options after rejection without discarding unsaved notes", async () => {
    let reads = 0;
    const onSaved = vi.fn();
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => Promise.resolve(init?.method === "PUT"
      ? jsonResponse({ error: { code: "PREFERRED_SUPPLIER_NOT_SHORTLISTED", message: "Choose from the current shortlist." } }, 409)
      : jsonResponse({ suppliers: ++reads === 1 ? choices : [] }))));
    render(<DecisionReview project={empty} refreshKey={0} onSaved={onSaved} />);
    await screen.findByRole("option", { name: "Supplier A" });
    fireEvent.change(screen.getByLabelText("Preferred supplier"), { target: { value: "a" } });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Keep draft" } });
    fireEvent.click(screen.getByRole("button", { name: "Mark as Preferred Supplier" }));
    await screen.findByText("No shortlisted suppliers are available for a new selection.");
    expect(screen.getByRole("alert")).toHaveTextContent("Choose from the current shortlist.");
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Keep draft");
    expect(screen.getByRole("button", { name: "Mark as Preferred Supplier" })).toBeDisabled();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("retries shortlist loading while keeping retained-choice notes and clear available", async () => {
    let fail = true;
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(fail
      ? jsonResponse({ error: { code: "UNAVAILABLE", message: "Shortlist unavailable." } }, 503)
      : jsonResponse({ suppliers: choices }))));
    render(<Host initial={saved} />);
    await screen.findByText("Shortlist unavailable.");
    expect(screen.getByRole("button", { name: "Save decision notes" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Clear preferred supplier" })).toBeEnabled();
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Reload decision shortlist" }));
    await screen.findByRole("option", { name: "Supplier C" });
  });

  it("reloads options after a supplier refresh without losing notes", async () => {
    const fetchMock = server();
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<DecisionReview project={saved} refreshKey={0} onSaved={vi.fn()} />);
    await screen.findByRole("option", { name: "Supplier C" });
    fireEvent.change(screen.getByLabelText("Decision notes"), { target: { value: "Draft" } });
    rerender(<DecisionReview project={saved} refreshKey={1} onSaved={vi.fn()} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(screen.getByLabelText("Decision notes")).toHaveValue("Draft");
  });

  it("prevents duplicate writes while saving", async () => {
    let resolveSave!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveSave = resolve; });
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => init?.method === "PUT" ? pending : Promise.resolve(jsonResponse({ suppliers: choices })));
    vi.stubGlobal("fetch", fetchMock);
    render(<Host initial={saved} />);
    await screen.findByRole("option", { name: "Supplier C" });
    const button = screen.getByRole("button", { name: "Save decision notes" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PUT")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Clear preferred supplier" })).toBeDisabled();
    await act(async () => resolveSave(jsonResponse(saved)));
  });

  it.each(["project change", "unmount"])("discards a late save after %s", async (action) => {
    let resolveSave!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveSave = resolve; });
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => init?.method === "PUT" ? pending : Promise.resolve(jsonResponse({ suppliers: choices }))));
    const onSaved = vi.fn();
    const view = render(<DecisionReview project={saved} refreshKey={0} onSaved={onSaved} />);
    await screen.findByRole("option", { name: "Supplier C" });
    fireEvent.click(screen.getByRole("button", { name: "Save decision notes" }));
    if (action === "unmount") view.unmount();
    else view.rerender(<DecisionReview project={{ ...empty, id: "new" }} refreshKey={0} onSaved={onSaved} />);
    await act(async () => resolveSave(jsonResponse(saved)));
    expect(onSaved).not.toHaveBeenCalled();
    if (action === "project change") expect(screen.getByLabelText("Decision notes")).toHaveValue("");
  });

  it("discards an obsolete shortlist load after changing projects", async () => {
    let resolveOld!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveOld = resolve; });
    vi.stubGlobal("fetch", vi.fn((path: string) => path.includes("/p/") ? pending : Promise.resolve(jsonResponse({ suppliers: [] }))));
    const view = render(<DecisionReview project={empty} refreshKey={0} onSaved={vi.fn()} />);
    view.rerender(<DecisionReview project={{ ...empty, id: "new" }} refreshKey={0} onSaved={vi.fn()} />);
    await screen.findByText("No shortlisted suppliers are available for a new selection.");
    await act(async () => resolveOld(jsonResponse({ suppliers: choices })));
    expect(screen.queryByRole("option", { name: "Supplier A" })).not.toBeInTheDocument();
  });
});
