"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type Evidence = {
  id: string; claim_key: string; source_label: string; source_reference: string | null;
  evidence_text: string; evidence_state: string;
};
type Finding = {
  requirement_id: string; kind: string; importance: string | null;
  expected_value: Record<string, unknown>; status: string; evidence_ids: string[];
};
type Supplier = {
  id: string; name: string; country: string; description: string;
  capabilities: { kind: string; value: string }[];
  general_moq: number | null; general_lead_time_days: number | null;
  indicative_price_amount: string | null; indicative_price_currency: string | null;
  shortlisted: boolean; dismissed: boolean; notes: string | null;
  stale: boolean; evaluated_against_brief_revision: number; evaluations: Finding[];
  derived_context: { kind: string; status: string; evidence_ids: string[] }[];
  informational_requirements: { requirement_id: string; kind: string; importance: string | null; expected_value: Record<string, unknown> }[];
  evidence: Evidence[];
};
type SupplierList = { brief_revision: number; brief_approved: boolean; shortlist_approved: boolean; suppliers: Supplier[] };
type ExplanationPoint = { text: string; requirement_id: string | null; evidence_ids: string[] };
type SupplierExplanation = {
  supplier_id: string;
  strengths: ExplanationPoint[]; required_failures: ExplanationPoint[];
  preferred_findings: ExplanationPoint[]; unknowns: ExplanationPoint[];
  conflicts: ExplanationPoint[]; concerns: ExplanationPoint[]; evidence_ids: string[];
};
type ExplanationResponse = { run_id: string; explanation: SupplierExplanation };

function expectedLabel(value: Record<string, unknown>): string {
  return Object.values(value).map((item) => String(item)).join(" · ");
}

function SupplierCard({ projectId, supplier, dataVersion, onUpdate, onRefresh, busy }: {
  projectId: string;
  supplier: Supplier;
  dataVersion: number;
  onUpdate: (id: string, payload: Record<string, unknown>) => Promise<void>;
  onRefresh: () => Promise<void>;
  busy: boolean;
}) {
  const [notes, setNotes] = useState(supplier.notes ?? "");
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const latestVersion = useRef(dataVersion);
  latestVersion.current = dataVersion;
  useEffect(() => setNotes(supplier.notes ?? ""), [supplier.notes]);
  useEffect(() => { setExplanation(null); setExplanationError(null); }, [dataVersion]);

  async function explain() {
    const requestedVersion = dataVersion;
    setExplaining(true);
    setExplanationError(null);
    try {
      const result = await apiRequest<ExplanationResponse>(
        `/api/projects/${projectId}/suppliers/${supplier.id}/explanation`, { method: "POST" },
      );
      if (requestedVersion === latestVersion.current) setExplanation(result);
    } catch (failure) {
      if (requestedVersion === latestVersion.current) {
        setExplanation(null);
        setExplanationError(failure instanceof ApiClientError ? failure.message : "The explanation could not be loaded. Try again.");
        if (failure instanceof ApiClientError && ["SUPPLIER_EVALUATION_STALE", "SUPPLIER_NOT_FOUND"].includes(failure.code)) {
          await onRefresh();
        }
      }
    } finally {
      setExplaining(false);
    }
  }

  const sections: [string, ExplanationPoint[]][] = explanation ? [
    ["Strengths", explanation.explanation.strengths],
    ["Required failures", explanation.explanation.required_failures],
    ["Preferred findings", explanation.explanation.preferred_findings],
    ["Unknowns", explanation.explanation.unknowns],
    ["Conflicts", explanation.explanation.conflicts],
    ["Concerns", explanation.explanation.concerns],
  ] : [];

  function saveNotes(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void onUpdate(supplier.id, { notes });
  }

  return (
    <article className="supplier-card">
      <h3>{supplier.name}</h3>
      <p>{supplier.country} · {supplier.description}</p>
      <p>MOQ: {supplier.general_moq ?? "Unknown"} · Typical lead time: {supplier.general_lead_time_days === null ? "Unknown" : `${supplier.general_lead_time_days} days`}</p>
      <p>Indicative price: {supplier.indicative_price_amount === null ? "Unknown" : `${supplier.indicative_price_amount} ${supplier.indicative_price_currency ?? ""}`}</p>
      <p>Capabilities: {supplier.capabilities.length ? supplier.capabilities.map((item) => `${item.kind}: ${item.value}`).join("; ") : "Unknown"}</p>
      {supplier.stale ? <p role="status" className="form-error">Evaluations need refreshing after the Brief changed.</p> : (
        <>
          <h4>Requirement fit</h4>
          {supplier.evaluations.length ? <ul>{supplier.evaluations.map((item) => (
            <li key={item.requirement_id}>
              {item.kind} ({item.importance ?? "Informational"}): {expectedLabel(item.expected_value)} — <strong>{item.status.replaceAll("_", " ")}</strong>
              {item.evidence_ids.length ? <span> · Evidence: {item.evidence_ids.map((id) => supplier.evidence.find((evidence) => evidence.id === id)?.source_label ?? id).join(", ")}</span> : null}
            </li>
          ))}</ul> : <p>No supported requirements to evaluate.</p>}
          {supplier.derived_context.map((item) => <p key={item.kind}>General {item.kind} compatibility: {item.status.replaceAll("_", " ")}</p>)}
          {supplier.informational_requirements.length ? <div>
            <h4>Other Brief requirements</h4>
            <ul>{supplier.informational_requirements.map((item) => <li key={item.requirement_id}>
              {item.kind} ({item.importance ?? "Informational"}): {expectedLabel(item.expected_value)} — Not evaluated at this stage
            </li>)}</ul>
          </div> : null}
        </>
      )}
      <details>
        <summary>Available evidence</summary>
        {supplier.evidence.length ? <ul>{supplier.evidence.map((item) => (
          <li key={item.id}>
            <strong>{item.source_label}</strong> ({item.evidence_state}): {item.evidence_text}
            {item.source_reference ? <> · {item.source_reference}</> : null}
          </li>
        ))}</ul> : <p>No supporting evidence is available.</p>}
      </details>
      {!supplier.stale ? <div className="supplier-explanation">
        <button type="button" disabled={busy || explaining} onClick={() => void explain()}>
          {explaining ? "Explaining…" : explanation ? "Generate explanation again" : "Explain this supplier"}
        </button>
        {explaining ? <p role="status">Preparing an evidence-backed explanation…</p> : null}
        {explanationError ? <div role="alert"><p>{explanationError}</p><button type="button" onClick={() => void explain()}>Retry explanation</button></div> : null}
        {explanation ? <div>
          <h4>Supplier explanation</h4>
          {sections.every(([, points]) => points.length === 0) ? <p>No grounded findings are available for this supplier.</p> : null}
          {sections.filter(([, points]) => points.length > 0).map(([title, points]) => <div key={title}>
            <h5>{title}</h5>
            <ul>{points.map((point, index) => <li key={`${title}-${index}`}>
              {point.text}
              {point.evidence_ids.length ? <span> · Evidence: {point.evidence_ids.map((id) => supplier.evidence.find((item) => item.id === id)?.source_label ?? id).join(", ")}</span> : null}
            </li>)}</ul>
          </div>)}
        </div> : null}
      </div> : null}
      <div className="supplier-actions">
        <button type="button" disabled={busy} onClick={() => void onUpdate(supplier.id, { shortlisted: !supplier.shortlisted })}>
          {supplier.shortlisted ? "Remove from shortlist" : "Add to shortlist"}
        </button>
        <button type="button" disabled={busy} onClick={() => void onUpdate(supplier.id, { dismissed: !supplier.dismissed })}>
          {supplier.dismissed ? "Restore" : "Dismiss"}
        </button>
      </div>
      <form onSubmit={saveNotes}>
        <label>Private notes for {supplier.name}
          <textarea value={notes} maxLength={10000} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button type="submit" disabled={busy || notes === (supplier.notes ?? "")}>Save notes</button>
      </form>
    </article>
  );
}

export function SupplierReview({ projectId, refreshKey, onStageChange }: {
  projectId: string; refreshKey: number; onStageChange?: () => Promise<void>;
}) {
  const [loaded, setLoaded] = useState<{ projectId: string; refreshKey: number; version: number; data: SupplierList } | null>(null);
  const data = loaded?.projectId === projectId && loaded.refreshKey === refreshKey ? loaded.data : null;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [approving, setApproving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reviewOpen, setReviewOpen] = useState(false);
  const requestSequence = useRef(0);

  const reload = useCallback(async () => {
    const request = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`);
      if (request === requestSequence.current) {
        setLoaded({ projectId, refreshKey, version: request, data: result });
        setError(null);
      }
    } catch (failure) {
      if (request === requestSequence.current) {
        setError(failure instanceof ApiClientError ? failure.message : "Suppliers could not be loaded. Try again.");
      }
    } finally {
      if (request === requestSequence.current) setLoading(false);
    }
  }, [projectId, refreshKey]);

  useEffect(() => {
    void reload();
    return () => { requestSequence.current += 1; };
  }, [reload, refreshKey]); // Reload after Brief edits or approval.

  async function discover() {
    setBusy(true);
    setError(null);
    try {
      await apiRequest(`/api/projects/${projectId}/suppliers/discover`, { method: "POST" });
      await reload();
      if (data?.shortlist_approved) await onStageChange?.();
    } catch (failure) {
      setError(failure instanceof ApiClientError ? failure.message : "Supplier discovery failed. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function update(id: string, payload: Record<string, unknown>) {
    const request = ++requestSequence.current;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers/${id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (request === requestSequence.current) {
        setLoaded({ projectId, refreshKey, version: request, data: updated });
        if (data?.shortlist_approved && !updated.shortlist_approved) await onStageChange?.();
      }
    } catch (failure) {
      setError(failure instanceof ApiClientError ? failure.message : "Supplier review could not be saved. Try again.");
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    setBusy(true);
    setApproving(true);
    setError(null);
    try {
      const approved = await apiRequest<SupplierList>(`/api/projects/${projectId}/shortlist/approve`, { method: "POST" });
      const request = ++requestSequence.current;
      setLoaded({ projectId, refreshKey, version: request, data: approved });
      setReviewOpen(false);
      await onStageChange?.();
    } catch (failure) {
      if (failure instanceof ApiClientError && failure.status === 409) await reload();
      setError(failure instanceof ApiClientError ? failure.message : "The shortlist could not be approved. Try again.");
    } finally {
      setApproving(false);
      setBusy(false);
    }
  }

  const selected = data?.suppliers.filter((item) => item.shortlisted) ?? [];
  const selectionReady = data?.brief_approved && selected.length >= 1 && selected.length <= 3
    && selected.every((item) => !item.dismissed && !item.stale);

  return (
    <section aria-labelledby="suppliers-title" className="supplier-review">
      <h2 id="suppliers-title">Suppliers</h2>
      {loading ? <p>Loading suppliers…</p> : null}
      {error ? <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry</button></div> : null}
      {data?.suppliers.some((item) => item.stale) ? <p role="status" className="form-error">Your sourcing requirements changed. Existing supplier evaluations may no longer reflect the current Brief.</p> : null}
      {data?.brief_approved ? <button type="button" disabled={busy} onClick={() => void discover()}>{data.suppliers.length ? "Re-discover and re-evaluate" : "Discover Suppliers"}</button> : data ? <p>Approve the Brief to discover or re-evaluate suppliers.</p> : null}
      {data ? <section aria-labelledby="shortlist-title">
        <h3 id="shortlist-title">Shortlist</h3>
        <p>{selected.length} selected · maximum 3 for approval</p>
        {selected.length > 3 ? <p role="status" className="form-error">Remove suppliers until no more than three remain.</p> : null}
        {data.shortlist_approved ? <p role="status">Shortlist approved. The project is ready for Quotes.</p> : null}
        {selected.length === 1 ? <p>One supplier can proceed; side-by-side comparison later requires at least two.</p> : null}
        {selected.length > 0 ? <button type="button" disabled={busy} onClick={() => setReviewOpen(true)}>Review selected suppliers</button> : null}
        {reviewOpen ? <div aria-label="Shortlist approval summary">
          <h4>Review before approval</h4>
          {selected.map((item) => <section key={item.id} aria-label={`${item.name} approval details`}>
            <h5>{item.name}</h5>
            <p>General MOQ: {item.general_moq ?? "Unknown"} · Typical lead time: {item.general_lead_time_days === null ? "Unknown" : `${item.general_lead_time_days} days`} · Indicative price: {item.indicative_price_amount === null ? "Unknown" : `${item.indicative_price_amount} ${item.indicative_price_currency ?? ""}`}</p>
            {item.stale ? <p>Evaluations are stale. Re-discover and re-evaluate before approval.</p> : <>
              <ul>{item.evaluations.filter((finding) => finding.importance === "REQUIRED" || finding.importance === "PREFERRED").map((finding) => <li key={finding.requirement_id}>
                {finding.importance}: {finding.kind} {expectedLabel(finding.expected_value)} — {finding.status.replaceAll("_", " ")}
              </li>)}</ul>
              {item.evaluations.some((finding) => finding.status === "UNKNOWN") ? <p>Some requirement information is Unknown.</p> : null}
              {item.evaluations.some((finding) => finding.status === "CONFLICT") ? <p>Some requirement evidence is in Conflict.</p> : null}
              {item.evaluations.some((finding) => finding.importance === "REQUIRED" && finding.status === "DOES_NOT_MEET") ? <p>Concern: a required requirement does not meet the Brief.</p> : null}
              {item.derived_context.some((finding) => finding.status !== "MEETS") ? <p>Concern: general MOQ compatibility is {item.derived_context.map((finding) => finding.status.replaceAll("_", " ")).join(", ")}.</p> : null}
            </>}
          </section>)}
          <button type="button" disabled={busy || !selectionReady || data.shortlist_approved} onClick={() => void approve()}>
            {approving ? "Approving…" : "Approve Shortlist"}
          </button>
          <button type="button" disabled={busy} onClick={() => setReviewOpen(false)}>Continue Reviewing</button>
        </div> : null}
      </section> : null}
      {data && data.suppliers.length === 0 && !loading ? <p>No suppliers discovered yet.</p> : null}
      {data?.suppliers.map((supplier) => <SupplierCard key={supplier.id} projectId={projectId} supplier={supplier} dataVersion={loaded?.version ?? 0} onUpdate={update} onRefresh={reload} busy={busy} />)}
    </section>
  );
}
