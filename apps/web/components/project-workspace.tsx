"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";
import { stageLabels, stageAnchors, workflowStages, workflowActions, workflowReasons, WorkflowSummary } from "../lib/workflow";
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
  const [project, setProject] = useState<Project | null>(null);
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [supplierRefreshKey, setSupplierRefreshKey] = useState(0);
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
  if (currentProjectId.current !== projectId) {
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
    if (currentProjectId.current !== projectId || renderedProjectVisit !== projectVisit.current) return;
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
    if (renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
    refreshComparison();
    setSupplierRefreshKey((value) => value + 1);
    refreshDecision();
    await refreshSummary();
  }

  const handleSuppliersChange = useCallback(() => {
    if (renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
    refreshDecision();
    void refreshSummary();
  }, [projectId, renderedProjectVisit, refreshDecision, refreshSummary]);
  const handleQuoteChange = useCallback(() => {
    if (renderedProjectVisit !== projectVisit.current || currentProjectId.current !== projectId) return;
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
  }, [loadAttempt, projectId]);

  async function handleRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = String(new FormData(event.currentTarget).get("name") ?? "").trim();
    if (!name) {
      setRenameError("Enter a project name.");
      return;
    }

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
      if (currentProjectId.current !== projectId || visit !== projectVisit.current || request !== renameRequest.current) return;
      applyProjectResponse(renamedProject, startedAtDecisionRevision, startedAtNameRevision, startedAtSummaryRequest, true);
    } catch (error) {
      if (currentProjectId.current !== projectId || visit !== projectVisit.current || request !== renameRequest.current) return;
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

  return (
    <section className="project-workspace" aria-labelledby="project-title">
      <Link href="/">Back to projects</Link>
      <p className="workspace-stage">Current stage: {project.workflow ? stageLabels[project.workflow.current_stage] : "Unavailable"}</p>
      {project.workflow && !loadError ? <div className="workflow-guidance" aria-label="Next action">
        <p>{workflowReasons[project.workflow.next_action.reason_code]}</p>
        <a href={`#${workflowActions[project.workflow.next_action.code].anchor}`}>Next: {workflowActions[project.workflow.next_action.code].label}</a>
      </div> : null}
      {loadError ? <p role="status">Progress guidance may be outdated until the refresh succeeds.</p> : null}
      {loadError ? <div className="form-error" role="alert"><p>{loadError}</p><button type="button" onClick={() => void refreshSummary()}>Refresh stage</button></div> : null}
      <h1 id="project-title">{project.name}</h1>
      <p>Preferred supplier: {project.preferred_supplier_name ?? "No Decision Yet"}</p>
      {project.workflow ? <nav aria-label="Sourcing workflow stages">
        <ul className="stage-list">
          {workflowStages.map((stage) => <li key={stage}
            aria-current={project.workflow!.current_stage === stage ? "step" : undefined}
            data-unavailable={project.workflow!.stage_prerequisites[stage] ? "true" : undefined}>
            <a href={`#${stageAnchors[stage]}`}><strong>{stageLabels[stage]}</strong></a>
            {project.workflow!.stage_prerequisites[stage] ? <span>{workflowReasons[project.workflow!.stage_prerequisites[stage]!]}</span> : null}
          </li>)}
        </ul>
      </nav> : <p role="status">Workflow progress is unavailable. Refresh the project to try again.</p>}
      <form className="rename-form" onSubmit={handleRename}>
        <label>
          Rename project
          <input name="name" defaultValue={project.name} maxLength={255} required />
        </label>
        {renameError ? <p className="form-error" role="alert">{renameError}</p> : null}
        <button type="submit" disabled={isRenaming}>
          {isRenaming ? "Saving…" : "Save name"}
        </button>
      </form>
      <section aria-labelledby="original-request-title">
        <h2 id="original-request-title">Original sourcing request</h2>
        <p>{project.original_request}</p>
      </section>
      <BriefEditor key={`BriefEditor-${projectId}`} projectId={projectId} onProjectChange={refreshProject} />
      <SupplierReview key={`SupplierReview-${projectId}`} projectId={projectId} refreshKey={supplierRefreshKey} onStageChange={refreshProject} onSuppliersChange={handleSuppliersChange} />
      <QuoteReview key={`QuoteReview-${projectId}`} projectId={projectId} active={project.workflow?.stage_prerequisites.QUOTES === null} refreshKey={supplierRefreshKey} onQuoteChange={handleQuoteChange} />
      <ComparisonReview key={`ComparisonReview-${projectId}`} projectId={projectId} refreshKey={comparisonRefreshKey} workflow={project.workflow} onGenerated={refreshSummary} />
      <DecisionReview key={`DecisionReview-${projectId}`} project={project} refreshKey={decisionRefreshKey} onSaved={handleDecisionSaved} />

    </section>
  );
}
