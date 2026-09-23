"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type Project = {
  id: string;
  name: string;
  original_request: string;
  stage: string;
  created_at: string;
  updated_at: string;
};

type LoadState = "loading" | "ready" | "unavailable";

export function ProjectDashboard() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creationError, setCreationError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);

  useEffect(() => {
    setLoadState("loading");
    setLoadError(null);
    void apiRequest<Project[]>("/api/projects")
      .then((loadedProjects) => {
        setProjects(loadedProjects);
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        setLoadError(error instanceof ApiClientError ? error.message : "Projects are unavailable. Please try again.");
        setLoadState("unavailable");
      });
  }, [loadAttempt]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") ?? "").trim();
    const originalRequest = String(formData.get("originalRequest") ?? "").trim();

    if (!name || !originalRequest) {
      setCreationError("Enter a project name and sourcing request.");
      return;
    }

    setCreationError(null);
    setIsCreating(true);
    try {
      const project = await apiRequest<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, original_request: originalRequest }),
      });
      router.push(`/projects/${project.id}`);
    } catch (error) {
      setCreationError(
        error instanceof ApiClientError ? error.message : "We could not create this project. Please try again.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="project-dashboard" aria-labelledby="project-dashboard-title">
      <h2 id="project-dashboard-title">Your sourcing projects</h2>
      <form className="project-form" onSubmit={handleCreate}>
        <label>
          Project name
          <input name="name" maxLength={255} required />
        </label>
        <label>
          What do you want to source?
          <textarea name="originalRequest" required rows={4} />
        </label>
        {creationError ? <p className="form-error" role="alert">{creationError}</p> : null}
        <button type="submit" disabled={isCreating}>
          {isCreating ? "Creating project…" : "Create project"}
        </button>
      </form>

      <h3>Recent projects</h3>
      {loadState === "loading" ? <p>Loading projects…</p> : null}
      {loadState === "unavailable" ? (
        <div className="form-error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={() => setLoadAttempt((attempt) => attempt + 1)}>
            Try again
          </button>
        </div>
      ) : null}
      {loadState === "ready" && projects.length === 0 ? <p>No projects yet.</p> : null}
      {loadState === "ready" && projects.length > 0 ? (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id}>
              <Link href={`/projects/${project.id}`}>
                <strong>{project.name}</strong>
                <span>Brief</span>
                <span>Updated {new Date(project.updated_at).toLocaleDateString()}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
