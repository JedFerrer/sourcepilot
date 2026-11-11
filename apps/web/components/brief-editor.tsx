"use client";

import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { ApiClientError, ApiFieldError, apiRequest } from "../lib/api";

import { useRecordDraft } from "./use-record-draft";
import { DraftConflict, RecordSaveStatus } from "./record-save-status";
import { useDraftRegistration } from "./workspace-drafts";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "./ui/dialog";
import { displayRequirement, humanLabel, requirementLabel } from "../lib/presentation";
import { sameRecord } from "../lib/record-draft";
import { focusEditorTarget } from "../lib/editor-focus";

type Importance = "REQUIRED" | "PREFERRED" | "INFORMATIONAL" | null;
type RequirementKind =
  | "MATERIAL" | "CERTIFICATION" | "MOQ" | "QUANTITY" | "UNIT_PRICE"
  | "PRODUCTION_LEAD_TIME" | "DELIVERY" | "CAPABILITY" | "INFORMATIONAL";
type Requirement = {
  id?: string;
  localId?: string;
  kind: RequirementKind;
  importance: Importance;
  expected_value: Record<string, unknown>;
  notes: string | null;
};
type Brief = {
  product_name: string | null;
  category: string | null;
  quantity: number | null;
  destination: string | null;
  delivery_target: Record<string, unknown> | null;
  target_unit_price: string | null;
  requirements: Requirement[];
  status: "IN_PROGRESS" | "READY_FOR_REVIEW" | "APPROVED";
  approved_at: string | null;
  missing_fields: { field_key: string; reason: string }[];
  uncertainties: string[];
  brief_revision: number;
  can_analyze: boolean;
};
type AnalyzeResult = Brief & { ambiguities: string[] };
type ClarificationQuestion = { field_key: string; question: string; reason: string };
type ClarificationResult = { brief_revision: number; questions: ClarificationQuestion[] };

const kinds: RequirementKind[] = [
  "MATERIAL", "CERTIFICATION", "MOQ", "QUANTITY", "UNIT_PRICE",
  "PRODUCTION_LEAD_TIME", "DELIVERY", "CAPABILITY", "INFORMATIONAL",
];
const subjects = [
  "DIMENSIONS", "SIZE_OR_CAPACITY", "COLOR", "PACKAGING", "LABELING",
  "PRODUCT_DESCRIPTION", "BRANDING_NOTES", "OTHER_CONTEXT",
];
const capabilityKeys = [
  "PRODUCT_CATEGORY", "CUSTOM_BRANDING", "BRANDING_METHOD", "PRODUCT_FEATURE", "MANUFACTURING_CAPABILITY",
];

function initialValue(kind: RequirementKind): Record<string, unknown> {
  if (kind === "MATERIAL" || kind === "CERTIFICATION") return { value: "" };
  if (kind === "MOQ" || kind === "QUANTITY") return { quantity: "" };
  if (kind === "UNIT_PRICE") return { amount: "", currency: "" };
  if (kind === "PRODUCTION_LEAD_TIME") return { max_days: "" };
  if (kind === "DELIVERY") return { kind: "DATE", date: "" };
  if (kind === "CAPABILITY") return { capability_key: "CUSTOM_BRANDING", value: true };
  return { subject: "OTHER_CONTEXT", text: "" };
}

function text(value: unknown): string {
  return value === null || value === undefined ? "" : String(value);
}


const briefFieldLabels: Record<string, string> = {
  product_name: "Product name",
  category: "Category",
  quantity: "Requested quantity",
  destination: "Destination",
  delivery_target: "Delivery target",
  target_unit_price: "Target unit price",
};

function fieldLabel(path: string): string {
  const parts = path.replace(/^body\./, "").split(".");
  if (parts[0] === "requirements" && /^\d+$/.test(parts[1] ?? "")) {
    const rest = parts.slice(2).join(" ").replaceAll("_", " ");
    return `Requirement ${Number(parts[1]) + 1}${rest ? ` ${rest}` : ""}`;
  }
  return briefFieldLabels[parts[0]] ?? parts.join(" ").replaceAll("_", " ");
}

function fieldMessage(field: ApiFieldError): string {
  return `${fieldLabel(field.field)}: ${field.message.replace(/^Value error,\s*/i, "")}`;
}

function normalizeRequirement(item: Requirement): Requirement {
  const value = item.expected_value;
  let expected: Record<string, unknown>;
  if (item.kind === "MOQ" || item.kind === "QUANTITY") {
    expected = { quantity: Number(value.quantity) };
  } else if (item.kind === "PRODUCTION_LEAD_TIME") {
    expected = { max_days: Number(value.max_days) };
  } else if (item.kind === "UNIT_PRICE") {
    expected = { amount: text(value.amount), ...(text(value.currency).trim() ? { currency: text(value.currency).trim().toUpperCase() } : {}) };
  } else if (item.kind === "DELIVERY" && value.kind === "PERIOD") {
    expected = { kind: "PERIOD", label: text(value.label), start_date: text(value.start_date) || null, end_date: text(value.end_date) || null };
  } else if (item.kind === "DELIVERY") {
    expected = { kind: "DATE", date: text(value.date) };
  } else if (item.kind === "CAPABILITY") {
    expected = { capability_key: value.capability_key, value: value.capability_key === "CUSTOM_BRANDING" ? value.value === true || value.value === "true" : text(value.value) };
  } else {
    expected = value;
  }
  return { ...(item.id ? { id: item.id } : {}), kind: item.kind, importance: item.importance, notes: item.notes, expected_value: expected };
}

function briefPayload(snapshot: Brief, expectedRevision?: number) {
  return {
    product_name: snapshot.product_name?.trim() || null,
    category: snapshot.category?.trim() || null,
    quantity: snapshot.quantity === null || snapshot.quantity === 0 ? null : Number(snapshot.quantity),
    destination: snapshot.destination?.trim() || null,
    delivery_target: snapshot.delivery_target,
    target_unit_price: snapshot.target_unit_price?.trim() || null,
    requirements: snapshot.requirements.map(normalizeRequirement),
    ...(expectedRevision === undefined ? {} : { expected_brief_revision: expectedRevision }),
  };
}

function editableBrief(value: Brief): Brief {
  return { ...value, status: "IN_PROGRESS", approved_at: null, missing_fields: [], uncertainties: [], brief_revision: 0, can_analyze: false };
}

function hasSavedContent(brief: Brief): boolean {
  return Boolean(brief.product_name || brief.category || brief.quantity || brief.destination || brief.delivery_target || brief.target_unit_price || brief.requirements.length);
}

function applyAnswers(brief: Brief, questions: ClarificationQuestion[], answers: Record<string, string>, deliveryKind: "DATE" | "PERIOD"): Brief {
  const next: Brief = { ...brief, requirements: [...brief.requirements] };
  for (const { field_key } of questions) {
    const value = answers[field_key].trim();
    if (field_key === "product_name" || field_key === "category" || field_key === "destination") next[field_key] = value;
    else if (field_key === "quantity") next.quantity = Number(value);
    else if (field_key === "delivery_target") next.delivery_target = deliveryKind === "DATE" ? { kind: "DATE", date: value } : { kind: "PERIOD", label: value, start_date: null, end_date: null };
    else if (field_key === "requirement.material") next.requirements.push({ kind: "MATERIAL", importance: null, expected_value: { value }, notes: null });
    else if (field_key === "requirement.custom_branding") next.requirements.push({ kind: "CAPABILITY", importance: null, expected_value: { capability_key: "CUSTOM_BRANDING", value: value === "yes" }, notes: null });
  }
  return next;
}

export function BriefEditor({ projectId, onProjectChange, originalRequest }: { projectId: string; onProjectChange?: () => Promise<void>; originalRequest?: string }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const remote = useRef<Brief | null>(null);
  if (brief && (!remote.current || !sameRecord(briefPayload(brief), briefPayload(remote.current)))) remote.current = editableBrief(brief);
  const record = useRecordDraft(remote.current);
  const draft = record.state.draft;
  const setDraft = record.edit;
  const [editing, setEditing] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [recoveredAnswers, setRecoveredAnswers] = useState<Record<string, string>>({});
  const [clarifications, setClarifications] = useState<ClarificationResult | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [deliveryKind, setDeliveryKind] = useState<"DATE" | "PERIOD">("DATE");
  const latestAnswers = useRef({ answers, deliveryKind });
  latestAnswers.current = { answers, deliveryKind };
  const [unsavedAnswers, setUnsavedAnswers] = useState<Record<string, { value: string; deliveryKind?: "DATE" | "PERIOD" }>>({});
  const [busy, setBusy] = useState<"analyze" | "save" | "clarify" | "answers" | "refresh" | "approve" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<ApiFieldError[]>([]);
  const errorSummary = useRef<HTMLDivElement>(null);
  const fieldPrefix = useId();
  const [failedSubmission, setFailedSubmission] = useState<{ snapshot: Brief; answers: boolean; attempt: number } | null>(null);
  const focusedFailure = useRef(0);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [needsConflictRefresh, setNeedsConflictRefresh] = useState(false);

  useEffect(() => {
    if (!failedSubmission || busy || failedSubmission.attempt === focusedFailure.current) return;
    focusedFailure.current = failedSubmission.attempt;
    focusEditorTarget(errorSummary.current);
  }, [failedSubmission, busy]);

  function errorTargets(field: ApiFieldError): string[] {
    const path = field.field.replace(/^body\./, "");
    const parts = path.split(".");
    if (failedSubmission?.answers && clarifications) {
      const submitted = failedSubmission.snapshot.requirements[Number(parts[1])];
      const answerKey = parts[0] === "requirements" ? submitted?.kind === "MATERIAL" ? "requirement.material" : submitted?.kind === "CAPABILITY" ? "requirement.custom_branding" : null : parts[0];
      if (answerKey && clarifications.questions.some(item => item.field_key === answerKey)) return [`answer.${answerKey}`];
    }
    if (parts[0] === "requirements") {
      const submitted = failedSubmission?.snapshot.requirements[Number(parts[1])];
      if (!submitted || !draft) return [];
      const identity = submitted.id ?? submitted.localId;
      const index = draft.requirements.findIndex(item => identity ? (item.id ?? item.localId) === identity : item === submitted);
      if (index < 0) return [];
      const item = draft.requirements[index];
      const prefix = `requirements.${index}`;
      if (["kind", "importance", "notes"].includes(parts[2])) return [`${prefix}.${parts[2]}`];
      const keys = Object.keys(item.expected_value).sort((a, b) => Number(["kind", "subject", "capability_key"].includes(a)) - Number(["kind", "subject", "capability_key"].includes(b)));
      if (parts[3] && keys.includes(parts[3])) return [`${prefix}.expected_value.${parts[3]}`];
      // Model-level errors apply to the whole value; link to its first control
      // and associate every related control rather than guessing from prose.
      return keys.map(key => `${prefix}.expected_value.${key}`);
    }
    if (parts[0] === "delivery_target") {
      const keys = Object.keys(draft?.delivery_target ?? {});
      return parts[1] && keys.includes(parts[1]) ? [path] : keys.length ? keys.filter(key => key !== "kind").map(key => `delivery_target.${key}`) : ["delivery_target.kind"];
    }
    return parts[0] in briefFieldLabels ? [parts[0]] : [];
  }

  function fieldProps(path: string) {
    const errors = fieldErrors.flatMap((field, index) => errorTargets(field).includes(path) ? [`${fieldPrefix}-error-${index}`] : []);
    return { id: `${fieldPrefix}-${path}`, "aria-invalid": errors.length ? true as const : undefined, "aria-describedby": errors.length ? errors.join(" ") : undefined };
  }

  function revealErrorField(path: string) {
    const target = document.getElementById(`${fieldPrefix}-${path}`);
    for (let parent = target?.parentElement; parent && parent !== errorSummary.current?.parentElement; parent = parent.parentElement) {
      if (parent instanceof HTMLDetailsElement) parent.open = true;
    }
    if (!focusEditorTarget(target)) focusEditorTarget(errorSummary.current);
  }

  const answerDirty = Object.values(answers).some((value) => value.trim()) || Object.keys(unsavedAnswers).length > 0;
  useDraftRegistration("brief", { label: "Brief", stage: "BRIEF", dirty: record.dirty || answerDirty,
    pending: busy === "save" || busy === "answers" || busy === "approve" || busy === "analyze",
    uncertain: record.state.uncertain, error,
    check: async () => { const latest = await apiRequest<Brief>(`/api/projects/${projectId}/brief`); setBrief(latest); },
  });

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(null);
    void apiRequest<Brief>(`/api/projects/${projectId}/brief`).then((value) => {
      if (!current) return;
      setBrief(value);

      setClarifications(null);
      setNeedsConflictRefresh(false);
      setLoading(false);
    }).catch((caught: unknown) => {
      if (!current) return;
      setError(caught instanceof ApiClientError ? caught.message : "Brief unavailable. Please try again.");
      setLoading(false);
    });
    return () => { current = false; };
  }, [projectId, reload]);

  async function analyze() {
    setBusy("analyze");
    setError(null);
    setFieldErrors([]);
    try {
      const result = await apiRequest<AnalyzeResult>(`/api/projects/${projectId}/brief/analyze`, { method: "POST" });
      setBrief(result);
      record.dispatch({ type: "reset", value: editableBrief(result) });
      setClarifications(null);
      await onProjectChange?.();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Analysis failed. Try again or enter the Brief manually.");
    } finally {
      setBusy(null);
    }
  }

  async function refreshAfterConflict(clearErrorOnSuccess = false) {
    setNeedsConflictRefresh(true);
    try {
      const latest = await apiRequest<Brief>(`/api/projects/${projectId}/brief`);
      setBrief(latest);
      record.dispatch({ type: "receive", value: editableBrief(latest) });
      const unresolved = new Set(latest.missing_fields.map((field) => field.field_key));
      setClarifications((current) => {
        const questions = current?.questions.filter((item) => unresolved.has(item.field_key)) ?? [];
        return questions.length ? { brief_revision: latest.brief_revision, questions } : null;
      });
      setAnswers((current) => {
        setRecoveredAnswers((previous) => ({ ...previous, ...Object.fromEntries(Object.entries(current).filter(([key, value]) => !unresolved.has(key) && value.trim())) }));
        return Object.fromEntries(Object.entries(current).filter(([fieldKey]) => unresolved.has(fieldKey)));
      });
      setNeedsConflictRefresh(false);
      if (clearErrorOnSuccess) setError(null);
    } catch {
      setError("This Brief changed, but we could not reload it. Try reloading before saving.");
    }
  }

  async function saveSnapshot(snapshot: Brief, expectedRevision: number, answerSave = false) {
    if (record.pending || record.state.conflict || record.state.uncertain) return;
    if (!record.begin(answerSave ? editableBrief(snapshot) : undefined)) return;
    const submittedAnswers = { answers: { ...answers }, deliveryKind };
    setBusy(answerSave ? "answers" : "save");
    setError(null);
    setFieldErrors([]);
    try {
      const result = await apiRequest<Brief>(`/api/projects/${projectId}/brief`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(briefPayload(snapshot, expectedRevision)),
      });
      setBrief(result);
      record.dispatch({ type: "saved", value: editableBrief(result) });
      // Acknowledge only answers included in this write. Later edits are recovery
      // drafts, even if the saved response no longer asks their questions.
      const latest = latestAnswers.current;
      const retained = Object.fromEntries(Object.entries(latest.answers)
        .filter(([key, value]) => !answerSave || value !== submittedAnswers.answers[key]
          || (key === "delivery_target" && latest.deliveryKind !== submittedAnswers.deliveryKind))
        .map(([key, value]) => [key, { value, ...(key === "delivery_target" ? { deliveryKind: latest.deliveryKind } : {}) }]));
      setUnsavedAnswers((current) => ({ ...current, ...retained }));
      setClarifications(null);
      setAnswers({});
      await onProjectChange?.();
    } catch (caught) {
      record.dispatch({ type: "failed", message: "Save failed", uncertain: caught instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE"].includes(caught.code) });
      setFailedSubmission(current => ({ snapshot, answers: answerSave, attempt: (current?.attempt ?? 0) + 1 }));
      if (caught instanceof ApiClientError && caught.fields?.length) {
        setFieldErrors(caught.fields);
      } else {
        setError(caught instanceof ApiClientError ? caught.message : "We could not save the Brief. Please try again.");
      }
      if (caught instanceof ApiClientError && caught.code === "BRIEF_CONFLICT") {
        await refreshAfterConflict();
      }
    } finally {
      setBusy(null);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (draft && brief && !needsConflictRefresh) await saveSnapshot(draft, brief.brief_revision);
  }

  async function approve() {
    if (!brief || !draft || brief.status !== "READY_FOR_REVIEW" || record.dirty || answerDirty || record.state.conflict) return;
    setBusy("approve");
    setError(null);
    setFieldErrors([]);
    try {
      const latest = await apiRequest<Brief>(`/api/projects/${projectId}/brief`);
      if (latest.brief_revision !== brief.brief_revision) {
        setBrief(latest); setError("Saved Brief changed. Review the latest saved values before approving again."); return;
      }
      const result = await apiRequest<Brief>(`/api/projects/${projectId}/brief/approve`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_brief_revision: brief.brief_revision }),
      });
      setBrief(result);
      setReviewOpen(false);
      setEditing(false);
      await onProjectChange?.();
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "We could not approve the Brief. Please try again.");
      if (caught instanceof ApiClientError && caught.code === "BRIEF_CONFLICT") setNeedsConflictRefresh(true);
    } finally {
      setBusy(null);
    }
  }

  async function generateQuestions() {
    setBusy("clarify");
    setError(null);
    setFieldErrors([]);
    setClarifications(null);
    setAnswers({});
    try {
      const result = await apiRequest<ClarificationResult>(`/api/projects/${projectId}/brief/clarifications`, { method: "POST" });
      setClarifications(result);
      setAnswers({});
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "We could not generate questions. Try again or edit the Brief manually.");
    } finally {
      setBusy(null);
    }
  }

  async function saveAnswers(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!brief || !draft || !clarifications || needsConflictRefresh || record.dirty) return;
    if (clarifications.questions.some((item) => !answers[item.field_key]?.trim())) return;
    await saveSnapshot(applyAnswers(brief, clarifications.questions, answers, deliveryKind), clarifications.brief_revision, true);
  }

  function updateField<K extends keyof Brief>(key: K, value: Brief[K]) {
    setFieldErrors([]);
    setDraft((current) => current ? { ...current, [key]: value } : current);
  }

  function updateRequirement(index: number, change: Partial<Requirement>) {
    setFieldErrors([]);
    setDraft((current) => current ? {
      ...current,
      requirements: current.requirements.map((item, at) => at === index ? { ...item, ...change } : item),
    } : current);
  }

  function updateValue(index: number, key: string, value: unknown) {
    if (!draft) return;
    updateRequirement(index, { expected_value: { ...draft.requirements[index].expected_value, [key]: value } });
  }

  function requirementFields(item: Requirement, index: number) {
    const value = item.expected_value;
    if (item.kind === "MATERIAL" || item.kind === "CERTIFICATION") return (
      <label>Value<input {...fieldProps(`requirements.${index}.expected_value.value`)} value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value)} required /></label>
    );
    if (item.kind === "MOQ" || item.kind === "QUANTITY") return (
      <label>Quantity<input {...fieldProps(`requirements.${index}.expected_value.quantity`)} type="number" min="1" step="1" value={text(value.quantity)} onChange={(event) => updateValue(index, "quantity", event.target.value)} required /></label>
    );
    if (item.kind === "UNIT_PRICE") return <>
      <label>Amount<input {...fieldProps(`requirements.${index}.expected_value.amount`)} type="number" min="0.0001" step="0.0001" value={text(value.amount)} onChange={(event) => updateValue(index, "amount", event.target.value)} required /></label>
      <label>Currency (optional)<input {...fieldProps(`requirements.${index}.expected_value.currency`)} maxLength={3} value={text(value.currency)} onChange={(event) => updateValue(index, "currency", event.target.value)} /></label>
    </>;
    if (item.kind === "PRODUCTION_LEAD_TIME") return (
      <label>Maximum days<input {...fieldProps(`requirements.${index}.expected_value.max_days`)} type="number" min="1" step="1" value={text(value.max_days)} onChange={(event) => updateValue(index, "max_days", event.target.value)} required /></label>
    );
    if (item.kind === "DELIVERY") return <>
      <label>Delivery target type<select {...fieldProps(`requirements.${index}.expected_value.kind`)} value={text(value.kind)} onChange={(event) => updateRequirement(index, { expected_value: event.target.value === "DATE" ? { kind: "DATE", date: "" } : { kind: "PERIOD", label: "", start_date: null, end_date: null } })}><option value="DATE">Date</option><option value="PERIOD">Period</option></select></label>
      {value.kind === "DATE" ? <label>Date<input {...fieldProps(`requirements.${index}.expected_value.date`)} type="date" value={text(value.date)} onChange={(event) => updateValue(index, "date", event.target.value)} required /></label> : <>
        <label>Period label<input {...fieldProps(`requirements.${index}.expected_value.label`)} value={text(value.label)} onChange={(event) => updateValue(index, "label", event.target.value)} required /></label>
        <label>Start date (optional)<input {...fieldProps(`requirements.${index}.expected_value.start_date`)} type="date" value={text(value.start_date)} onChange={(event) => updateValue(index, "start_date", event.target.value || null)} /></label>
        <label>End date (optional)<input {...fieldProps(`requirements.${index}.expected_value.end_date`)} type="date" value={text(value.end_date)} onChange={(event) => updateValue(index, "end_date", event.target.value || null)} /></label>
      </>}
    </>;
    if (item.kind === "CAPABILITY") return <>
      <label>Capability<select {...fieldProps(`requirements.${index}.expected_value.capability_key`)} value={text(value.capability_key)} onChange={(event) => updateRequirement(index, { expected_value: { capability_key: event.target.value, value: event.target.value === "CUSTOM_BRANDING" ? true : "" } })}>{capabilityKeys.map((key) => <option key={key} value={key}>{humanLabel(key)}</option>)}</select></label>
      {value.capability_key === "CUSTOM_BRANDING" ? <label>Custom branding<select {...fieldProps(`requirements.${index}.expected_value.value`)} value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value === "true")}><option value="true">Yes</option><option value="false">No</option></select></label> : <label>Value<input {...fieldProps(`requirements.${index}.expected_value.value`)} value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value)} required /></label>}
    </>;
    return <>
      <label>Subject<select {...fieldProps(`requirements.${index}.expected_value.subject`)} value={text(value.subject)} onChange={(event) => updateValue(index, "subject", event.target.value)}>{subjects.map((subject) => <option key={subject} value={subject}>{humanLabel(subject)}</option>)}</select></label>
      <label>Context<textarea {...fieldProps(`requirements.${index}.expected_value.text`)} value={text(value.text)} onChange={(event) => updateValue(index, "text", event.target.value)} required /></label>
    </>;
  }

  function renderRequirement(item: Requirement, index: number) {
    const heading = item.kind === "INFORMATIONAL" ? `Attribute ${index + 1}` : `Requirement ${index + 1}`;
    return <fieldset key={item.id ?? item.localId} className="brief-requirement" aria-label={heading}>
      <legend><span className="requirement-heading"><span>{heading}</span><button type="button" onClick={() => updateField("requirements", draft!.requirements.filter((_, at) => at !== index))}>Remove {item.kind === "INFORMATIONAL" ? "attribute" : "requirement"}</button></span></legend>
      <label>Kind<select {...fieldProps(`requirements.${index}.kind`)} value={item.kind} onChange={(event) => { const kind = event.target.value as RequirementKind; updateRequirement(index, { kind, expected_value: initialValue(kind) }); }}>{kinds.map((kind) => <option key={kind} value={kind}>{humanLabel(kind)}</option>)}</select></label>
      {requirementFields(item, index)}
      <label>Importance<select {...fieldProps(`requirements.${index}.importance`)} value={item.importance ?? ""} onChange={(event) => updateRequirement(index, { importance: event.target.value ? event.target.value as Importance : null })}><option value="">Not set</option><option value="REQUIRED">Required</option><option value="PREFERRED">Preferred</option><option value="INFORMATIONAL">Informational</option></select></label>
      <label>Notes (optional)<textarea {...fieldProps(`requirements.${index}.notes`)} value={item.notes ?? ""} onChange={(event) => updateRequirement(index, { notes: event.target.value || null })} /></label>
    </fieldset>;
  }

  if (loading) return <p>Loading Brief…</p>;
  if (!draft || !brief) return <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => setReload((value) => value + 1)}>Try again</button></div>;
  const hasUnsavedEdits = record.dirty;
  const conflict = record.state.conflict;

  return <section id="brief" className="brief-editor" aria-labelledby="brief-title">
    <div className="record-heading"><h2 id="brief-title" tabIndex={-1}>Sourcing Brief</h2><RecordSaveStatus savedVersion={record.savedVersion} dirty={hasUnsavedEdits || answerDirty} pending={record.pending} conflict={conflict} error={record.state.error} /></div>
    <div className="brief-status"><p>Readiness: {brief.status === "READY_FOR_REVIEW" ? "Ready for review" : brief.status === "APPROVED" ? "Approved" : "In progress"}</p></div>
    {conflict && record.state.remote ? <DraftConflict
      saved={<BriefValues brief={record.state.remote} />} draft={<BriefValues brief={draft} />}
      structural={!sameRecord(record.state.remote.requirements.map((item) => item.id).sort(), draft.requirements.map((item) => item.id).sort())}
      onUseSaved={() => record.dispatch({ type: "use-saved" })}
      onKeepDraft={() => record.dispatch({ type: "reconcile", value: draft })} /> : null}
    {record.state.uncertain ? <p role="alert">The save outcome is uncertain. Reload saved state before deciding how to recover. Do not repeat the write. <button type="button" onClick={() => void refreshAfterConflict()}>Check saved Brief</button></p> : null}
    {Object.keys(recoveredAnswers).length ? <details><summary>Earlier clarification answers—copy for recovery</summary><dl>{Object.entries(recoveredAnswers).map(([key, value]) => <div key={key}><dt>{fieldLabel(key)}</dt><dd>{value}</dd></div>)}</dl><p>These answers are not replayed. Deliberately edit the latest Brief if needed.</p></details> : null}
    {Object.keys(unsavedAnswers).length ? <section className="notice" aria-label="Unsaved clarification answers">
      <h3>Unsaved clarification answers</h3>
      <p>These edits were not included in the completed save. Copy them into the latest Brief deliberately, or discard them. They are never replayed automatically.</p>
      <dl>{Object.entries(unsavedAnswers).map(([key, answer]) => <div key={key}><dt>{fieldLabel(key)}{answer.deliveryKind ? ` (${answer.deliveryKind === "DATE" ? "Date" : "Period"})` : ""}</dt><dd>{answer.value || "Empty answer (cleared)"}</dd>
        <button type="button" onClick={() => setUnsavedAnswers((current) => { const next = { ...current }; delete next[key]; return next; })}>Discard retained answer for {fieldLabel(key)}</button>
      </div>)}</dl>
    </section> : null}
    {brief.status === "APPROVED" && !editing ? <section className="saved-brief"><div className="card-head"><h3>Approved Brief</h3><button type="button" onClick={() => setEditing(true)}>Edit Brief</button></div><BriefValues brief={brief} />{originalRequest ? <details className="original-request"><summary>Original sourcing request</summary><p>{originalRequest}</p></details> : null}</section> : null}
    {brief.approved_at ? <p>Approved on {new Date(brief.approved_at).toLocaleDateString()}</p> : null}
    {brief.missing_fields.length > 0 ? <section aria-label="Missing information"><h3>Missing information</h3><ul>{brief.missing_fields.map((field) => <li key={field.field_key}>{field.reason}</li>)}</ul></section> : null}
    <Dialog open={reviewOpen} onOpenChange={setReviewOpen}><DialogContent className="approval-dialog">
      <DialogTitle>Review saved Brief before approval</DialogTitle>
      <DialogDescription>This review contains saved values only. Confirm these are the requirements suppliers should be evaluated against.</DialogDescription>
      <BriefValues brief={brief} />
      {brief.requirements.some((item) => item.importance === null) ? <p className="issue-copy">Some requirement importance values are not set. Review them before approving.</p> : null}
      {brief.uncertainties.length > 0 ? <section aria-label="Uncertainties to review"><h3>Uncertainties to review</h3><ul>{brief.uncertainties.map((item, index) => <li key={index}>{item}</li>)}</ul></section> : null}
      {originalRequest ? <details className="original-request"><summary>Original sourcing request</summary><p>{originalRequest}</p></details> : null}
      {error ? <p role="alert" className="form-error">{error}</p> : null}
      {needsConflictRefresh ? <button type="button" onClick={() => { setBusy("refresh"); void refreshAfterConflict(true).finally(() => setBusy(null)); }} disabled={busy !== null}>Reload Brief</button> : null}
      <div className="review-actions"><button type="button" onClick={() => setReviewOpen(false)}>Continue editing</button><button type="button" className="primary-action" onClick={() => void approve()} disabled={brief.status !== "READY_FOR_REVIEW" || busy !== null || hasUnsavedEdits || answerDirty || conflict || needsConflictRefresh || record.state.uncertain}>{busy === "approve" ? "Approving…" : "Approve Brief"}</button></div>
    </DialogContent></Dialog>
    {brief.can_analyze ? <button type="button" id="brief-analyze" onClick={() => void analyze()} disabled={busy !== null || hasUnsavedEdits || answerDirty}>{busy === "analyze" ? "Analyzing…" : "Analyze request"}</button> : null}
    {hasSavedContent(brief) && brief.missing_fields.length > 0 ? <>
      <button type="button" id="brief-clarify" onClick={() => void generateQuestions()} disabled={busy !== null || hasUnsavedEdits}>{busy === "clarify" ? "Generating questions…" : "Get clarification questions"}</button>
      {hasUnsavedEdits ? <p>Save your Brief edits before generating questions.</p> : null}
    </> : null}
    {clarifications ? <form className="clarification-form" onSubmit={(event) => void saveAnswers(event)} aria-label="Clarification questions">
      <h3>Clarification questions</h3>
      {clarifications.questions.map((item) => <div key={item.field_key}>
        {item.field_key === "delivery_target" ? <>
          <p>{item.question}</p>
          <label>Delivery answer type<select value={deliveryKind} onChange={(event) => setDeliveryKind(event.target.value as "DATE" | "PERIOD")}><option value="DATE">Date</option><option value="PERIOD">Period</option></select></label>
          <label>Delivery answer<input {...fieldProps(`answer.${item.field_key}`)} type={deliveryKind === "DATE" ? "date" : "text"} value={answers[item.field_key] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [item.field_key]: event.target.value }))} required /></label>
        </> : <label>{item.question}
          {item.field_key === "requirement.custom_branding" ? <select {...fieldProps(`answer.${item.field_key}`)} value={answers[item.field_key] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [item.field_key]: event.target.value }))} required><option value="">Choose an answer</option><option value="yes">Yes</option><option value="no">No</option></select> :
            <input {...fieldProps(`answer.${item.field_key}`)} type={item.field_key === "quantity" ? "number" : "text"} min={item.field_key === "quantity" ? 1 : undefined} step={item.field_key === "quantity" ? 1 : undefined} value={answers[item.field_key] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [item.field_key]: event.target.value }))} required />}
        </label>}
        <p>{item.reason}</p>
      </div>)}
      <button type="submit" disabled={busy !== null || hasUnsavedEdits || needsConflictRefresh}>{busy === "answers" ? "Saving answers…" : "Save answers"}</button>
    </form> : null}
    {brief.uncertainties.length > 0 && !reviewOpen ? <section aria-label="Uncertainties to review"><h3>Uncertainties to review</h3><ul>{brief.uncertainties.map((item, index) => <li key={index}>{item}</li>)}</ul></section> : null}
    {(!reviewOpen && error) || fieldErrors.length > 0 ? <div className="form-error" role="alert" ref={errorSummary} tabIndex={-1} aria-label="Brief errors">
      <h3>Review these errors</h3>
      {error ? <p>{error}</p> : null}
      {fieldErrors.length > 0 ? <ul>{fieldErrors.map((field, index) => {
        const target = errorTargets(field)[0];
        return <li id={`${fieldPrefix}-error-${index}`} key={`${field.field}-${index}`}>{target ? <a href={`#${fieldPrefix}-${target}`} onClick={event => { event.preventDefault(); revealErrorField(target); }}>{fieldMessage(field)}</a> : fieldMessage(field)}</li>;
      })}</ul> : null}
    </div> : null}
    {needsConflictRefresh ? <button type="button" onClick={() => { setBusy("refresh"); void refreshAfterConflict(true).finally(() => setBusy(null)); }} disabled={busy !== null}>Reload Brief</button> : null}
    <form hidden={brief.status === "APPROVED" && !editing} id="brief-complete" className="brief-form" onSubmit={(event) => void save(event)}>
      <div className="brief-group"><h3>Product and quantity</h3><p className="group-help">Start with the essentials. Save before reviewing approval.</p><div className="form-fields">
      <label>Product name<input {...fieldProps("product_name")} value={draft.product_name ?? ""} onChange={(event) => updateField("product_name", event.target.value)} /></label>
      <label>Category<input {...fieldProps("category")} value={draft.category ?? ""} onChange={(event) => updateField("category", event.target.value)} /></label>
      <label>Requested quantity<input {...fieldProps("quantity")} type="number" min="1" step="1" value={draft.quantity ?? ""} onChange={(event) => updateField("quantity", event.target.value ? Number(event.target.value) : null)} /></label>
      </div>{originalRequest ? <details className="original-request"><summary>Original sourcing request</summary><p>{originalRequest}</p></details> : null}</div>
      <div className="brief-group"><h3>Commercial and delivery</h3><div className="form-fields">
      <label>Destination<input {...fieldProps("destination")} value={draft.destination ?? ""} onChange={(event) => updateField("destination", event.target.value)} /></label>
      <label>Delivery target type<select {...fieldProps("delivery_target.kind")} value={text(draft.delivery_target?.kind)} onChange={(event) => updateField("delivery_target", event.target.value === "DATE" ? { kind: "DATE", date: "" } : event.target.value === "PERIOD" ? { kind: "PERIOD", label: "", start_date: null, end_date: null } : null)}><option value="">Not set</option><option value="DATE">Date</option><option value="PERIOD">Period</option></select></label>
      {draft.delivery_target?.kind === "DATE" ? <label>Delivery date<input {...fieldProps("delivery_target.date")} type="date" value={text(draft.delivery_target.date)} onChange={(event) => updateField("delivery_target", { kind: "DATE", date: event.target.value })} required /></label> : null}
      {draft.delivery_target?.kind === "PERIOD" ? <>
        <label>Delivery period<input {...fieldProps("delivery_target.label")} value={text(draft.delivery_target.label)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, label: event.target.value })} required /></label>
        <label>Start date (optional)<input {...fieldProps("delivery_target.start_date")} type="date" value={text(draft.delivery_target.start_date)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, start_date: event.target.value || null })} /></label>
        <label>End date (optional)<input {...fieldProps("delivery_target.end_date")} type="date" value={text(draft.delivery_target.end_date)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, end_date: event.target.value || null })} /></label>
      </> : null}
      <label>Target unit price (optional)<input {...fieldProps("target_unit_price")} type="number" min="0.0001" step="0.0001" value={draft.target_unit_price ?? ""} onChange={(event) => updateField("target_unit_price", event.target.value)} /></label>
      </div></div><div className="brief-group brief-requirements-group"><h3>Requirements and importance</h3>
      {draft.requirements.map((item, index) => item.kind === "INFORMATIONAL" ? null : renderRequirement(item, index))}
      <button type="button" onClick={() => updateField("requirements", [...draft.requirements, { localId: crypto.randomUUID(), kind: "MATERIAL", importance: null, expected_value: initialValue("MATERIAL"), notes: null }])}>Add requirement</button>
      </div><div className="brief-group"><details className="additional-context"><summary>Additional context <span>Optional</span></summary>
      {draft.requirements.map((item, index) => item.kind === "INFORMATIONAL" ? renderRequirement(item, index) : null)}
      <button type="button" onClick={() => updateField("requirements", [...draft.requirements, { localId: crypto.randomUUID(), kind: "INFORMATIONAL", importance: "INFORMATIONAL", expected_value: initialValue("INFORMATIONAL"), notes: null }])}>Add attribute</button>
      </details></div>{hasUnsavedEdits ? <p className="group-help">Save your Brief edits before approving.</p> : null}
      <div className="editor-footer"><RecordSaveStatus savedVersion={record.savedVersion} dirty={hasUnsavedEdits || answerDirty} pending={record.pending} conflict={conflict} error={record.state.error} /><div className="actions">
      <button type="submit" disabled={busy !== null || needsConflictRefresh || conflict || record.state.uncertain || !hasUnsavedEdits}>{busy === "save" ? "Saving…" : "Save Brief"}</button>
      <button type="button" id="brief-approve" disabled={brief.status !== "READY_FOR_REVIEW" || busy !== null || hasUnsavedEdits || answerDirty || conflict || needsConflictRefresh || record.state.uncertain} onClick={() => setReviewOpen(true)}>Review saved Brief</button>
      </div></div>
    </form>
  </section>;
}

function BriefValues({ brief }: { brief: Brief }) {
  return <div className="saved-values"><dl className="review-summary">{Object.entries(briefFieldLabels).map(([key, label]) => {
    const value = brief[key as keyof Brief];
    return <div key={key}><dt>{label}</dt><dd>{value == null ? "Not provided" : typeof value === "object" ? displayRequirement(value as Record<string, unknown>) : String(value)}</dd></div>;
  })}</dl>{[false, true].map((context) => {
    const items = brief.requirements.filter((item) => (item.kind === "INFORMATIONAL") === context);
    return items.length ? <section key={String(context)}><h4>{context ? "Additional context" : "Requirements and importance"}</h4><dl className="review-summary">{items.map((item, index) => <div key={item.id ?? item.localId ?? index}><dt>{requirementLabel(item.kind, item.expected_value)}{!context ? ` · ${item.importance ? humanLabel(item.importance) : "Importance not set"}` : ""}</dt><dd>{displayRequirement(item.expected_value)}{item.notes ? <p className="value-note">{item.notes}</p> : null}</dd></div>)}</dl></section> : null;
  })}</div>;
}
