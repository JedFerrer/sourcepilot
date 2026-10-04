"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type QuoteEvidence = { block_id: string; page: number; block_text: string; evidence_value: string | number | null };
type QuoteField = {
  current_value: string | number | null; current_origin: string;
  ai_extracted_value: string | number | null; uncertainty?: string | null;
  review_state?: "KNOWN" | "UNKNOWN" | "CONFLICT" | "UNAVAILABLE";
  evidence?: QuoteEvidence[];
  conflicting_values?: { value: string | number; evidence: QuoteEvidence[] }[];
};
type Quote = {
  id: string; supplier_id: string; entry_type: string; status: string;
  revision: number; confirmed_at: string | null; notes: string | null;
  values: Record<string, QuoteField>;
  processing?: { status: string; attempts: number; started_at: string | null; completed_at: string | null; failure: string | null } | null;
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

function displayValue(value: string | number | null | undefined): string {
  return value == null ? "Unknown" : String(value);
}

function SourceCitations({ evidence }: { evidence: QuoteEvidence[] }) {
  return <ul>{evidence.map((source, index) => <li key={`${source.block_id}-${index}`}>
    <p>Page {source.page}, block {source.block_id}</p>
    <blockquote>{source.block_text}</blockquote>
    {source.evidence_value != null ?
      <p>Associated extracted value: {displayValue(source.evidence_value)}</p> : null}
  </li>)}</ul>;
}

function ManualQuoteCard({ projectId, supplier, quote, onSaved }: {
  projectId: string; supplier: Supplier; quote?: Quote; onSaved: () => Promise<void>;
}) {
  const [values, setValues] = useState<Record<string, string>>(() => draftFromQuote(quote));
  const [notes, setNotes] = useState(quote?.notes ?? "");
  const [editing, setEditing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [fallbackEditing, setFallbackEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
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
      if (quote && fallbackEditing) {
        const entered = Object.fromEntries(fields.filter(({ key }) => values[key]?.trim())
          .map((field) => [field.key, parseField(field, values[field.key])]));
        await apiRequest(`/api/quotes/${quote.id}/manual-fallback`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ values: entered, notes: notes.trim() || null }),
        });
      } else if (quote) {
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
      setFallbackEditing(false);
      setReviewing(quote?.entry_type !== "PDF" || fallbackEditing);
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

  async function retryProcessing() {
    if (!quote) return;
    setBusy(true);
    setError(null);
    try {
      await apiRequest(`/api/quotes/${quote.id}/retry`, { method: "POST" });
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setBusy(false);
    }
  }

  async function uploadPdf(file: File) {
    setUploading(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("supplier_id", supplier.id);
      body.append("file", file);
      await apiRequest(`/api/projects/${projectId}/quotes/upload`, { method: "POST", body });
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
    } finally {
      setUploading(false);
    }
  }

  function cancelEditing() {
    setValues(draftFromQuote(quote));
    setNotes(quote?.notes ?? "");
    setError(null);
    setEditing(false);
    setFallbackEditing(false);
  }

  const showForm = !quote || ((quote.status === "NEEDS_REVIEW" || quote.status === "CONFIRMED") && editing)
    || fallbackEditing;
  return <article className="supplier-card">
    <h3>{supplier.name}</h3>
    <p>Status: {quote ? quote.status.replaceAll("_", " ") : "Not Added"}</p>
    {quote?.entry_type === "PDF" && quote.status === "PROCESSING" ?
      <p role="status">Processing PDF quote…</p> : null}
    {quote?.entry_type === "PDF" && quote.status === "STALE_PROCESSING" ? <>
      <p role="alert">Processing was interrupted. Retry quote processing.</p>
      <button type="button" disabled={busy} onClick={() => void retryProcessing()}>
        {busy ? "Retrying…" : "Retry processing"}
      </button>
    </> : null}
    {quote?.entry_type === "PDF" && (quote.status === "NEEDS_REVIEW" || quote.status === "CONFIRMED") ?
      <>
        {quote.status === "NEEDS_REVIEW" ? <p role="status">PDF quote needs review.</p> :
          <p role="status">Confirmed PDF quote. Current values are ready for comparison.</p>}
        <p>Review the PDF source, AI extraction, and current values.</p>
        <dl>{fields.map((field) => {
          const value = quote.values[field.key];
          const alternatives = value?.conflicting_values ?? [];
          const sources = value?.evidence ?? [];
          const reviewState = value?.review_state ??
            (alternatives.length >= 2 ? "CONFLICT" :
              value?.ai_extracted_value == null ? "UNAVAILABLE" : "KNOWN");
          return <div key={field.key}>
            <dt>{field.label}</dt>
            <dd>
              <p>Extraction: {reviewState === "UNAVAILABLE" ? "Indeterminate (source evidence unavailable)" :
                reviewState === "CONFLICT" ? "Conflict" :
                  reviewState === "UNKNOWN" ? "Unknown" : "Known"}</p>
              <p>AI extracted value: {value?.ai_extracted_value == null && reviewState === "CONFLICT" ?
                "No single value" : value?.ai_extracted_value == null && reviewState === "UNAVAILABLE" ?
                  "Indeterminate" : displayValue(value?.ai_extracted_value)}</p>
              <p>Current {quote.status === "CONFIRMED" ? "confirmed" : "draft"} value: {value?.current_value == null && reviewState !== "UNKNOWN" ?
                "Not set" : displayValue(value?.current_value)}</p>
              <p>Current origin: {value?.current_origin?.replaceAll("_", " ") ?? "Unknown"}</p>
              {value?.uncertainty ? <p>Uncertainty: {value.uncertainty}</p> : null}
              {alternatives.length >= 2 ? <div>
                <p>Conflicting PDF interpretations:</p>
                <ul>{alternatives.map((alternative, index) => <li key={index}>
                  <p>{displayValue(alternative.value)}</p>
                  <SourceCitations evidence={alternative.evidence} />
                </li>)}</ul>
              </div> : sources.length ? <div>
                <p>PDF source evidence:</p><SourceCitations evidence={sources} />
              </div> : <p>No saved source citations available for this field.</p>}
            </dd>
          </div>;
        })}</dl>
        <p>Notes: {quote.notes ?? "None"}</p>
        {!editing ? <button type="button" disabled={busy} onClick={() => setEditing(true)}>
          {quote.status === "CONFIRMED" ? "Edit confirmed PDF quote" : "Edit PDF draft"}
        </button> : null}
        {quote.status === "NEEDS_REVIEW" && !editing ? <>
          <button type="button" disabled={busy} onClick={() => setReviewing(true)}>Review for confirmation</button>
          {reviewing ? <div>
            <p>Confirm these normalized values as accurate enough to use in comparison. Unknown fields may remain.</p>
            <button type="button" disabled={busy} onClick={() => void confirm()}>{busy ? "Confirming…" : "Confirm Quote"}</button>
            <button type="button" disabled={busy} onClick={() => setReviewing(false)}>Continue reviewing</button>
          </div> : null}
        </> : null}
      </> : null}
    {quote?.entry_type === "PDF" && quote.status === "FAILED" ?
      <>
        <p role="alert">We couldn&apos;t reliably extract this quotation.</p>
        {!fallbackEditing ? <>
          <button type="button" disabled={busy} onClick={() => void retryProcessing()}>
            {busy ? "Retrying…" : "Retry processing"}
          </button>
          <label>Upload a clearer PDF
            <input type="file" accept=".pdf,application/pdf" disabled={uploading || busy}
              onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadPdf(file); }} />
          </label>
          <button type="button" disabled={busy} onClick={() => setFallbackEditing(true)}>
            Enter quote manually
          </button>
        </> : null}
      </> : null}
    {quote?.entry_type === "MANUAL" && quote.status === "CONFIRMED" ?
      <p role="status">Confirmed manual quote. Current values are ready for comparison.</p> : null}
    {error ? <p className="form-error" role="alert">{error}</p> : null}
    {quote && quote.entry_type === "MANUAL" && !showForm ? <>
      <h4>Review normalized values</h4>
      <dl>{fields.map((field) => <div key={field.key}>
        <dt>{field.label}</dt><dd>{quote.values[field.key]?.current_value ?? "Unknown"}</dd>
      </div>)}</dl>
      <p>Notes: {quote.notes ?? "None"}</p>
      {quote.status === "CONFIRMED" ? <button type="button" disabled={busy} onClick={() => setEditing(true)}>
        Edit confirmed quote
      </button> : null}
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
    {!quote ? <label>Upload PDF quote
      <input type="file" accept=".pdf,application/pdf" disabled={uploading || busy}
        onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadPdf(file); }} />
      {uploading ? "Uploading…" : null}
    </label> : null}
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
      <button type="submit" disabled={busy}>{busy ? "Saving…" : fallbackEditing ? "Save manual draft" :
        quote?.status === "CONFIRMED" ? "Save quote" : quote ? "Save draft" : "Create manual quote"}</button>
      {quote ? <button type="button" disabled={busy} onClick={cancelEditing}>Cancel editing</button> : null}
    </form> : null}
  </article>;
}

export function QuoteReview({ projectId, active, refreshKey, onQuoteChange }: {
  projectId: string; active: boolean; refreshKey: number; onQuoteChange?: () => void;
}) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async (silent = false, reconcileSaved = false) => {
    if (!active) return;
    if (!silent) { setLoading(true); setError(null); }
    try {
      const [supplierResult, quoteResult] = await Promise.all([
        apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`),
        apiRequest<Quote[]>(`/api/projects/${projectId}/quotes`),
      ]);
      setSuppliers(supplierResult.suppliers.filter((supplier) => supplier.shortlisted && !supplier.dismissed));
      // Unchanged reads must not reset unsaved card state. A save explicitly reconciles it.
      setQuotes((current) => quoteResult.map((quote) => {
        const previous = current.find((item) => item.id === quote.id);
        return !reconcileSaved && previous && JSON.stringify(previous) === JSON.stringify(quote)
          ? previous : quote;
      }));
    } catch (failure) {
      if (!silent) setError(errorMessage(failure));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [active, projectId]);

  useEffect(() => { void reload(); }, [reload, refreshKey]);

  async function savedQuote() {
    onQuoteChange?.();
    await reload(false, true);
  }

  useEffect(() => {
    const processingIds = quotes.filter((quote) => quote.entry_type === "PDF" && quote.status === "PROCESSING")
      .map((quote) => quote.id);
    if (!active || processingIds.length === 0) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      for (const id of processingIds) {
        void apiRequest<Quote>(`/api/quotes/${id}`).then((updated) => {
          if (cancelled) return;
          if (updated.status !== "PROCESSING") onQuoteChange?.();
          setQuotes((current) => current.map((quote) =>
            quote.id === id && quote.status === "PROCESSING" ? updated : quote));
        }).catch(() => { /* The next poll can recover a transient read failure. */ });
      }
    }, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [active, quotes, onQuoteChange]);

  return <section id="quotes" aria-labelledby="quotes-title">
    <h2 id="quotes-title">Quotes</h2>
    {!active ? <>
      <p>Approve the current shortlist before adding or reviewing quotes.</p>
      <a href="#shortlist-review">Review shortlist</a>
    </> : null}
    <div hidden={!active}>
      <div id="quotes-review" />
      {loading ? <p>Loading quotes…</p> : null}
      {error ? <div role="alert" className="form-error"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry quotes</button></div> : null}
      {!loading && !error && suppliers.length === 0 ? <p>No suppliers are currently shortlisted.</p> : null}
      <fieldset className="quote-controls" disabled={!active || loading || Boolean(error)}>
        {suppliers.map((supplier) => <ManualQuoteCard
          key={supplier.id} projectId={projectId} supplier={supplier}
          quote={quotes.find((quote) => quote.supplier_id === supplier.id)} onSaved={savedQuote}
        />)}
      </fieldset>
    </div>
  </section>;
}
