"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

import { useRecordDraft } from "./use-record-draft";
import { useDraftRegistration, useWorkspaceDrafts } from "./workspace-drafts";
import { DraftConflict, RecordSaveStatus } from "./record-save-status";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { displayRequirement, humanLabel, requirementLabel } from "../lib/presentation";
import { sameRecord } from "../lib/record-draft";

type Evidence = {
  id: string; claim_key: string; source_label: string; source_reference: string | null;
  evidence_text: string; evidence_state: string;
};
type Finding = {
  requirement_id: string; kind: string; importance: string | null;
  expected_value: Record<string, unknown>; status: string; evidence_ids: string[];
};
type Supplier = {
  unavailable?: boolean;
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
  return displayRequirement(value);
}

function SupplierCard({ projectId, supplier, dataVersion, onUpdate, onRefresh, busy }: {
  projectId: string;
  supplier: Supplier;
  dataVersion: number;
  onUpdate: (id: string, payload: Record<string, unknown>) => Promise<void>;
  onRefresh: () => Promise<void>;
  busy: boolean;
}) {
  const evidencePanel = useRef<HTMLDetailsElement>(null);
  const secondaryContext = supplier.informational_requirements.filter((item) => item.importance === "INFORMATIONAL");
  const unevaluatedRequirements = supplier.informational_requirements.filter((item) => item.importance !== "INFORMATIONAL");
  const record = useRecordDraft(supplier.notes ?? "");
  const notes = record.state.draft;
  const setNotes = record.edit;
  const [noteError, setNoteError] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<ExplanationResponse | null>(null);
  const [explanationError, setExplanationError] = useState<string | null>(null);
  const [explaining, setExplaining] = useState(false);
  const latestVersion = useRef(dataVersion);
  latestVersion.current = dataVersion;
  useDraftRegistration(`notes-${supplier.id}`, { label: `Private notes · ${supplier.name}`, stage: "SUPPLIERS", supplierId: supplier.id,
    dirty: record.dirty, pending: record.pending, uncertain: record.state.uncertain, error: noteError,
    check: checkNotes, discard: () => record.dispatch({ type: "use-saved" }),
  });
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

  async function checkNotes() {
    const latest = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`);
    const saved = latest.suppliers.find((item) => item.id === supplier.id);
    if (!saved) { setNoteError("This supplier is unavailable. Copy your retained notes before leaving."); return; }
    record.dispatch({ type: "receive", value: saved.notes ?? "" });
  }
  async function saveNotes(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (supplier.unavailable) return;
    const submitted = record.begin(); if (submitted === null) return;
    setNoteError(null);
    try {
      const result = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers/${supplier.id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ notes: submitted }),
      });
      record.dispatch({ type: "saved", value: result.suppliers.find((item) => item.id === supplier.id)?.notes ?? "" });
      await onRefresh();
    } catch (failure) {
      const message = failure instanceof ApiClientError ? failure.message : "Notes could not be saved. Your draft is retained.";
      setNoteError(message); record.dispatch({ type: "failed", message, uncertain: failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code) });
    }
  }

  return (
    <article className="supplier-card">
      <div className="supplier-card-heading"><h3>{supplier.name}</h3><span className="supplier-selection">{supplier.dismissed ? "Dismissed" : supplier.shortlisted ? "Shortlisted" : "Not shortlisted"}</span></div>
      {supplier.unavailable ? <p role="alert">This supplier is no longer available. Your private notes remain here for copying or discarding. They cannot be saved until this supplier is restored.</p> : null}
      <p className="supplier-description">{supplier.country} · {supplier.description}</p>
      <dl className="supplier-facts">
        <div><dt>Minimum order</dt><dd>{supplier.general_moq === null ? "Unknown" : `${supplier.general_moq.toLocaleString("en-US")} units`}</dd></div>
        <div><dt>Typical lead time</dt><dd>{supplier.general_lead_time_days === null ? "Unknown" : `${supplier.general_lead_time_days} days`}</dd></div>
        <div><dt>Indicative unit price</dt><dd>{supplier.indicative_price_amount === null ? "Unknown" : `${supplier.indicative_price_currency ?? "Currency unknown"} ${Number(supplier.indicative_price_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}</dd></div>
      </dl>
      {supplier.stale ? <p role="status" className="form-error">Evaluations need refreshing after the Brief changed.</p> : <>
        {supplier.derived_context.map((item) => <p className={item.status === "MEETS" ? "supplier-context" : "supplier-concern"} key={item.kind}>{item.kind === "MOQ" && item.status === "DOES_NOT_MEET" ? "Minimum order exceeds your requested quantity." : item.kind === "MOQ" && item.status === "MEETS" ? "Minimum order fits your requested quantity." : `General ${item.kind} compatibility: ${humanLabel(item.status)}`}</p>)}
        <section className="supplier-findings" aria-label="Requirement fit"><h4>Requirement fit</h4>
          {supplier.evaluations.length ? <ul>{supplier.evaluations.map((item) => <li key={item.requirement_id}>
            <div><span className="finding-name">{requirementLabel(item.kind, item.expected_value)}</span><span className="finding-expected">{expectedLabel(item.expected_value)}</span><span className="finding-importance">{humanLabel(item.importance ?? "Importance not set")}</span></div>
            <strong className="finding-status" data-status={item.status}>{humanLabel(item.status)}</strong>
            {item.evidence_ids.length ? <details className="finding-sources"><summary>Finding evidence</summary><p>Evidence: {item.evidence_ids.map((id) => supplier.evidence.find((evidence) => evidence.id === id)?.source_label ?? id).join(", ")}</p></details> : null}
          </li>)}</ul> : <p>No supported requirements to evaluate.</p>}
          {supplier.evaluations.some((item) => item.status === "UNKNOWN") ? <p className="supplier-context">Unknown means there is not enough reliable evidence, not that the supplier failed.</p> : null}
          {supplier.evaluations.some((item) => item.status === "CONFLICT") ? <p className="supplier-concern">Conflicting evidence needs review before relying on these findings.</p> : null}
        </section>
        {unevaluatedRequirements.length ? <section><h4>Requirements not evaluated at this stage</h4><ul>{unevaluatedRequirements.map((item) => <li key={item.requirement_id}>{requirementLabel(item.kind, item.expected_value)} ({humanLabel(item.importance ?? "Importance not set")}): {expectedLabel(item.expected_value)} — Not evaluated at this stage</li>)}</ul></section> : null}
        {secondaryContext.length ? <details><summary>Additional Brief context · {secondaryContext.length} {secondaryContext.length === 1 ? "item" : "items"}</summary><p>Context retained from your Brief. Not evaluated at this stage.</p><ul>{secondaryContext.map((item) => <li key={item.requirement_id}>{requirementLabel(item.kind, item.expected_value)}: {expectedLabel(item.expected_value)}</li>)}</ul></details> : null}
      </>}
      <div className="supplier-actions">
        <button type="button" className={supplier.shortlisted ? undefined : "primary-action"} disabled={busy || supplier.unavailable} onClick={() => void onUpdate(supplier.id, { shortlisted: !supplier.shortlisted })}>{supplier.shortlisted ? "Remove from shortlist" : "Add to shortlist"}</button>
        <button type="button" onClick={() => { if (evidencePanel.current) { evidencePanel.current.open = true; evidencePanel.current.querySelector("summary")?.focus(); } }}>View evidence</button>
        <button type="button" className="quiet-action" disabled={busy || supplier.unavailable} onClick={() => void onUpdate(supplier.id, { dismissed: !supplier.dismissed })}>{supplier.dismissed ? "Restore" : "Dismiss"}</button>
      </div>
      <details ref={evidencePanel}>
        <summary>Available evidence</summary>
        {supplier.evidence.length ? <ul>{supplier.evidence.map((item) => <li key={item.id}><strong>{item.source_label}</strong> ({item.evidence_state}): {item.evidence_text}{item.source_reference ? <> · {item.source_reference}</> : null}</li>)}</ul> : <p>No supporting evidence is available.</p>}
      </details>
      <details><summary>Supporting capabilities</summary><p>{supplier.capabilities.length ? supplier.capabilities.map((item) => `${humanLabel(item.kind)}: ${item.value}`).join("; ") : "Unknown"}</p></details>
      {!supplier.stale ? <div className="supplier-explanation">
        <button className="quiet-action" type="button" disabled={busy || explaining} onClick={() => void explain()}>
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
      {record.dirty ? <p className="record-status">Notes not saved</p> : null}
      <details><summary>Private notes</summary>
      <RecordSaveStatus savedVersion={record.savedVersion} dirty={record.dirty} pending={record.pending} error={noteError} conflict={record.state.conflict} />
      {record.state.conflict ? <DraftConflict saved={<p>{record.state.remote}</p>} draft={<p>{notes}</p>} onUseSaved={() => record.dispatch({ type: "use-saved" })} onKeepDraft={() => record.dispatch({ type: "reconcile", value: notes })} /> : null}
      {noteError ? <p role="alert">{noteError}</p> : null}
      {record.state.uncertain ? <p role="alert">Notes save outcome is uncertain. <button type="button" onClick={() => void checkNotes().catch(() => setNoteError("Saved notes could not be checked. Your draft is retained."))}>Check saved notes</button></p> : null}
      <form onSubmit={(event) => void saveNotes(event)}>
        <label>Private notes for {supplier.name}
          <textarea value={notes} maxLength={10000} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <button type="submit" disabled={supplier.unavailable || record.pending || !record.dirty || record.state.conflict || record.state.uncertain}>Save notes</button>
      </form></details>
    </article>
  );
}

export function SupplierReview({ projectId, refreshKey, onStageChange, onSuppliersChange }: {
  projectId: string; refreshKey: number; onStageChange?: () => Promise<void>;
  onSuppliersChange?: () => void;
}) {
  const [loaded, setLoaded] = useState<{ projectId: string; refreshKey: number; version: number; data: SupplierList } | null>(null);
  const data = loaded?.projectId === projectId ? loaded.refreshKey === refreshKey ? loaded.data : {
    ...loaded.data, brief_approved: false,
    suppliers: loaded.data.suppliers.map((supplier) => ({ ...supplier, stale: true })),
  } : null;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [approving, setApproving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [reviewOpen, setReviewOpen] = useState(false);
  const requestSequence = useRef(0);
  const registry = useWorkspaceDrafts();
  const registryRef = useRef(registry); registryRef.current = registry;
  const retainNotes = useCallback((previous: SupplierList | undefined, next: SupplierList): SupplierList => ({ ...next,
    suppliers: [...next.suppliers, ...(previous?.suppliers ?? []).filter((old) => {
      const note = registryRef.current?.records[`notes-${old.id}`];
      return !next.suppliers.some((item) => item.id === old.id) && Boolean(note?.dirty || note?.pending || note?.uncertain);
    }).map((old) => ({ ...old, unavailable: true, shortlisted: false, dismissed: true, stale: true }))],
  }), []);
  const [removal, setRemoval] = useState<{ id: string; payload: Record<string, unknown> } | null>(null);
  const [membershipUncertain, setMembershipUncertain] = useState(false);
  const membershipWrite = useRef(false);
  const [emptyDiscovery, setEmptyDiscovery] = useState<number | null>(null);

  const reload = useCallback(async () => {
    const request = ++requestSequence.current;
    setLoading(true);
    setError(null);
    setEmptyDiscovery(null);
    try {
      const result = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`);
      if (request === requestSequence.current) {
        setLoaded((previous) => ({ projectId, refreshKey, version: request, data: retainNotes(previous?.data, result) }));
        setError(null);
        return { version: request, data: result };
      }
    } catch (failure) {
      if (request === requestSequence.current) {
        setError(failure instanceof ApiClientError ? failure.message : "Suppliers could not be loaded. Try again.");
      }
    } finally {
      if (request === requestSequence.current) setLoading(false);
    }
  }, [projectId, refreshKey, retainNotes]);

  useEffect(() => {
    void reload();
    return () => { requestSequence.current += 1; };
  }, [reload, refreshKey]); // Reload after Brief edits or approval.

  async function discover() {
    const request = ++requestSequence.current;
    setBusy(true);
    setError(null);
    setEmptyDiscovery(null);
    try {
      const result = await apiRequest<{ brief_revision: number; suppliers: { id: string }[] }>(
        `/api/projects/${projectId}/suppliers/discover`, { method: "POST" },
      );
      if (request !== requestSequence.current) return;
      const refreshed = await reload();
      if (!refreshed) return;
      if (result.suppliers.length === 0 && refreshed.data.suppliers.length === 0 &&
          result.brief_revision === refreshed.data.brief_revision) setEmptyDiscovery(refreshed.version);
      if (data?.shortlist_approved) await onStageChange?.();
      else onSuppliersChange?.();
    } catch (failure) {
      if (request === requestSequence.current) {
        setError(failure instanceof ApiClientError ? failure.message : "Supplier discovery failed. Try again.");
      }
    } finally {
      setBusy(false);
    }
  }

  useDraftRegistration("membership", { label: "Supplier shortlist", stage: "SUPPLIERS", dirty: false, pending: busy, uncertain: membershipUncertain, error, check: async () => { await reload(); } });
  async function update(id: string, payload: Record<string, unknown>) {
    if (membershipWrite.current || membershipUncertain) return;
    if (payload.shortlisted === false || payload.dismissed === true) {
      const affected = Object.values(registry?.records ?? {}).filter((record) => record.supplierId === id);
      if (affected.some((record) => record.pending || record.uncertain)) { setError("Wait for this supplier's pending changes to settle before removing them. You can cancel removal or leave the project."); return; }
      if (affected.some((record) => record.dirty)) { setRemoval({ id, payload }); return; }
    }
    await performUpdate(id, payload);
  }
  async function performUpdate(id: string, payload: Record<string, unknown>, discard = false) {
    if (membershipWrite.current || membershipUncertain) return;
    if ((payload.shortlisted === false || payload.dismissed === true) && Object.values(registry?.records ?? {}).some((record) => record.supplierId === id && (record.pending || record.uncertain))) { setError("Wait for pending supplier changes to settle before removing them."); return; }
    membershipWrite.current = true;
    const request = ++requestSequence.current;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers/${id}`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      if (request === requestSequence.current) {
        setLoaded((previous) => ({ projectId, refreshKey, version: request, data: retainNotes(previous?.data, updated) }));
        if (discard) Object.values(registry?.records ?? {}).filter((record) => record.supplierId === id).forEach((record) => record.discard?.());
        setRemoval(null);
        if (data?.shortlist_approved && !updated.shortlist_approved) await onStageChange?.();
        else onSuppliersChange?.();
      }
    } catch (failure) {
      setMembershipUncertain(failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(failure.code));
      setError(failure instanceof ApiClientError ? failure.message : "Supplier review could not be saved. Try again.");
    } finally {
      membershipWrite.current = false;
      setBusy(false);
    }
  }

  async function approve() {
    if (membershipWrite.current || membershipUncertain) return;
    setBusy(true);
    setApproving(true);
    setError(null);
    try {
      const latest = await apiRequest<SupplierList>(`/api/projects/${projectId}/suppliers`);
      const approvalData = (value: SupplierList | null) => value ? { ...value, suppliers: value.suppliers.filter((item) => !item.unavailable).map((item) => ({ ...item, notes: null })) } : null;
      if (!sameRecord(approvalData(latest), approvalData(data))) {
        const version = ++requestSequence.current;
        setLoaded((previous) => ({ projectId, refreshKey, version, data: retainNotes(previous?.data, latest) }));
        setError("Saved shortlist changed. Review the current selection and findings before approving again."); return;
      }
      const approved = await apiRequest<SupplierList>(`/api/projects/${projectId}/shortlist/approve`, { method: "POST" });
      const request = ++requestSequence.current;
      setLoaded((previous) => ({ projectId, refreshKey, version: request, data: retainNotes(previous?.data, approved) }));
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
    <section id="suppliers" aria-labelledby="suppliers-title" className="supplier-review">
      <h2 id="suppliers-title" tabIndex={-1}>Suppliers</h2>
      <p className="demo-notice">Demo suppliers use a curated synthetic dataset. SourcePilot does not perform live supplier research.</p>
      {membershipUncertain ? <p role="alert">Membership save outcome is uncertain. Check the saved shortlist and review it before another membership write. <button type="button" onClick={async () => { const result = await reload(); if (result) { setMembershipUncertain(false); setReviewOpen(false); } }}>Check saved shortlist</button></p> : null}
      <Dialog open={removal !== null} onOpenChange={(open) => { if (!open) setRemoval(null); }}><DialogContent><DialogTitle>Remove supplier with unsaved edits?</DialogTitle><DialogDescription>Quote or private-note edits will be discarded only after removal succeeds. Cancel to keep working.</DialogDescription><button type="button" onClick={() => setRemoval(null)}>Cancel removal</button><button type="button" disabled={busy} onClick={() => { if (removal) void performUpdate(removal.id, removal.payload, true); }}>Discard edits and remove</button></DialogContent></Dialog>
      {loading ? <p>Loading suppliers…</p> : null}
      {error ? <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry</button></div> : null}
      {data?.suppliers.some((item) => item.stale) ? <p role="status" className="form-error">Your sourcing requirements changed. Existing supplier evaluations may no longer reflect the current Brief.</p> : null}
      {data?.brief_approved ? <button type="button" disabled={busy} id="supplier-discover" onClick={() => void discover()}>{data.suppliers.length ? "Re-discover and re-evaluate" : "Discover Suppliers"}</button> : data ? <p>Approve the Brief to discover or re-evaluate suppliers.</p> : null}
      {data ? <section className="shortlist-strip" aria-labelledby="shortlist-review">
        <h3 id="shortlist-review">Shortlist</h3>
        <p>{selected.length} selected · maximum 3 for approval</p>
        {selected.length > 3 ? <p role="status" className="form-error">Remove suppliers until no more than three remain.</p> : null}
        {data.shortlist_approved ? <p role="status">Shortlist approved. The project is ready for Quotes.</p> : null}
        {selected.length === 1 ? <p>One supplier can proceed; side-by-side comparison later requires at least two.</p> : null}
        {selected.length > 0 ? <button type="button" disabled={busy} id="shortlist-approve" onClick={() => setReviewOpen(true)}>Review selected suppliers</button> : null}
        <Dialog open={reviewOpen} onOpenChange={setReviewOpen}><DialogContent className="approval-dialog shortlist-dialog" aria-label="Shortlist approval summary">
          <DialogTitle>Review your saved shortlist</DialogTitle>
          <DialogDescription>{selected.length} {selected.length === 1 ? "supplier selected" : "suppliers selected"}. Review each supplier below. Approve this group to continue to Quotes; this does not select a preferred supplier.</DialogDescription>
          {error ? <p role="alert" className="form-error">{error}</p> : null}
          <div className="shortlist-review-body" role="region" aria-label="Selected supplier details" tabIndex={0}>
          <p className="shortlist-review-help">Unknown means evidence is missing or insufficient. Conflict means evidence disagrees. Neither is the same as a confirmed failure.</p>
          {selected.map((item) => <section className="shortlist-supplier" key={item.id} aria-label={`${item.name} approval details`}>
            <h3>{item.name}</h3>
            <dl className="supplier-facts">
              <div><dt>Minimum order</dt><dd>{item.general_moq === null ? "Unknown" : `${item.general_moq.toLocaleString("en-US")} units`}</dd></div>
              <div><dt>Typical lead time</dt><dd>{item.general_lead_time_days === null ? "Unknown" : `${item.general_lead_time_days} days`}</dd></div>
              <div><dt>Indicative unit price</dt><dd>{item.indicative_price_amount === null ? "Unknown" : `${item.indicative_price_currency ?? "Currency unknown"} ${Number(item.indicative_price_amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 })}`}</dd></div>
            </dl>
            {item.stale ? <p className="supplier-concern">Evaluations are stale. Re-discover and re-evaluate before approval.</p> : <>
              <ul className="shortlist-findings">{item.evaluations.map((finding) => <li key={finding.requirement_id}>
                <div><span className="finding-name">{requirementLabel(finding.kind, finding.expected_value)} <span className="shortlist-importance">· {humanLabel(finding.importance ?? "Importance not set")}</span></span><span className="finding-expected">{expectedLabel(finding.expected_value)}</span></div>
                <strong className="finding-status" data-status={finding.status}>{humanLabel(finding.status)}</strong>
              </li>)}</ul>
              {item.informational_requirements.filter((finding) => finding.importance !== "INFORMATIONAL").map((finding) => <p className="supplier-concern" key={finding.requirement_id}>{requirementLabel(finding.kind, finding.expected_value)} · {humanLabel(finding.importance ?? "Importance not set")}: {expectedLabel(finding.expected_value)} — Not evaluated at this stage.</p>)}
              {item.derived_context.map((finding) => <p className={finding.status === "MEETS" ? "supplier-context" : "supplier-concern"} key={finding.kind}>{finding.kind === "MOQ" && finding.status === "DOES_NOT_MEET" ? "Minimum order exceeds your requested quantity." : finding.kind === "MOQ" && finding.status === "MEETS" ? "Minimum order fits your requested quantity." : `General ${finding.kind} compatibility: ${humanLabel(finding.status)}`}</p>)}
            </>}
          </section>)}
          </div>
          <p className="shortlist-notes-note">Private-note drafts are preserved and are not saved by this approval.</p>
          <div className="review-actions"><button type="button" disabled={busy} onClick={() => setReviewOpen(false)}>Continue Reviewing</button><button type="button" className="primary-action" disabled={busy || membershipUncertain || !selectionReady || data.shortlist_approved} onClick={() => void approve()}>
            {approving ? "Approving…" : "Approve Shortlist"}
          </button>
        </div></DialogContent></Dialog>
      </section> : null}
      {data && data.suppliers.length === 0 && !loading && !error ? <div>
        <p>{emptyDiscovery === loaded?.version ?
          "No supplier candidates were found in the curated dataset for this Brief. Review the product category and requirements, then discover suppliers again." :
          "No supplier candidates to review yet. Review and approve the Brief, then discover suppliers."}</p>
        <a href="#brief-complete">Review Brief</a>
      </div> : null}
      <div className="supplier-grid">{data?.suppliers.map((supplier) => <SupplierCard key={supplier.id} projectId={projectId} supplier={supplier} dataVersion={loaded?.version ?? 0} onUpdate={update} onRefresh={async () => { await reload(); }} busy={busy || membershipUncertain} />)}</div>
    </section>
  );
}
