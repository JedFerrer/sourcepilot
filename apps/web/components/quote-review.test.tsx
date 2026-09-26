import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { QuoteReview } from "./quote-review";
import { jsonResponse } from "../test/api-responses";

const supplier = { id: "supplier-1", name: "Fictional Bags", shortlisted: true, dismissed: false };

describe("QuoteReview", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

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
    fireEvent.click(screen.getByRole("button", { name: "Cancel editing" }));
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
    fireEvent.click(screen.getByRole("button", { name: "Cancel editing" }));
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
    expect(await screen.findByRole("button", { name: "Create manual quote" })).toBeInTheDocument();
  });
});
