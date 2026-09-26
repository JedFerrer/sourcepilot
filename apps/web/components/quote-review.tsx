"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type QuoteField = { current_value: string | number | null; current_origin: string; ai_extracted_value: unknown | null };
type Quote = {
  id: string; supplier_id: string; entry_type: string; status: string;
  revision: number; confirmed_at: string | null; notes: string | null;
  values: Record<string, QuoteField>;
};
type Supplier = { id: string; name: string; shortlisted: boolean; dismissed: boolean };
type SupplierList = { suppliers: Supplier[] };
type Field = { key: string; label: string; kind: "number" | "money" | "currency" | "text" };

const fields: Field[] = [
  { key: "quoted_quantity", label: "Quoted quantity", kind: "number" },
  { key: "unit_price", label: "Unit price", kind: "money" },
  { key: "currency", label: "Original currency (three-letter code)", kind: "currency" },
  { key: "moq", label: "Minimum order quantity", kind: "number" },
  { key: "sample_cost", label: "Sample cost", kind: "money" },
  { key: "tooling_cost", label: "Tooling or setup cost", kind: "money" },
  { key: "packaging_cost", label: "Packaging cost", kind: "money" },
  { key: "shipping_cost", label: "Shipping cost", kind: "money" },
  { key: "sample_lead_time", label: "Sample lead time", kind: "text" },
  { key: "production_lead_time", label: "Production lead time", kind: "text" },
  { key: "shipping_time", label: "Shipping time", kind: "text" },
  { key: "total_lead_time", label: "Total stated lead time", kind: "text" },
  { key: "payment_terms", label: "Payment terms", kind: "text" },
  { key: "incoterm", label: "Incoterm", kind: "text" },
  { key: "quote_validity", label: "Quote validity", kind: "text" },
  { key: "warranty", label: "Warranty", kind: "text" },
  { key: "certifications", label: "Certifications", kind: "text" },
  { key: "compliance_notes", label: "Compliance notes", kind: "text" },
  { key: "exclusions", label: "Exclusions", kind: "text" },
  { key: "special_conditions", label: "Special conditions", kind: "text" },
  { key: "supplier_notes", label: "Supplier notes", kind: "text" },
];

function draftFromQuote(quote: Quote | undefined): Record<string, string> {
  return Object.fromEntries(fields.map(({ key }) => [key, String(quote?.values[key]?.current_value ?? "")]));
}

function parseField(field: Field, raw: string): string | number | null {
  const value = raw.trim();
  if (!value) return null;
  if (field.kind === "number") return Number(value);
  return value;
}

function errorMessage(error: unknown): string {
  return error instanceof ApiClientError ? error.message : "The quote could not be saved. Try again.";
}

function ManualQuoteCard({ projectId, supplier, quote, onSaved }: {
  projectId: string; supplier: Supplier; quote?: Quote; onSaved: () => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => draftFromQuote(quote));
  const [notes, setNotes] = useState(quote?.notes ?? "");
  const [editing, setEditing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setValues(draftFromQuote(quote));
    setNotes(quote?.notes ?? "");
  }, [quote]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (quote) {
        const changed = Object.fromEntries(fields.filter(({ key }) =>
          values[key] !== String(quote.values[key]?.current_value ?? "")
        ).map((field) => [field.key, parseField(field, values[field.key] ?? "")]));
        const body: { values: Record<string, string | number | null>; notes?: string | null } = { values: changed };
        if (notes !== (quote.notes ?? "")) body.notes = notes.trim() || null;
        await apiRequest(`/api/quotes/${quote.id}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
        });
      } else {
        const entered = Object.fromEntries(fields.filter(({ key }) => values[key]?.trim())
          .map((field) => [field.key, parseField(field, values[field.key])]));
        await apiRequest(`/api/projects/${projectId}/quotes/manual`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supplier_id: supplier.id, values: entered, notes: notes.trim() || null }),
        });
      }
      setEditing(false);
      setReviewing(true);
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    if (!quote) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest(`/api/quotes/${quote.id}/confirm`, { method: "POST" });
      setReviewing(false);
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  function cancelEditing() {
    setValues(draftFromQuote(quote));
    setNotes(quote?.notes ?? "");
    setError(null);
    setEditing(false);
  }

  const showForm = !quote || (quote.status === "NEEDS_REVIEW" && editing);
  return <article className="supplier-card">
    <h3>{supplier.name}</h3>
    <p>Status: {quote ? quote.status.replaceAll("_", " ") : "Not Added"}</p>
    {quote?.status === "CONFIRMED" ? <p role="status">Confirmed manual quote. Current values are ready for comparison.</p> : null}
    {error ? <p className="form-error" role="alert">{error}</p> : null}
    {quote && !showForm ? <>
      <h4>Review normalized values</h4>
      <dl>{fields.map((field) => <div key={field.key}>
        <dt>{field.label}</dt><dd>{quote.values[field.key]?.current_value ?? "Unknown"}</dd>
      </div>)}</dl>
      <p>Notes: {quote.notes ?? "None"}</p>
      {quote.status === "NEEDS_REVIEW" ? <>
        <button type="button" disabled={busy} onClick={() => setEditing(true)}>Edit draft</button>
        <button type="button" disabled={busy} onClick={() => setReviewing(true)}>Review for confirmation</button>
        {reviewing ? <div>
          <p>Confirm these normalized values as accurate enough to use in comparison. Unknown fields may remain.</p>
          <button type="button" disabled={busy} onClick={() => void confirm()}>{busy ? "Confirming…" : "Confirm Quote"}</button>
          <button type="button" disabled={busy} onClick={() => setReviewing(false)}>Continue reviewing</button>
        </div> : null}
      </> : null}
    </> : null}
    {showForm ? <form onSubmit={(event) => void save(event)}>
      <p>Leave a field blank if it is Unknown.</p>
      {fields.map((field) => <label key={field.key}>{field.label}
        <input
          type={field.kind === "number" || field.kind === "money" ? "number" : "text"}
          min={field.kind === "number" ? "1" : field.key === "unit_price" ? "0.0001" : field.kind === "money" ? "0" : undefined}
          step={field.kind === "number" ? "1" : field.kind === "money" ? "0.0001" : undefined}
          maxLength={field.kind === "currency" ? 3 : field.kind === "text" ? 10000 : undefined}
          value={values[field.key] ?? ""}
          onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
        />
      </label>)}
      <label>Quote notes<textarea maxLength={10000} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <button type="submit" disabled={busy}>{busy ? "Saving…" : quote ? "Save draft" : "Create manual quote"}</button>
      {quote ? <button type="button" disabled={busy} onClick={cancelEditing}>Cancel editing</button> : null}
    </form> : null}
  </article>;
}

export function QuoteReview({ projectId, active, refreshKey }: { projectId: string; active: boolean; refreshKey: number }) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!active) return;
    setLoading(true);
    setError(null);
    try {
      const [supplierResult, quoteResult] = await Promise.all([
        apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`),
        apiRequest<Quote[]>(`/api/projects/${projectId}/quotes`),
      ]);
      setSuppliers(supplierResult.suppliers.filter((supplier) => supplier.shortlisted && !supplier.dismissed));
      setQuotes(quoteResult);
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setLoading(false);
    }
  }, [active, projectId]);

  useEffect(() => { void reload(); }, [reload, refreshKey]);

  if (!active) return null;
  return <section aria-labelledby="quotes-title">
    <h2 id="quotes-title">Quotes</h2>
    {loading ? <p>Loading quotes…</p> : null}
    {error ? <div role="alert" className="form-error"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry quotes</button></div> : null}
    {!loading && !error && suppliers.length === 0 ? <p>No suppliers are currently shortlisted.</p> : null}
    {!loading && !error ? suppliers.map((supplier) => <ManualQuoteCard
      key={supplier.id} projectId={projectId} supplier={supplier}
      quote={quotes.find((quote) => quote.supplier_id === supplier.id)} onSaved={reload}
    />) : null}
  </section>;
}
