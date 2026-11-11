"use client";

import { useEffect, useRef, useState } from "react";
import { WorkflowSummary } from "../lib/workflow";
import { ApiClientError, apiRequest } from "../lib/api";

import { Dialog, DialogContent, DialogTitle, DialogDescription } from "./ui/dialog";
import { useRecordDraft } from "./use-record-draft";
import { useDraftRegistration } from "./workspace-drafts";
import { DraftConflict, RecordSaveStatus } from "./record-save-status";

export type DecisionProject = {
  id: string;
  preferred_supplier_id: string | null;
  preferred_supplier_name: string | null;
  decision_notes: string | null;
  workflow?: WorkflowSummary;
};

type Supplier = { id: string; name: string; shortlisted: boolean };

type DecisionProps = {
  project: DecisionProject; refreshKey: number; onSaved: (project: DecisionProject) => void;
};

export function DecisionReview(props: DecisionProps) {
  return <DecisionPanel key={props.project.id} {...props} />;
}

function DecisionPanel({ project, refreshKey, onSaved }: DecisionProps) {
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [selected, setSelected] = useState("");
  const [reviewOpen, setReviewOpen] = useState(false);
  const record = useRecordDraft(project.decision_notes ?? "");
  const notes = record.state.draft;
  const setNotes = record.edit;
  const [busy, setBusy] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const saving = useRef(false);
  const generation = useRef(0);

  useEffect(() => {
    const current = ++generation.current;
    return () => { if (generation.current === current) generation.current += 1; };
  }, [project.id]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setListError(null);
    void apiRequest<{ suppliers: Supplier[] }>(`/api/projects/${project.id}/suppliers`)
      .then((result) => {
        if (!Array.isArray(result.suppliers)) throw new Error("Invalid supplier response");
        if (active) setSuppliers(result.suppliers.filter((supplier) => supplier.shortlisted));
      })
      .catch((error: unknown) => {
        if (active) setListError(error instanceof ApiClientError ? error.message : "The shortlist could not be loaded. Try again.");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [project.id, refreshKey, attempt]);

  useDraftRegistration("decision", { label: "Decision", stage: "DECISION", dirty: record.dirty || Boolean(selected), pending: busy, uncertain: record.state.uncertain, error: saveError,
    check: async () => { const latest = await apiRequest<DecisionProject>(`/api/projects/${project.id}`); onSaved(latest); },
  });
  async function save(supplierId: string | null, success: string, action: "preference" | "notes" | "clear" = "preference") {
    if (saving.current || record.state.uncertain || (action !== "clear" && record.state.conflict)) return;
    if (action !== "clear" && record.begin() === null) return;
    saving.current = true;
    setBusy(true);
    setSaveError(null);
    setMessage(null);
    const current = generation.current;
    try {
      const updated = await apiRequest<DecisionProject>(`/api/projects/${project.id}/preferred-supplier`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ supplier_id: supplierId, decision_notes: action === "clear" ? project.decision_notes : notes }),
      });
      if (current !== generation.current || updated.id !== project.id) return;
      onSaved(updated);
      if (action !== "clear") record.dispatch({ type: "saved", value: updated.decision_notes ?? "" });
      if (action === "preference") setSelected("");
      setMessage(success);
    } catch (error: unknown) {
      if (current !== generation.current) return;
      record.dispatch({ type: "failed", message: "Decision save failed", uncertain: error instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(error.code) });
      setSaveError(error instanceof ApiClientError ? error.message : "The decision could not be saved. Try again.");
      // Re-read membership after a rejection while preserving the user's draft.
      if (error instanceof ApiClientError && error.code === "PREFERRED_SUPPLIER_NOT_SHORTLISTED") {
        setAttempt((value) => value + 1);
      }
    } finally {
      if (current === generation.current) {
        saving.current = false;
        setBusy(false);
      }
    }
  }

  const retainedOutsideShortlist = project.preferred_supplier_id && !loading && !listError
    && !suppliers.some((supplier) => supplier.id === project.preferred_supplier_id);
  const selectedAvailable = suppliers.some((supplier) => supplier.id === selected);

  return <section id="decision" className="decision-review" aria-labelledby="decision-title">
    <div className="record-heading"><h2 id="decision-title" tabIndex={-1}>Decision</h2>
    <RecordSaveStatus savedVersion={record.savedVersion} dirty={record.dirty || Boolean(selected)} pending={busy} error={saveError} conflict={record.state.conflict} /></div>
    {selected ? <p className="notice">Unsaved replacement: {suppliers.find((supplier) => supplier.id === selected)?.name ?? "Unavailable supplier"}. Your saved preference has not changed.</p> : null}
    {record.state.uncertain ? <p role="alert">Decision save outcome is uncertain. Check saved state before deciding how to recover. <button type="button" onClick={async () => {
      try { const latest = await apiRequest<DecisionProject>(`/api/projects/${project.id}`); onSaved(latest); record.dispatch({ type: "receive", value: latest.decision_notes ?? "" }); }
      catch { setSaveError("Saved decision could not be checked. Your draft is retained."); }
    }}>Check saved decision</button></p> : null}
    {record.state.conflict ? <DraftConflict saved={<p>{record.state.remote}</p>} draft={<p>{notes}</p>} onUseSaved={() => record.dispatch({ type: "use-saved" })} onKeepDraft={() => record.dispatch({ type: "reconcile", value: notes })} /> : null}
    <div className="saved-preference"><p>Current preference: <strong>{project.preferred_supplier_name ?? "No Decision Yet"}</strong></p>
    <p>This records your choice. It does not place an order or contact a supplier.</p></div>
    {retainedOutsideShortlist ? <p role="status">Your saved preferred supplier is no longer shortlisted. You can still edit notes, clear the choice, or select another shortlisted supplier.</p> : null}
    {loading ? <p>Loading shortlist for decision…</p> : null}
    {listError ? <div className="form-error" role="alert"><p>{listError}</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Reload decision shortlist</button></div> : null}
    {!loading && !listError && !suppliers.length ? <p>No shortlisted suppliers are available for a new selection.</p> : null}
    <form className="decision-form" onSubmit={(event) => { event.preventDefault(); if (selectedAvailable && !loading && !listError) setReviewOpen(true); }}>
      <label>Preferred supplier
        <select id="decision-choice" value={selected} onChange={(event) => setSelected(event.target.value)} disabled={busy || loading || !!listError}>
          <option value="">Choose a shortlisted supplier</option>
          {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
        </select>
      </label>
      <label>Decision notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={10000} rows={3} disabled={busy} />
      </label>
      <div className="actions"><button type="submit" disabled={busy || loading || !!listError || !selectedAvailable}>Mark as Preferred Supplier</button>
      <button type="button" disabled={busy} onClick={() => void save(project.preferred_supplier_id, "Decision notes saved.", "notes")}>Save decision notes</button>
      {project.preferred_supplier_id ? <button type="button" disabled={busy} onClick={() => void save(null, "Preferred supplier cleared.", "clear")}>Clear preferred supplier</button> : null}</div>
    </form>
    <Dialog open={reviewOpen} onOpenChange={setReviewOpen}><DialogContent className="approval-dialog">
      <DialogTitle>Save this human preference?</DialogTitle>
      <DialogDescription>This saves your chosen supplier and these notes together. It does not place an order or contact a supplier.</DialogDescription>
      <dl className="review-summary"><div><dt>Proposed preferred supplier</dt><dd>{suppliers.find((supplier) => supplier.id === selected)?.name ?? "Unavailable supplier"}</dd></div><div><dt>Decision notes</dt><dd>{notes || "No decision notes entered."}</dd></div></dl>
      <div className="review-actions"><button type="button" onClick={() => setReviewOpen(false)}>Keep reviewing</button><button type="button" className="primary-action" disabled={busy || loading || !!listError || !selectedAvailable || record.state.conflict || record.state.uncertain} onClick={() => { setReviewOpen(false); void save(selected, "Preferred supplier saved."); }}>Save preferred supplier</button></div>
    </DialogContent></Dialog>
    {busy ? <p role="status">Saving decision…</p> : null}
    {saveError ? <p className="form-error" role="alert">{saveError}</p> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
