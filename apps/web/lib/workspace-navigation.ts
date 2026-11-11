import { stageAnchors, workflowStages, type WorkflowStage } from "./workflow";

export function fragmentStage(fragment: string): WorkflowStage | null {
  const id = fragment.replace(/^#/, "");
  const known: Record<string, WorkflowStage> = {
    brief: "BRIEF", "brief-title": "BRIEF", "brief-analyze": "BRIEF", "brief-complete": "BRIEF", "brief-approve": "BRIEF",
    suppliers: "SUPPLIERS", "suppliers-title": "SUPPLIERS", "supplier-discover": "SUPPLIERS", "shortlist-review": "SUPPLIERS", "shortlist-approve": "SUPPLIERS",
    quotes: "QUOTES", "quotes-title": "QUOTES", "quotes-review": "QUOTES",
    comparison: "COMPARISON", "comparison-title": "COMPARISON", "comparison-generate": "COMPARISON",
    decision: "DECISION", "decision-title": "DECISION", "decision-choice": "DECISION",
  };
  if (known[id]) return known[id];
  return null;
}
export function resolveStage(url: URL, fallback?: WorkflowStage): WorkflowStage {
  const values = url.searchParams.getAll("stage");
  const valid = workflowStages.find((stage) => stageAnchors[stage] === values[0]);
  return values.length === 1 && valid ? valid : fragmentStage(url.hash) ?? fallback ?? "BRIEF";
}
export function stageUrl(url: URL, stage: WorkflowStage, fragment?: string): string {
  const result = new URL(url);
  result.searchParams.set("stage", stageAnchors[stage]);
  result.hash = fragment ?? "";
  return `${result.pathname}${result.search}${result.hash}`;
}
