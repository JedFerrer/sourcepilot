"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";
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
  const [hasComparison, setHasComparison] = useState(false);
  const handleSnapshotChange = useCallback((present: boolean) => setHasComparison(present), []);
  const refreshComparison = useCallback(() => setComparisonRefreshKey((value) => value + 1), []);
  const refreshDecision = useCallback(() => setDecisionRefreshKey((value) => value + 1), []);
  const applyProjectResponse = useCallback((updated: Project, startedAtDecisionRevision: number) => {
    setProject((current) => {
      if (current?.id !== updated.id) return current;
      // A full project response may have been read before the latest decision write.
      return decisionRevision.current === startedAtDecisionRevision ? updated : { ...updated,
        preferred_supplier_id: current.preferred_supplier_id,
        preferred_supplier_name: current.preferred_supplier_name,
        decision_notes: current.decision_notes,
      };
    });
  }, []);
  const handleDecisionSaved = useCallback((updated: DecisionProject) => {
    decisionRevision.current += 1;
    setProject((current) => current?.id === updated.id ? { ...current,
      preferred_supplier_id: updated.preferred_supplier_id,
      preferred_supplier_name: updated.preferred_supplier_name,
      decision_notes: updated.decision_notes,
    } : current);
  }, []);

  async function refreshProject() {
    const startedAtDecisionRevision = decisionRevision.current;
    refreshComparison();
    setSupplierRefreshKey((value) => value + 1);
    refreshDecision();
    try {
      const latest = await apiRequest<Project>(`/api/projects/${projectId}`);
      applyProjectResponse(latest, startedAtDecisionRevision);
      setLoadError(null);
    } catch {
      setLoadError("The project stage could not be refreshed. Try again.");
    }
  }

  useEffect(() => {
    let isCurrentRequest = true;
    setWorkspaceState("loading");
    setLoadError(null);
    void apiRequest<Project>(`/api/projects/${projectId}`)
      .then((loadedProject) => {
        if (!isCurrentRequest) {
          return;
        }
        setProject(loadedProject);
        setWorkspaceState("ready");
      })
      .catch((error: unknown) => {
        if (!isCurrentRequest) {
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
    const startedAtDecisionRevision = decisionRevision.current;
    try {
      const renamedProject = await apiRequest<Project>(`/api/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      applyProjectResponse(renamedProject, startedAtDecisionRevision);
    } catch (error) {
      setRenameError(
        error instanceof ApiClientError ? error.message : "We could not rename this project. Please try again.",
      );
    } finally {
      setIsRenaming(false);
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
      <p className="workspace-stage">Current stage: {project.stage === "QUOTES" ? "Quotes" : project.stage === "SUPPLIERS" ? "Suppliers" : "Brief"}</p>
      {loadError ? <div className="form-error" role="alert"><p>{loadError}</p><button type="button" onClick={() => void refreshProject()}>Refresh stage</button></div> : null}
      <h1 id="project-title">{project.name}</h1>
      <p>Preferred supplier: {project.preferred_supplier_name ?? "No Decision Yet"}</p>
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
      <BriefEditor projectId={projectId} onProjectChange={refreshProject} />
      <SupplierReview projectId={projectId} refreshKey={supplierRefreshKey} onStageChange={refreshProject} onSuppliersChange={refreshDecision} />
      <QuoteReview projectId={projectId} active={project.stage === "QUOTES"} refreshKey={supplierRefreshKey} onQuoteChange={refreshComparison} />
      <ComparisonReview projectId={projectId} refreshKey={comparisonRefreshKey} onSnapshotChange={handleSnapshotChange} />
      <DecisionReview key={projectId} project={project} refreshKey={decisionRefreshKey} onSaved={handleDecisionSaved} />
      <nav aria-label="Sourcing workflow stages">
        <ul className="stage-list">
          <li aria-current={project.stage === "BRIEF" ? "step" : undefined}><strong>Brief</strong><span>Edit the sourcing brief above.</span></li>
          <li aria-current={project.stage === "SUPPLIERS" ? "step" : undefined} data-unavailable={project.stage === "BRIEF" ? "true" : undefined}><strong>Suppliers</strong><span>{project.stage === "BRIEF" ? "Available after Brief approval." : "Review discovered suppliers above."}</span></li>
          <li aria-current={project.stage === "QUOTES" ? "step" : undefined} data-unavailable={project.stage === "QUOTES" ? undefined : "true"}><strong>Quotes</strong><span>{project.stage === "QUOTES" ? "Add and confirm manual quotes above." : "Available after shortlist approval."}</span></li>
          <li><strong>Comparison</strong><span>{hasComparison ? "Review factual comparison above." : "Check comparison availability above."}</span></li>
          <li><strong>Decision</strong><span>Record or update your preference above.</span></li>
        </ul>
      </nav>
    </section>
  );
}
