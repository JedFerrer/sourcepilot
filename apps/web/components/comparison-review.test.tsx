import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ComparisonReview } from "./comparison-review";
import { jsonResponse } from "../test/api-responses";

const fact = (value: unknown, source = "quote-value:price") => ({
  value, context: "PROJECT_QUOTE", source_reference: source, related_source_references: [] as string[],
  supporting_evidence_ids: [] as string[], provenance_evidence_ids: ["evidence-1"],
  component_attributions: [] as { field_key: string; source_reference: string; supporting_evidence_ids: string[]; provenance_evidence_ids: string[] }[],
});
const resolution = (value: unknown) => ({ status: "SELECTED", selected: fact(value), project_facts: [fact(value)], general_facts: [] });
const requirements = [
  { id: "required", kind: "MATERIAL", importance: "REQUIRED", expected_value: { material: "Recycled" }, notes: null },
  { id: "preferred", kind: "CERTIFICATION", importance: "PREFERRED", expected_value: { certification: "GOTS" }, notes: null },
  { id: "informational", kind: "INFORMATIONAL", importance: "INFORMATIONAL", expected_value: { note: "Packaging" }, notes: null },
];
const supplier = (id: string, name: string, corrected = false) => ({
  supplier_id: id, supplier_name: name, quote_id: `quote-${id}`,
  quote_fields: [{ field_key: "unit_price", current_value: (corrected ? "4.50" : "4.25") as string | null,
    origin: corrected ? "USER_CORRECTED" : "AI_EXTRACTED", ai_extracted_value: "4.25" as string | null,
    source_reference: "quote-value:price", evidence: [{ id: "evidence-1", value: "4.25",
      role: corrected ? "provenance" : "supporting", page_number: 2, block_number: 3, document_block_id: "block-1" }] }],
  resolved_facts: { unit_price: resolution({ amount: corrected ? "4.50" : "4.25", currency: id === "a" ? "USD" : "EUR" }),
    quoted_quantity: resolution(2000), moq: resolution(500), production_lead_time: resolution("25 days"),
    delivery_date: { status: "UNAVAILABLE", selected: null, project_facts: [], general_facts: [] } },
  evaluation: { results: [
    { requirement_id: "required", kind: "MATERIAL", status: id === "a" ? "DOES_NOT_MEET" : "MEETS", selected_fact: null, evidence_ids: [], conflicting_facts: [] },
    { requirement_id: "preferred", kind: "CERTIFICATION", status: id === "a" ? "UNKNOWN" : "CONFLICT", selected_fact: null, evidence_ids: [], conflicting_facts: [] },
  ], informational_requirement_ids: ["informational"], warnings: [{ code: "MIXED_QUOTE_CURRENCIES", requirement_id: null }] },
  completeness: [{ field_key: "delivery_date", state: "missing", source_references: [] as string[] }],
  supplier_facts: { evidence: [] as { id: string; source_label: string; source_reference: string | null; evidence_state: string }[] },
});
const snapshot = (stale = false, corrected = false) => ({
  id: corrected ? "comparison-2" : "comparison-1", generated_at: "2026-09-29T00:00:00Z", stale,
  comparison_payload: { brief: { requirements }, suppliers: [supplier("a", "Willow", corrected), supplier("b", "Moss")] },
});
const notFound = () => jsonResponse({ error: { code: "COMPARISON_NOT_FOUND", message: "No comparison exists." } }, 404);

describe("ComparisonReview", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it("lets the server decide generation eligibility and shows its rejection", async () => {
    let generationAttempts = 0;
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => Promise.resolve(
      init?.method === "POST"
        ? ++generationAttempts === 1
          ? jsonResponse({ error: { code: "COMPARISON_NOT_READY", message: "At least two shortlisted suppliers need confirmed quotes." } }, 409)
          : jsonResponse(snapshot(), 201)
        : notFound(),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate Comparison" }));
    expect(await screen.findByText("At least two shortlisted suppliers need confirmed quotes.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry comparison" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry generation" }));
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    expect(generationAttempts).toBe(2);
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/comparison/generate", expect.objectContaining({ method: "POST" }));
  });

  it("generates the first snapshot from the server response", async () => {
    vi.stubGlobal("fetch", vi.fn((_path: string, init?: RequestInit) => Promise.resolve(init?.method === "POST" ? jsonResponse(snapshot(), 201) : notFound())));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate Comparison" }));
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Willow" })).toBeInTheDocument();
  });

  it("ignores A generation before B's read resolves and lets B complete normally", async () => {
    let resolveGeneration!: (response: Response) => void;
    let resolveB!: (response: Response) => void;
    const onGeneratedA = vi.fn();
    const onGeneratedB = vi.fn();
    const onSnapshotChange = vi.fn();
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "POST") return path.includes("/a/")
        ? new Promise<Response>((resolve) => { resolveGeneration = resolve; })
        : Promise.resolve(jsonResponse(snapshot(false, true), 201));
      return path.includes("/b/")
        ? new Promise<Response>((resolve) => { resolveB = resolve; })
        : Promise.resolve(notFound());
    });
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<ComparisonReview projectId="a" refreshKey={0} onGenerated={onGeneratedA} onSnapshotChange={onSnapshotChange} />);
    fireEvent.click(await screen.findByRole("button", { name: "Generate Comparison" }));
    rerender(<ComparisonReview projectId="b" refreshKey={0} onGenerated={onGeneratedB} onSnapshotChange={onSnapshotChange} />);
    onSnapshotChange.mockClear();
    await act(async () => resolveGeneration(jsonResponse(snapshot(), 201)));
    expect(onGeneratedA).not.toHaveBeenCalled();
    expect(onGeneratedB).not.toHaveBeenCalled();
    expect(onSnapshotChange).not.toHaveBeenCalled();
    expect(screen.getByText("Loading comparison…")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(3);
    await act(async () => resolveB(notFound()));
    fireEvent.click(screen.getByRole("button", { name: "Generate Comparison" }));
    await screen.findByText("Comparison is current.");
    expect(onGeneratedB).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Regenerate Comparison" })).toBeEnabled();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
  });

  it("does not display a previously current snapshot when refresh fails", async () => {
    let failure = false;
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(failure
      ? jsonResponse({ error: { code: "SERVER_ERROR", message: "Could not refresh comparison." } }, 500)
      : jsonResponse(snapshot()))));
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    failure = true;
    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    expect(await screen.findByText("Could not refresh comparison.")).toBeInTheDocument();
    expect(screen.queryByText("Comparison is current.")).not.toBeInTheDocument();
  });

  it("removes the current label while an input-change comparison read is pending and after it fails", async () => {
    let finishRefresh: ((response: Response) => void) | undefined;
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn(() => {
      reads += 1;
      return reads === 1 ? Promise.resolve(jsonResponse(snapshot()))
        : new Promise<Response>((resolve) => { finishRefresh = resolve; });
    }));
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();

    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    expect(reads).toBe(2);
    expect(screen.getByText("Loading comparison…")).toBeInTheDocument();
    expect(screen.queryByText("Comparison is current.")).not.toBeInTheDocument();
    await act(async () => { finishRefresh?.(jsonResponse({
      error: { code: "SERVER_ERROR", message: "Could not refresh comparison." },
    }, 500)); });
    expect(screen.getByRole("alert")).toHaveTextContent("Could not refresh comparison.");
    expect(screen.queryByText("Comparison is current.")).not.toBeInTheDocument();
  });

  it("ignores an older comparison read that finishes after a newer reload", async () => {
    const pending: ((response: Response) => void)[] = [];
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { pending.push(resolve); }));
    vi.stubGlobal("fetch", fetchMock);
    const onSnapshotChange = vi.fn();
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} onSnapshotChange={onSnapshotChange} />);
    await act(async () => { pending[0](jsonResponse(snapshot())); });
    expect(screen.getByText("Comparison is current.")).toBeInTheDocument();

    rerender(<ComparisonReview projectId="project-1" refreshKey={1} onSnapshotChange={onSnapshotChange} />);
    rerender(<ComparisonReview projectId="project-1" refreshKey={2} onSnapshotChange={onSnapshotChange} />);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    await act(async () => { pending[2](jsonResponse(snapshot(true, true))); });
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
    await act(async () => { pending[1](jsonResponse(snapshot())); });
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
    expect(onSnapshotChange).toHaveBeenCalledTimes(2);
  });

  it("refreshes a successful generation after an input-change GET supersedes its display result", async () => {
    const pendingPosts: ((response: Response) => void)[] = [];
    const pendingFinalReads: ((response: Response) => void)[] = [];
    let reads = 0;
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => {
      if (init?.method === "POST") return new Promise<Response>((resolve) => { pendingPosts.push(resolve); });
      reads += 1;
      return reads === 3
        ? new Promise<Response>((resolve) => { pendingFinalReads.push(resolve); })
        : Promise.resolve(jsonResponse(snapshot(true)));
    });
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison outdated")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Regenerate Comparison" }));
    expect(screen.getByRole("button", { name: "Generating…" })).toBeDisabled();

    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    await waitFor(() => expect(reads).toBe(2));
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    await act(async () => { pendingPosts[0](jsonResponse(snapshot(false, true), 201)); });

    expect(reads).toBe(3);
    expect(screen.getByText("Loading comparison…")).toBeInTheDocument();
    expect(screen.queryByText("Comparison is current.")).not.toBeInTheDocument();
    await act(async () => { pendingFinalReads[0](jsonResponse(snapshot(false, true))); });

    expect(screen.getByText("Comparison is current.")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
    expect(screen.getByRole("button", { name: "Regenerate Comparison" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1);
  });

  it("keeps a generation rejection visible when an input-change GET supersedes its display result", async () => {
    let rejectGeneration: ((response: Response) => void) | undefined;
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => init?.method === "POST"
      ? new Promise<Response>((resolve) => { rejectGeneration = resolve; })
      : Promise.resolve(jsonResponse(snapshot(true))));
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison outdated")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Regenerate Comparison" }));
    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method !== "POST")).toHaveLength(2));
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();

    await act(async () => { rejectGeneration?.(jsonResponse({
      error: { code: "COMPARISON_NOT_READY", message: "Approve the current shortlist before generating a comparison." },
    }, 409)); });
    expect(screen.getByRole("alert")).toHaveTextContent("Approve the current shortlist before generating a comparison.");
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.25");
    expect(screen.getByRole("button", { name: "Regenerate Comparison" })).toBeEnabled();
  });

  it("clears settled generation feedback on an input-change refresh", async () => {
    let finishRefresh: ((response: Response) => void) | undefined;
    let reads = 0;
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => {
      if (init?.method === "POST") return Promise.resolve(jsonResponse({
        error: { code: "COMPARISON_NOT_READY", message: "Approve the current shortlist before generating a comparison." },
      }, 409));
      reads += 1;
      return reads === 1 ? Promise.resolve(jsonResponse(snapshot(true)))
        : new Promise<Response>((resolve) => { finishRefresh = resolve; });
    });
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison outdated")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Regenerate Comparison" }));
    expect(await screen.findByText("Approve the current shortlist before generating a comparison.")).toBeInTheDocument();

    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    expect(reads).toBe(2);
    expect(screen.queryByText("Approve the current shortlist before generating a comparison.")).not.toBeInTheDocument();
    await act(async () => { finishRefresh?.(jsonResponse(snapshot(true, true))); });
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows available supplier evidence labels for a selected general MOQ fact", async () => {
    const data = snapshot();
    data.comparison_payload.suppliers[0].resolved_facts.moq.selected = {
      ...fact(500, "supplier-fact:moq"), context: "GENERAL_SUPPLIER",
      supporting_evidence_ids: ["supplier-evidence-1"], provenance_evidence_ids: ["supplier-evidence-2"],
    };
    data.comparison_payload.suppliers[0].supplier_facts.evidence = [
      { id: "supplier-evidence-1", source_label: "Supplier catalog", source_reference: "catalog:moq", evidence_state: "SUPPORTED" },
      { id: "supplier-evidence-2", source_label: "Supplier data sheet", source_reference: "data-sheet:moq", evidence_state: "SUPPORTED" },
    ];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const moq = await screen.findByRole("row", { name: /Minimum order quantity/ });
    const willowMoq = within(moq).getAllByRole("cell")[0];
    fireEvent.click(within(willowMoq).getByText("Source details"));
    expect(within(willowMoq).getByText(/General supplier information · supplier-fact:moq/)).toBeInTheDocument();
    expect(within(willowMoq).getByText(/Supplier evidence: Supplier catalog · catalog:moq · Supported/)).toBeInTheDocument();
    expect(within(willowMoq).getByText(/Supplier evidence: Supplier data sheet · data-sheet:moq · Supported/)).toBeInTheDocument();
  });

  it("shows requirement evidence IDs when supplier labels and references repeat or are absent", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    const result: { evidence_ids: string[] } = willow.evaluation.results[0];
    result.evidence_ids = ["supplier-evidence-a", "supplier-evidence-b", "supplier-evidence-c"];
    willow.supplier_facts.evidence = [
      { id: "supplier-evidence-a", source_label: "Shared catalog", source_reference: "catalog:material", evidence_state: "SUPPORTS" },
      { id: "supplier-evidence-b", source_label: "Shared catalog", source_reference: "catalog:material", evidence_state: "SUPPORTS" },
      { id: "supplier-evidence-c", source_label: "", source_reference: null, evidence_state: "SUPPORTS" },
    ];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const requirement = await screen.findByRole("row", { name: /Material Required/ });
    const willowResult = within(requirement).getAllByRole("cell")[0];
    fireEvent.click(within(willowResult).getByText("Source details"));
    expect(within(willowResult).getByText("Supplier evidence: Shared catalog · catalog:material · Supports · ID: supplier-evidence-a")).toBeInTheDocument();
    expect(within(willowResult).getByText("Supplier evidence: Shared catalog · catalog:material · Supports · ID: supplier-evidence-b")).toBeInTheDocument();
    expect(within(willowResult).getByText("Supplier evidence: Supports · ID: supplier-evidence-c")).toBeInTheDocument();
  });

  it("keeps selected quote provenance separate from differing general supplier context evidence", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    const moq: { selected: ReturnType<typeof fact> | null; general_facts: ReturnType<typeof fact>[] } = willow.resolved_facts.moq;
    moq.selected = {
      ...fact(500, "quote-value:moq"), provenance_evidence_ids: ["quote-evidence-moq"],
    };
    moq.general_facts = [{
      ...fact(1000, "supplier-fact:moq"), context: "GENERAL_SUPPLIER",
      supporting_evidence_ids: ["supplier-evidence-support"],
      provenance_evidence_ids: ["supplier-evidence-context"],
    }];
    willow.quote_fields.push({
      field_key: "moq", current_value: "500", origin: "USER_CORRECTED", ai_extracted_value: "600",
      source_reference: "quote-value:moq", evidence: [{
        id: "quote-evidence-moq", value: "600", role: "provenance",
        page_number: 2, block_number: 4, document_block_id: "block-moq",
      }],
    });
    willow.supplier_facts.evidence = [
      { id: "supplier-evidence-support", source_label: "Supplier catalog", source_reference: "catalog:moq", evidence_state: "SUPPORTS" },
      { id: "supplier-evidence-context", source_label: "Supplier terms", source_reference: "terms:moq", evidence_state: "PARTIAL" },
    ];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const moqRow = await screen.findByRole("row", { name: /Minimum order quantity/ });
    const willowMoq = within(moqRow).getAllByRole("cell")[0];
    expect(within(willowMoq).getByText("500")).toBeInTheDocument();
    fireEvent.click(within(willowMoq).getByText("Source details"));
    expect(within(willowMoq).getByText("Confirmed project quote · quote-value:moq")).toBeInTheDocument();
    const quoteProvenance = within(willowMoq).getByText(/Original PDF provenance: page 2, block 4; extracted 600/).closest("div");
    const generalContext = within(willowMoq).getByText("General supplier context: 1000 · supplier-fact:moq").closest("div");
    expect(quoteProvenance).not.toBeNull();
    expect(generalContext).not.toBeNull();
    expect(within(quoteProvenance!).queryByText(/Supplier catalog|Supplier terms/)).not.toBeInTheDocument();
    expect(within(generalContext!).getByText("General supplier context evidence: Supplier catalog · catalog:moq · Supports · ID: supplier-evidence-support")).toBeInTheDocument();
    expect(within(generalContext!).getByText("General supplier context evidence: Supplier terms · terms:moq · Partial · ID: supplier-evidence-context")).toBeInTheDocument();
    expect(within(generalContext!).queryByText(/PDF provenance/)).not.toBeInTheDocument();
  });

  it("shows supporting and contradicting supplier evidence for a conflicting general MOQ fact", async () => {
    const data = snapshot();
    const moq: {
      status: string; selected: ReturnType<typeof fact> | null;
      project_facts: ReturnType<typeof fact>[]; general_facts: ReturnType<typeof fact>[];
    } = data.comparison_payload.suppliers[0].resolved_facts.moq;
    moq.status = "CONFLICT";
    moq.selected = null;
    moq.project_facts = [];
    moq.general_facts = [{
      ...fact(500, "supplier-fact:moq"), context: "GENERAL_SUPPLIER",
      supporting_evidence_ids: ["supplier-evidence-support"],
      provenance_evidence_ids: ["supplier-evidence-contradiction"],
    }];
    data.comparison_payload.suppliers[0].supplier_facts.evidence = [
      { id: "supplier-evidence-support", source_label: "Supplier catalog", source_reference: "catalog:moq", evidence_state: "SUPPORTS" },
      { id: "supplier-evidence-contradiction", source_label: "Other terms", source_reference: "terms:moq", evidence_state: "CONTRADICTS" },
    ];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const moqRow = await screen.findByRole("row", { name: /Minimum order quantity/ });
    const willowMoq = within(moqRow).getAllByRole("cell")[0];
    expect(within(willowMoq).getByText("Conflict")).toBeInTheDocument();
    fireEvent.click(within(willowMoq).getByText("Source details"));
    expect(within(willowMoq).getByText(/General supplier context: 500 · supplier-fact:moq/)).toBeInTheDocument();
    expect(within(willowMoq).getByText(/General supplier context evidence: Supplier catalog · catalog:moq · Supports/)).toBeInTheDocument();
    expect(within(willowMoq).getByText(/General supplier context evidence: Other terms · terms:moq · Contradicts/)).toBeInTheDocument();
    expect(within(willowMoq).queryByText(/General supplier information ·/)).not.toBeInTheDocument();
  });

  it("shows conflicting project price and currency alternatives with PDF citations", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    const price: {
      status: string; selected: ReturnType<typeof fact> | null;
      project_facts: ReturnType<typeof fact>[]; general_facts: ReturnType<typeof fact>[];
    } = willow.resolved_facts.unit_price;
    price.status = "CONFLICT";
    price.selected = null;
    price.project_facts = [{
      ...fact(null),
      component_attributions: [
        { field_key: "unit_price", source_reference: "quote-value:price", supporting_evidence_ids: [], provenance_evidence_ids: ["price-1", "price-2"] },
        { field_key: "currency", source_reference: "quote-value:currency", supporting_evidence_ids: [], provenance_evidence_ids: ["currency-1", "currency-2"] },
      ],
    }];
    willow.quote_fields[0].current_value = null;
    willow.quote_fields[0].ai_extracted_value = null;
    willow.quote_fields[0].evidence = [
      { id: "price-1", value: "4.50", role: "provenance", page_number: 2, block_number: 3, document_block_id: "price-block-1" },
      { id: "price-2", value: "5.00", role: "provenance", page_number: 4, block_number: 1, document_block_id: "price-block-2" },
    ];
    willow.quote_fields.push({
      field_key: "currency", current_value: null, origin: "AI_EXTRACTED", ai_extracted_value: null,
      source_reference: "quote-value:currency", evidence: [
        { id: "currency-1", value: "USD", role: "provenance", page_number: 2, block_number: 4, document_block_id: "currency-block-1" },
        { id: "currency-2", value: "EUR", role: "provenance", page_number: 4, block_number: 2, document_block_id: "currency-block-2" },
      ],
    });
    willow.completeness.push({ field_key: "unit_price", state: "conflicting", source_references: ["quote-value:price", "quote-value:currency"] });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const row = await screen.findByRole("row", { name: /Unit price/ });
    const cell = within(row).getAllByRole("cell")[0];
    expect(within(cell).getByText("Conflict")).toBeInTheDocument();
    fireEvent.click(within(cell).getByText("Source details"));
    expect(within(cell).getByText(/Conflicting project quote context: Unknown · quote-value:price/)).toBeInTheDocument();
    expect(within(cell).getByText(/No project quote value was selected/)).toBeInTheDocument();
    expect(within(cell).getByText(/Original PDF provenance: page 2, block 3; extracted 4.50 · price-1/)).toBeInTheDocument();
    expect(within(cell).getByText(/Original PDF provenance: page 4, block 1; extracted 5.00 · price-2/)).toBeInTheDocument();
    expect(within(cell).getByText(/Original PDF provenance: page 2, block 4; extracted USD · currency-1/)).toBeInTheDocument();
    expect(within(cell).getByText(/Original PDF provenance: page 4, block 2; extracted EUR · currency-2/)).toBeInTheDocument();
    expect(within(cell).getByText("Currency source: quote-value:currency")).toBeInTheDocument();
    expect(within(cell).queryByText(/Confirmed project quote ·/)).not.toBeInTheDocument();
  });

  it("shows raw tooling and shipping sources without assigning an unresolved currency", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    willow.quote_fields.push(
      { field_key: "currency", current_value: "USD", origin: "AI_EXTRACTED", ai_extracted_value: "USD",
        source_reference: "quote-value:currency", evidence: [] },
      { field_key: "tooling_cost", current_value: "120", origin: "USER_ENTERED", ai_extracted_value: null,
        source_reference: "quote-value:tooling", evidence: [] },
      { field_key: "shipping_cost", current_value: "35", origin: "USER_ENTERED", ai_extracted_value: null,
        source_reference: "quote-value:shipping", evidence: [] },
    );
    willow.completeness.push(
      { field_key: "currency", state: "conflicting", source_references: ["quote-value:currency"] },
      { field_key: "tooling_cost", state: "known", source_references: ["quote-value:tooling"] },
      { field_key: "shipping_cost", state: "known", source_references: ["quote-value:shipping"] },
    );
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);

    const tooling = within(await screen.findByRole("row", { name: /Tooling or setup cost/ })).getAllByRole("cell")[0];
    const shipping = within(screen.getByRole("row", { name: /Shipping cost/ })).getAllByRole("cell")[0];
    expect(tooling).toHaveTextContent("120 (currency: Conflict)");
    expect(tooling).not.toHaveTextContent("USD 120");
    fireEvent.click(within(tooling).getByText("Source details"));
    expect(within(tooling).getByText("Tooling Cost source: quote-value:tooling")).toBeInTheDocument();
    expect(shipping).toHaveTextContent("35 (currency: Conflict)");
    fireEvent.click(within(shipping).getByText("Source details"));
    expect(within(shipping).getByText("Shipping Cost source: quote-value:shipping")).toBeInTheDocument();

    willow.completeness.find((item) => item.field_key === "currency")!.state = "missing";
    willow.quote_fields.find((item) => item.field_key === "currency")!.current_value = null;
    // A fresh payload with no resolved currency must keep the amount but label the currency Unknown.
    const missingCurrency = snapshot();
    missingCurrency.comparison_payload.suppliers[0] = willow;
    cleanup();
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(missingCurrency))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(within(await screen.findByRole("row", { name: /Tooling or setup cost/ })).getAllByRole("cell")[0])
      .toHaveTextContent("120 (currency: Unknown)");
    expect(within(screen.getByRole("row", { name: /Shipping cost/ })).getAllByRole("cell")[0])
      .toHaveTextContent("35 (currency: Unknown)");
  });

  it("shows PDF provenance for both cost and currency in tooling and shipping", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    willow.quote_fields.push(
      { field_key: "currency", current_value: "USD", origin: "AI_EXTRACTED", ai_extracted_value: "USD",
        source_reference: "quote-value:currency", evidence: [{ id: "currency-pdf", value: "USD", role: "supporting",
          page_number: 1, block_number: 2, document_block_id: "currency-block" }] },
      { field_key: "tooling_cost", current_value: "120", origin: "AI_EXTRACTED", ai_extracted_value: "120",
        source_reference: "quote-value:tooling", evidence: [{ id: "tooling-pdf", value: "120", role: "supporting",
          page_number: 2, block_number: 3, document_block_id: "tooling-block" }] },
      { field_key: "shipping_cost", current_value: "35", origin: "AI_EXTRACTED", ai_extracted_value: "35",
        source_reference: "quote-value:shipping", evidence: [{ id: "shipping-pdf", value: "35", role: "supporting",
          page_number: 3, block_number: 4, document_block_id: "shipping-block" }] },
    );
    willow.completeness.push({ field_key: "currency", state: "known", source_references: ["quote-value:currency"] });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);

    for (const [row, amount, sourceLabel, source, citation] of [
      ["Tooling or setup cost", "120", "Tooling Cost", "quote-value:tooling", /Supporting PDF evidence: page 2, block 3; extracted 120 · tooling-pdf/],
      ["Shipping cost", "35", "Shipping Cost", "quote-value:shipping", /Supporting PDF evidence: page 3, block 4; extracted 35 · shipping-pdf/],
    ] as const) {
      const cell = within(await screen.findByRole("row", { name: new RegExp(row) })).getAllByRole("cell")[0];
      expect(cell).toHaveTextContent(`USD ${amount}`);
      fireEvent.click(within(cell).getByText("Source details"));
      expect(within(cell).getByText(`${sourceLabel} source: ${source}`)).toBeInTheDocument();
      expect(within(cell).getByText(`${sourceLabel} current origin: Ai Extracted`)).toBeInTheDocument();
      expect(within(cell).getByText("Currency source: quote-value:currency")).toBeInTheDocument();
      expect(within(cell).getByText("Currency current origin: Ai Extracted")).toBeInTheDocument();
      expect(within(cell).getByText(citation)).toBeInTheDocument();
      expect(within(cell).getByText(/Supporting PDF evidence: page 1, block 2; extracted USD · currency-pdf/)).toBeInTheDocument();
    }
  });

  it("shows corrected currency as current and its original PDF evidence on tooling and shipping", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    willow.quote_fields.push(
      { field_key: "currency", current_value: "EUR", origin: "USER_CORRECTED", ai_extracted_value: "USD",
        source_reference: "quote-value:currency", evidence: [{ id: "currency-pdf", value: "USD", role: "provenance",
          page_number: 1, block_number: 2, document_block_id: "currency-block" }] },
      { field_key: "tooling_cost", current_value: "120", origin: "USER_ENTERED", ai_extracted_value: null,
        source_reference: "quote-value:tooling", evidence: [] },
      { field_key: "shipping_cost", current_value: "35", origin: "USER_ENTERED", ai_extracted_value: null,
        source_reference: "quote-value:shipping", evidence: [] },
    );
    willow.completeness.push({ field_key: "currency", state: "known", source_references: ["quote-value:currency"] });
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);

    for (const [row, amount, sourceLabel, source] of [
      ["Tooling or setup cost", "120", "Tooling Cost", "quote-value:tooling"],
      ["Shipping cost", "35", "Shipping Cost", "quote-value:shipping"],
    ] as const) {
      const cell = within(await screen.findByRole("row", { name: new RegExp(row) })).getAllByRole("cell")[0];
      expect(cell).toHaveTextContent(`EUR ${amount}`);
      fireEvent.click(within(cell).getByText("Source details"));
      expect(within(cell).getByText(`${sourceLabel} source: ${source}`)).toBeInTheDocument();
      expect(within(cell).getByText(`${sourceLabel} current origin: User Entered`)).toBeInTheDocument();
      expect(within(cell).getByText("Currency source: quote-value:currency")).toBeInTheDocument();
      expect(within(cell).getByText("Currency current origin: User Corrected")).toBeInTheDocument();
      expect(within(cell).getByText("Original extracted value: USD")).toBeInTheDocument();
      expect(within(cell).getByText(/Original PDF provenance: page 1, block 2; extracted USD · currency-pdf/)).toBeInTheDocument();
      expect(within(cell).getByText(/User-corrected value is current.*does not verify the correction/)).toBeInTheDocument();
    }
  });

  it("shows mixed quote currencies beside the unit prices", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(snapshot()))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    const price = await screen.findByRole("row", { name: /Unit price/ });
    for (const cell of within(price).getAllByRole("cell")) {
      expect(within(cell).getByText("Quotes use different currencies; prices cannot be directly compared.")).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: "Warnings" })).toBeInTheDocument();
  });

  it("labels a general indicative price when the confirmed quote has no unit price", async () => {
    const data = snapshot();
    const willow = data.comparison_payload.suppliers[0];
    willow.quote_fields = [];
    const generalPrice = {
      ...fact({ amount: "4.00", currency: "USD" }, "supplier:willow:unit_price"),
      context: "GENERAL_SUPPLIER",
    };
    const priceResolution: {
      status: string; selected: ReturnType<typeof fact> | null;
      project_facts: ReturnType<typeof fact>[]; general_facts: ReturnType<typeof fact>[];
    } = willow.resolved_facts.unit_price;
    priceResolution.selected = generalPrice;
    priceResolution.project_facts = [];
    priceResolution.general_facts = [generalPrice];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);

    const price = await screen.findByRole("row", { name: /Unit price/ });
    const [willowPrice, mossPrice] = within(price).getAllByRole("cell");
    expect(within(willowPrice).getByText("USD 4.00")).toBeInTheDocument();
    expect(within(willowPrice).getByText("General supplier indicative price")).toBeVisible();
    expect(within(willowPrice).queryByText("Confirmed project quote price")).not.toBeInTheDocument();
    expect(within(mossPrice).getByText("Confirmed project quote price")).toBeVisible();
    fireEvent.click(within(willowPrice).getByText("Source details"));
    expect(within(willowPrice).getByText(/General supplier information · supplier:willow:unit_price/)).toBeInTheDocument();
  });

  it("renders days for selected and contextual general supplier lead times", async () => {
    const data = snapshot();
    const lead: {
      selected: ReturnType<typeof fact> | null; project_facts: ReturnType<typeof fact>[];
      general_facts: ReturnType<typeof fact>[];
    } = data.comparison_payload.suppliers[0].resolved_facts.production_lead_time;
    const generalLead = { ...fact(35, "supplier:willow:lead-time"), context: "GENERAL_SUPPLIER" };
    lead.selected = generalLead;
    lead.project_facts = [];
    lead.general_facts = [generalLead];
    const mossLead: { general_facts: ReturnType<typeof fact>[] } =
      data.comparison_payload.suppliers[1].resolved_facts.production_lead_time;
    mossLead.general_facts = [{ ...fact(40, "supplier:moss:lead-time"), context: "GENERAL_SUPPLIER" }];
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(data))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);

    const row = await screen.findByRole("row", { name: /Production lead time/ });
    const [willow, moss] = within(row).getAllByRole("cell");
    expect(within(willow).getByText("35 days")).toBeInTheDocument();
    expect(within(moss).getByText("25 days")).toBeInTheDocument();
    fireEvent.click(within(moss).getByText("Source details"));
    expect(within(moss).getByText("General supplier context: 40 days · supplier:moss:lead-time")).toBeInTheDocument();
  });

  it("shows requirement states, warnings, completeness, and corrected-value provenance", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(snapshot(false, true)))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    const price = screen.getByRole("row", { name: /Unit price/ });
    const willowPrice = within(price).getAllByRole("cell")[0];
    expect(within(price).getByText("USD 4.50")).toBeInTheDocument();
    expect(screen.getByText("Does Not Meet")).toHaveClass("comparison-required-failure");
    expect(screen.getByText("Meets")).toBeInTheDocument();
    expect(screen.getByText("Conflict")).toBeInTheDocument();
    expect(screen.getAllByText("Informational", { selector: "strong" })).toHaveLength(2);
    expect(screen.getAllByText(/Quotes use different currencies/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Missing or conflicting information"));
    expect(screen.getByText("Willow: Delivery Date — missing")).toBeInTheDocument();
    fireEvent.click(within(willowPrice).getByText("Source details"));
    expect(within(willowPrice).getByText(/User-corrected value is current/)).toBeInTheDocument();
    expect(within(willowPrice).getByText("Original extracted value: 4.25")).toBeInTheDocument();
    expect(within(willowPrice).getByText(/Original PDF provenance: page 2, block 3; extracted 4.25/)).toBeInTheDocument();
    expect(within(willowPrice).queryByText(/Supporting PDF evidence/)).not.toBeInTheDocument();
  });

  it("marks the old snapshot outdated and shows regenerated current values", async () => {
    const fetchMock = vi.fn((_path: string, init?: RequestInit) => Promise.resolve(jsonResponse(init?.method === "POST" ? snapshot(false, true) : snapshot(true))));
    vi.stubGlobal("fetch", fetchMock);
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison outdated")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Regenerate Comparison" }));
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    expect(screen.getByRole("row", { name: /Unit price/ })).toHaveTextContent("USD 4.50");
  });

  it("refreshes the server state after an input-change signal", async () => {
    let stale = false;
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse(snapshot(stale))));
    vi.stubGlobal("fetch", fetchMock);
    const { rerender } = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByText("Comparison is current.")).toBeInTheDocument();
    stale = true;
    rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    expect(await screen.findByText("Comparison outdated")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});


type AdvicePoint = { text: string; supplier_ids: string[]; requirement_ids: string[];
  quote_fields: { quote_id: string; field_key: string }[]; evidence_ids: string[] };
const advicePoint = (text: string): AdvicePoint => ({ text, supplier_ids: ["a"], requirement_ids: [], quote_fields: [], evidence_ids: [] });
const adviceResponse = (selected: string | null = "a") => ({
  run_id: "run-1", snapshot_id: "comparison-1",
  analysis: { supplier_summaries: [advicePoint("Willow has confirmed quote information.")],
    key_tradeoffs: [advicePoint("Compare the quote terms before proceeding.")],
    important_unknowns: [], important_conflicts: [] },
  suggestion: { supplier_id: selected, supporting_reasons: selected ? [advicePoint("Investigate its confirmed terms.")] : [],
    tradeoffs: [advicePoint("Willow fails the required material requirement.")],
    uncertainties: [advicePoint("No single supplier has enough confirmed information.")], evidence_ids: [] as string[] },
});

describe("Comparison advice", () => {
  afterEach(() => { cleanup(); vi.restoreAllMocks(); });

  it("requests one combined result and displays analysis, suggestion and cited sources", async () => {
    const output = adviceResponse();
    output.suggestion.supporting_reasons[0].quote_fields = [{ quote_id: "quote-a", field_key: "unit_price" }];
    output.suggestion.supporting_reasons[0].evidence_ids = ["evidence-1"];
    const fetchMock = vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/advice") ? output : snapshot())));
    vi.stubGlobal("fetch", fetchMock);
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    const analysis = await screen.findByRole("region", { name: "Comparison analysis" });
    expect(within(analysis).getByText("Tradeoff analysis")).toBeInTheDocument();
    expect(within(analysis).getByText("Suggested Supplier to Investigate First")).toBeInTheDocument();
    expect(within(analysis).getByText("Willow fails the required material requirement.")).toBeInTheDocument();
    expect(within(analysis).getByText(/Supporting PDF evidence/)).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/advice"))).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/comparison/advice", expect.objectContaining({
      method: "POST", body: JSON.stringify({ snapshot_id: "comparison-1" }),
    }));
  });

  it.each([false, true])("renders evidence-only PDF advice citations with corrected value = %s", async (corrected) => {
    const comparison = snapshot(false, corrected);
    const output = adviceResponse();
    output.snapshot_id = comparison.id;
    for (const point of [output.analysis.supplier_summaries[0], output.suggestion.supporting_reasons[0]]) {
      point.evidence_ids = ["evidence-1"];
    }
    output.suggestion.evidence_ids = ["evidence-1"];
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/advice") ? output : comparison))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    const analysis = await screen.findByRole("region", { name: "Comparison analysis" });
    for (const text of ["Willow has confirmed quote information.", "Investigate its confirmed terms."]) {
      const point = within(analysis).getByText(text).closest("li")!;
      fireEvent.click(within(point).getByText("Source details"));
      expect(point.querySelector("details")).toHaveAttribute("open");
      expect(within(point).getByText("Unit Price source: quote-value:price")).toBeInTheDocument();
      expect(within(point).getByText(`Unit Price current origin: ${corrected ? "User Corrected" : "Ai Extracted"}`)).toBeInTheDocument();
      expect(within(point).getByText("Original extracted value: 4.25")).toBeInTheDocument();
      expect(within(point).getByText(`${corrected ? "Original PDF provenance" : "Supporting PDF evidence"}: page 2, block 3; extracted 4.25 · evidence-1`)).toBeInTheDocument();
      if (corrected) expect(within(point).getByText(/does not verify the correction/)).toBeInTheDocument();
      expect(within(point).getAllByText("Source details")).toHaveLength(1);
    }
  });

  it("shows a successful no-suggestion explanation", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/advice") ? adviceResponse(null) : snapshot()))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    expect(await screen.findByText("No supplier suggested yet")).toBeInTheDocument();
    expect(screen.getByText("No single supplier has enough confirmed information.")).toBeInTheDocument();
  });

  it("keeps provider failure distinct from null and retries", async () => {
    let attempts = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(path.endsWith("/advice")
      ? ++attempts === 1 ? jsonResponse({ error: { code: "COMPARISON_ADVICE_UNAVAILABLE", message: "Please retry analysis." } }, 503)
        : jsonResponse(adviceResponse(null)) : jsonResponse(snapshot()))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    expect(await screen.findByText("Please retry analysis.")).toBeInTheDocument();
    expect(screen.queryByText("No supplier suggested yet")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry analysis" }));
    expect(await screen.findByText("No supplier suggested yet")).toBeInTheDocument();
  });

  it("blocks analysis on stale snapshots", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(jsonResponse(snapshot(true)))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    expect(await screen.findByRole("button", { name: "Analyze Comparison" })).toBeDisabled();
  });

  it.each(["stale", "replacement", "missing", "failure"])("hides output when the final freshness check reports %s", async (outcome) => {
    let reads = 0;
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(path.endsWith("/advice") ? jsonResponse(adviceResponse())
      : ++reads === 1 ? jsonResponse(snapshot())
        : outcome === "missing" ? notFound()
        : outcome === "failure" ? jsonResponse({ error: { code: "SERVER_ERROR", message: "Freshness unavailable." } }, 500)
          : jsonResponse(outcome === "replacement" ? snapshot(false, true) : snapshot(true)))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("region", { name: "Comparison analysis" })).not.toBeInTheDocument();
    if (outcome !== "failure") expect(screen.getByRole("button", { name: "Retry analysis" })).toBeDisabled();
  });

  it("handles a stale API failure as regeneration-required", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(path.endsWith("/advice")
      ? jsonResponse({ error: { code: "COMPARISON_STALE", message: "Inputs changed during analysis." } }, 409)
      : jsonResponse(snapshot()))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    expect(await screen.findByText("Inputs changed during analysis.")).toBeInTheDocument();
    expect(screen.getByText("Comparison outdated")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry analysis" })).toBeDisabled();
  });

  it.each(["refresh", "project", "regenerate", "unmount"])("discards late advice after %s", async (change) => {
    let finish: ((response: Response) => void) | undefined;
    vi.stubGlobal("fetch", vi.fn((path: string) => path.endsWith("/advice")
      ? new Promise<Response>((resolve) => { finish = resolve; }) : Promise.resolve(jsonResponse(snapshot()))));
    const view = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    await screen.findByRole("button", { name: "Analyzing…" });
    if (change === "refresh") view.rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    else if (change === "project") view.rerender(<ComparisonReview projectId="project-2" refreshKey={0} />);
    else if (change === "regenerate") fireEvent.click(screen.getByRole("button", { name: "Regenerate Comparison" }));
    else view.unmount();
    await act(async () => { finish?.(jsonResponse(adviceResponse())); });
    expect(screen.queryByRole("region", { name: "Comparison analysis" })).not.toBeInTheDocument();
  });

  it("invalidates prior advice immediately on focus and failed verification", async () => {
    let failure = false;
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(path.endsWith("/advice") ? jsonResponse(adviceResponse())
      : failure ? jsonResponse({ error: { code: "SERVER_ERROR", message: "Could not verify comparison." } }, 500) : jsonResponse(snapshot()))));
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    await screen.findByRole("region", { name: "Comparison analysis" });
    failure = true;
    fireEvent(window, new Event("focus"));
    expect(screen.queryByRole("region", { name: "Comparison analysis" })).not.toBeInTheDocument();
    expect(await screen.findByText("Could not verify comparison.")).toBeInTheDocument();
  });

  it("retains advice after focus verifies the same current snapshot", async () => {
    const fetchMock = vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/advice") ? adviceResponse() : snapshot())));
    vi.stubGlobal("fetch", fetchMock);
    render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    await screen.findByRole("region", { name: "Comparison analysis" });
    fireEvent(window, new Event("focus"));
    await screen.findByRole("region", { name: "Comparison analysis" });
    expect(fetchMock.mock.calls.filter(([path]) => path.endsWith("/advice"))).toHaveLength(1);
    expect(screen.queryByText(/Previous analysis is outdated/)).not.toBeInTheDocument();
  });

  it("shows outdated state after a quote refresh and requires fresh analysis", async () => {
    let stale = false;
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(jsonResponse(path.endsWith("/advice") ? adviceResponse() : snapshot(stale)))));
    const view = render(<ComparisonReview projectId="project-1" refreshKey={0} />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze Comparison" }));
    await screen.findByRole("region", { name: "Comparison analysis" });
    stale = true;
    view.rerender(<ComparisonReview projectId="project-1" refreshKey={1} />);
    await screen.findByText("Comparison outdated");
    expect(screen.getByText(/Previous analysis is outdated/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Comparison analysis" })).not.toBeInTheDocument();
  });
});
