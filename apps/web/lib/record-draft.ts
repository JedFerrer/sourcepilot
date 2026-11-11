// Whole-record reconciliation deliberately avoids guessing field merges. Related
// amounts/currency, delivery variants and requirement collections stay together.
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => [key, canonical(item)]));
  return value;
}
export function sameRecord(a: unknown, b: unknown): boolean { return JSON.stringify(canonical(a)) === JSON.stringify(canonical(b)); }
export type RecordDraft<T> = {
  baseline: T; draft: T; remote: T; conflict: boolean;
  submitted: T | null; generation: number; submittedGeneration: number | null;
  error: string | null; uncertain: boolean;
};
export function createDraft<T>(value: T): RecordDraft<T> {
  return { baseline: value, draft: value, remote: value, conflict: false, submitted: null, generation: 0, submittedGeneration: null, error: null, uncertain: false };
}
export type DraftAction<T> =
  | { type: "reset"; value: T }
  | { type: "edit"; value: T }
  | { type: "receive"; value: T }
  | { type: "submit"; value?: T }
  | { type: "saved"; value: T }
  | { type: "failed"; message: string; uncertain?: boolean }
  | { type: "use-saved" }
  | { type: "reconcile"; value: T };

export function reduceDraft<T>(state: RecordDraft<T>, action: DraftAction<T>): RecordDraft<T> {
  switch (action.type) {
    case "reset": return createDraft(action.value);
    case "edit": return { ...state, draft: action.value, generation: state.generation + 1 };
    case "receive": {
      if (state.uncertain) return { ...state, remote: action.value, conflict: true };
      if (sameRecord(action.value, state.remote)) return state;
      if (state.submitted !== null) return { ...state, remote: action.value, conflict: true };
      if (sameRecord(state.draft, state.baseline) && !state.conflict && !state.uncertain) return createDraft(action.value);
      return { ...state, remote: action.value, conflict: true };
    }
    case "submit":
      if (state.submitted !== null || state.conflict || state.uncertain) return state;
      return { ...state, submitted: action.value === undefined ? state.draft : action.value, submittedGeneration: state.generation, error: null };
    case "saved": {
      const newer = state.generation !== state.submittedGeneration;
      const normalized = !sameRecord(action.value, state.submitted);
      return { ...state, baseline: action.value, remote: action.value,
        draft: newer ? state.draft : action.value, conflict: newer && normalized,
        submitted: null, submittedGeneration: null, uncertain: false, error: null };
    }
    case "failed": return { ...state, submitted: null, submittedGeneration: null, error: action.message, uncertain: action.uncertain ?? false };
    case "use-saved": return createDraft(state.remote);
    case "reconcile": return { ...createDraft(state.remote), draft: action.value, generation: state.generation + 1 };
  }
}
