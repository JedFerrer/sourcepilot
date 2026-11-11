import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuoteReview } from "./quote-review";
import { ComparisonReview } from "./comparison-review";
import { jsonResponse } from "../test/api-responses";
import userEvent from "@testing-library/user-event";

const supplier = { id: "supplier-1", name: "Fictional Bags", shortlisted: true, dismissed: false };

function QuoteComparisonHarness() {
  const [refreshKey, setRefreshKey] = useState(0);
  return <>
    <QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={() => setRefreshKey((value) => value + 1)} />
    <ComparisonReview projectId="project-1" refreshKey={refreshKey} />
  </>;
}

describe("QuoteReview", () => {
  it("uses the quote editor fallback when its heading is unavailable and leaves later focus alone", async () => {
    const { quote, reads, view, setListedQuote } = await uncertainRecovery();
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await act(async () => { reads[0].resolve(jsonResponse(quote)); });
    const heading = screen.getByRole("heading", { name: supplier.name });
    heading.hidden = true;
    fireEvent.click(screen.getByRole("button", { name: "Use saved record" }));
    expect(screen.getByRole("article", { name: `${supplier.name} quote editor` })).toHaveFocus();
    const notes = screen.getByLabelText("Quote notes"); notes.focus();
    setListedQuote({ ...quote, notes: "Background saved record" });
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={1} />);
    await waitFor(() => expect(notes).toHaveValue("Background saved record"));
    expect(notes).toHaveFocus();
  });
  it.each(["saved", "keep"])("returns keyboard focus and announces the %s recovery choice without another write", async (choice) => {
    const user = userEvent.setup();
    const { quote, reads, fetchMock } = await uncertainRecovery();
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await act(async () => { reads[0].resolve(jsonResponse(quote)); });
    const button = screen.getByRole("button", { name: choice === "saved" ? "Use saved record" : /I reviewed both records/ });
    button.focus(); await user.keyboard("{Enter}");
    const heading = screen.getByRole("heading", { name: supplier.name });
    expect(heading).toHaveFocus();
    expect(screen.getByRole("status", { name: "Quote recovery" })).toHaveTextContent(choice === "saved" ? "Saved record loaded" : "Your edits are retained");
    expect(screen.getByLabelText("Quote notes")).toHaveValue(choice === "saved" ? quote.notes : "Retained edits");
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });
  async function uncertainRecovery() {
    const quote = { id: "q", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW", revision: 1, notes: "Original", values: {} };
    let listedQuote = quote;
    const reads: { resolve: (value: Response) => void; reject: (error: Error) => void }[] = [];
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return Promise.reject(new TypeError("Disconnected"));
      if (path === "/api/quotes/q") return new Promise<Response>((resolve, reject) => reads.push({ resolve, reject }));
      return Promise.resolve(jsonResponse(path.endsWith("/suppliers") ? { suppliers: [supplier] } : [listedQuote]));
    });
    vi.stubGlobal("fetch", fetchMock);
    const onQuoteChange = vi.fn();
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={onQuoteChange} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Retained edits" } });
    fireEvent.submit(screen.getByRole("button", { name: "Save draft" }).closest("form")!);
    await screen.findByRole("button", { name: "Check saved quote" });
    return { quote, reads, fetchMock, onQuoteChange, view, setListedQuote: (value: typeof quote) => { listedQuote = value; } };
  }

  it.each(["saved", "keep"])("ignores an older recovery success after accepting the newer record with %s", async (choice) => {
    const { quote, reads, fetchMock } = await uncertainRecovery();
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await act(async () => { reads[1].resolve(jsonResponse({ ...quote, revision: 2, notes: "New saved notes" })); });
    fireEvent.click(screen.getByRole("button", { name: choice === "saved" ? "Use saved record" : /I reviewed both records/ }));
    await act(async () => { reads[0].resolve(jsonResponse(quote)); });
    expect(screen.getByLabelText("Quote notes")).toHaveValue(choice === "saved" ? "New saved notes" : "Retained edits");
    expect(screen.queryByRole("region", { name: "Review changes saved elsewhere" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check saved quote" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
    // Discarding after keeping edits must still use the newer saved baseline.
    if (choice === "keep") {
      fireEvent.click(screen.getByRole("button", { name: "Discard unsaved quote edits" }));
      fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
      expect(screen.getByLabelText("Quote notes")).toHaveValue("New saved notes");
    }
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });

  it.each([
    ["saved", "success"], ["saved", "failure"], ["keep", "success"], ["keep", "failure"],
  ])("invalidates an outstanding recovery on %s choice before late %s", async (choice, outcome) => {
    const { quote, reads, fetchMock } = await uncertainRecovery();
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await act(async () => { reads[0].resolve(jsonResponse(quote)); });
    // Start a read after a review exists: sequence ordering alone cannot protect this choice.
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    fireEvent.click(screen.getByRole("button", { name: choice === "saved" ? "Use saved record" : /I reviewed both records/ }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Edits after recovery" } });
    await act(async () => {
      if (outcome === "failure") reads[1].reject(new TypeError("Late failure"));
      else reads[1].resolve(jsonResponse({ ...quote, revision: 2, notes: "Late saved notes" }));
    });
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Edits after recovery");
    expect(screen.queryByRole("region", { name: "Review changes saved elsewhere" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Saved quote could not be checked/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check saved quote" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });

  it("keeps newer recovery failure feedback when an older read succeeds", async () => {
    const { quote, reads } = await uncertainRecovery();
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await act(async () => { reads[1].reject(new TypeError("Newer read failed")); });
    await act(async () => { reads[0].resolve(jsonResponse(quote)); });
    expect(screen.getByText(/Saved quote could not be checked/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Use saved record" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Retained edits");
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
  });

  it.each(["success", "failure"])("ignores late recovery %s after a quote change, project change or unmount", async (outcome) => {
    for (const change of ["quote", "project", "unmount"] as const) {
      const { quote, reads, onQuoteChange, view, setListedQuote } = await uncertainRecovery();
      fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
      if (change === "unmount") {
        view.unmount();
      } else {
        setListedQuote({ ...quote, id: "replacement", notes: "Replacement quote" });
        view.rerender(<QuoteReview projectId={change === "project" ? "project-2" : "project-1"} active refreshKey={1} onQuoteChange={onQuoteChange} />);
        await screen.findByText("Replacement quote");
      }
      const calls = onQuoteChange.mock.calls.length;
      await act(async () => {
        if (outcome === "success") reads[0].resolve(jsonResponse({ ...quote, notes: "Obsolete quote" }));
        else reads[0].reject(new TypeError("Late failure"));
      });
      expect(onQuoteChange).toHaveBeenCalledTimes(calls);
      expect(screen.queryByText("Obsolete quote")).not.toBeInTheDocument();
      expect(screen.queryByText(/Saved quote could not be checked/)).not.toBeInTheDocument();
      if (change !== "unmount") expect(screen.getByText("Replacement quote")).toBeInTheDocument();
      view.unmount();
    }
  });

  it.each(["keep", "saved"])("reconciles unchanged reads after uncertain saves using explicit %s choice", async (choice) => {
    const quote = { id: "q", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW", revision: 1, notes: "Original", values: {} };
    let failRead = true;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return Promise.reject(new TypeError("Disconnected"));
      if (path.endsWith("/quotes/q")) return failRead ? Promise.reject(new TypeError("Disconnected")) : Promise.resolve(jsonResponse(quote));
      return Promise.resolve(jsonResponse(path.endsWith("/suppliers") ? { suppliers: [supplier] } : [quote]));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Retained edits" } });
    fireEvent.submit(screen.getByRole("button", { name: "Save draft" }).closest("form")!);
    fireEvent.click(await screen.findByRole("button", { name: "Check saved quote" }));
    await screen.findByText("Saved quote could not be checked. Your draft is retained; retry the read.");
    expect(screen.queryByRole("button", { name: "Use saved record" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
    failRead = false;
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    await screen.findByRole("button", { name: "Use saved record" });
    expect(screen.getByText(/Unchanged saved values do not prove the write failed/)).toBeInTheDocument();
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Retained edits");
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: choice === "keep" ? "I reviewed both records—keep my edits" : "Use saved record" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue(choice === "keep" ? "Retained edits" : "Original");
    expect(screen.getByRole("button", { name: "Save draft" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });

  it("recovers an uncertain manual creation with no saved quote without replaying creation", async () => {
    const fetchMock = vi.fn((path: string, init?: RequestInit) => init?.method === "POST" ? Promise.reject(new TypeError("Disconnected"))
      : Promise.resolve(jsonResponse(path.endsWith("/suppliers") ? { suppliers: [supplier] } : [])));
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Enter manually" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "New quote draft" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create manual quote" }).closest("form")!);
    fireEvent.click(await screen.findByRole("button", { name: "Check saved quote" }));
    fireEvent.click(await screen.findByRole("button", { name: "I reviewed both records—keep my edits" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("New quote draft");
    expect(screen.getByRole("button", { name: "Create manual quote" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("adopts a quote found by creation recovery so a later deliberate save updates it", async () => {
    const quote = { id: "recovered", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW", revision: 1, notes: "Submitted", values: {} };
    let created = false;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "POST") { created = true; return Promise.reject(new TypeError("Disconnected")); }
      if (init?.method === "PATCH") return Promise.resolve(jsonResponse({ ...quote, notes: "Later edit" }));
      return Promise.resolve(jsonResponse(path.endsWith("/suppliers") ? { suppliers: [supplier] } : created ? [quote] : []));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Enter manually" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Submitted" } });
    fireEvent.submit(screen.getByRole("button", { name: "Create manual quote" }).closest("form")!);
    await screen.findByRole("button", { name: "Check saved quote" });
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Later edit" } });
    fireEvent.click(screen.getByRole("button", { name: "Check saved quote" }));
    fireEvent.click(await screen.findByRole("button", { name: "I reviewed both records—keep my edits" }));
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Later edit");
    fireEvent.submit(screen.getByRole("button", { name: "Save draft" }).closest("form")!);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/quotes/recovered", expect.objectContaining({ method: "PATCH" })));
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("names material issues in collapsed saved and editing groups without treating omissions as blockers", async () => {
    const quote = { id: "q", supplier_id: supplier.id, entry_type: "PDF", status: "NEEDS_REVIEW", revision: 1, notes: null, values: {
      certifications: { current_value: null, ai_extracted_value: null, current_origin: "AI_EXTRACTED", review_state: "CONFLICT" },
      payment_terms: { current_value: "Deposit", ai_extracted_value: "Deposit", current_origin: "AI_EXTRACTED", uncertainty: "Deposit percentage unclear" },
      warranty: { current_value: null, ai_extracted_value: null, current_origin: "AI_EXTRACTED", review_state: "UNKNOWN" },
    } };
    const fetchMock = vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/suppliers") ? { suppliers: [supplier] } : [quote])));
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await screen.findByRole("button", { name: "Edit PDF draft" });
    for (const edit of [false, true]) {
      if (edit) fireEvent.click(screen.getByRole("button", { name: "Edit PDF draft" }));
      const summaries = [...document.querySelectorAll("summary")].filter((item) => !item.closest("[hidden]"));
      const compliance = summaries.find((item) => item.textContent === "Compliance · Certifications: Conflict")!;
      const terms = summaries.find((item) => item.textContent === "Terms · Payment terms: Uncertainty")!;
      expect(compliance).toBeVisible();
      expect(compliance.closest("details")).not.toHaveAttribute("open");
      expect(terms).toBeVisible();
      expect(terms.closest("details")).not.toHaveAttribute("open");
      expect(terms).not.toHaveTextContent("Warranty");
    }
    fireEvent.click(screen.getByRole("button", { name: "Cancel editing" }));
    fireEvent.click(screen.getByRole("button", { name: "Review for confirmation" }));
    expect(screen.getByRole("button", { name: "Confirm Quote" })).toBeEnabled();
    expect(fetchMock.mock.calls.every(([path]) => path.endsWith("/suppliers") || path.endsWith("/quotes"))).toBe(true);
  });
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); });

  it("hides removed suppliers while preserving drafts and saved quotes for restoration", async () => {
    const harbor = { ...supplier, name: "Harbor" };
    const moss = { ...supplier, id: "moss", name: "Moss" };
    const willow = { ...supplier, id: "willow", name: "Willow" };
    const cedar = { ...supplier, id: "cedar", name: "Cedar" };
    let removed = false;
    const quote = { id: "quote-harbor", supplier_id: harbor.id, entry_type: "MANUAL", status: "NEEDS_REVIEW", revision: 1, confirmed_at: null, notes: "Saved notes", values: {} };
    const fetchMock = vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/suppliers")
      ? { suppliers: removed ? [cedar, moss, willow, { ...harbor, shortlisted: false }] : [harbor, moss, willow] }
      : [quote])));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Keep this unsaved note" } });
    removed = true;
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={1} />);
    const activeChoices = screen.getByRole("group", { name: "Choose a quote supplier" });
    await waitFor(() => expect(within(activeChoices).getAllByRole("button")).toHaveLength(3));
    expect(within(activeChoices).queryByRole("button", { name: /Harbor/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Harbor/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Harbor" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Cedar/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Keep this unsaved note");
    expect(screen.getByLabelText("Quote notes")).not.toBeVisible();
    removed = false;
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={2} />);
    fireEvent.click(await screen.findByRole("button", { name: /Harbor/ }));
    expect(screen.getByLabelText("Quote notes")).toBeVisible();
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Keep this unsaved note");
    view.unmount();
    removed = true;
    const reopened = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await screen.findByRole("button", { name: /Cedar/ });
    expect(screen.queryByRole("button", { name: /Harbor/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Harbor" })).not.toBeInTheDocument();
    removed = false;
    reopened.rerender(<QuoteReview projectId="project-1" active refreshKey={1} />);
    fireEvent.click(await screen.findByRole("button", { name: /Harbor/ }));
    expect(screen.getByText("Notes: Saved notes")).toBeVisible();
    expect(within(screen.getByRole("group", { name: "Choose a quote supplier" })).getAllByRole("button")).toHaveLength(3);
    expect(fetchMock.mock.calls.every(([path]) => path.endsWith("/suppliers") || path.endsWith("/quotes"))).toBe(true);
  });

  it.each(["FAILED", "STALE_PROCESSING", "NEEDS_REVIEW"])("recovers failed status reads with GET only into %s, preserving another draft", async (status) => {
    vi.useFakeTimers();
    const quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 1, confirmed_at: null, notes: null, values: {}, processing: { attempts: 1 } };
    const other = { ...supplier, id: "supplier-2", name: "Another supplier" };
    let resolveRead: (value: Response) => void;
    let reads = 0;
    const fetchMock = vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier, other] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      reads += 1;
      if (reads <= 2) return Promise.resolve(jsonResponse({ error: { code: "UNAVAILABLE", message: "Unavailable" } }, 503));
      return new Promise<Response>((resolve) => { resolveRead = resolve; });
    });
    vi.stubGlobal("fetch", fetchMock);
    await act(async () => { render(<QuoteReview projectId="project-1" active refreshKey={0} />); });
    fireEvent.change(screen.getByLabelText("Quote supplier"), { target: { value: "supplier-2" } });
    fireEvent.click(screen.getByRole("button", { name: "Enter manually" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Unsaved other quote" } });
    fireEvent.change(screen.getByLabelText("Quote supplier"), { target: { value: supplier.id } });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByRole("alert")).toHaveTextContent("We couldn't check this quote's processing status");
    expect(screen.queryByRole("button", { name: "Retry processing" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enter quote manually" })).not.toBeInTheDocument();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Retry status check" })); });
    expect(reads).toBe(2);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Retry status check" })); });
    expect(screen.getByRole("button", { name: "Retry status check" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry status check" }));
    expect(reads).toBe(3); // Pending explicit retry cannot be double-submitted.
    await act(async () => { resolveRead!(jsonResponse({ ...quote, status })); });
    expect(screen.queryByRole("button", { name: "Retry status check" })).not.toBeInTheDocument();
    expect(screen.getByText(`Status: ${status.replaceAll("_", " ")}`)).toBeInTheDocument();
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Unsaved other quote");
    expect(Boolean(screen.queryByRole("button", { name: "Enter quote manually" }))).toBe(status === "FAILED");
    for (const [, init] of fetchMock.mock.calls as unknown as [string, RequestInit | undefined][]) {
      expect(init?.method ?? "GET").toBe("GET");
    }
  });

  it("recovers automatically after an authorization-denied status read without bypassing the endpoint", async () => {
    vi.useFakeTimers();
    const quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 1, confirmed_at: null, notes: null, values: {} };
    let reads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      expect(init?.method ?? "GET").toBe("GET");
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      expect(path).toBe("/api/quotes/pdf-1");
      reads += 1;
      return Promise.resolve(reads === 1 ? jsonResponse({ error: { code: "NOT_FOUND", message: "Not found" } }, 404) : jsonResponse(quote));
    });
    vi.stubGlobal("fetch", fetchMock);
    await act(async () => { render(<QuoteReview projectId="project-1" active refreshKey={0} />); });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByRole("button", { name: "Retry status check" })).toBeEnabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(reads).toBe(2);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Processing PDF quote…")).toBeInTheDocument();
  });

  it.each(["deactivate", "project", "remove"])("ignores late status errors after %s", async (change) => {
    vi.useFakeTimers();
    const quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 1, confirmed_at: null, notes: null, values: {} };
    let rejectRead: (error: Error) => void;
    let removed = false;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse(removed ? [] : [quote]));
      return new Promise<Response>((_, reject) => { rejectRead = reject; });
    }));
    let view: ReturnType<typeof render>;
    await act(async () => { view = render(<QuoteReview projectId="project-1" active refreshKey={0} />); });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    removed = change === "remove";
    await act(async () => { view.rerender(<QuoteReview projectId={change === "project" ? "project-2" : "project-1"}
      active={change !== "deactivate"} refreshKey={1} />); });
    await act(async () => { rejectRead!(new Error("Old outage")); });
    expect(screen.queryByText(/We couldn't check this quote/)).not.toBeInTheDocument();
  });

  it("does not replace a successful automatic status check with an older failed read", async () => {
    vi.useFakeTimers();
    const quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 1, confirmed_at: null, notes: null, values: {} };
    let rejectOld: (error: Error) => void;
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      reads += 1;
      if (reads === 1) return new Promise<Response>((_, reject) => { rejectOld = reject; });
      return Promise.resolve(jsonResponse(quote));
    }));
    await act(async () => { render(<QuoteReview projectId="project-1" active refreshKey={0} />); });
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(reads).toBe(2);
    await act(async () => { rejectOld!(new Error("Old outage")); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByText("Processing PDF quote…")).toBeInTheDocument();
  });

  it("releases a cancelled pending retry when the status callback changes", async () => {
    vi.useFakeTimers();
    const quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 1, confirmed_at: null, notes: null, values: {} };
    let reads = 0;
    let rejectOld: (error: Error) => void;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      reads += 1;
      if (reads === 2) return new Promise<Response>((_, reject) => { rejectOld = reject; });
      if (reads === 1) return Promise.reject(new Error("Outage"));
      return Promise.resolve(jsonResponse(quote));
    }));
    let view: ReturnType<typeof render>;
    await act(async () => { view = render(<QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={vi.fn()} />); });
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    fireEvent.click(screen.getByRole("button", { name: "Retry status check" }));
    expect(screen.getByRole("button", { name: "Retry status check" })).toBeDisabled();
    await act(async () => { view.rerender(<QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={vi.fn()} />); });
    expect(screen.getByRole("button", { name: "Retry status check" })).toBeEnabled();
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Retry status check" })); });
    await act(async () => { rejectOld!(new Error("Cancelled outage")); });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it.each([false, true])("preserves unsaved fields and editor state across unavailable prerequisites (existing quote: %s)", async (existing) => {
    const quote = { id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
      revision: 1, confirmed_at: null, notes: "Saved notes", values: {} };
    const fetchMock = vi.fn((path: string) => Promise.resolve(path.endsWith("/suppliers")
      ? jsonResponse({ suppliers: [supplier] }) : jsonResponse(existing ? [quote] : [])));
    vi.stubGlobal("fetch", fetchMock);
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await waitFor(() => expect(screen.queryByText("Loading quotes…")).not.toBeInTheDocument());
    if (existing) fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    else fireEvent.click(await screen.findByRole("button", { name: "Enter manually" }));
    const notes = await screen.findByLabelText("Quote notes");
    fireEvent.change(notes, { target: { value: "UNSAVED FOCUS QUOTE" } });
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.75" } });
    view.rerender(<QuoteReview projectId="project-1" active={false} refreshKey={1} />);
    expect(screen.getByText("Approve the current shortlist before adding or reviewing quotes.")).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Quote notes" })).not.toBeInTheDocument();
    expect(notes).toBeDisabled();
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={1} />);
    await waitFor(() => expect(screen.queryByText("Loading quotes…")).not.toBeInTheDocument());
    expect(screen.getByLabelText("Quote notes")).toBe(notes);
    expect(notes).toHaveValue("UNSAVED FOCUS QUOTE");
    expect(notes).toBeEnabled();
    expect(screen.getByLabelText("Unit price")).toHaveValue(4.75);
    expect(screen.queryByText("Approve the current shortlist before adding or reviewing quotes.")).not.toBeInTheDocument();
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={2} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6));
    await waitFor(() => expect(screen.queryByText("Loading quotes…")).not.toBeInTheDocument());
    expect(notes).toHaveValue("UNSAVED FOCUS QUOTE");
  });

  it("preserves dirty server conflicts, requires explicit discard, and reconciles successful saves", async () => {
    let quote = { id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
      revision: 1, confirmed_at: null, notes: "Saved notes", values: {} };
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") {
        const body = JSON.parse(String(init.body));
        quote = { ...quote, notes: body.notes };
        return Promise.resolve(jsonResponse(quote));
      }
      return Promise.resolve(path.endsWith("/suppliers") ? jsonResponse({ suppliers: [supplier] }) : jsonResponse([quote]));
    }));
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Unsaved notes" } });
    // Notes-only server updates need not advance the quote value revision.
    quote = { ...quote, notes: "External saved notes" };
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={1} />);
    await screen.findByRole("region", { name: "Review changes saved elsewhere" });
    expect(screen.getByLabelText("Quote notes")).toHaveValue("Unsaved notes");
    expect(screen.getByRole("button", { name: "Save draft" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Use saved record" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("External saved notes");
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Discard me" } });
    fireEvent.click(screen.getByRole("button", { name: /Cancel editing|Discard unsaved quote edits/ }));
    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("External saved notes");
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "  External saved notes  " } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await screen.findByRole("button", { name: "Edit draft" });
    await waitFor(() => expect(screen.queryByText("Loading quotes…")).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    expect(screen.getByLabelText("Quote notes")).toHaveValue("External saved notes");
  });

  it.each(["save", "confirmation"])("clears settled generation feedback after a successful quote %s", async (mutation) => {
    const quote = {
      id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL",
      status: mutation === "save" ? "CONFIRMED" : "NEEDS_REVIEW",
      revision: 1, confirmed_at: null, notes: null,
      values: { unit_price: { current_value: "4.25", current_origin: "USER_ENTERED", ai_extracted_value: null } },
    };
    let comparisonReads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/comparison/generate") && init?.method === "POST") return Promise.resolve(jsonResponse({
        error: { code: "COMPARISON_NOT_READY", message: "Comparison inputs need approval." },
      }, 409));
      if (path.endsWith("/comparison")) {
        comparisonReads += 1;
        return Promise.resolve(jsonResponse({ error: { code: "COMPARISON_NOT_FOUND", message: "No comparison exists." } }, 404));
      }
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/quote-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/quote-1") && init?.method === "PATCH") return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/quote-1/confirm") && init?.method === "POST") return Promise.resolve(jsonResponse(quote));
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteComparisonHarness />);

    const generate = await screen.findByRole("button", { name: "Generate Comparison" });
    await waitFor(() => expect(generate).toBeEnabled());
    fireEvent.click(generate);
    expect(await screen.findByText("Comparison inputs need approval.")).toBeInTheDocument();
    if (mutation === "save") {
      fireEvent.click(await screen.findByRole("button", { name: "Edit confirmed quote" }));
      fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.50" } });
      fireEvent.click(screen.getByRole("button", { name: "Save quote" }));
    } else {
      fireEvent.click(await screen.findByRole("button", { name: "Review for confirmation" }));
      fireEvent.click(screen.getByRole("button", { name: "Confirm Quote" }));
    }

    await waitFor(() => expect(comparisonReads).toBe(2));
    expect(screen.queryByText("Comparison inputs need approval.")).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(mutation === "save"
      ? "/api/quotes/quote-1" : "/api/quotes/quote-1/confirm", expect.objectContaining({ method: mutation === "save" ? "PATCH" : "POST" }));
  });

  it("shows an uploaded PDF awaiting extraction without review or confirmation controls", async () => {
    const pdfQuote = {
      id: "quote-pdf", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 0, confirmed_at: null, notes: null, values: {},
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/suppliers") ? jsonResponse({ suppliers: [supplier] }) : jsonResponse([pdfQuote]),
    )));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText("Processing PDF quote…")).toBeInTheDocument();
    expect(screen.queryByText("Review normalized values")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review for confirmation" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm Quote" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create manual quote" })).not.toBeInTheDocument();
  });

  it("uploads a PDF and shows processing without later review controls", async () => {
    let quote: Record<string, unknown> | null = null;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes/upload")) {
        expect(init?.body).toBeInstanceOf(FormData);
        quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
          revision: 0, confirmed_at: null, notes: null, values: {} };
        return Promise.resolve(jsonResponse({ quote, document: {} }, 201));
      }
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse(quote ? [quote] : []));
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Upload PDF" }));
    const upload = await screen.findByLabelText("Upload PDF quote");
    fireEvent.change(upload, { target: { files: [new File(["%PDF-"], "quote.pdf", { type: "application/pdf" })] } });
    expect(await screen.findByText("Processing PDF quote…")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm Quote" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit draft" })).not.toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/quotes/upload", expect.objectContaining({ method: "POST" }));
  });

  it.each(["NEEDS_REVIEW", "FAILED"])("shows PDF %s recovery or review controls", async (status) => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/suppliers") ? jsonResponse({ suppliers: [supplier] }) : jsonResponse([{
        id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status,
        revision: 0, confirmed_at: null, notes: null, values: {},
      }]),
    )));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText(status === "FAILED" ? "We couldn't reliably extract this quotation." : "PDF quote needs review.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm Quote" })).not.toBeInTheDocument();
    expect(Boolean(screen.queryByRole("button", { name: "Review for confirmation" }))).toBe(status === "NEEDS_REVIEW");
    expect(Boolean(screen.queryByRole("button", { name: "Enter quote manually" }))).toBe(status === "FAILED");
  });

  it("keeps PDF source, AI extraction, and corrected draft distinct", async () => {
    const evidence = [{ block_id: "p1-b5", page: 1,
      block_text: "Unit price: USD 4.22", evidence_value: "4.22" }];
    let quote = {
      id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: null,
      values: {
        unit_price: { current_value: "4.22", current_origin: "AI_EXTRACTED",
          ai_extracted_value: "4.22", uncertainty: null, evidence, conflicting_values: [] },
        shipping_cost: { current_value: null as string | null, current_origin: "AI_EXTRACTED",
          ai_extracted_value: null, uncertainty: null, review_state: "UNKNOWN",
          evidence: [], conflicting_values: [] },
      },
    };
    const patches: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/pdf-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/pdf-1") && init?.method === "PATCH") {
        patches.push(JSON.parse(String(init.body)) as Record<string, unknown>);
        quote = { ...quote, values: {
          ...quote.values,
          unit_price: { ...quote.values.unit_price, current_value: "4.50", current_origin: "USER_CORRECTED" },
          shipping_cost: { ...quote.values.shipping_cost, current_value: "12.00", current_origin: "USER_CORRECTED" },
        } };
        return Promise.resolve(jsonResponse(quote));
      }
      throw new Error(`Unexpected request: ${path}`);
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "View source evidence for Unit price" }));
    expect(await screen.findByText("Unit price: USD 4.22")).toBeInTheDocument();
    expect(screen.getByText("AI extracted value: 4.22")).toBeInTheDocument();
    expect(screen.getByText("Associated extracted value: 4.22")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.getByText("Extraction: Unknown")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit PDF draft" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.50" } });
    fireEvent.change(screen.getByLabelText("Shipping cost"), { target: { value: "12.00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patches).toEqual([{
      values: { unit_price: "4.50", shipping_cost: "12.00" },
    }]));
    expect(await screen.findByText("Current draft value: 4.50")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View source evidence for Unit price" }));
    expect(screen.getByText("AI extracted value: 4.22")).toBeInTheDocument();
    expect(screen.getByText("Unit price: USD 4.22")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm Quote" })).not.toBeInTheDocument();
  });

  it("shows conflict citations and discards or reports failed PDF edits", async () => {
    const quote = {
      id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: null,
      values: { production_lead_time: {
        current_value: null, current_origin: "AI_EXTRACTED", ai_extracted_value: null,
        uncertainty: "Contradictory production times", review_state: "CONFLICT", evidence: [],
        conflicting_values: [
          { value: "25 days", evidence: [{ block_id: "p1-b10", page: 1,
            block_text: "Production: 25 days", evidence_value: "25 days" }] },
          { value: "30-35 days", evidence: [{ block_id: "p2-b3", page: 2,
            block_text: "Production: 30-35 days", evidence_value: "30-35 days" }] },
        ],
      } },
    };
    const patches: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/pdf-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/pdf-1") && init?.method === "PATCH") {
        patches.push(JSON.parse(String(init.body)) as Record<string, unknown>);
        return Promise.resolve(jsonResponse({ error: { code: "QUOTE_NOT_EDITABLE", message: "Save failed." } }, 409));
      }
      throw new Error(`Unexpected request: ${path}`);
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "View source evidence for Production lead time" }));
    expect(await screen.findByText("Production: 25 days")).toBeInTheDocument();
    expect(screen.getByText("Production: 30-35 days")).toBeInTheDocument();
    expect(screen.getAllByText("Uncertainty: Contradictory production times").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    fireEvent.click(screen.getByRole("button", { name: "Edit PDF draft" }));
    fireEvent.change(screen.getByLabelText("Production lead time"), { target: { value: "25 days" } });
    fireEvent.click(screen.getByRole("button", { name: /Cancel editing|Discard unsaved quote edits/ }));
    expect(patches).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Edit PDF draft" }));
    expect((screen.getByLabelText("Production lead time") as HTMLInputElement).value).toBe("");
    fireEvent.change(screen.getByLabelText("Production lead time"), { target: { value: "25 days" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Save failed.")).toBeInTheDocument();
    expect(patches).toEqual([{ values: { production_lead_time: "25 days" } }]);
    expect(screen.getAllByText("Current draft value: Not set").length).toBeGreaterThan(0);
  });

  it("renders legacy null extraction as indeterminate while retaining known values", async () => {
    const quote = {
      id: "pdf-legacy", supplier_id: supplier.id, entry_type: "PDF", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: null,
      values: {
        unit_price: { current_value: "4.22", current_origin: "AI_EXTRACTED",
          ai_extracted_value: "4.22", review_state: "KNOWN", evidence: [], conflicting_values: [] },
        production_lead_time: { current_value: null, current_origin: "AI_EXTRACTED",
          ai_extracted_value: null, review_state: "UNAVAILABLE", evidence: [], conflicting_values: [] },
      },
    };
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/suppliers") ? jsonResponse({ suppliers: [supplier] }) : jsonResponse([quote]),
    )));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "View source evidence for Unit price" }));
    expect(await screen.findByText("AI extracted value: 4.22")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.getByText("Extraction: Known")).toBeInTheDocument();
    expect(screen.getAllByText("Extraction: Indeterminate (source evidence unavailable)").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "View source evidence for Production lead time" }));
    expect(screen.getByText("AI extracted value: Indeterminate")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(screen.getAllByText("Current draft value: Not set").length).toBeGreaterThan(0);
  });

  it("polls while processing and stops after completion or deactivation", async () => {
    let status = "PROCESSING";
    let quoteReads = 0;
    const paths: string[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      paths.push(path);
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      const quote = {
        id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status,
        revision: 0, confirmed_at: null, notes: null, values: {},
      };
      if (path.endsWith("/quotes/pdf-1")) { quoteReads += 1; return Promise.resolve(jsonResponse(quote)); }
      return Promise.resolve(jsonResponse([quote]));
    }));
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText("Processing PDF quote…")).toBeInTheDocument();
    status = "NEEDS_REVIEW";
    expect(await screen.findByText("PDF quote needs review.", {}, { timeout: 3500 })).toBeInTheDocument();
    expect(paths).toContain("/api/quotes/pdf-1");
    const readsAtCompletion = quoteReads;
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 2200)); });
    expect(quoteReads).toBe(readsAtCompletion);
    view.rerender(<QuoteReview projectId="project-1" active={false} refreshKey={0} />);
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 2200)); });
    expect(quoteReads).toBe(readsAtCompletion);
  }, 10000);

  it("ignores a poll response from before the Quotes page was deactivated", async () => {
    const processingQuote = {
      id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 0, confirmed_at: null, notes: null, values: {},
    };
    let resolveOldPoll!: (response: Response) => void;
    const oldPoll = new Promise<Response>((resolve) => { resolveOldPoll = resolve; });
    let quoteReads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes/pdf-1")) {
        quoteReads += 1;
        return quoteReads === 1 ? oldPoll : Promise.resolve(jsonResponse(processingQuote));
      }
      return Promise.resolve(jsonResponse([processingQuote]));
    }));

    vi.useFakeTimers();
    const view = render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await act(async () => {});
    expect(screen.getByText("Processing PDF quote…")).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(quoteReads).toBe(1);

    view.rerender(<QuoteReview projectId="project-1" active={false} refreshKey={0} />);
    await act(async () => { resolveOldPoll(jsonResponse({ ...processingQuote, status: "NEEDS_REVIEW" })); });
    view.rerender(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(quoteReads).toBe(2);
    expect(screen.getByText("Processing PDF quote…")).toBeInTheDocument();
  });

  it.each(["NEEDS_REVIEW", "FAILED"])("keeps a newer %s result when an older poll returns PROCESSING", async (terminalStatus) => {
    const processingQuote = {
      id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "PROCESSING",
      revision: 0, confirmed_at: null, notes: null, values: {},
    };
    let resolveOldPoll!: (response: Response) => void;
    const oldPoll = new Promise<Response>((resolve) => { resolveOldPoll = resolve; });
    let quoteReads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes/pdf-1")) {
        quoteReads += 1;
        return quoteReads === 1 ? oldPoll : Promise.resolve(jsonResponse({ ...processingQuote, status: terminalStatus }));
      }
      return Promise.resolve(jsonResponse([processingQuote]));
    }));

    vi.useFakeTimers();
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    await act(async () => {});
    expect(screen.getByText("Processing PDF quote…")).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(4000); });
    expect(quoteReads).toBe(2);
    expect(screen.getByText(terminalStatus === "FAILED" ? "We couldn't reliably extract this quotation." : "PDF quote needs review.")).toBeInTheDocument();

    await act(async () => { resolveOldPoll(jsonResponse(processingQuote)); });
    expect(screen.queryByText("Processing PDF quote…")).not.toBeInTheDocument();
    expect(screen.getByText(terminalStatus === "FAILED" ? "We couldn't reliably extract this quotation." : "PDF quote needs review.")).toBeInTheDocument();
  });

  it("creates an all-unknown draft, edits it, and explicitly confirms it", async () => {
    let quote: Record<string, unknown> | null = null;
    const requests: { path: string; body: Record<string, unknown> }[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) as Record<string, unknown> : {};
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes") && !init?.method) return Promise.resolve(jsonResponse(quote ? [quote] : []));
      if (path.endsWith("/quotes/manual")) {
        requests.push({ path, body });
        quote = {
          id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
          revision: 0, confirmed_at: null, notes: null, values: {},
        };
        return Promise.resolve(jsonResponse(quote, 201));
      }
      if (path.endsWith("/quotes/quote-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/quote-1") && init?.method === "PATCH") {
        requests.push({ path, body });
        quote = { ...quote, values: { unit_price: {
          current_value: "4.25", current_origin: "USER_ENTERED", ai_extracted_value: null,
        } } };
        return Promise.resolve(jsonResponse(quote));
      }
      if (path.endsWith("/confirm")) {
        quote = { ...quote, status: "CONFIRMED", confirmed_at: "2026-09-26T00:00:00Z" };
        return Promise.resolve(jsonResponse(quote));
      }
      return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "Missing" } }, 404));
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Enter manually" }));
    fireEvent.click(await screen.findByRole("button", { name: "Create manual quote" }));
    expect(await screen.findByText("Status: NEEDS REVIEW")).toBeInTheDocument();
    expect(requests[0].body).toMatchObject({ supplier_id: supplier.id, values: {} });
    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.25" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(requests[1].body).toEqual({ values: { unit_price: "4.25" } }));
    expect(await screen.findByText("4.25")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review for confirmation" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm Quote" }));
    expect(await screen.findByText(/Confirmed manual quote/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit draft" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Edit confirmed quote" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "5.00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save quote" }));
    await waitFor(() => expect(requests[2].body).toEqual({ values: { unit_price: "5.00" } }));
  });

  it("discards every cancelled field and note without saving them later", async () => {
    const savedValues = {
      unit_price: { current_value: "4.25", current_origin: "USER_ENTERED", ai_extracted_value: null },
      currency: { current_value: "USD", current_origin: "USER_ENTERED", ai_extracted_value: null },
      quoted_quantity: { current_value: null, current_origin: "UNKNOWN", ai_extracted_value: null },
    };
    const quote = {
      id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: "Saved note", values: savedValues,
    };
    const changes = [
      ["Quoted quantity", "100"], ["Unit price", "5.50"],
      ["Original currency (three-letter code)", "EUR"], ["Minimum order quantity", "50"],
      ["Sample cost", "1"], ["Tooling or setup cost", "2"], ["Packaging cost", "3"],
      ["Shipping cost", "4"], ["Sample lead time", "1 week"],
      ["Production lead time", "2 weeks"], ["Shipping time", "3 weeks"],
      ["Total stated lead time", "4 weeks"], ["Payment terms", "Net 30"],
      ["Incoterm", "FOB"], ["Quote validity", "30 days"], ["Warranty", "1 year"],
      ["Certifications", "ISO"], ["Compliance notes", "Compliant"],
      ["Exclusions", "None"], ["Special conditions", "Special"],
      ["Supplier notes", "Supplier note"],
    ] as const;
    const patches: Record<string, unknown>[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes") && !init?.method) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/quote-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/quote-1") && init?.method === "PATCH") {
        patches.push(JSON.parse(String(init.body)) as Record<string, unknown>);
        return Promise.resolve(jsonResponse(quote));
      }
      return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "Missing" } }, 404));
    }));

    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    for (const [label, value] of changes) {
      fireEvent.change(screen.getByLabelText(label), { target: { value } });
    }
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Cancelled note" } });
    fireEvent.click(screen.getByRole("button", { name: /Cancel editing|Discard unsaved quote edits/ }));
    expect(patches).toHaveLength(0);

    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    for (const [label] of changes) {
      const expected = label === "Unit price" ? "4.25" :
        label === "Original currency (three-letter code)" ? "USD" : "";
      expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe(expected);
    }
    expect((screen.getByLabelText("Quote notes") as HTMLTextAreaElement).value).toBe("Saved note");
    fireEvent.change(screen.getByLabelText("Shipping cost"), { target: { value: "7" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(patches).toEqual([{ values: { shipping_cost: "7" } }]));
  });

  it("keeps edits after a failed save until the user cancels them", async () => {
    const quote = {
      id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: null,
      values: { unit_price: { current_value: null, current_origin: "UNKNOWN", ai_extracted_value: null } },
    };
    let patches = 0;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes") && !init?.method) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/quote-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/quote-1") && init?.method === "PATCH") {
        patches += 1;
        return Promise.resolve(jsonResponse({ error: { code: "UNAVAILABLE", message: "Save failed" } }, 503));
      }
      return Promise.resolve(jsonResponse({ error: { code: "NOT_FOUND", message: "Missing" } }, 404));
    }));

    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Edit draft" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "5" } });
    fireEvent.change(screen.getByLabelText("Quote notes"), { target: { value: "Unsaved" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(await screen.findByText("Save failed")).toBeInTheDocument();
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("5");
    expect((screen.getByLabelText("Quote notes") as HTMLTextAreaElement).value).toBe("Unsaved");
    fireEvent.click(screen.getByRole("button", { name: /Cancel editing|Discard unsaved quote edits/ }));
    fireEvent.click(screen.getByRole("button", { name: "Edit draft" }));
    expect((screen.getByLabelText("Unit price") as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText("Quote notes") as HTMLTextAreaElement).value).toBe("");
    expect(screen.queryByText("Save failed")).not.toBeInTheDocument();
    expect(patches).toBe(1);
  });

  it("shows a retry when quotes cannot load", async () => {
    let fails = true;
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/suppliers") ? jsonResponse({ suppliers: [supplier] }) :
      fails ? jsonResponse({ error: { code: "UNAVAILABLE", message: "Quotes unavailable" } }, 503) : jsonResponse([]),
    )));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText("Quotes unavailable")).toBeInTheDocument();
    fails = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry quotes" }));
    fireEvent.click(await screen.findByRole("button", { name: "Enter manually" }));
    expect(await screen.findByRole("button", { name: "Create manual quote" })).toBeInTheDocument();
  });

  it("confirms a reviewed PDF and edits its confirmed current value", async () => {
    const onQuoteChange = vi.fn();
    let quote = {
      id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "NEEDS_REVIEW",
      revision: 0, confirmed_at: null as string | null, notes: null,
      values: { unit_price: { current_value: "4.22", current_origin: "AI_EXTRACTED",
        ai_extracted_value: "4.22", review_state: "KNOWN",
        evidence: [{ block_id: "p1-b5", page: 1, block_text: "Unit price: USD 4.22", evidence_value: "4.22" }] } },
    };
    const writes: { path: string; body?: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/confirm")) {
        writes.push({ path });
        quote = { ...quote, status: "CONFIRMED", confirmed_at: "2026-09-28T00:00:00Z" };
        return Promise.resolve(jsonResponse(quote));
      }
      if (path.endsWith("/quotes/pdf-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (path.endsWith("/quotes/pdf-1") && init?.method === "PATCH") {
        writes.push({ path, body: JSON.parse(String(init.body)) as unknown });
        quote = { ...quote, revision: 1, values: { unit_price: {
          ...quote.values.unit_price, current_value: "4.50", current_origin: "USER_CORRECTED",
        } } };
        return Promise.resolve(jsonResponse(quote));
      }
      throw new Error(`Unexpected request: ${path}`);
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={onQuoteChange} />);
    expect(await screen.findByText("PDF quote needs review.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review for confirmation" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm Quote" }));
    expect(await screen.findByText(/Confirmed PDF quote/)).toBeInTheDocument();
    await waitFor(() => expect(onQuoteChange).toHaveBeenCalledTimes(1));
    fireEvent.click(screen.getByRole("button", { name: "Edit confirmed PDF quote" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.50" } });
    fireEvent.click(screen.getByRole("button", { name: "Save quote" }));
    await waitFor(() => expect(writes).toEqual([
      { path: "/api/quotes/pdf-1/confirm" },
      { path: "/api/quotes/pdf-1", body: { values: { unit_price: "4.50" } } },
    ]));
    expect(await screen.findByText("Current confirmed value: 4.50")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "View source evidence for Unit price" }));
    expect(screen.getByText("Unit price: USD 4.22")).toBeInTheDocument();
    await waitFor(() => expect(onQuoteChange).toHaveBeenCalledTimes(2));
  });

  it.each(["save", "confirm"])("notifies comparison after a successful %s before a failing quote reload settles", async (mutation) => {
    const onQuoteChange = vi.fn();
    const quote = {
      id: "quote-1", supplier_id: supplier.id, entry_type: "MANUAL",
      status: mutation === "save" ? "CONFIRMED" : "NEEDS_REVIEW",
      revision: 0, confirmed_at: null, notes: null,
      values: { unit_price: { current_value: "4.25", current_origin: "USER_ENTERED", ai_extracted_value: null } },
    };
    let quoteReads = 0;
    let finishReload: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes") && !init?.method) {
        quoteReads += 1;
        return quoteReads === 1 ? Promise.resolve(jsonResponse([quote]))
          : new Promise<Response>((resolve) => { finishReload = resolve; });
      }
      if (path.endsWith("/quotes/quote-1") && !init?.method) return Promise.resolve(jsonResponse(quote));
      if (init?.method === "PATCH" || path.endsWith("/confirm")) return Promise.resolve(jsonResponse(quote));
      throw new Error(`Unexpected request: ${path}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<QuoteReview projectId="project-1" active refreshKey={0} onQuoteChange={onQuoteChange} />);
    if (mutation === "save") {
      fireEvent.click(await screen.findByRole("button", { name: "Edit confirmed quote" }));
      fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.50" } });
      fireEvent.click(screen.getByRole("button", { name: "Save quote" }));
    } else {
      fireEvent.click(await screen.findByRole("button", { name: "Review for confirmation" }));
      fireEvent.click(screen.getByRole("button", { name: "Confirm Quote" }));
    }
    await waitFor(() => expect(quoteReads).toBe(2));
    expect(onQuoteChange).toHaveBeenCalledTimes(1);
    expect(finishReload).toBeDefined();
    await act(async () => { finishReload?.(jsonResponse({ error: { code: "SERVER_ERROR", message: "Quote list unavailable." } }, 500)); });
    expect(onQuoteChange).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("alert")).toHaveTextContent("Saved; quotes could not refresh.");
  });

  it("offers only retry for stale PDF processing", async () => {
    let quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "STALE_PROCESSING",
      revision: 0, confirmed_at: null, notes: null, values: {} };
    const retries: string[] = [];
    let fail = true;
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes")) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/retry") && init?.method === "POST") {
        retries.push(path);
        if (fail) return Promise.resolve(jsonResponse({
          error: { code: "RETRY_UNAVAILABLE", message: "Retry unavailable" },
        }, 503));
        quote = { ...quote, status: "PROCESSING" };
        return Promise.resolve(jsonResponse(quote));
      }
      throw new Error(`Unexpected request: ${path}`);
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText("Processing was interrupted. Retry quote processing.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Upload a clearer PDF")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enter quote manually" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry processing" }));
    expect(await screen.findByText("Retry unavailable")).toBeInTheDocument();
    fail = false;
    fireEvent.click(screen.getByRole("button", { name: "Retry processing" }));
    expect(await screen.findByText("Processing PDF quote…")).toBeInTheDocument();
    expect(screen.queryByText("Retry unavailable")).not.toBeInTheDocument();
    expect(retries).toEqual(["/api/quotes/pdf-1/retry", "/api/quotes/pdf-1/retry"]);
  });

  it("replaces a failed PDF or converts it to a manual draft", async () => {
    let quote = { id: "pdf-1", supplier_id: supplier.id, entry_type: "PDF", status: "FAILED",
      revision: 0, confirmed_at: null, notes: null, values: {} };
    const writes: { path: string; body?: unknown }[] = [];
    vi.stubGlobal("fetch", vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/suppliers")) return Promise.resolve(jsonResponse({ suppliers: [supplier] }));
      if (path.endsWith("/quotes") && !init?.method) return Promise.resolve(jsonResponse([quote]));
      if (path.endsWith("/quotes/upload")) {
        writes.push({ path });
        return Promise.resolve(jsonResponse({ quote: { ...quote, status: "PROCESSING" }, document: {} }, 201));
      }
      if (path.endsWith("/manual-fallback")) {
        writes.push({ path, body: JSON.parse(String(init?.body)) as unknown });
        quote = { ...quote, entry_type: "MANUAL", status: "NEEDS_REVIEW",
          values: { unit_price: { current_value: "4.75", current_origin: "USER_ENTERED",
            ai_extracted_value: null } } };
        return Promise.resolve(jsonResponse(quote));
      }
      throw new Error(`Unexpected request: ${path}`);
    }));
    render(<QuoteReview projectId="project-1" active refreshKey={0} />);
    expect(await screen.findByText("We couldn't reliably extract this quotation.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Upload a clearer PDF"), {
      target: { files: [new File(["%PDF-"], "clearer.pdf", { type: "application/pdf" })] },
    });
    await waitFor(() => expect(writes[0]).toEqual({ path: "/api/projects/project-1/quotes/upload" }));
    fireEvent.click(screen.getByRole("button", { name: "Enter quote manually" }));
    fireEvent.change(screen.getByLabelText("Unit price"), { target: { value: "4.75" } });
    fireEvent.click(screen.getByRole("button", { name: "Save manual draft" }));
    await waitFor(() => expect(writes[1]).toEqual({
      path: "/api/quotes/pdf-1/manual-fallback", body: { values: { unit_price: "4.75" }, notes: null },
    }));
    expect(await screen.findByText("Status: NEEDS REVIEW")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review for confirmation" })).toBeInTheDocument();
  });
});
