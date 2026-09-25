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
  stale: boolean; evaluations: Finding[];
  derived_context: { kind: string; status: string; evidence_ids: string[] }[];
  informational_requirements: { requirement_id: string; kind: string; importance: string | null; expected_value: Record<string, unknown> }[];
  evidence: Evidence[];
};
type SupplierList = { brief_revision: number; brief_approved: boolean; suppliers: Supplier[] };

function expectedLabel(value: Record<string, unknown>): string {
  return Object.values(value).map((item) => String(item)).join(" · ");
}

function SupplierCard({ supplier, onUpdate, busy }: {
  supplier: Supplier;
  onUpdate: (id: string, payload: Record<string, unknown>) => Promise<void>;
  busy: boolean;
}) {
  const [notes, setNotes] = useState(supplier.notes ?? "");
  useEffect(() => setNotes(supplier.notes ?? ""), [supplier.notes]);

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

export function SupplierReview({ projectId, refreshKey }: { projectId: string; refreshKey: number }) {
  const [loaded, setLoaded] = useState<{ projectId: string; refreshKey: number; data: SupplierList } | null>(null);
  const data = loaded?.projectId === projectId && loaded.refreshKey === refreshKey ? loaded.data : null;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const requestSequence = useRef(0);

  const reload = useCallback(async () => {
    const request = ++requestSequence.current;
    setLoading(true);
    setError(null);
    try {
      const result = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`);
      if (request === requestSequence.current) {
        setLoaded({ projectId, refreshKey, data: result });
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
      if (request === requestSequence.current) setLoaded({ projectId, refreshKey, data: updated });
    } catch (failure) {
      setError(failure instanceof ApiClientError ? failure.message : "Supplier review could not be saved. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="suppliers-title" className="supplier-review">
      <h2 id="suppliers-title">Suppliers</h2>
      {loading ? <p>Loading suppliers…</p> : null}
      {error ? <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry</button></div> : null}
      {data?.suppliers.some((item) => item.stale) ? <p role="status" className="form-error">Your sourcing requirements changed. Existing supplier evaluations may no longer reflect the current Brief.</p> : null}
      {data?.brief_approved ? <button type="button" disabled={busy} onClick={() => void discover()}>{data.suppliers.length ? "Re-discover and re-evaluate" : "Discover Suppliers"}</button> : data ? <p>Approve the Brief to discover or re-evaluate suppliers.</p> : null}
      {data && data.suppliers.length === 0 && !loading ? <p>No suppliers discovered yet.</p> : null}
      {data?.suppliers.map((supplier) => <SupplierCard key={supplier.id} supplier={supplier} onUpdate={update} busy={busy} />)}
    </section>
  );
}
