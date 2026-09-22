"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

type Project = {
  id: string;
  name: string;
  original_request: string;
  stage: string;
};

type WorkspaceState = "loading" | "ready" | "unavailable" | "not-found";

const unavailableStages = ["Suppliers", "Quotes", "Comparison", "Decision"];

export function ProjectWorkspace({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [workspaceState, setWorkspaceState] = useState<WorkspaceState>("loading");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [isRenaming, setIsRenaming] = useState(false);

  useEffect(() => {
    void fetch(`/api/projects/${projectId}`, { credentials: "same-origin" })
      .then(async (response) => {
        if (response.status === 404) {
          setWorkspaceState("not-found");
          return;
        }
        if (!response.ok) {
          throw new Error("Project request failed");
        }
        const loadedProject = (await response.json()) as Project;
        setProject(loadedProject);
        setWorkspaceState("ready");
      })
      .catch(() => setWorkspaceState("unavailable"));
  }, [projectId]);

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
      const response = await fetch(`/api/projects/${projectId}`, {
        method: "PATCH",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!response.ok) {
        throw new Error("Project rename request failed");
      }
      setProject((await response.json()) as Project);
    } catch {
      setRenameError("We could not rename this project. Please try again.");
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
    return <p className="form-error">Project unavailable. Refresh to try again.</p>;
  }

  return (
    <section className="project-workspace" aria-labelledby="project-title">
      <Link href="/">Back to projects</Link>
      <p className="workspace-stage">Current stage: Brief</p>
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
      <nav aria-label="Sourcing workflow stages">
        <ul className="stage-list">
          <li aria-current="step"><strong>Brief</strong><span>Brief setup is not part of this slice.</span></li>
          {unavailableStages.map((stage) => (
            <li key={stage} data-unavailable="true"><strong>{stage}</strong><span>Available in a later step.</span></li>
          ))}
        </ul>
      </nav>
    </section>
  );
}
