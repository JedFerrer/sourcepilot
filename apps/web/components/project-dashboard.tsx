"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useRef, useState } from "react";
import { stageLabels, workflowActions, WorkflowSummary } from "../lib/workflow";
import { ApiClientError, apiRequest } from "../lib/api";

import { Plus, ArrowRight } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { Button } from "./ui/button";

type Project = {
  id: string;
  name: string;
  original_request: string;
  stage: string;
  workflow?: WorkflowSummary;
  created_at: string;
  updated_at: string;
  preferred_supplier_name: string | null;
};

type LoadState = "loading" | "ready" | "unavailable";

export function ProjectDashboard() {
  const router = useRouter();
  const departed = useRef(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [creationError, setCreationError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [creatingOpen, setCreatingOpen] = useState(false);
  const [creationDirty, setCreationDirty] = useState(false);
  const [nameDraft, setNameDraft] = useState("");
  const [requestDraft, setRequestDraft] = useState("");
  const [closeWarning, setCloseWarning] = useState(false);
  const [uncertain, setUncertain] = useState(false);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const pendingNavigation = useRef<string | null>(null);

  // Include dashboard/header links outside this component. Native unload
  // protection cannot intercept Next's same-document navigation.
  useEffect(() => {
    const guardLink = (event: MouseEvent) => {
      if (!(creationDirty || (!departed.current && (isCreating || uncertain)))
        || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const link = (event.target as Element).closest?.("a[href]") as HTMLAnchorElement | null;
      if (!link || link.hasAttribute("download") || (link.target && link.target !== "_self")) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin || !["http:", "https:"].includes(url.protocol)
        || link.getAttribute("href")?.startsWith("#")) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      pendingNavigation.current = `${url.pathname}${url.search}${url.hash}`;
      setCreatingOpen(true);
      setCloseWarning(true);
    };
    document.addEventListener("click", guardLink, true);
    return () => document.removeEventListener("click", guardLink, true);
  }, [creationDirty, isCreating, uncertain]);

  function stay() {
    pendingNavigation.current = null;
    setCloseWarning(false);
  }

  useEffect(() => { if (closeWarning) document.getElementById("stay-on-dashboard")?.focus(); }, [closeWarning]);

  function leave() {
    const destination = pendingNavigation.current;
    pendingNavigation.current = null;
    departed.current = true;
    setCloseWarning(false);
    setCreatingOpen(false);
    setCreationDirty(false);
    setUncertain(false);
    setCreationError(null);
    setLoadAttempt((value) => value + 1);
    setNameDraft("");
    setRequestDraft("");
    if (destination) router.push(destination);
  }

  useEffect(() => {
    let current = true;
    setLoadState("loading");
    setLoadError(null);
    void apiRequest<Project[]>("/api/projects")
      .then((loadedProjects) => {
        if (!current) return;
        setProjects(loadedProjects);
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (!current) return;
        setLoadError(error instanceof ApiClientError ? error.message : "Projects are unavailable. Please try again.");
        setLoadState("unavailable");
      });
    return () => { current = false; };
  }, [loadAttempt]);

  useEffect(() => {
    const onFocus = () => setLoadAttempt((value) => value + 1);
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (creationDirty || (!departed.current && (isCreating || uncertain))) { event.preventDefault(); event.returnValue = ""; } };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [creationDirty, isCreating, uncertain]);

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

    if (isCreating || uncertain) return;
    setCreationError(null);
    setIsCreating(true);
    departed.current = false;
    try {
      const project = await apiRequest<Project>("/api/projects", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, original_request: originalRequest }),
      });
      if (!departed.current) router.push(`/projects/${project.id}`);
      else setLoadAttempt((value) => value + 1);
    } catch (error) {
      if (departed.current) { setLoadAttempt((value) => value + 1); return; }
      setUncertain(error instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(error.code));
      setCreationError(
        error instanceof ApiClientError ? error.message : "We could not create this project. Please try again.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <section className="project-dashboard" aria-labelledby="project-dashboard-title">
      <div className="dashboard-heading"><div><h1 id="project-dashboard-title">Your sourcing projects</h1><p>Turn a sourcing request into an evidence-backed decision.</p></div><Button onClick={() => setCreatingOpen(true)}><Plus size={18} aria-hidden="true" />New project</Button></div>
      <Dialog open={creatingOpen} onOpenChange={(open) => { if (!open && (creationDirty || isCreating || uncertain)) setCloseWarning(true); else setCreatingOpen(open); }}><DialogContent onOpenAutoFocus={(event) => { if (closeWarning) { event.preventDefault(); document.getElementById("stay-on-dashboard")?.focus(); } }}><DialogTitle>New sourcing project</DialogTitle><DialogDescription>Start with what you need. You can complete and approve the Brief before discovering suppliers.</DialogDescription>
      <form onChange={() => setCreationDirty(true)} className="project-form" onSubmit={handleCreate}>
        <label>
          Project name
          <input name="name" value={nameDraft} onChange={(event) => setNameDraft(event.target.value)} maxLength={255} required />
        </label>
        <label>
          What do you want to source?
          <textarea name="originalRequest" value={requestDraft} onChange={(event) => setRequestDraft(event.target.value)} required rows={4} />
        </label>
        {creationError ? <p className="form-error" role="alert">{creationError}</p> : null}
        <button type="submit" disabled={isCreating || uncertain}>
          {isCreating ? "Creating project…" : "Create project"}
        </button>
      </form>
      {uncertain ? <p role="alert">Creation outcome is uncertain. Check the project list before creating another project; the submitted request may still complete. <button type="button" onClick={() => { setCreatingOpen(false); setLoadAttempt((value) => value + 1); }}>Check saved projects</button></p> : null}
      {closeWarning ? <div className="notice"><p>{isCreating || uncertain ? "Leaving does not cancel the submitted request. Check saved projects on return." : "Discard this unsaved project request?"}</p><button id="stay-on-dashboard" type="button" onClick={stay}>Stay</button><button type="button" onClick={leave}>{isCreating || uncertain ? "Leave anyway" : "Discard unsaved changes and leave"}</button></div> : null}
      </DialogContent></Dialog>
      {uncertain && !creatingOpen && loadState === "ready" ? <p className="notice">Review the saved projects below. The earlier request may still complete. Your draft remains available; do not create a duplicate project. <button type="button" onClick={() => setCreatingOpen(true)}>Return to retained request</button></p> : null}
      <h2>Recent projects</h2>
      {loadState === "loading" ? <p>Loading projects…</p> : null}
      {loadState === "unavailable" ? (
        <div className="form-error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={() => setLoadAttempt((attempt) => attempt + 1)}>
            Try again
          </button>
        </div>
      ) : null}
      {loadState === "ready" && projects.length === 0 ? <div className="empty-state"><h3>No projects yet.</h3><p>Describe the product you need, then review and approve your sourcing requirements.</p><Button onClick={() => setCreatingOpen(true)}>Create your first project<ArrowRight size={16} aria-hidden="true" /></Button></div> : null}
      {loadState === "ready" && projects.length > 0 ? (
        <ul className="project-list">
          {projects.map((project) => (
            <li key={project.id}>
              <Link href={`/projects/${project.id}`}>
                <div className="project-identity"><strong>{project.name}</strong><span>Updated {new Date(project.updated_at).toLocaleDateString()}</span></div>
                <div className="project-progress"><span className="project-stage">{project.workflow ? stageLabels[project.workflow.current_stage] : "Progress unavailable"}</span>
                {project.workflow ? <><span>Next: {workflowActions[project.workflow.next_action.code].label}</span><span>{project.workflow.comparison_stale ? "Comparison needs refreshing" : project.workflow.comparison_ready ? "Comparison ready" : "Comparison prerequisites incomplete"}</span></> : null}</div>
                <div className="project-counts">{project.workflow ? <span>Shortlisted: {project.workflow.shortlist_count} · Confirmed quotes: {project.workflow.confirmed_quote_count}</span> : null}<span>Preferred supplier: {project.preferred_supplier_name ?? "No Decision Yet"}</span></div>
                <span className="project-open">Open project →</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    <p className="demo-notice">Demo suppliers use a curated synthetic dataset. SourcePilot does not perform live supplier research.</p>
    </section>
  );
}
