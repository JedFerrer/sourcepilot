"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiClientError, apiRequest } from "../lib/api";

type Evidence = {
  id: string; value: string | number | null; role: "supporting" | "provenance";
  page_number: number; block_number: number; document_block_id: string;
};
type QuoteField = {
  field_key: string; current_value: string | number | null; origin: string;
  ai_extracted_value: string | number | null; source_reference: string; evidence: Evidence[];
};
type Fact = {
  value: unknown; context: "PROJECT_QUOTE" | "GENERAL_SUPPLIER";
  source_reference: string; related_source_references: string[];
  supporting_evidence_ids: string[]; provenance_evidence_ids: string[];
  component_attributions?: { field_key: string; source_reference: string; supporting_evidence_ids: string[]; provenance_evidence_ids: string[] }[];
};
type Resolution = { status: "SELECTED" | "UNAVAILABLE" | "CONFLICT"; selected: Fact | null; project_facts: Fact[]; general_facts: Fact[] };
type Requirement = { id: string; kind: string; importance: string | null; expected_value: unknown; notes: string | null };
type Result = { requirement_id: string | null; kind: string; status: string; selected_fact: Fact | null; evidence_ids: string[]; conflicting_facts: Fact[] };
type Warning = { code: string; requirement_id: string | null };
type Supplier = {
  supplier_id: string; supplier_name: string; quote_fields: QuoteField[];
  resolved_facts: Record<string, Resolution>;
  evaluation: { results: Result[]; informational_requirement_ids: string[]; warnings: Warning[] };
  completeness: { field_key: string; state: "known" | "missing" | "conflicting"; source_references: string[] }[];
  supplier_facts: { evidence: { id: string; source_label: string; source_reference: string | null; evidence_state: string }[] };
};
type SupplierEvidence = Supplier["supplier_facts"]["evidence"][number];
type Comparison = {
  id: string; generated_at: string; stale: boolean;
  comparison_payload: { brief: { requirements: Requirement[] }; suppliers: Supplier[] };
};

const commercialRows = [
  ["unit_price", "Unit price"], ["quoted_quantity", "Quoted quantity"],
  ["moq", "Minimum order quantity"], ["production_lead_time", "Production lead time"],
  ["delivery_date", "Delivery commitment"], ["tooling_cost", "Tooling or setup cost"],
  ["shipping_cost", "Shipping cost"],
] as const;

const warningText: Record<string, string> = {
  MIXED_QUOTE_CURRENCIES: "Quotes use different currencies; prices cannot be directly compared.",
  QUANTITY_MISMATCH: "Quoted quantity differs from the requested quantity.",
  TARGET_CURRENCY_MISSING: "The target price has no currency.",
  PRICE_CURRENCY_MISSING: "A price currency is missing.",
  TARGET_CURRENCY_MISMATCH: "The target and quoted price use different currencies.",
  SELECTED_PRICE_CURRENCY_MISMATCH: "The selected price uses a different currency.",
};
const priceWarningCodes = new Set([
  "MIXED_QUOTE_CURRENCIES", "TARGET_CURRENCY_MISSING", "PRICE_CURRENCY_MISSING",
  "TARGET_CURRENCY_MISMATCH", "SELECTED_PRICE_CURRENCY_MISMATCH",
]);

function label(value: string): string {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function display(value: unknown): string {
  if (value === null || value === undefined || value === "") return "Unknown";
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.map(display).join(", ");
  if (typeof value === "object") {
    const item = value as Record<string, unknown>;
    if (item.amount !== undefined) return `${display(item.currency)} ${display(item.amount)}`;
    return Object.values(item).map(display).join(" · ");
  }
  return "Unknown";
}

function displayCommercialFact(fact: Fact, fieldKey?: string): string {
  return fieldKey === "production_lead_time" && fact.context === "GENERAL_SUPPLIER" && typeof fact.value === "number"
    ? `${fact.value} days`
    : display(fact.value);
}

function quoteField(supplier: Supplier, key: string): QuoteField | undefined {
  return supplier.quote_fields.find((field) => field.field_key === key);
}

function supplierEvidenceText(item: SupplierEvidence): string {
  return [item.source_label, item.source_reference, label(item.evidence_state), `ID: ${item.id}`]
    .filter(Boolean).join(" · ");
}

function SourceDetails({ supplier, fact, resolution, fieldKey, evidenceIds = [], includeCurrency = false }: {
  supplier: Supplier; fact?: Fact | null; resolution?: Resolution; fieldKey?: string; evidenceIds?: string[]; includeCurrency?: boolean;
}) {
  const field = fieldKey ? quoteField(supplier, fieldKey) : undefined;
  const projectFacts = resolution?.status === "CONFLICT" && !fact ? resolution.project_facts : [];
  const quoteReferences = new Set([...(fact ? [fact] : projectFacts)].flatMap((item) =>
    [item.source_reference, ...item.related_source_references,
      ...(item.component_attributions ?? []).map((component) => component.source_reference)]));
  const referencedQuoteFields = quoteReferences.size
    ? supplier.quote_fields.filter((item) => quoteReferences.has(item.source_reference))
    : field ? [field] : [];
  const currencyField = includeCurrency ? quoteField(supplier, "currency") : undefined;
  const selectedQuoteFields = currencyField && !referencedQuoteFields.includes(currencyField)
    ? [...referencedQuoteFields, currencyField] : referencedQuoteFields;
  const generalContextFacts = resolution?.general_facts.filter((item) => item.source_reference !== fact?.source_reference) ?? [];
  const selectedEvidenceIds = new Set([
    ...evidenceIds,
    ...(fact?.supporting_evidence_ids ?? []),
    ...(fact?.provenance_evidence_ids ?? []),
    ...(resolution?.status === "CONFLICT" && !fact
      ? projectFacts.flatMap((item) => [...item.supporting_evidence_ids, ...item.provenance_evidence_ids])
      : []),
  ]);
  const supplierEvidence = supplier.supplier_facts.evidence.filter((item) => selectedEvidenceIds.has(item.id));
  if (!fact && selectedQuoteFields.length === 0 && supplierEvidence.length === 0 && !generalContextFacts.length && !projectFacts.length) return null;
  return <details className="comparison-source">
    <summary>Source details</summary>
    {fact ? <>
      <p>{fact.context === "PROJECT_QUOTE" ? "Confirmed project quote" : "General supplier information"} · {fact.source_reference}</p>
      {fact.related_source_references?.length ? <p>Related sources: {fact.related_source_references.join(", ")}</p> : null}
    </> : null}
    {projectFacts.map((item) => <p key={item.source_reference}>Conflicting project quote context: {display(item.value)} · {item.source_reference}</p>)}
    {projectFacts.length ? <p>No project quote value was selected. PDF alternatives below are provenance for this conflict.</p> : null}
    {generalContextFacts.map((item) => {
      const contextEvidenceIds = new Set([...item.supporting_evidence_ids, ...item.provenance_evidence_ids]);
      return <div key={item.source_reference}>
        <p>General supplier context: {displayCommercialFact(item, fieldKey)} · {item.source_reference}</p>
        {supplier.supplier_facts.evidence.filter((evidence) => contextEvidenceIds.has(evidence.id)).map((evidence) =>
          <p key={evidence.id}>General supplier context evidence: {supplierEvidenceText(evidence)}</p>)}
      </div>;
    })}
    {selectedQuoteFields.map((selectedQuoteField) => <div key={selectedQuoteField.source_reference}>
      <p>{label(selectedQuoteField.field_key)} source: {selectedQuoteField.source_reference}</p>
      <p>{label(selectedQuoteField.field_key)} current origin: {label(selectedQuoteField.origin)}</p>
      {selectedQuoteField.origin === "USER_CORRECTED" ? <p>User-corrected value is current. Original PDF extraction below is provenance only; it does not verify the correction.</p> : null}
      {selectedQuoteField.ai_extracted_value != null ? <p>Original extracted value: {display(selectedQuoteField.ai_extracted_value)}</p> : null}
      {selectedQuoteField.evidence.map((item) => <p key={item.id}>
        {item.role === "provenance" ? "Original PDF provenance" : "Supporting PDF evidence"}: page {item.page_number}, block {item.block_number}; extracted {display(item.value)} · {item.id}
      </p>)}
    </div>)}
    {fact?.supporting_evidence_ids?.length ? <p>Supporting evidence IDs: {fact.supporting_evidence_ids.join(", ")}</p> : null}
    {fact?.provenance_evidence_ids?.length ? <p>Provenance evidence IDs: {fact.provenance_evidence_ids.join(", ")}</p> : null}
    {supplierEvidence.map((item) => <p key={item.id}>Supplier evidence: {supplierEvidenceText(item)}</p>)}
  </details>;
}

function ComparisonTable({ comparison }: { comparison: Comparison }) {
  const { suppliers, brief } = comparison.comparison_payload;
  return <div className="comparison-table-wrap">
    <table className="comparison-table">
      <caption>Factual comparison of confirmed supplier quotes</caption>
      <thead><tr><th scope="col">Criterion</th>{suppliers.map((supplier) => <th scope="col" key={supplier.supplier_id}>{supplier.supplier_name}</th>)}</tr></thead>
      <tbody>
        {commercialRows.map(([key, title]) => <tr key={key}><th scope="row">{title}</th>{suppliers.map((supplier) => {
          const resolution = supplier.resolved_facts[key];
          const fact = resolution?.selected;
          const state = resolution?.status;
          const completeness = supplier.completeness.find((item) => item.field_key === key);
          const rawField = !resolution ? quoteField(supplier, key) : undefined;
          const rawCurrency = quoteField(supplier, "currency")?.current_value;
          const currencyState = supplier.completeness.find((item) => item.field_key === "currency")?.state;
          const rawValue = rawField?.current_value != null && (key === "tooling_cost" || key === "shipping_cost")
            ? currencyState === "known" && rawCurrency != null && rawCurrency !== ""
              ? `${display(rawCurrency)} ${display(rawField.current_value)}`
              : `${display(rawField.current_value)} (currency: ${currencyState === "conflicting" ? "Conflict" : "Unknown"})`
            : display(rawField?.current_value);
          return <td key={supplier.supplier_id}>
            <strong>{state === "CONFLICT" || completeness?.state === "conflicting" ? "Conflict" : fact ? displayCommercialFact(fact, key) : rawValue}</strong>
            {key === "unit_price" && state === "SELECTED" && fact ? <small>
              {fact.context === "GENERAL_SUPPLIER" ? "General supplier indicative price" : "Confirmed project quote price"}
            </small> : null}
            <SourceDetails supplier={supplier} fact={fact} resolution={resolution} fieldKey={key}
              includeCurrency={rawField?.current_value != null && (key === "tooling_cost" || key === "shipping_cost")} />
            {(key === "unit_price" || key === "quoted_quantity") ? supplier.evaluation.warnings
              .filter((item) => key === "unit_price" ? priceWarningCodes.has(item.code) : item.code === "QUANTITY_MISMATCH")
              .map((item) => <small key={item.code}>{warningText[item.code] ?? label(item.code)}</small>) : null}
          </td>;
        })}</tr>)}
        {brief.requirements.map((requirement) => <tr key={requirement.id}><th scope="row">
          {label(requirement.kind)} <span className="comparison-importance">{label(requirement.importance ?? "informational")}</span>
          <small>Expected: {display(requirement.expected_value)}</small>
        </th>{suppliers.map((supplier) => {
          const result = supplier.evaluation.results.find((item) => item.requirement_id === requirement.id);
          const informational = supplier.evaluation.informational_requirement_ids.includes(requirement.id);
          const status = informational ? "Informational" : result ? label(result.status) : "Unknown";
          return <td key={supplier.supplier_id}>
            <strong className={requirement.importance === "REQUIRED" && result?.status === "DOES_NOT_MEET" ? "comparison-required-failure" : undefined}>{status}</strong>
            <SourceDetails supplier={supplier} fact={result?.selected_fact} evidenceIds={result?.evidence_ids} />
            {result?.conflicting_facts.map((item) => <div key={item.source_reference}>
              <p>Conflicting value: {display(item.value)}</p>
              <SourceDetails supplier={supplier} fact={item} />
            </div>)}
          </td>;
        })}</tr>)}
      </tbody>
    </table>
  </div>;
}

export function ComparisonReview({ projectId, refreshKey, onSnapshotChange }: {
  projectId: string; refreshKey: number; onSnapshotChange?: (hasSnapshot: boolean) => void;
}) {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const displaySequence = useRef(0);
  const mutationSequence = useRef(0);
  const currentProjectId = useRef(projectId);
  const active = useRef(false);

  const reload = useCallback(async () => {
    const request = ++displaySequence.current;
    setLoading(true);
    setError(null);
    try {
      const latest = await apiRequest<Comparison>(`/api/projects/${projectId}/comparison`);
      if (!latest.comparison_payload?.suppliers || !latest.comparison_payload?.brief) throw new Error("Invalid comparison response");
      if (request === displaySequence.current) {
        setComparison(latest);
        onSnapshotChange?.(true);
      }
    } catch (failure) {
      if (request === displaySequence.current) {
        setComparison(null);
        onSnapshotChange?.(false);
        if (!(failure instanceof ApiClientError && failure.status === 404 && failure.code === "COMPARISON_NOT_FOUND")) {
          setError(failure instanceof ApiClientError ? failure.message : "The comparison could not be loaded. Try again.");
        }
      }
    } finally {
      if (request === displaySequence.current) setLoading(false);
    }
  }, [projectId, onSnapshotChange]);

  useEffect(() => {
    active.current = true;
    currentProjectId.current = projectId;
    setGenerationError(null);
    void reload();
    return () => { active.current = false; displaySequence.current += 1; };
  }, [reload, refreshKey, projectId]);

  async function generate() {
    const request = ++displaySequence.current;
    const mutation = ++mutationSequence.current;
    setBusy(true);
    setError(null);
    setGenerationError(null);
    try {
      const latest = await apiRequest<Comparison>(`/api/projects/${projectId}/comparison/generate`, { method: "POST" });
      if (request === displaySequence.current) {
        setComparison(latest);
        onSnapshotChange?.(true);
      } else if (active.current && projectId === currentProjectId.current) {
        void reload();
      }
    } catch (failure) {
      if (mutation === mutationSequence.current && active.current && projectId === currentProjectId.current) {
        setGenerationError(failure instanceof ApiClientError ? failure.message : "The comparison could not be generated. Try again.");
      }
    } finally {
      if (mutation === mutationSequence.current) setBusy(false);
    }
  }

  const warnings = comparison?.comparison_payload.suppliers.flatMap((supplier) =>
    supplier.evaluation.warnings.map((warning) => `${supplier.supplier_name}: ${warningText[warning.code] ?? label(warning.code)}`)) ?? [];
  const missing = comparison?.comparison_payload.suppliers.flatMap((supplier) => supplier.completeness
    .filter((item) => item.state !== "known")
    .map((item) => `${supplier.supplier_name}: ${label(item.field_key)} — ${item.state}`)) ?? [];

  return <section className="comparison-review" aria-labelledby="comparison-title" id="comparison">
    <h2 id="comparison-title">Comparison</h2>
    {loading ? <p role="status">Loading comparison…</p> : null}
    {error ? <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry comparison</button></div> : null}
    {generationError ? <p className="form-error" role="alert">{generationError}</p> : null}
    {!loading && !comparison && !error ? <p>No comparison has been generated. Generate one when the current shortlist has at least two confirmed quotes.</p> : null}
    {!loading && comparison ? <>
      {comparison.stale ? <div className="comparison-stale" role="status"><strong>Comparison outdated</strong><p>Inputs have changed. These are previous facts. Regenerate after the current Brief and shortlist are approved.</p></div> : <p role="status">Comparison is current.</p>}
      <ComparisonTable comparison={comparison} />
      {warnings.length ? <div><h3>Warnings</h3><ul>{[...new Set(warnings)].map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}
      {missing.length ? <details><summary>Missing or conflicting information</summary><ul>{missing.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
    </> : null}
    {!error || comparison || generationError ? <button type="button" disabled={busy || loading} onClick={() => void generate()}>
      {busy ? "Generating…" : generationError && !comparison ? "Retry generation" : comparison ? "Regenerate Comparison" : "Generate Comparison"}
    </button> : null}
  </section>;
}
