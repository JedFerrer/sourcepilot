"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

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
  const [creationError, setCreationError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  useEffect(() => {
    void fetch("/api/projects", { credentials: "same-origin" })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("Project list request failed");
        }
        return (await response.json()) as Project[];
      })
      .then((loadedProjects) => {
        setProjects(loadedProjects);
        setLoadState("ready");
      })
      .catch(() => setLoadState("unavailable"));
  }, []);

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
      const response = await fetch("/api/projects", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, original_request: originalRequest }),
      });
      if (!response.ok) {
        throw new Error("Project creation request failed");
      }
      const project = (await response.json()) as Project;
      router.push(`/projects/${project.id}`);
    } catch {
      setCreationError("We could not create this project. Please try again.");
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
        <p className="form-error">Projects are unavailable. Refresh to try again.</p>
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
