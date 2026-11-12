"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";
import { WorkflowSummary } from "../lib/workflow";
import { WorkspaceShell } from "./workspace-shell";
import { useRecordDraft } from "./use-record-draft";
import { DraftConflict, RecordSaveStatus } from "./record-save-status";
import { useDraftRegistration } from "./workspace-drafts";
import { WorkspaceDraftProvider } from "./workspace-drafts";
import { BriefEditor } from "./brief-editor";
import { ComparisonReview } from "./comparison-review";
import { DecisionProject, DecisionReview } from "./decision-review";
import { QuoteReview } from "./quote-review";
import { SupplierReview } from "./supplier-review";

type Project = DecisionProject & {
  id: string;
  name: string;
  original_request: string;
  stage: string;
  workflow?: WorkflowSummary;
};

type WorkspaceState = "loading" | "ready" | "unavailable" | "not-found";

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  return <WorkspaceDraftProvider key={projectId}><ProjectWorkspaceContent projectId={projectId} /></WorkspaceDraftProvider>;
}

function ProjectWorkspaceContent({ projectId }: { projectId: string }) {
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const [project, setProject] = useState<Project | null>(null);
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const renameRecord = useRecordDraft(project?.name ?? "");
  const dispatchRename = renameRecord.dispatch;
  const renameDisclosure = useRef<HTMLDetailsElement>(null);
  const [renameCloseWarning, setRenameCloseWarning] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [supplierRefreshKey, setSupplierRefreshKey] = useState(0);
  const [timingRefreshKey, setTimingRefreshKey] = useState(0);
  const [decisionRefreshKey, setDecisionRefreshKey] = useState(0);
  const decisionRevision = useRef(0);
  const [comparisonRefreshKey, setComparisonRefreshKey] = useState(0);
  const summaryRequest = useRef(0);
  const appliedSummaryRequest = useRef(0);
  const renameRequest = useRef(0);
  const nameRevision = useRef(0);
  const acceptedName = useRef<string | null>(null);
  const projectVisit = useRef(0);
  const currentProjectId = useRef(projectId);
  if (!mounted.current || currentProjectId.current !== projectId) {
    projectVisit.current += 1;
    renameRequest.current += 1;
  }
  currentProjectId.current = projectId;
  const renderedProjectVisit = projectVisit.current;
  const refreshComparison = useCallback(() => setComparisonRefreshKey((value) => value + 1), []);
  const refreshDecision = useCallback(() => setDecisionRefreshKey((value) => value + 1), []);
  const applyProjectResponse = useCallback((updated: Project, startedAtDecisionRevision: number, startedAtNameRevision: number, startedAtSummaryRequest = summaryRequest.current, isNameMutation = false) => {
    if (updated.id !== currentProjectId.current) return;
    // An unchanged read is not newer name data; an accepted rename still invalidates older reads.
    const acceptName = startedAtNameRevision === nameRevision.current;
    if (acceptName) {
      if (isNameMutation || updated.name !== acceptedName.current) nameRevision.current += 1;
      acceptedName.current = updated.name;
    }
    setProject((current) => {
      if (updated.id !== currentProjectId.current) return current;
      if (current === null) return updated;
      if (current.id !== updated.id) return current;
      // A full project response may have been read before the latest decision write.
      const named = acceptName ? updated : { ...updated, name: current.name };
      const reconciled = startedAtSummaryRequest === summaryRequest.current ? named : { ...named, stage: current.stage, workflow: current.workflow };
      return decisionRevision.current === startedAtDecisionRevision ? reconciled : { ...reconciled,
        preferred_supplier_id: current.preferred_supplier_id,
        preferred_supplier_name: current.preferred_supplier_name,
        decision_notes: current.decision_notes,
        workflow: current.workflow,
      };
    });
  }, []);
  const refreshSummary = useCallback(async () => {
    if (!mounted.current || currentProjectId.current !== projectId || renderedProjectVisit !== projectVisit.current) return;
    const request = ++summaryRequest.current;
    try {
      while (request === summaryRequest.current && renderedProjectVisit === projectVisit.current) {
        const startedAtDecisionRevision = decisionRevision.current;
        const startedAtNameRevision = nameRevision.current;
        const latest = await apiRequest<Project>(`/api/projects/${projectId}`);
        if (request !== summaryRequest.current || renderedProjectVisit !== projectVisit.current) return;
        applyProjectResponse(latest, startedAtDecisionRevision, startedAtNameRevision);
        if (startedAtDecisionRevision !== decisionRevision.current) {
          // This read may predate the saved decision. Re-read before treating guidance as current.
          setLoadError("The project stage could not be refreshed. Try again.");
          continue;
        }
        appliedSummaryRequest.current = request;
        setWorkspaceState("ready");
        setLoadError(null);
        return;
      }
    } catch {
      if (request === summaryRequest.current && renderedProjectVisit === projectVisit.current) {
        setLoadError("The project stage could not be refreshed. Try again.");
        setWorkspaceState((state) => state === "loading" ? "unavailable" : state);
      }
    }
  }, [projectId, renderedProjectVisit, applyProjectResponse]);

  const renderedSummaryRequest = summaryRequest.current;
  const renderedWorkflow = project?.workflow;
  const handleDecisionSaved = useCallback((updated: DecisionProject) => {
    if (updated.id !== currentProjectId.current || renderedProjectVisit !== projectVisit.current) return;
    decisionRevision.current += 1;
    const reconcileCompletedRead = renderedSummaryRequest !== summaryRequest.current
      && appliedSummaryRequest.current === summaryRequest.current;
    if (renderedSummaryRequest !== summaryRequest.current) {
      setLoadError("The project stage could not be refreshed. Try again.");
    }
    setProject((current) => current?.id === updated.id ? { ...current,
      preferred_supplier_id: updated.preferred_supplier_id,
      preferred_supplier_name: updated.preferred_supplier_name,
      decision_notes: updated.decision_notes,
      // Reconcile the saved choice even when upstream guidance has moved on.
      workflow: renderedSummaryRequest === summaryRequest.current && renderedWorkflow === current.workflow
        ? updated.workflow ?? current.workflow : current.workflow,
    } : current);
    // A completed overlapping read may also predate this save. Pending reads reconcile in their loop.
    if (reconcileCompletedRead) void refreshSummary();
  }, [renderedSummaryRequest, renderedWorkflow, renderedProjectVisit, refreshSummary]);

  async function refreshProject() {
    if (!mounted.current || renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
    refreshComparison();
    setSupplierRefreshKey((value) => value + 1);
    refreshDecision();
    await refreshSummary();
  }

  const handleSuppliersChange = useCallback(() => {
    if (!mounted.current || renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
    refreshDecision();
    void refreshSummary();
  }, [projectId, renderedProjectVisit, refreshDecision, refreshSummary]);
  const handleQuoteChange = useCallback(() => {
    if (!mounted.current || renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
    setTimingRefreshKey((value) => value + 1);
    refreshComparison();
    void refreshSummary();
  }, [projectId, renderedProjectVisit, refreshComparison, refreshSummary]);

  useEffect(() => {
    const onFocus = () => { void refreshSummary(); };
    window.addEventListener("focus", onFocus);
    return () => { window.removeEventListener("focus", onFocus); summaryRequest.current += 1; };
  }, [refreshSummary]);

  useEffect(() => {
    let isCurrentRequest = true;
    const request = ++summaryRequest.current;
    setProject(null);
    setWorkspaceState("loading");
    setLoadError(null);
    renameRequest.current += 1;
    setRenameError(null);
    setIsRenaming(false);
    void apiRequest<Project>(`/api/projects/${projectId}`)
      .then((loadedProject) => {
        if (!isCurrentRequest || request !== summaryRequest.current) {
          return;
        }
        appliedSummaryRequest.current = request;
        nameRevision.current += 1;
        acceptedName.current = loadedProject.name;
        dispatchRename({ type: "reset", value: loadedProject.name });
        setProject(loadedProject);
        setWorkspaceState("ready");
      })
      .catch((error: unknown) => {
        if (!isCurrentRequest || request !== summaryRequest.current) {
          return;
        }
        if (error instanceof ApiClientError && error.status === 404) {
          setWorkspaceState("not-found");
          return;
        }
        setLoadError(error instanceof ApiClientError ? error.message : "Project unavailable. Please try again.");
        setWorkspaceState("unavailable");
      });

    return () => {
      isCurrentRequest = false;
    };
  }, [loadAttempt, projectId, dispatchRename]);

  useDraftRegistration("project-name", { label: "Project name", stage: "BRIEF", dirty: renameRecord.dirty,
    pending: isRenaming, uncertain: renameRecord.state.uncertain, error: renameError, check: checkName });

  async function checkName() {
    try {
      const latest = await apiRequest<Project>(`/api/projects/${projectId}`);
      if (!mounted.current) return;
      renameRecord.dispatch({ type: "receive", value: latest.name });
      await refreshSummary();
    } catch { setRenameError("Saved name could not be checked. Your draft is retained."); }
  }

  async function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = String(new FormData(event.currentTarget).get("name") ?? "").trim();
    if (!name) {
      setRenameError("Enter a project name.");
      return;
    }

    if (renameRecord.begin() === null) return;
    setRenameError(null);
    setIsRenaming(true);
    const request = ++renameRequest.current;
    const visit = projectVisit.current;
    const startedAtDecisionRevision = decisionRevision.current;
    const startedAtNameRevision = nameRevision.current;
    const startedAtSummaryRequest = summaryRequest.current;
    try {
      const renamedProject = await apiRequest<Project>(`/api/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!mounted.current || currentProjectId.current !== projectId || visit !== projectVisit.current || request !== renameRequest.current) return;
      applyProjectResponse(renamedProject, startedAtDecisionRevision, startedAtNameRevision, startedAtSummaryRequest, true);
      renameRecord.dispatch({ type: "saved", value: renamedProject.name });
    } catch (error) {
      if (!mounted.current || currentProjectId.current !== projectId || visit !== projectVisit.current || request !== renameRequest.current) return;
      renameRecord.dispatch({ type: "failed", message: "Name could not be saved", uncertain: error instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(error.code) });
      setRenameError(
        error instanceof ApiClientError ? error.message : "We could not rename this project. Please try again.",
      );
    } finally {
      if (currentProjectId.current === projectId && visit === projectVisit.current && request === renameRequest.current) setIsRenaming(false);
    }
  }

  if (workspaceState === "loading") {
    return <p>Loading project…</p>;
  }
  if (workspaceState === "not-found") {
    return <p>Project not found in this demo session.</p>;
  }
  if (workspaceState === "unavailable" || project === null) {
    return (
      <div className="form-error" role="alert">
        <p>{loadError}</p>
        <button type="button" onClick={() => setLoadAttempt((attempt) => attempt + 1)}>
          Try again
        </button>
      </div>
    );
  }

  return <WorkspaceShell projectId={projectId} name={project.name} preference={project.preferred_supplier_name}
    workflow={project.workflow} outdated={Boolean(loadError)} refreshError={loadError} retry={() => void refreshSummary()}
    rename={<details ref={renameDisclosure} onToggle={(event) => {
      if (!event.currentTarget.open && (renameRecord.dirty || isRenaming)) { event.currentTarget.open = true; setRenameCloseWarning(true); }
    }}><summary>Rename project</summary>
      <RecordSaveStatus savedVersion={renameRecord.savedVersion} dirty={renameRecord.dirty} pending={isRenaming} error={renameError} conflict={renameRecord.state.conflict} />
      {renameRecord.state.conflict ? <DraftConflict saved={<p>{renameRecord.state.remote}</p>} draft={<p>{renameRecord.state.draft}</p>} onUseSaved={() => renameRecord.dispatch({ type: "use-saved" })} onKeepDraft={() => renameRecord.dispatch({ type: "reconcile", value: renameRecord.state.draft })} /> : null}
      {renameRecord.state.uncertain ? <p role="alert">Name save outcome is uncertain. <button type="button" onClick={() => void checkName()}>Check saved name</button></p> : null}
      {renameCloseWarning ? <p className="notice">The name has unsaved or pending changes. Keep editing, or discard unsaved edits after saving finishes. <button type="button" onClick={() => setRenameCloseWarning(false)}>Keep editing</button><button type="button" disabled={isRenaming || renameRecord.state.uncertain} onClick={() => { renameRecord.dispatch({ type: "use-saved" }); setRenameCloseWarning(false); }}>Discard name edits</button></p> : null}      <form className="rename-form" onSubmit={handleRename}>
        <label>
          Rename project
          <input name="name" value={renameRecord.state.draft} onChange={(event) => renameRecord.edit(event.target.value)} maxLength={255} required />
        </label>
        {renameError ? <p className="form-error" role="alert">{renameError}</p> : null}
        <button type="submit" disabled={isRenaming || renameRecord.state.conflict || renameRecord.state.uncertain || !renameRecord.dirty}>
          {isRenaming ? "Saving…" : "Save name"}
        </button>
      </form>
</details>}
    stages={{
      BRIEF: <><BriefEditor key={`BriefEditor-${projectId}`} projectId={projectId} originalRequest={project.original_request} onProjectChange={refreshProject} /></>,
      SUPPLIERS: <SupplierReview key={`SupplierReview-${projectId}`} projectId={projectId} refreshKey={supplierRefreshKey + timingRefreshKey} onStageChange={refreshProject} onSuppliersChange={handleSuppliersChange} />,
      QUOTES: <QuoteReview key={`QuoteReview-${projectId}`} projectId={projectId} active={project.workflow?.stage_prerequisites.QUOTES === null} refreshKey={supplierRefreshKey} onQuoteChange={handleQuoteChange} />,
      COMPARISON: <ComparisonReview key={`ComparisonReview-${projectId}`} projectId={projectId} refreshKey={comparisonRefreshKey} workflow={project.workflow} onGenerated={refreshSummary} />,
      DECISION: <DecisionReview key={`DecisionReview-${projectId}`} project={project} refreshKey={decisionRefreshKey} onSaved={handleDecisionSaved} />,
    }} />;
}
