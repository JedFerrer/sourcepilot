"use client";
import Link from "next/link";
import { type ReactNode } from "react";
import { ArrowLeft, ArrowRight, FileText, Users, ReceiptText, Columns3, Flag } from "lucide-react";
import { stageLabels, workflowStages, workflowActions, workflowReasons, type WorkflowStage, type WorkflowSummary } from "../lib/workflow";
import { useWorkspaceNavigation } from "./use-workspace-navigation";
import { useWorkspaceDrafts } from "./workspace-drafts";

const icons = { BRIEF: FileText, SUPPLIERS: Users, QUOTES: ReceiptText, COMPARISON: Columns3, DECISION: Flag };
export function WorkspaceShell({ projectId, name, preference, workflow, outdated, refreshError, retry, rename, stages }: {
  projectId: string; name: string; preference: string | null; workflow?: WorkflowSummary;
  outdated: boolean; refreshError?: string | null; retry: () => void; rename: ReactNode; stages: Record<WorkflowStage, ReactNode>;
}) {
  const { stage, navigate } = useWorkspaceNavigation(projectId, workflow?.current_stage);
  const drafts = useWorkspaceDrafts();
  const hiddenErrors = Object.values(drafts?.records ?? {}).filter((record) => record.stage !== stage && record.error);
  return <section className="project-workspace" aria-labelledby="project-title">
    <header className="app-header"><Link className="brand" href="/" onClick={(event) => { event.preventDefault(); drafts?.leave(() => window.location.assign("/")); }}><span className="brand-mark">SP</span>SourcePilot</Link>
      <p>Evidence for better sourcing decisions</p>
      <Link href="/" onClick={(event) => { event.preventDefault(); drafts?.leave(() => window.location.assign("/")); }}><ArrowLeft size={16} aria-hidden="true" /> All projects</Link></header>
    <div className="workspace-layout">
      <aside className="workspace-rail"><nav aria-label="Sourcing workflow stages">
        <label className="mobile-stage-selector">Stage
          <select value={stage} onChange={(event) => navigate(event.target.value as WorkflowStage)}>
            {workflowStages.map((item, index) => <option key={item} value={item}>
              {index + 1}. {stageLabels[item]}{workflow?.current_stage === item ? " — Needs attention" : ""}
            </option>)}
          </select>
        </label>
        <ul className="stage-list">
        {workflowStages.map((item) => { const Icon = icons[item]; return <li key={item} data-unavailable={workflow?.stage_prerequisites[item] ? "true" : undefined}>
          <a href={`?stage=${item.toLowerCase()}`} aria-label={stageLabels[item]} aria-current={stage === item ? "page" : undefined} onClick={(event) => { event.preventDefault(); navigate(item); }}>
            <Icon size={18} aria-hidden="true" /><span>{stageLabels[item]}{workflow?.current_stage === item ? <small>Needs attention</small> : null}</span>
          </a></li>; })}
      </ul></nav><p className="rail-note">A saved preference never hides upstream work that needs attention.</p></aside>
      <div className="workspace-main">
        <div className="project-context"><div><h1 id="project-title">{name}</h1><p className="project-preference">Saved preference: <strong>{preference ?? "No Decision Yet"}</strong></p>{rename}</div></div>
        <p className="workspace-stage">Current stage: {workflow ? stageLabels[workflow.current_stage] : "Unavailable"}</p>
        {workflow ? <div className="workflow-guidance" aria-label="Next action"><div><strong>Needs attention · {stageLabels[workflow.next_action.target_stage]}</strong><p>{workflowReasons[workflow.next_action.reason_code]}</p></div>
          <a href={`#${workflowActions[workflow.next_action.code].anchor}`} onClick={(event) => { event.preventDefault(); event.stopPropagation(); navigate(workflow.next_action.target_stage, workflowActions[workflow.next_action.code].anchor); }}>Next: {workflowActions[workflow.next_action.code].label}<ArrowRight size={16} aria-hidden="true" /></a>
        </div> : <p role="status">Workflow progress is unavailable. Refresh the project to try again.</p>}
        {outdated ? <div className="notice" role="status"><p>Progress guidance may be outdated until the refresh succeeds.</p><p>{refreshError}</p><button type="button" onClick={retry}>Refresh stage</button></div> : null}
        {hiddenErrors.length ? <div className="notice" role="status">{hiddenErrors.map((record) => <p key={record.label}>{record.label} needs attention. <button type="button" onClick={() => navigate(record.stage)}>Review {stageLabels[record.stage]}</button></p>)}</div> : null}
        {workflowStages.map((item) => <div key={item} hidden={stage !== item} className="stage-panel">
          {workflow?.stage_prerequisites[item] && item !== "DECISION" ? <p className="notice">{workflowReasons[workflow.stage_prerequisites[item]!]}</p> : null}
          {stages[item]}
        </div>)}
      </div>
    </div>
  </section>;
}
