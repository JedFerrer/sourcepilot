"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

import { useRecordDraft } from "./use-record-draft";
import { DraftConflict, RecordSaveStatus } from "./record-save-status";
import { useDraftRegistration, useWorkspaceDrafts } from "./workspace-drafts";
import { sameRecord } from "../lib/record-draft";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { focusEditorTarget } from "../lib/editor-focus";

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

const fieldGroups = [
  { label: "Commercial", expanded: true, fields: fields.slice(0, 8).map((field) => field.key) },
  { label: "Timeline", expanded: true, fields: fields.slice(8, 12).map((field) => field.key) },
  { label: "Terms", expanded: false, fields: fields.slice(12, 16).map((field) => field.key) },
  { label: "Compliance", expanded: false, fields: fields.slice(16, 18).map((field) => field.key) },
  { label: "Other", expanded: false, fields: fields.slice(18).map((field) => field.key) },
];

function groupIssues(keys: string[], quote?: Quote): string {
  return fields.filter((field) => keys.includes(field.key)).flatMap((field) => {
    const value = quote?.values[field.key];
    const states = [value?.review_state === "CONFLICT" || (value?.conflicting_values?.length ?? 0) >= 2 ? "Conflict" : null,
      value?.uncertainty ? "Uncertainty" : null].filter(Boolean);
    return states.length ? [`${field.label}: ${states.join(" and ")}`] : [];
  }).join("; ");
}

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

function ProcessingStatus({ quoteId, onStatus }: { quoteId: string; onStatus: (quote: Quote) => void }) {
  const [failed, setFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const retry = useRef<() => void>(() => {});

  useEffect(() => {
    let cancelled = false;
    let sequence = 0;
    let settledSequence = 0;
    let retryPending = false;
    setPending(false);
    async function readStatus(explicit = false) {
      if (cancelled || (explicit && retryPending)) return;
      if (explicit) { retryPending = true; setPending(true); }
      const request = ++sequence;
      try {
        const updated = await apiRequest<Quote>(`/api/quotes/${quoteId}`);
        if (cancelled || request < settledSequence) return;
        settledSequence = request;
        setFailed(false);
        onStatus(updated);
      } catch {
        if (!cancelled && request >= settledSequence) {
          settledSequence = request;
          setFailed(true);
        }
      } finally {
        if (explicit) retryPending = false;
        if (!cancelled && explicit) setPending(false);
      }
    }
    retry.current = () => { void readStatus(true); };
    const timer = window.setInterval(() => { void readStatus(); }, 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [quoteId, onStatus]);

  return <>
    <p role="status">Processing PDF quote…</p>
    {failed ? <div role="alert">
      <p>We couldn&apos;t check this quote&apos;s processing status. The last known status is shown. Try checking again.</p>
      <button type="button" disabled={pending} onClick={() => retry.current()}>Retry status check</button>
    </div> : null}
  </>;
}

function ManualQuoteCard({ projectId, supplier, quote, onSaved, statusActive, onStatus }: {
  projectId: string; supplier: Supplier; quote?: Quote; onSaved: () => Promise<void>;
  statusActive: boolean; onStatus: (quote: Quote) => void;
}) {
  const incoming = useRef({ values: draftFromQuote(quote), notes: quote?.notes ?? "" });
  const next = { values: draftFromQuote(quote), notes: quote?.notes ?? "" };
  if (!sameRecord(incoming.current, next)) incoming.current = next;
  const record = useRecordDraft(incoming.current);
  const { values, notes } = record.state.draft;
  const setValues = (change: (current: Record<string, string>) => Record<string, string>) => record.edit((current) => ({ ...current, values: change(current.values) }));
  const setNotes = (value: string) => record.edit((current) => ({ ...current, notes: value }));
  const [editing, setEditing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [fallbackEditing, setFallbackEditing] = useState(false);
  const [entry, setEntry] = useState<"upload" | "manual" | null>(null);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [writeUncertain, setWriteUncertain] = useState(false);
  const [replacement, setReplacement] = useState<File | null>(null);
  const eligible = supplier.shortlisted && !supplier.dismissed;
  const [error, setError] = useState<string | null>(null);
  const [evidenceField, setEvidenceField] = useState<string | null>(null);
  const [large, setLarge] = useState(false);
  const writing = useRef(false);
  const recoverySequence = useRef(0);
  const recoveryHeading = useRef<HTMLHeadingElement>(null);
  const recoveryCard = useRef<HTMLElement>(null);
  const [recoveryResult, setRecoveryResult] = useState<{ message: string; version: number } | null>(null);
  useEffect(() => {
    if (!recoveryResult) return;
    if (!focusEditorTarget(recoveryHeading.current)) focusEditorTarget(recoveryCard.current);
  }, [recoveryResult]);
  function recoverWithFocus(choice: "saved" | "keep") {
    if (choice === "saved") acceptSavedRecord(); else keepDraft();
    setRecoveryResult(current => ({ version: (current?.version ?? 0) + 1,
      message: choice === "saved" ? "Saved record loaded. Review the quote before making further changes." : "Your edits are retained. Review them against the saved record before saving." }));
  }
  useEffect(() => {
    // Changed saved records and editor lifetimes supersede outstanding recovery reads.
    recoverySequence.current += 1;
    return () => { recoverySequence.current += 1; };
  }, [projectId, supplier.id, quote]);
  function acceptSavedRecord() {
    recoverySequence.current += 1;
    setError(null);
    record.dispatch({ type: "use-saved" });
  }
  function keepDraft() {
    recoverySequence.current += 1;
    setError(null);
    record.dispatch({ type: "reconcile", value: record.state.draft });
  }
  const evidenceTrigger = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const media = window.matchMedia("(min-width: 1280px)");
    const update = () => setLarge(media.matches); update();
    media.addEventListener("change", update); return () => media.removeEventListener("change", update);
  }, []);
  useDraftRegistration(`quote-${supplier.id}`, { label: `Quote · ${supplier.name}`, stage: "QUOTES", supplierId: supplier.id,
    dirty: record.dirty, pending: busy || uploading, uncertain: record.state.uncertain || writeUncertain, error,
    discard: acceptSavedRecord,
    check: checkSavedQuote,
  });
  async function checkSavedQuote() {
    const request = ++recoverySequence.current;
    try {
      const latest = quote ? await apiRequest<Quote>(`/api/quotes/${quote.id}`)
        : (await apiRequest<Quote[]>(`/api/projects/${projectId}/quotes`)).find((item) => item.supplier_id === supplier.id);
      if (request !== recoverySequence.current) return;
      setError(null);
      if (latest) onStatus(latest);
      // An unchanged read permits explicit reconciliation, not a failed-write inference.
      record.dispatch({ type: "receive", value: { values: draftFromQuote(latest), notes: latest?.notes ?? "" } });
    } catch (failure) {
      if (request !== recoverySequence.current) return;
      setError("Saved quote could not be checked. Your draft is retained; retry the read.");
      // The workspace departure check also needs to know a current read failed.
      throw failure;
    }
  }
  function quoteValues(value: typeof record.state.draft) {
    return <dl className="review-summary">{fields.map((field) => <div key={field.key}><dt>{field.label}</dt><dd>{value.values[field.key] || "Unknown"}</dd></div>)}<div><dt>Quote notes</dt><dd>{value.notes || "None"}</dd></div></dl>;
  }
  function openEvidence(key: string, trigger: HTMLElement) { evidenceTrigger.current = trigger; setEvidenceField(key); }
  function closeEvidence() { setEvidenceField(null); evidenceTrigger.current?.focus(); }
  const selectedField = fields.find((field) => field.key === evidenceField);
  const evidenceValue = evidenceField ? quote?.values[evidenceField] : undefined;
  const evidenceBody = selectedField ? <>
    <p>{supplier.name} · {selectedField.label}</p>
    <p>AI extracted value: {evidenceValue?.ai_extracted_value == null && evidenceValue?.review_state === "CONFLICT" ? "No single value" : evidenceValue?.ai_extracted_value == null && evidenceValue?.review_state !== "UNKNOWN" ? "Indeterminate" : displayValue(evidenceValue?.ai_extracted_value)}</p>
    <p>Saved current value: {displayValue(evidenceValue?.current_value)} · {evidenceValue?.current_origin?.replaceAll("_", " ") ?? "Unknown origin"}</p>
    <p>Your unsaved value: {record.dirty ? values[selectedField.key] || "Unknown" : "No unsaved correction"}</p>
    {evidenceValue?.uncertainty ? <p className="notice">Uncertainty: {evidenceValue.uncertainty}</p> : null}
    {evidenceValue?.conflicting_values?.length ? <div><h4>Conflicting PDF interpretations</h4>{evidenceValue.conflicting_values.map((value, index) => <section key={index}><p>{displayValue(value.value)}</p><SourceCitations evidence={value.evidence} /></section>)}</div> :
      evidenceValue?.evidence?.length ? <SourceCitations evidence={evidenceValue.evidence} /> : <p>No saved source citations available for this field.</p>}
    <p>Corrections change the current value. They never rewrite original evidence.</p>
  </> : null;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (writing.current || writeUncertain || !eligible) return;
    const submitted = record.begin(); if (!submitted) return;
    writing.current = true;
    setBusy(true);
    setError(null);
    try {
      let saved: Quote;
      if (quote && fallbackEditing) {
        const entered = Object.fromEntries(fields.filter(({ key }) => values[key]?.trim())
          .map((field) => [field.key, parseField(field, values[field.key])]));
        saved = await apiRequest<Quote>(`/api/quotes/${quote.id}/manual-fallback`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ values: entered, notes: notes.trim() || null }),
        });
      } else if (quote) {
        const changed = Object.fromEntries(fields.filter(({ key }) =>
          values[key] !== String(quote.values[key]?.current_value ?? "")
        ).map((field) => [field.key, parseField(field, values[field.key] ?? "")]));
        const body: { values: Record<string, string | number | null>; notes?: string | null } = { values: changed };
        if (notes !== (quote.notes ?? "")) body.notes = notes.trim() || null;
        saved = await apiRequest<Quote>(`/api/quotes/${quote.id}`, {
          method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
        });
      } else {
        const entered = Object.fromEntries(fields.filter(({ key }) => values[key]?.trim())
          .map((field) => [field.key, parseField(field, values[field.key])]));
        saved = await apiRequest<Quote>(`/api/projects/${projectId}/quotes/manual`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ supplier_id: supplier.id, values: entered, notes: notes.trim() || null }),
        });
      }
      record.dispatch({ type: "saved", value: saved?.values ? { values: draftFromQuote(saved), notes: saved.notes ?? "" } : submitted });
      setEditing(false);
      setFallbackEditing(false);
      setReviewing(false);
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
      record.dispatch({ type: "failed", message: errorMessage(failure), uncertain: failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code) });
    } finally {
      writing.current = false;
      setBusy(false);
    }
  }

  async function confirm() {
    if (!quote || !eligible || writeUncertain || writing.current || record.dirty || record.state.conflict || record.state.uncertain) return;
    writing.current = true;
    setBusy(true);
    setError(null);
    try {
      const latest = await apiRequest<Quote>(`/api/quotes/${quote.id}`);
      if (!sameRecord(latest, quote)) { onStatus(latest); setReviewing(false); setError("The saved quote changed. Review its current values before confirming again."); return; }
      await apiRequest(`/api/quotes/${quote.id}/confirm`, { method: "POST" });
      setReviewing(false);
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
      setWriteUncertain(failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code));
    } finally {
      writing.current = false;
      setBusy(false);
    }
  }

  async function retryProcessing() {
    if (!quote || writing.current || writeUncertain || !eligible || record.dirty) return;
    writing.current = true;
    setBusy(true);
    setError(null);
    try {
      await apiRequest(`/api/quotes/${quote.id}/retry`, { method: "POST" });
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
      setWriteUncertain(failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code));
    } finally {
      writing.current = false;
      setBusy(false);
    }
  }

  async function uploadPdf(file: File, discard = false) {
    if (writing.current || writeUncertain || !eligible) return;
    if (record.dirty && !discard) { setReplacement(file); return; }
    writing.current = true;
    setReplacement(null);
    setUploading(true);
    setError(null);
    try {
      const body = new FormData();
      body.append("supplier_id", supplier.id);
      body.append("file", file);
      await apiRequest(`/api/projects/${projectId}/quotes/upload`, { method: "POST", body });
      if (discard) record.dispatch({ type: "use-saved" });
      await onSaved();
    } catch (failure) {
      setError(errorMessage(failure));
      setWriteUncertain(failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code));
    } finally {
      writing.current = false;
      setUploading(false);
    }
  }

  function cancelEditing() {
    acceptSavedRecord();
    setEditing(false);
    setFallbackEditing(false);
  }

  const showForm = (!quote && entry === "manual") || ((quote?.status === "NEEDS_REVIEW" || quote?.status === "CONFIRMED") && editing)
    || fallbackEditing;
  return <article className="quote-card" ref={recoveryCard} tabIndex={-1} aria-label={`${supplier.name} quote editor`}>
    <Dialog open={reviewing} onOpenChange={setReviewing}><DialogContent className="approval-dialog"><DialogTitle>Review saved quote before confirmation</DialogTitle><DialogDescription>Confirm these normalized values as accurate enough to use in comparison. Unknown fields may remain. This review contains saved values only.</DialogDescription>
      <h3>{supplier.name}</h3>
      {quote ? quoteValues({ values: draftFromQuote(quote), notes: quote.notes ?? "" }) : null}
      {quote ? fields.filter((field) => quote.values[field.key]?.review_state === "CONFLICT" || quote.values[field.key]?.uncertainty).map((field) => <p className="issue-copy" key={field.key}>{field.label}: {quote.values[field.key]?.review_state === "CONFLICT" ? "Conflict—source interpretations disagree. " : ""}{quote.values[field.key]?.uncertainty}</p>) : null}
      {error ? <p role="alert" className="form-error">{error}</p> : null}
      <div className="review-actions"><button type="button" onClick={() => setReviewing(false)}>Continue reviewing</button><button type="button" className="primary-action" disabled={busy || !eligible || record.dirty || record.state.conflict || record.state.uncertain || writeUncertain} onClick={() => void confirm()}>{busy ? "Confirming…" : "Confirm Quote"}</button></div>
    </DialogContent></Dialog>
    <div className={evidenceField && large ? "quote-with-evidence" : "quote-layout"}><div className="quote-fields">
    <div className="record-heading"><h3 ref={recoveryHeading} tabIndex={-1}>{supplier.name}</h3><RecordSaveStatus savedVersion={record.savedVersion} dirty={record.dirty} pending={busy || uploading} error={record.state.error} conflict={record.state.conflict} /></div>
    <p className={recoveryResult ? undefined : "sr-only"} role="status" aria-label="Quote recovery" aria-atomic="true">{recoveryResult ? <span key={recoveryResult.version}>{recoveryResult.message}</span> : null}</p>
    {writeUncertain ? <p role="alert">Write outcome is uncertain. Check the saved quote before another write. <button type="button" onClick={async () => { try { if (quote) onStatus(await apiRequest<Quote>(`/api/quotes/${quote.id}`)); else await onSaved(); setWriteUncertain(false); setReviewing(false); } catch { setError("Saved state could not be checked. Try the read again."); } }}>Check write outcome</button></p> : null}
    <Dialog open={replacement !== null} onOpenChange={(open) => { if (!open) setReplacement(null); }}><DialogContent><DialogTitle>Replace this unsaved quote?</DialogTitle><DialogDescription>Your manual draft will be discarded only after the PDF upload succeeds.</DialogDescription><button type="button" onClick={() => setReplacement(null)}>Keep manual draft</button><button type="button" onClick={() => { if (replacement) void uploadPdf(replacement, true); }}>Discard draft and upload</button></DialogContent></Dialog>
    {!supplier.shortlisted || supplier.dismissed ? <p role="alert">This supplier is no longer eligible. Your unavailable draft is retained for copying or discarding. It cannot be saved unless the supplier is restored.</p> : null}
    {record.state.conflict ? <DraftConflict saved={quoteValues(record.state.remote)} draft={quoteValues(record.state.draft)} onUseSaved={() => recoverWithFocus("saved")} onKeepDraft={() => recoverWithFocus("keep")} /> : null}
    {record.state.uncertain ? <p role="alert">Save outcome not confirmed. Unchanged saved values do not prove the write failed; it may still complete. Check saved state, then deliberately review both records before choosing how to recover. Nothing is resubmitted automatically. <button type="button" onClick={() => void checkSavedQuote().catch(() => { /* Current errors are reported inside the guarded read. */ })}>Check saved quote</button></p> : null}
    <p>Status: {quote ? quote.status.replaceAll("_", " ") : "Not Added"}</p>
    {quote?.entry_type === "PDF" && quote.status === "PROCESSING" ?
      statusActive ? <ProcessingStatus key={`${projectId}-${quote.id}`} quoteId={quote.id} onStatus={onStatus} /> :
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
        {!showForm ? <p>Review the PDF source, AI extraction, and current values.</p> : null}
        <div hidden={showForm} className="quote-saved-groups">{fieldGroups.map((group) => <details className="quote-group" key={group.label} open={group.expanded}><summary>{group.label}{groupIssues(group.fields, quote) ? ` · ${groupIssues(group.fields, quote)}` : ""}</summary><dl className="quote-saved-values">{fields.filter((field) => group.fields.includes(field.key)).map((field) => {
          const value = quote.values[field.key];
          return <div key={field.key}><dt>{field.label}</dt><dd>
            <p className="field-origin">Extraction: {value?.review_state === "CONFLICT" || (value?.conflicting_values?.length ?? 0) >= 2 ? "Conflict" : value?.review_state === "UNKNOWN" ? "Unknown" : value?.ai_extracted_value == null ? "Indeterminate (source evidence unavailable)" : "Known"}</p>
            <p>Current {quote.status === "CONFIRMED" ? "confirmed" : "draft"} value: {value?.current_value == null && value?.review_state !== "UNKNOWN" ? "Not set" : displayValue(value?.current_value)}</p>
            <p className="field-origin">Current origin: {value?.current_origin?.replaceAll("_", " ") ?? "Unknown"}</p>
            {value?.review_state === "CONFLICT" || (value?.conflicting_values?.length ?? 0) >= 2 ? <p className="notice">Conflict: source interpretations disagree.</p> : null}
            {value?.uncertainty ? <p className="notice">Uncertainty: {value.uncertainty}</p> : null}
            {value?.current_value == null ? <p>Unknown—no current value saved.</p> : null}
            <button type="button" className="source-action" onClick={(event) => openEvidence(field.key, event.currentTarget)}>View source evidence for {field.label}</button>
          </dd></div>;
        })}</dl></details>)}</div>
        {!showForm ? <p>Notes: {quote.notes ?? "None"}</p> : null}
        <div className="actions quote-saved-actions" hidden={editing}>
        {!editing ? <button type="button" disabled={busy} onClick={() => setEditing(true)}>
          {quote.status === "CONFIRMED" ? "Edit confirmed PDF quote" : "Edit PDF draft"}
        </button> : null}
        {quote.status === "NEEDS_REVIEW" && !editing ? <>
          <button type="button" disabled={busy} onClick={() => setReviewing(true)}>Review for confirmation</button>

        </> : null}
        </div>
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
      <div className="manual-quote-summary">{fieldGroups.map((group) => <section className="quote-summary-group" aria-label={group.label} key={group.label}>
        <h5>{group.label}</h5>
        <dl className="quote-saved-values">{fields.filter((field) => group.fields.includes(field.key)).map((field) => <div className={["compliance_notes", "supplier_notes", "special_conditions", "exclusions"].includes(field.key) ? "quote-value-wide" : undefined} key={field.key}>
          <dt>{field.label}</dt><dd>{quote.values[field.key]?.current_value ?? "Unknown"}</dd>
        </div>)}</dl>
      </section>)}</div>
      {!showForm ? <p>Notes: {quote.notes ?? "None"}</p> : null}
      <div className="actions quote-saved-actions">
      {quote.status === "CONFIRMED" ? <button type="button" disabled={busy} onClick={() => setEditing(true)}>
        Edit confirmed quote
      </button> : null}
      {quote.status === "NEEDS_REVIEW" ? <>
        <button type="button" disabled={busy} onClick={() => setEditing(true)}>Edit draft</button>
        <button type="button" disabled={busy} onClick={() => setReviewing(true)}>Review for confirmation</button>

      </> : null}
      </div>
    </> : null}
    {!quote ? <div className="entry-choice"><button type="button" aria-pressed={entry === "upload"} onClick={() => setEntry("upload")}>Upload PDF</button><button type="button" aria-pressed={entry === "manual"} onClick={() => setEntry("manual")}>Enter manually</button></div> : null}
    {!quote && entry === "upload" ? <label>Upload PDF quote
      <input type="file" accept=".pdf,application/pdf" disabled={uploading || busy}
        onChange={(event) => { const file = event.target.files?.[0]; if (file) void uploadPdf(file); }} />
      {uploading ? "Uploading…" : null}
    </label> : null}
    {showForm ? <form onSubmit={(event) => void save(event)}>
      <p className="group-help">Leave a field blank if it is Unknown.</p>{quote?.status === "CONFIRMED" ? <p className="issue-copy">Saving corrections makes the comparison outdated.</p> : null}
      {fieldGroups.map((group) => <details className="quote-group" key={group.label} open={group.expanded}><summary>{group.label}{groupIssues(group.fields, quote) ? ` · ${groupIssues(group.fields, quote)}` : ""}</summary><div className="form-fields">{fields.filter((field) => group.fields.includes(field.key)).map((field) => <div key={field.key}><label>{field.label}
        <input
          type={field.kind === "number" || field.kind === "money" ? "number" : "text"}
          min={field.kind === "number" ? "1" : field.key === "unit_price" ? "0.0001" : field.kind === "money" ? "0" : undefined}
          step={field.kind === "number" ? "1" : field.kind === "money" ? "0.0001" : undefined}
          maxLength={field.kind === "currency" ? 3 : field.kind === "text" ? 10000 : undefined}
          value={values[field.key] ?? ""}
          onChange={(event) => setValues((current) => ({ ...current, [field.key]: event.target.value }))}
        />
        </label>
        {quote?.values[field.key]?.uncertainty ? <span className="field-warning">{quote.values[field.key].uncertainty}</span> : null}
        {quote?.values[field.key]?.review_state === "CONFLICT" ? <span className="field-warning">Conflict—source interpretations disagree.</span> : null}
        {quote?.entry_type === "PDF" ? <><span className="field-origin">{quote.values[field.key]?.current_origin?.replaceAll("_", " ") ?? "Unknown"} · Saved: {displayValue(quote.values[field.key]?.current_value)}</span><button type="button" className="source-action" onClick={(event) => openEvidence(field.key, event.currentTarget)}>View source evidence for {field.label}</button></> : null}
      </div>)}</div></details>)}
      <label>Quote notes<textarea maxLength={10000} value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
      <div className="editor-footer"><RecordSaveStatus savedVersion={record.savedVersion} dirty={record.dirty} pending={busy || uploading} conflict={record.state.conflict} error={record.state.error} /><div className="actions"><button type="submit" disabled={busy || uploading || record.state.conflict || record.state.uncertain || !supplier.shortlisted || supplier.dismissed}>{busy ? "Saving…" : fallbackEditing ? "Save manual draft" :
        quote?.status === "CONFIRMED" ? "Save quote" : quote ? "Save draft" : "Create manual quote"}</button>
      {quote ? <button type="button" disabled={busy || record.state.uncertain || writeUncertain} onClick={cancelEditing}>{record.dirty ? "Discard unsaved quote edits" : "Cancel editing"}</button> : null}
      </div></div>
    </form> : null}
    </div>
    {large && evidenceField ? <aside className="evidence-panel" aria-label="Original document evidence"><h3>Original document evidence</h3>{evidenceBody}<button type="button" onClick={closeEvidence}>Close evidence</button></aside> : null}
    </div>
    <Dialog open={Boolean(evidenceField) && !large} onOpenChange={(open) => { if (!open) closeEvidence(); }}><DialogContent className="evidence-sheet" onCloseAutoFocus={(event) => { event.preventDefault(); evidenceTrigger.current?.focus(); }}><DialogTitle>Original document evidence</DialogTitle><DialogDescription>Original source, extraction, saved value and your draft remain distinct.</DialogDescription>{evidenceBody}</DialogContent></Dialog>
  </article>;
}

export function QuoteReview({ projectId, active, refreshKey, onQuoteChange }: {
  projectId: string; active: boolean; refreshKey: number; onQuoteChange?: () => void;
}) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [selectedSupplier, setSelectedSupplier] = useState("");
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const sequence = useRef(0);
  const registry = useWorkspaceDrafts();
  const reload = useCallback(async (silent = false, reconcileSaved = false) => {
    if (!active) return;
    const request = ++sequence.current;
    if (!silent) { setLoading(true); setError(null); }
    try {
      const [supplierResult, quoteResult] = await Promise.all([
        apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`),
        apiRequest<Quote[]>(`/api/projects/${projectId}/quotes`),
      ]);
      if (request !== sequence.current) return;
      const eligible = supplierResult.suppliers.filter((supplier) => supplier.shortlisted && !supplier.dismissed);
      setSuppliers((current) => {
        // Preserve mounted drafts and recover saved quotes after a page reload.
        const retained = new Map(current.map((item) => [item.id, item]));
        for (const item of supplierResult.suppliers) {
          if (retained.has(item.id) || quoteResult.some((quote) => quote.supplier_id === item.id)) retained.set(item.id, item);
        }
        return [...eligible, ...[...retained.values()].filter((item) => !eligible.some((candidate) => candidate.id === item.id)).map((item) => ({ ...item, shortlisted: false }))];
      });
      setSelectedSupplier((current) => eligible.some((supplier) => supplier.id === current) ? current : eligible[0]?.id || "");
      // Unchanged reads must not reset unsaved card state. A save explicitly reconciles it.
      setQuotes((current) => quoteResult.map((quote) => {
        const previous = current.find((item) => item.id === quote.id);
        return !reconcileSaved && previous && JSON.stringify(previous) === JSON.stringify(quote)
          ? previous : quote;
      }));
    } catch (failure) {
      if (request === sequence.current) setError(reconcileSaved ? "Saved; quotes could not refresh. Retry the read to update guidance." : errorMessage(failure));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [active, projectId]);

  useEffect(() => { void reload(); return () => { sequence.current += 1; }; }, [reload, refreshKey]);

  async function savedQuote() {
    onQuoteChange?.();
    await reload(false, true);
  }

  const receivedStatus = useCallback((updated: Quote) => {
    if (updated.status !== "PROCESSING") onQuoteChange?.();
    setQuotes((current) => current.some((quote) => quote.id === updated.id)
      ? current.map((quote) => quote.id === updated.id ? updated : quote) : [...current, updated]);
  }, [onQuoteChange]);

  const currentSuppliers = suppliers.filter((supplier) => supplier.shortlisted && !supplier.dismissed);
  function supplierChoice(supplier: Supplier) {
    return <button type="button" key={supplier.id} aria-pressed={selectedSupplier === supplier.id} onClick={() => setSelectedSupplier(supplier.id)}>{supplier.name}<small>{quotes.find((quote) => quote.supplier_id === supplier.id)?.status.replaceAll("_", " ") ?? "Not added"}{registry?.records[`quote-${supplier.id}`]?.dirty ? " · Unsaved changes" : ""}</small></button>;
  }

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
      {!loading && !error && currentSuppliers.length === 0 ? <p>No suppliers are currently shortlisted.</p> : null}
      <label className="mobile-supplier" hidden={!currentSuppliers.length}>Quote supplier<select value={selectedSupplier} onChange={(event) => setSelectedSupplier(event.target.value)}>{currentSuppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select></label>
      <div className="supplier-switch" role="group" aria-label="Choose a quote supplier">{currentSuppliers.map(supplierChoice)}</div>
      <fieldset className="quote-controls" disabled={!active || loading || Boolean(error)}>
        {suppliers.map((supplier) => <div key={supplier.id} hidden={!supplier.shortlisted || supplier.dismissed || supplier.id !== selectedSupplier}><ManualQuoteCard
          key={supplier.id} projectId={projectId} supplier={supplier}
          quote={quotes.find((quote) => quote.supplier_id === supplier.id)} onSaved={savedQuote}
          statusActive={active && !error} onStatus={receivedStatus}
        /></div>)}
      </fieldset>
    </div>
  </section>;
}
