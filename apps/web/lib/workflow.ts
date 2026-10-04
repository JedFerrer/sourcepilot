export const workflowStages = ["BRIEF", "SUPPLIERS", "QUOTES", "COMPARISON", "DECISION"] as const;
export type WorkflowStage = typeof workflowStages[number];
export type WorkflowAction = keyof typeof workflowActions;
export type WorkflowReason = keyof typeof workflowReasons;
export type WorkflowSummary = {
  current_stage: WorkflowStage;
  next_action: { code: WorkflowAction; reason_code: WorkflowReason; target_stage: WorkflowStage };
  shortlist_count: number; confirmed_quote_count: number;
  comparison_ready: boolean; comparison_present: boolean; comparison_stale: boolean;
  suppliers_stale: boolean;
  stage_prerequisites: Record<WorkflowStage, WorkflowReason | null>;
};
export const stageLabels: Record<WorkflowStage, string> = {
  BRIEF: "Brief", SUPPLIERS: "Suppliers", QUOTES: "Quotes", COMPARISON: "Comparison", DECISION: "Decision",
};
export const stageAnchors: Record<WorkflowStage, string> = {
  BRIEF: "brief", SUPPLIERS: "suppliers", QUOTES: "quotes", COMPARISON: "comparison", DECISION: "decision",
};
export const workflowActions = {
  ANALYZE_BRIEF: { label: "Analyze request", anchor: "brief-analyze" },
  COMPLETE_BRIEF: { label: "Complete the Brief", anchor: "brief-complete" },
  APPROVE_BRIEF: { label: "Approve Brief", anchor: "brief-approve" },
  DISCOVER_SUPPLIERS: { label: "Discover Suppliers", anchor: "supplier-discover" },
  REFRESH_SUPPLIERS: { label: "Re-discover and re-evaluate", anchor: "supplier-discover" },
  REVIEW_SHORTLIST: { label: "Review shortlist", anchor: "shortlist-review" },
  APPROVE_SHORTLIST: { label: "Review and approve shortlist", anchor: "shortlist-approve" },
  COMPLETE_QUOTES: { label: "Add, review, and confirm quotes", anchor: "quotes-review" },
  GENERATE_COMPARISON: { label: "Generate Comparison", anchor: "comparison-generate" },
  REGENERATE_COMPARISON: { label: "Regenerate Comparison", anchor: "comparison-generate" },
  RECORD_PREFERENCE: { label: "Review comparison and choose a preferred supplier", anchor: "decision-choice" },
  MANAGE_PREFERENCE: { label: "Manage your preferred supplier", anchor: "decision-choice" },
} as const;
export const workflowReasons = {
  BRIEF_ANALYSIS_AVAILABLE: "Analyze the request or enter the Brief manually.",
  BRIEF_INCOMPLETE: "Complete the missing Brief information. Clarification questions can help.",
  BRIEF_APPROVAL_REQUIRED: "Review and approve the Brief to continue.",
  SUPPLIERS_NOT_DISCOVERED: "Discover candidates from the curated supplier dataset.",
  SUPPLIER_EVALUATIONS_STALE: "The Brief changed. Re-discover and re-evaluate suppliers.",
  SHORTLIST_EMPTY: "Select at least one supplier for the shortlist.",
  SHORTLIST_OVER_LIMIT: "Reduce the shortlist to no more than three suppliers.",
  SHORTLIST_APPROVAL_REQUIRED: "Review and approve your current shortlist.",
  INSUFFICIENT_CONFIRMED_QUOTES: "Side-by-side comparison requires two shortlisted suppliers with confirmed quotes. Review the shortlist if only one supplier was selected.",
  COMPARISON_NOT_GENERATED: "Your confirmed quotes are ready for factual comparison.",
  COMPARISON_STALE: "The comparison is outdated. Regenerate it using current inputs.",
  PREFERENCE_NOT_RECORDED: "Review the comparison and record your choice. AI analysis is optional.",
  PREFERENCE_RECORDED: "Your preference is recorded. You can change it, edit notes, or clear it.",
} as const;
