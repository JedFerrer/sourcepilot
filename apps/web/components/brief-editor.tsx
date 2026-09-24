"use client";

import { FormEvent, useEffect, useState } from "react";
import { ApiClientError, ApiFieldError, apiRequest } from "../lib/api";

type Importance = "REQUIRED" | "PREFERRED" | "INFORMATIONAL" | null;
type RequirementKind =
  | "MATERIAL" | "CERTIFICATION" | "MOQ" | "QUANTITY" | "UNIT_PRICE"
  | "PRODUCTION_LEAD_TIME" | "DELIVERY" | "CAPABILITY" | "INFORMATIONAL";
type Requirement = {
  id?: string;
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
  missing_fields: { field_key: string; reason: string }[];
  brief_revision: number;
  can_analyze: boolean;
};
type AnalyzeResult = Brief & { ambiguities: string[] };

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
  return { ...item, expected_value: expected };
}

export function BriefEditor({ projectId }: { projectId: string }) {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [draft, setDraft] = useState<Brief | null>(null);
  const [ambiguities, setAmbiguities] = useState<string[]>([]);
  const [busy, setBusy] = useState<"analyze" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<ApiFieldError[]>([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    let current = true;
    setLoading(true);
    setError(null);
    void apiRequest<Brief>(`/api/projects/${projectId}/brief`).then((value) => {
      if (!current) return;
      setBrief(value);
      setDraft(value);
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
      setDraft(result);
      setAmbiguities(result.ambiguities);
    } catch (caught) {
      setError(caught instanceof ApiClientError ? caught.message : "Analysis failed. Try again or enter the Brief manually.");
    } finally {
      setBusy(null);
    }
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draft) return;
    setBusy("save");
    setError(null);
    setFieldErrors([]);
    const payload = {
      product_name: draft.product_name?.trim() || null,
      category: draft.category?.trim() || null,
      quantity: draft.quantity === null || draft.quantity === 0 ? null : Number(draft.quantity),
      destination: draft.destination?.trim() || null,
      delivery_target: draft.delivery_target,
      target_unit_price: draft.target_unit_price?.trim() || null,
      requirements: draft.requirements.map(normalizeRequirement),
    };
    try {
      const result = await apiRequest<Brief>(`/api/projects/${projectId}/brief`, {
        method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
      });
      setBrief(result);
      setDraft(result);
      setAmbiguities([]);
    } catch (caught) {
      if (caught instanceof ApiClientError && caught.fields?.length) {
        setFieldErrors(caught.fields);
      } else {
        setError(caught instanceof ApiClientError ? caught.message : "We could not save the Brief. Please try again.");
      }
    } finally {
      setBusy(null);
    }
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
      <label>Value<input value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value)} required /></label>
    );
    if (item.kind === "MOQ" || item.kind === "QUANTITY") return (
      <label>Quantity<input type="number" min="1" step="1" value={text(value.quantity)} onChange={(event) => updateValue(index, "quantity", event.target.value)} required /></label>
    );
    if (item.kind === "UNIT_PRICE") return <>
      <label>Amount<input type="number" min="0.0001" step="0.0001" value={text(value.amount)} onChange={(event) => updateValue(index, "amount", event.target.value)} required /></label>
      <label>Currency (optional)<input maxLength={3} value={text(value.currency)} onChange={(event) => updateValue(index, "currency", event.target.value)} /></label>
    </>;
    if (item.kind === "PRODUCTION_LEAD_TIME") return (
      <label>Maximum days<input type="number" min="1" step="1" value={text(value.max_days)} onChange={(event) => updateValue(index, "max_days", event.target.value)} required /></label>
    );
    if (item.kind === "DELIVERY") return <>
      <label>Delivery target type<select value={text(value.kind)} onChange={(event) => updateRequirement(index, { expected_value: event.target.value === "DATE" ? { kind: "DATE", date: "" } : { kind: "PERIOD", label: "", start_date: null, end_date: null } })}><option value="DATE">Date</option><option value="PERIOD">Period</option></select></label>
      {value.kind === "DATE" ? <label>Date<input type="date" value={text(value.date)} onChange={(event) => updateValue(index, "date", event.target.value)} required /></label> : <>
        <label>Period label<input value={text(value.label)} onChange={(event) => updateValue(index, "label", event.target.value)} required /></label>
        <label>Start date (optional)<input type="date" value={text(value.start_date)} onChange={(event) => updateValue(index, "start_date", event.target.value || null)} /></label>
        <label>End date (optional)<input type="date" value={text(value.end_date)} onChange={(event) => updateValue(index, "end_date", event.target.value || null)} /></label>
      </>}
    </>;
    if (item.kind === "CAPABILITY") return <>
      <label>Capability<select value={text(value.capability_key)} onChange={(event) => updateRequirement(index, { expected_value: { capability_key: event.target.value, value: event.target.value === "CUSTOM_BRANDING" ? true : "" } })}>{capabilityKeys.map((key) => <option key={key} value={key}>{key.replaceAll("_", " ")}</option>)}</select></label>
      {value.capability_key === "CUSTOM_BRANDING" ? <label>Custom branding<select value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value === "true")}><option value="true">Yes</option><option value="false">No</option></select></label> : <label>Value<input value={text(value.value)} onChange={(event) => updateValue(index, "value", event.target.value)} required /></label>}
    </>;
    return <>
      <label>Subject<select value={text(value.subject)} onChange={(event) => updateValue(index, "subject", event.target.value)}>{subjects.map((subject) => <option key={subject} value={subject}>{subject.replaceAll("_", " ")}</option>)}</select></label>
      <label>Context<textarea value={text(value.text)} onChange={(event) => updateValue(index, "text", event.target.value)} required /></label>
    </>;
  }

  function renderRequirement(item: Requirement, index: number) {
    return <fieldset key={item.id ?? `new-${index}`} className="brief-requirement">
      <legend>{item.kind === "INFORMATIONAL" ? `Attribute ${index + 1}` : `Requirement ${index + 1}`}</legend>
      <label>Kind<select value={item.kind} onChange={(event) => { const kind = event.target.value as RequirementKind; updateRequirement(index, { kind, expected_value: initialValue(kind) }); }}>{kinds.map((kind) => <option key={kind} value={kind}>{kind.replaceAll("_", " ")}</option>)}</select></label>
      {requirementFields(item, index)}
      <label>Importance<select value={item.importance ?? ""} onChange={(event) => updateRequirement(index, { importance: event.target.value ? event.target.value as Importance : null })}><option value="">Not set</option><option value="REQUIRED">Required</option><option value="PREFERRED">Preferred</option><option value="INFORMATIONAL">Informational</option></select></label>
      <label>Notes (optional)<textarea value={item.notes ?? ""} onChange={(event) => updateRequirement(index, { notes: event.target.value || null })} /></label>
      <button type="button" onClick={() => updateField("requirements", draft!.requirements.filter((_, at) => at !== index))}>Remove {item.kind === "INFORMATIONAL" ? "attribute" : "requirement"}</button>
    </fieldset>;
  }

  if (loading) return <p>Loading Brief…</p>;
  if (!draft || !brief) return <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => setReload((value) => value + 1)}>Try again</button></div>;

  return <section className="brief-editor" aria-labelledby="brief-title">
    <h2 id="brief-title">Sourcing Brief</h2>
    <p>Readiness: {brief.status === "READY_FOR_REVIEW" ? "Ready for review" : brief.status === "APPROVED" ? "Approved" : "In progress"}</p>
    {brief.missing_fields.length > 0 ? <section aria-label="Missing information"><h3>Missing information</h3><ul>{brief.missing_fields.map((field) => <li key={field.field_key}>{field.reason}</li>)}</ul></section> : <p>No required information is missing.</p>}
    {brief.can_analyze ? <button type="button" onClick={() => void analyze()} disabled={busy !== null}>{busy === "analyze" ? "Analyzing…" : "Analyze request"}</button> : null}
    {ambiguities.length > 0 ? <section aria-label="Unclear information"><h3>Unclear information</h3><ul>{ambiguities.map((item, index) => <li key={index}>{item}</li>)}</ul></section> : null}
    {error || fieldErrors.length > 0 ? <div className="form-error" role="alert">
      {error ? <p>{error}</p> : null}
      {fieldErrors.length > 0 ? <ul>{fieldErrors.map((field, index) => <li key={`${field.field}-${index}`}>{fieldMessage(field)}</li>)}</ul> : null}
    </div> : null}
    <form className="brief-form" onSubmit={(event) => void save(event)}>
      <h3>Product and delivery</h3>
      <label>Product name<input value={draft.product_name ?? ""} onChange={(event) => updateField("product_name", event.target.value)} /></label>
      <label>Category<input value={draft.category ?? ""} onChange={(event) => updateField("category", event.target.value)} /></label>
      <label>Requested quantity<input type="number" min="1" step="1" value={draft.quantity ?? ""} onChange={(event) => updateField("quantity", event.target.value ? Number(event.target.value) : null)} /></label>
      <label>Destination<input value={draft.destination ?? ""} onChange={(event) => updateField("destination", event.target.value)} /></label>
      <label>Delivery target type<select value={text(draft.delivery_target?.kind)} onChange={(event) => updateField("delivery_target", event.target.value === "DATE" ? { kind: "DATE", date: "" } : event.target.value === "PERIOD" ? { kind: "PERIOD", label: "", start_date: null, end_date: null } : null)}><option value="">Not set</option><option value="DATE">Date</option><option value="PERIOD">Period</option></select></label>
      {draft.delivery_target?.kind === "DATE" ? <label>Delivery date<input type="date" value={text(draft.delivery_target.date)} onChange={(event) => updateField("delivery_target", { kind: "DATE", date: event.target.value })} required /></label> : null}
      {draft.delivery_target?.kind === "PERIOD" ? <>
        <label>Delivery period<input value={text(draft.delivery_target.label)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, label: event.target.value })} required /></label>
        <label>Start date (optional)<input type="date" value={text(draft.delivery_target.start_date)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, start_date: event.target.value || null })} /></label>
        <label>End date (optional)<input type="date" value={text(draft.delivery_target.end_date)} onChange={(event) => updateField("delivery_target", { ...draft.delivery_target, end_date: event.target.value || null })} /></label>
      </> : null}
      <label>Target unit price (optional)<input type="number" min="0.0001" step="0.0001" value={draft.target_unit_price ?? ""} onChange={(event) => updateField("target_unit_price", event.target.value)} /></label>
      <h3>Sourcing requirements</h3>
      {draft.requirements.map((item, index) => item.kind === "INFORMATIONAL" ? null : renderRequirement(item, index))}
      <button type="button" onClick={() => updateField("requirements", [...draft.requirements, { kind: "MATERIAL", importance: null, expected_value: initialValue("MATERIAL"), notes: null }])}>Add requirement</button>
      <h3>Informational attributes</h3>
      {draft.requirements.map((item, index) => item.kind === "INFORMATIONAL" ? renderRequirement(item, index) : null)}
      <button type="button" onClick={() => updateField("requirements", [...draft.requirements, { kind: "INFORMATIONAL", importance: "INFORMATIONAL", expected_value: initialValue("INFORMATIONAL"), notes: null }])}>Add attribute</button>
      <button type="submit" disabled={busy !== null}>{busy === "save" ? "Saving…" : "Save Brief"}</button>
    </form>
  </section>;
}
