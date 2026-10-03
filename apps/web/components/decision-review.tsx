"use client";

import { useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

export type DecisionProject = {
  id: string;
  preferred_supplier_id: string | null;
  preferred_supplier_name: string | null;
  decision_notes: string | null;
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
  const [notes, setNotes] = useState(project.decision_notes ?? "");
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

  async function save(supplierId: string | null, success: string) {
    if (saving.current) return;
    saving.current = true;
    setBusy(true);
    setSaveError(null);
    setMessage(null);
    const current = generation.current;
    try {
      const updated = await apiRequest<DecisionProject>(`/api/projects/${project.id}/preferred-supplier`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ supplier_id: supplierId, decision_notes: notes }),
      });
      if (current !== generation.current || updated.id !== project.id) return;
      onSaved(updated);
      setNotes(updated.decision_notes ?? "");
      setSelected("");
      setMessage(success);
    } catch (error: unknown) {
      if (current !== generation.current) return;
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

  return <section className="decision-review" aria-labelledby="decision-title">
    <h2 id="decision-title">Decision</h2>
    <p>Current preference: <strong>{project.preferred_supplier_name ?? "No Decision Yet"}</strong></p>
    <p>This records your choice. It does not place an order or contact a supplier.</p>
    {retainedOutsideShortlist ? <p role="status">Your saved preferred supplier is no longer shortlisted. You can still edit notes, clear the choice, or select another shortlisted supplier.</p> : null}
    {loading ? <p>Loading shortlist for decision…</p> : null}
    {listError ? <div className="form-error" role="alert"><p>{listError}</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Reload decision shortlist</button></div> : null}
    {!loading && !listError && !suppliers.length ? <p>No shortlisted suppliers are available for a new selection.</p> : null}
    <form className="decision-form" onSubmit={(event) => { event.preventDefault(); if (selectedAvailable && !loading && !listError) void save(selected, "Preferred supplier saved."); }}>
      <label>Preferred supplier
        <select value={selected} onChange={(event) => setSelected(event.target.value)} disabled={busy || loading || !!listError}>
          <option value="">Choose a shortlisted supplier</option>
          {suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}
        </select>
      </label>
      <label>Decision notes
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={10000} rows={3} disabled={busy} />
      </label>
      <button type="submit" disabled={busy || loading || !!listError || !selectedAvailable}>Mark as Preferred Supplier</button>
      <button type="button" disabled={busy} onClick={() => void save(project.preferred_supplier_id, "Decision notes saved.")}>Save decision notes</button>
      {project.preferred_supplier_id ? <button type="button" disabled={busy} onClick={() => void save(null, "Preferred supplier cleared.")}>Clear preferred supplier</button> : null}
    </form>
    {busy ? <p role="status">Saving decision…</p> : null}
    {saveError ? <p className="form-error" role="alert">{saveError}</p> : null}
    {message ? <p role="status">{message}</p> : null}
  </section>;
}
