"use client";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "./ui/button";
export function RecordSaveStatus({ dirty, pending, error, conflict, savedVersion = 0 }: { dirty: boolean; pending: boolean; error?: string | null; conflict?: boolean; savedVersion?: number }) {
  const [visibleSave, setVisibleSave] = useState(0);
  const initialVersion = useRef(savedVersion);
  useEffect(() => {
    if (!savedVersion || savedVersion === initialVersion.current) return;
    setVisibleSave(savedVersion);
    const timer = window.setTimeout(() => setVisibleSave(0), 3000);
    return () => window.clearTimeout(timer);
  }, [savedVersion]);
  const message = pending ? "Saving" : conflict ? "Saved elsewhere—review changes" : error ? "Save failed. Your draft is retained." : dirty ? "Unsaved changes" : visibleSave ? "Saved" : null;
  return message ? <p className="record-status" role="status">{message}</p> : null;
}
export function DraftConflict({ saved, draft, structural = false, onUseSaved, onKeepDraft }: {
  saved: ReactNode; draft: ReactNode; structural?: boolean; onUseSaved: () => void; onKeepDraft: () => void;
}) {
  return <section className="draft-conflict" aria-label="Review changes saved elsewhere">
    <h3>This record changed elsewhere</h3>
    <p>Your complete draft is preserved. Review the saved values and your edits before continuing. Nothing is saved by this review.</p>
    <div className="record-comparison"><div><h4>Latest saved record</h4>{saved}</div><div><h4>Your unsaved record</h4>{draft}</div></div>
    {structural ? <p>Requirements were added, removed or assigned new identities. Copy any edits you need, use the saved record, then deliberately add or edit its requirements. Deleted requirements will not be restored automatically.</p> : <p>Keeping your edits uses your complete record, including related currencies, amounts and delivery details. Check all changed groups before saving.</p>}
    <div className="actions"><Button variant="outline" onClick={onUseSaved}>Use saved record</Button>
      {!structural ? <Button variant="outline" onClick={onKeepDraft}>I reviewed both records—keep my edits</Button> : null}</div>
  </section>;
}
