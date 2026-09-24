"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";
import { BriefEditor } from "./brief-editor";

type Project = {
  id: string;
  name: string;
  original_request: string;
  stage: string;
};

type WorkspaceState = "loading" | "ready" | "unavailable" | "not-found";

const laterStages = ["Quotes", "Comparison", "Decision"];

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);

  async function refreshProject() {
    try {
      const latest = await apiRequest<Project>(`/api/projects/${projectId}`);
      setProject(latest);
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
    try {
      const renamedProject = await apiRequest<Project>(`/api/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      setProject(renamedProject);
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
      <p className="workspace-stage">Current stage: {project.stage === "SUPPLIERS" ? "Suppliers" : "Brief"}</p>
      {loadError ? <div className="form-error" role="alert"><p>{loadError}</p><button type="button" onClick={() => void refreshProject()}>Refresh stage</button></div> : null}
      <h1 id="project-title">{project.name}</h1>
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
      <nav aria-label="Sourcing workflow stages">
        <ul className="stage-list">
          <li aria-current={project.stage === "BRIEF" ? "step" : undefined}><strong>Brief</strong><span>Edit the sourcing brief above.</span></li>
          <li aria-current={project.stage === "SUPPLIERS" ? "step" : undefined} data-unavailable={project.stage === "SUPPLIERS" ? undefined : "true"}><strong>Suppliers</strong><span>{project.stage === "SUPPLIERS" ? "Current stage. Supplier discovery is planned for M2." : "Available after Brief approval. Supplier discovery is planned for M2."}</span></li>
          {laterStages.map((stage) => (
            <li key={stage} data-unavailable="true"><strong>{stage}</strong><span>Available in a later step.</span></li>
          ))}
        </ul>
      </nav>
    </section>
  );
}
