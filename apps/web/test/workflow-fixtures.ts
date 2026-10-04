import { WorkflowSummary, WorkflowStage } from "../lib/workflow";
import { jsonResponse } from "./api-responses";

// Baselines for legacy workspace regression fixtures; actual workflow cases
// use explicit server summaries in project-workflow.test.tsx.
export function workflowFixture(stage: WorkflowStage = "BRIEF"): WorkflowSummary {
  const next = {
    BRIEF: { code: "ANALYZE_BRIEF", reason_code: "BRIEF_ANALYSIS_AVAILABLE", target_stage: "BRIEF" },
    SUPPLIERS: { code: "APPROVE_SHORTLIST", reason_code: "SHORTLIST_APPROVAL_REQUIRED", target_stage: "SUPPLIERS" },
    QUOTES: { code: "COMPLETE_QUOTES", reason_code: "INSUFFICIENT_CONFIRMED_QUOTES", target_stage: "QUOTES" },
    COMPARISON: { code: "GENERATE_COMPARISON", reason_code: "COMPARISON_NOT_GENERATED", target_stage: "COMPARISON" },
    DECISION: { code: "RECORD_PREFERENCE", reason_code: "PREFERENCE_NOT_RECORDED", target_stage: "DECISION" },
  } as const;
  return { current_stage: stage, next_action: next[stage], shortlist_count: 0,
    confirmed_quote_count: 0, comparison_ready: true, comparison_present: false,
    comparison_stale: false, suppliers_stale: false,
    stage_prerequisites: { BRIEF: null, SUPPLIERS: stage === "BRIEF" ? "BRIEF_APPROVAL_REQUIRED" : null,
      QUOTES: stage === "QUOTES" ? null : "SHORTLIST_APPROVAL_REQUIRED", COMPARISON: null, DECISION: null } };
}

export function workspaceFixtureResponse(body: unknown, status = 200): Response {
  if (body && typeof body === "object" && "original_request" in body) {
    const project = body as { stage?: WorkflowStage; workflow?: WorkflowSummary };
    return jsonResponse({ ...body, workflow: project.workflow ?? workflowFixture(project.stage) }, status);
  }
  return jsonResponse(body, status);
}
