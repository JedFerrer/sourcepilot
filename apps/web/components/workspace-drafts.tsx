"use client";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";
import type { WorkflowStage } from "../lib/workflow";

export type DraftRegistration = {
  label: string; stage: WorkflowStage; dirty: boolean; pending: boolean; uncertain?: boolean;
  error?: string | null; supplierId?: string; check?: () => Promise<void>; discard?: () => void;
};
type Registry = {
  records: Record<string, DraftRegistration>;
  register: (id: string, record: DraftRegistration | null) => void;
  leave: (action: () => void) => void;
};
const Context = createContext<Registry | null>(null);
export const useWorkspaceDrafts = () => useContext(Context);
export function useDraftRegistration(id: string, record: DraftRegistration) {
  const registry = useContext(Context);
  const latest = useRef(record);
  latest.current = record;
  const register = registry?.register;
  useEffect(() => {
    register?.(id, { ...record, check: () => latest.current.check?.() ?? Promise.resolve(), discard: () => latest.current.discard?.() });
    // Callbacks are read from latest; only user-visible metadata triggers a registry update.
  }, [id, register, record.label, record.stage, record.dirty, record.pending, record.uncertain, record.error, record.supplierId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => register?.(id, null), [id, register]);
}
export function WorkspaceDraftProvider({ children }: { children: ReactNode }) {
  const [records, setRecords] = useState<Record<string, DraftRegistration>>({});
  const [departure, setDeparture] = useState<{ action: () => void } | null>(null);
  const [elapsed, setElapsed] = useState(false);
  const [checking, setChecking] = useState(false);
  const [checkMessage, setCheckMessage] = useState<string | null>(null);
  const authorizedDeparture = useRef(false);
  const recordsRef = useRef(records);
  recordsRef.current = records;
  const register = useCallback((id: string, record: DraftRegistration | null) => setRecords((current) => {
    const next = { ...current }; if (record) next[id] = record; else delete next[id]; return next;
  }), []);
  const affected = Object.values(records).filter((record) => record.dirty || record.pending || record.uncertain);
  const pending = affected.some((record) => record.pending || record.uncertain);
  const leave = useCallback((action: () => void) => {
    if (Object.values(records).some((record) => record.dirty || record.pending || record.uncertain)) { setDeparture({ action }); setElapsed(false); setCheckMessage(null); }
    else action();
  }, [records]);
  useEffect(() => {
    const unload = (event: BeforeUnloadEvent) => { if (affected.length && !authorizedDeparture.current) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", unload);
    return () => window.removeEventListener("beforeunload", unload);
  }, [affected.length]);
  useEffect(() => {
    // Keep browser Back/Forward within the project native. For a project exit,
    // restore the current entry before asking, then replay only the navigation
    // after explicit consent. Submitted writes are never replayed or cancelled.
    const projectPath = window.location.pathname;
    let position = Number(window.history.state?.sourcepilotPosition ?? 0);
    let restoring = false;
    const push = window.history.pushState;
    const replace = window.history.replaceState;
    replace.call(window.history, { ...window.history.state, sourcepilotPosition: position }, "");
    const trackedPush: History["pushState"] = function (this: History, data, unused, url) {
      position += 1; push.call(this, { ...data, sourcepilotPosition: position }, unused, url);
    };
    const trackedReplace: History["replaceState"] = function (this: History, data, unused, url) {
      replace.call(this, { ...data, sourcepilotPosition: position }, unused, url);
    };
    window.history.pushState = trackedPush;
    window.history.replaceState = trackedReplace;
    const pop = (event: PopStateEvent) => {
      if (authorizedDeparture.current) return;
      if (restoring) { restoring = false; event.stopImmediatePropagation(); return; }
      const target = event.state?.sourcepilotPosition as number | undefined;
      const changed = window.location.pathname !== projectPath;
      const dirty = Object.values(recordsRef.current).some((record) => record.dirty || record.pending || record.uncertain);
      if (changed && dirty) {
        event.stopImmediatePropagation();
        const delta = target === undefined ? -1 : target - position || -1;
        restoring = true;
        window.history.go(-delta);
        setElapsed(false); setCheckMessage(null);
        setDeparture({ action: () => { authorizedDeparture.current = true; window.history.go(delta); } });
      } else if (target !== undefined) position = target;
    };
    window.addEventListener("popstate", pop, true);
    return () => {
      window.removeEventListener("popstate", pop, true);
      if (window.history.pushState === trackedPush) window.history.pushState = push;
      if (window.history.replaceState === trackedReplace) window.history.replaceState = replace;
    };
  }, []);
  useEffect(() => {
    if (!departure) return;
    const timer = window.setTimeout(() => setElapsed(true), 10000);
    return () => window.clearTimeout(timer);
  }, [departure]);
  async function checkSaved() {
    setChecking(true); setCheckMessage(null);
    let timer: ReturnType<typeof setTimeout> | undefined;
    try {
      await Promise.race([Promise.all(affected.map((record) => record.check?.())), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("timeout")), 10000); })]);
      setCheckMessage("Saved state checked. A pending request may still complete; review the affected records before leaving.");
    } catch { setCheckMessage("Saved state could not be confirmed. You can retry or leave anyway."); }
    finally { clearTimeout(timer); setChecking(false); }
  }
  return <Context.Provider value={{ records, register, leave }}>
    {children}
    <Dialog open={departure !== null} onOpenChange={(open) => { if (!open) setDeparture(null); }}>
      <DialogContent onOpenAutoFocus={(event) => { event.preventDefault(); document.getElementById("stay-in-project")?.focus(); }}>
        <DialogTitle>Leave this project?</DialogTitle>
        <DialogDescription>{pending ? "Leaving does not cancel a request already submitted. Unsaved drafts may be lost. On return, saved data is reloaded." : "Your unsaved changes are kept only during this visit. Stay to save each record separately."}</DialogDescription>
        <ul>{affected.map((record) => <li key={record.label}>{record.label}: {record.pending ? "Saving" : record.uncertain ? "Outcome uncertain" : "Unsaved changes"}</li>)}</ul>
        {elapsed && pending ? <p role="status">Save outcome not yet confirmed.</p> : null}
        {checkMessage ? <p role="status">{checkMessage}</p> : null}
        <div className="actions">
          <Button id="stay-in-project" onClick={() => setDeparture(null)}>Stay</Button>
          {elapsed && pending ? <Button variant="outline" disabled={checking} onClick={() => void checkSaved()}>{checking ? "Checking…" : "Check saved state"}</Button> : null}
          <Button variant="destructive" onClick={() => { const action = departure?.action; authorizedDeparture.current = true; setDeparture(null); action?.(); }}>{pending ? "Leave anyway" : "Discard unsaved changes and leave"}</Button>
        </div>
      </DialogContent>
    </Dialog>
  </Context.Provider>;
}
