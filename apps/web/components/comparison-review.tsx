"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WorkflowSummary, workflowReasons } from "../lib/workflow";
import { ApiClientError, apiRequest } from "../lib/api";
import { analysisBackendMs, analysisBrowserMs } from "../lib/analysis-timeouts";

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
  supplier_id: string; supplier_name: string; quote_id: string; quote_fields: QuoteField[];
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

type AnalysisPoint = {
  text: string; supplier_ids: string[]; requirement_ids: string[];
  quote_fields: { quote_id: string; field_key: string }[]; evidence_ids: string[];
};
type Advice = {
  run_id: string; snapshot_id: string;
  analysis: { supplier_summaries: AnalysisPoint[]; key_tradeoffs: AnalysisPoint[];
    important_unknowns: AnalysisPoint[]; important_conflicts: AnalysisPoint[] };
  suggestion: { supplier_id: string | null; supporting_reasons: AnalysisPoint[];
    tradeoffs: AnalysisPoint[]; uncertainties: AnalysisPoint[]; evidence_ids: string[] };
};

function AdvicePoints({ title, points, comparison }: { title: string; points: AnalysisPoint[]; comparison: Comparison }) {
  if (!points.length) return null;
  return <div><h4>{title}</h4><ul>{points.map((point, index) => <li key={index}>
    <p>{point.text}</p>
    {comparison.comparison_payload.suppliers.filter((supplier) => point.supplier_ids.includes(supplier.supplier_id)).map((supplier) => {
      const fieldKeys = new Set(point.quote_fields.filter((ref) => ref.quote_id === supplier.quote_id).map((ref) => ref.field_key));
      for (const field of supplier.quote_fields) {
        if (field.evidence.some((evidence) => point.evidence_ids.includes(evidence.id))) fieldKeys.add(field.field_key);
      }
      const fields = [...fieldKeys];
      const results = supplier.evaluation.results.filter((result) => result.requirement_id && point.requirement_ids.includes(result.requirement_id));
      return <div key={supplier.supplier_id}>
        {results.map((result) => {
          const requirement = comparison.comparison_payload.brief.requirements.find((item) => item.id === result.requirement_id);
          return <div key={result.requirement_id}>
            <p>{supplier.supplier_name}: {label(result.kind)} — {label(result.status)}</p>
            {requirement && <p><span className="comparison-importance">{label(requirement.importance ?? "informational")}</span>{" · Expected: "}{display(requirement.expected_value)}</p>}
            <SourceDetails supplier={supplier} fact={result.selected_fact} evidenceIds={result.evidence_ids} />
          </div>;
        })}
        {fields.map((fieldKey) => <SourceDetails key={fieldKey} supplier={supplier} fieldKey={fieldKey} evidenceIds={point.evidence_ids} />)}
        {!fields.length ? <SourceDetails supplier={supplier} evidenceIds={point.evidence_ids} /> : null}
      </div>;
    })}
  </li>)}</ul></div>;
}

function ComparisonAdviceView({ advice, comparison }: { advice: Advice; comparison: Comparison }) {
  const selected = comparison.comparison_payload.suppliers.find((supplier) => supplier.supplier_id === advice.suggestion.supplier_id);
  return <section aria-label="Comparison analysis">
    <h3>Tradeoff analysis</h3>
    <AdvicePoints title="Supplier summaries" points={advice.analysis.supplier_summaries} comparison={comparison} />
    <AdvicePoints title="Key tradeoffs" points={advice.analysis.key_tradeoffs} comparison={comparison} />
    <AdvicePoints title="Important unknowns" points={advice.analysis.important_unknowns} comparison={comparison} />
    <AdvicePoints title="Important conflicts" points={advice.analysis.important_conflicts} comparison={comparison} />
    <h3>{selected ? "Suggested Supplier to Investigate First" : "No supplier suggested yet"}</h3>
    {selected ? <p><strong>{selected.supplier_name}</strong></p> : null}
    <p>This advice supports your review. You remain responsible for the supplier decision.</p>
    <AdvicePoints title="Supporting reasons" points={advice.suggestion.supporting_reasons} comparison={comparison} />
    <AdvicePoints title="Tradeoffs" points={advice.suggestion.tradeoffs} comparison={comparison} />
    <AdvicePoints title="Uncertainties" points={advice.suggestion.uncertainties} comparison={comparison} />
  </section>;
}

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
      {selectedQuoteField.origin === "USER_CORRECTED" ? <>
        <p>Current user-corrected value: {display(selectedQuoteField.current_value)}</p>
        {selectedQuoteField.field_key === "unit_price" && supplier.completeness.some((item) => item.field_key === "currency" && item.state === "conflicting")
          ? <p>Currency conflict remains unresolved; no currency is assigned to this amount.</p> : null}
      </> : null}
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

export function ComparisonReview({ projectId, refreshKey, onSnapshotChange, workflow, onGenerated }: {
  projectId: string; refreshKey: number; onSnapshotChange?: (hasSnapshot: boolean) => void; workflow?: WorkflowSummary; onGenerated?: () => void;
}) {
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [adviceBusy, setAdviceBusy] = useState(false);
  const [adviceError, setAdviceError] = useState<string | null>(null);
  const [adviceOutdated, setAdviceOutdated] = useState(false);
  const adviceSequence = useRef(0);
  const advicePresent = useRef(false);
  // Request ownership survives read-only freshness checks, including failed reads.
  const adviceBinding = useRef<string | null>(null);
  const advicePending = useRef(false);
  const adviceAbort = useRef<AbortController | null>(null);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [retryWaiting, setRetryWaiting] = useState(false);
  const displaySequence = useRef(0);
  const mutationSequence = useRef(0);
  const currentProjectId = useRef(projectId);
  currentProjectId.current = projectId;
  const active = useRef(false);

  const invalidateAdvice = useCallback(() => {
    adviceAbort.current?.abort();
    adviceAbort.current = null;
    if (retryTimer.current) clearTimeout(retryTimer.current);
    retryTimer.current = null;
    setRetryWaiting(false);
    adviceSequence.current += 1;
    if (advicePresent.current) setAdviceOutdated(true);
    advicePresent.current = false;
    adviceBinding.current = null;
    advicePending.current = false;
    setAdvice(null);
    setAdviceBusy(false);
    setAdviceError(null);
  }, []);

  const reload = useCallback(async (signal?: AbortSignal) => {
    const request = ++displaySequence.current;
    const parent = signal ?? (advicePending.current ? adviceAbort.current?.signal : undefined);
    const read = new AbortController();
    const abort = () => read.abort(parent?.reason);
    if (parent?.aborted) abort();
    else parent?.addEventListener("abort", abort, { once: true });
    const readTimer = setTimeout(() => read.abort(new DOMException("Verification deadline", "TimeoutError")), 15_000);
    setLoading(true);
    setError(null);
    try {
      const latest = await apiRequest<Comparison>(`/api/projects/${projectId}/comparison`, { signal: read.signal });
      if (!latest.comparison_payload?.suppliers || !latest.comparison_payload?.brief) throw new Error("Invalid comparison response");
      if (request === displaySequence.current) {
        setComparison(latest);
        if (adviceBinding.current && (adviceBinding.current !== latest.id || latest.stale)) {
          invalidateAdvice();
          setAdviceError("The comparison changed. Review the current comparison before analyzing again.");
        }
        onSnapshotChange?.(true);
      }
    } catch (failure) {
      if (request === displaySequence.current) {
        if (failure instanceof ApiClientError && failure.status === 404 && failure.code === "COMPARISON_NOT_FOUND" && adviceBinding.current) {
          invalidateAdvice();
          setAdviceError("The comparison is no longer available. Generate it before analyzing again.");
        }
        setComparison(null);
        onSnapshotChange?.(false);
        if (!(failure instanceof ApiClientError && failure.status === 404 && failure.code === "COMPARISON_NOT_FOUND")) {
          setError(failure instanceof ApiClientError ? failure.message : "The comparison could not be loaded. Try again.");
        }
      }
    } finally {
      clearTimeout(readTimer);
      parent?.removeEventListener("abort", abort);
      if (request === displaySequence.current) setLoading(false);
    }
  }, [projectId, onSnapshotChange, invalidateAdvice]);

  useEffect(() => {
    mutationSequence.current += 1;
    setBusy(false);
    return () => { mutationSequence.current += 1; };
  }, [projectId]);

  useEffect(() => {
    active.current = true;
    currentProjectId.current = projectId;
    invalidateAdvice();
    setAdviceOutdated(false);
    return () => {
      active.current = false;
      displaySequence.current += 1;
      adviceSequence.current += 1;
      adviceAbort.current?.abort();
      if (retryTimer.current) clearTimeout(retryTimer.current);
    };
  }, [projectId, invalidateAdvice]);

  useEffect(() => {
    setGenerationError(null);
    void reload();
    return () => { displaySequence.current += 1; };
  }, [reload, refreshKey, projectId]);

  useEffect(() => {
    const onFocus = () => { void reload(); };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [reload]);

  async function analyze() {
    if (!comparison || comparison.stale || loading || busy || advicePending.current || retryWaiting) return;
    const bound = comparison.id;
    const request = ++adviceSequence.current;
    const current = () => active.current && request === adviceSequence.current && projectId === currentProjectId.current;
    setAdvice(null);
    advicePresent.current = false;
    adviceBinding.current = bound;
    advicePending.current = true;
    const started = performance.now();
    const controller = new AbortController();
    adviceAbort.current = controller;
    const waitTimer = setTimeout(() => controller.abort(new DOMException("Analysis deadline", "TimeoutError")), analysisBrowserMs);
    setAdviceBusy(true);
    setAdviceError(null);
    try {
      const result = await apiRequest<Advice>(`/api/projects/${projectId}/comparison/advice`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ snapshot_id: bound }),
        signal: controller.signal,
      });
      if (!current()) return;
      if (result.snapshot_id !== bound) {
        throw new ApiClientError("The comparison changed. Regenerate it and analyze again.", "COMPARISON_STALE", 409);
      }
      setAdvice(result);
      advicePresent.current = true;
      setAdviceOutdated(false);
      // All reads share reload's sequence. Never let an older focus read restore
      // current presentation after a newer post-result verification.
      await reload(controller.signal);
    } catch (failure) {
      if (!current()) return;
      setAdvice(null);
      setAdviceError(failure instanceof ApiClientError ? failure.message : "Analysis could not be verified. Try again.");
      if (failure instanceof ApiClientError && ["NETWORK_ERROR", "INVALID_RESPONSE", "ANALYSIS_CONNECTION_LOST"].includes(failure.code)) {
        const remaining = Math.max(0, analysisBackendMs - (performance.now() - started));
        if (remaining > 0) {
          setAdviceError("The connection was interrupted. Analysis may still be finishing. Please wait before retrying.");
          setRetryWaiting(true);
          retryTimer.current = setTimeout(() => {
            if (current()) setRetryWaiting(false);
            retryTimer.current = null;
          }, remaining);
        }
      }
      if (failure instanceof ApiClientError && failure.code === "COMPARISON_STALE") {
        displaySequence.current += 1;
        setLoading(false);
        setError(null);
        setAdviceOutdated(true);
        setComparison((previous) => previous ? { ...previous, stale: true } : previous);
      }
    } finally {
      clearTimeout(waitTimer);
      if (current()) { advicePending.current = false; setAdviceBusy(false); }
    }
  }

  async function generate() {
    invalidateAdvice();
    const request = ++displaySequence.current;
    const mutation = ++mutationSequence.current;
    const current = () => mutation === mutationSequence.current && active.current && projectId === currentProjectId.current;
    setBusy(true);
    setError(null);
    setGenerationError(null);
    try {
      const latest = await apiRequest<Comparison>(`/api/projects/${projectId}/comparison/generate`, { method: "POST" });
      if (!current()) return;
      onGenerated?.();
      if (request === displaySequence.current) {
        setComparison(latest);
        onSnapshotChange?.(true);
      } else if (active.current && projectId === currentProjectId.current) {
        void reload();
      }
    } catch (failure) {
      if (current()) {
        setGenerationError(failure instanceof ApiClientError ? failure.message : "The comparison could not be generated. Try again.");
      }
    } finally {
      if (current()) setBusy(false);
    }
  }

  const warnings = comparison?.comparison_payload.suppliers.flatMap((supplier) =>
    supplier.evaluation.warnings.map((warning) => `${supplier.supplier_name}: ${warningText[warning.code] ?? label(warning.code)}`)) ?? [];
  const missing = comparison?.comparison_payload.suppliers.flatMap((supplier) => supplier.completeness
    .filter((item) => item.state !== "known")
    .map((item) => `${supplier.supplier_name}: ${label(item.field_key)} — ${item.state}`)) ?? [];

  return <section className="comparison-review" aria-labelledby="comparison-title" id="comparison">
    <h2 id="comparison-title">Comparison</h2>
    {workflow?.stage_prerequisites.COMPARISON ? <p role="status">{workflowReasons[workflow.stage_prerequisites.COMPARISON]}</p> : null}
    {loading ? <p role="status">Loading comparison…</p> : null}
    {(loading || error) && adviceBusy ? <p role="status">Analysis is pending while we verify the comparison.</p> : null}
    {error ? <div className="form-error" role="alert"><p>{error}</p><button type="button" onClick={() => void reload()}>Retry comparison</button></div> : null}
    {generationError ? <p className="form-error" role="alert">{generationError}</p> : null}
    {!loading && !error && adviceError ? <p className="form-error" role="alert">{adviceError}</p> : null}
    {!loading && !comparison && !error ? <p>No comparison has been generated. Generate one when the current shortlist has at least two confirmed quotes.</p> : null}
    {!loading && comparison ? <>
      {comparison.stale ? <div className="comparison-stale" role="status"><strong>Comparison outdated</strong><p>Inputs have changed. These are previous facts. Regenerate after the current Brief and shortlist are approved.</p></div> : <p role="status">Comparison is current.</p>}
      <ComparisonTable comparison={comparison} />
      {adviceOutdated ? <p role="status">Previous analysis is outdated. Analyze the current comparison again.</p> : null}
      <button type="button" disabled={adviceBusy || retryWaiting || busy || comparison.stale} onClick={() => void analyze()}>
        {adviceBusy ? "Analyzing…" : adviceError ? "Retry analysis" : "Analyze Comparison"}
      </button>
      {advice && advice.snapshot_id === comparison.id && !comparison.stale ? <ComparisonAdviceView advice={advice} comparison={comparison} /> : null}
      {warnings.length ? <div><h3>Warnings</h3><ul>{[...new Set(warnings)].map((warning) => <li key={warning}>{warning}</li>)}</ul></div> : null}
      {missing.length ? <details><summary>Missing or conflicting information</summary><ul>{missing.map((item) => <li key={item}>{item}</li>)}</ul></details> : null}
    </> : null}
    {!error || comparison || generationError ? <button type="button" id="comparison-generate" disabled={busy || loading || (workflow !== undefined && !workflow.comparison_ready)} onClick={() => void generate()}>
      {busy ? "Generating…" : generationError && !comparison ? "Retry generation" : comparison ? "Regenerate Comparison" : "Generate Comparison"}
    </button> : null}
  </section>;
}
