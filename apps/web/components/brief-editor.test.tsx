import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BriefEditor } from "./brief-editor";
import { jsonResponse } from "../test/api-responses";

const emptyBrief = {
  product_name: null, category: null, quantity: null, destination: null,
  delivery_target: null, target_unit_price: null, requirements: [],
  status: "IN_PROGRESS", brief_revision: 0, can_analyze: true,
  missing_fields: [{ field_key: "product_name", reason: "Name the product to source." }],
};

describe("BriefEditor", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads an empty editable Brief and saves manual content after analysis fails", async () => {
    const fetchMock = vi.fn((_: string, init?: RequestInit) => Promise.resolve(
      init?.method === "POST" ? jsonResponse({ error: { code: "BRIEF_ANALYSIS_UNAVAILABLE", message: "Try again or enter the Brief manually." } }, 503) :
      init?.method === "PATCH" ? jsonResponse({ ...emptyBrief, product_name: "Manual bag", brief_revision: 1, can_analyze: false }) :
      jsonResponse(emptyBrief),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    expect(await screen.findByText("Name the product to source.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Analyze request" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again or enter the Brief manually.");
    fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "Manual bag" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief", expect.objectContaining({ method: "PATCH" })));
    const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(saveCall?.[1]?.body))).toMatchObject({ product_name: "Manual bag", expected_brief_revision: 0 });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Analyze request" })).not.toBeInTheDocument());
  });

  it("shows extracted unknown importance and transient ambiguities, then saves an edit", async () => {
    const extracted = {
      ...emptyBrief, product_name: "Cosmetic bag", brief_revision: 1, can_analyze: false,
      requirements: [{ id: "req-1", kind: "MATERIAL", importance: null, expected_value: { value: "recycled polyester" }, notes: null }],
      ambiguities: ["Branding method was not stated."],
    };
    const fetchMock = vi.fn((_: string, init?: RequestInit) => Promise.resolve(
      init?.method === "POST" ? jsonResponse(extracted) :
      init?.method === "PATCH" ? jsonResponse({ ...extracted, requirements: [{ ...extracted.requirements[0], importance: "REQUIRED" }] }) :
      jsonResponse(emptyBrief),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze request" }));
    expect(await screen.findByText("Branding method was not stated.")).toBeInTheDocument();
    expect(screen.getByLabelText("Importance")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Importance"), { target: { value: "REQUIRED" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief", expect.objectContaining({ method: "PATCH" })));
    const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(saveCall?.[1]?.body)).requirements[0].importance).toBe("REQUIRED");
    await waitFor(() => expect(screen.queryByText("Branding method was not stated.")).not.toBeInTheDocument());
  });

  it("reloads saved requirements and informational attributes in separate sections", async () => {
    const saved = {
      ...emptyBrief, product_name: "Bag", brief_revision: 2, can_analyze: false,
      requirements: [
        { id: "req-1", kind: "MATERIAL", importance: null, expected_value: { value: "cotton" }, notes: null },
        { id: "attr-1", kind: "INFORMATIONAL", importance: "INFORMATIONAL", expected_value: { subject: "COLOR", text: "blue" }, notes: null },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(saved));
    vi.stubGlobal("fetch", fetchMock);
    const first = render(<BriefEditor projectId="project-1" />);
    expect(await screen.findByText("Informational attributes")).toBeInTheDocument();
    expect(screen.getByDisplayValue("cotton")).toBeInTheDocument();
    expect(screen.getByDisplayValue("blue")).toBeInTheDocument();
    first.unmount();
    render(<BriefEditor projectId="project-1" />);
    expect(await screen.findByDisplayValue("cotton")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("button", { name: "Analyze request" })).not.toBeInTheDocument();
  });

  it("shows backend field validation and preserves the editable draft after a failed save", async () => {
    const saved = { ...emptyBrief, product_name: "Original bag", quantity: 2000, brief_revision: 1, can_analyze: false };
    let saves = 0;
    const fetchMock = vi.fn((_: string, init?: RequestInit) => {
      if (init?.method !== "PATCH") return Promise.resolve(jsonResponse(saved));
      saves += 1;
      if (saves === 1) return Promise.resolve(jsonResponse({
        error: {
          code: "VALIDATION_ERROR",
          message: "Request validation failed.",
          fields: [
            { field: "body.quantity", message: "Value error, quantity must be at most 2147483647" },
            { field: "body.product_name", message: "Value error, must be at most 255 characters" },
          ],
        },
      }, 422));
      return Promise.resolve(jsonResponse({ ...saved, product_name: "Edited bag", quantity: 3000, brief_revision: 2 }));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    expect(await screen.findByLabelText("Requested quantity")).toHaveValue(2000);
    fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "Edited bag" } });
    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "2147483648" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Requested quantity: quantity must be at most 2147483647");
    expect(alert).toHaveTextContent("Product name: must be at most 255 characters");
    expect(alert).not.toHaveTextContent("Request validation failed.");
    expect(screen.getByLabelText("Requested quantity")).toHaveValue(2147483648);
    expect(screen.getByLabelText("Product name")).toHaveValue("Edited bag");
    expect(JSON.parse(String(fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH")?.[1]?.body)).quantity).toBe(2147483648);

    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "3000" } });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    await waitFor(() => expect(saves).toBe(2));
    expect(screen.getByLabelText("Requested quantity")).toHaveValue(3000);
    expect(screen.getByLabelText("Product name")).toHaveValue("Edited bag");
  });

  it("generates questions and saves answers together through revision-checked Brief PATCH", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", category: "Totes", destination: "Sydney",
      delivery_target: { kind: "DATE", date: "2027-01-01" }, brief_revision: 1, can_analyze: false,
      missing_fields: [{ field_key: "quantity", reason: "Enter a positive requested quantity." }],
    };
    const ready = { ...saved, quantity: 1000, brief_revision: 2, status: "READY_FOR_REVIEW", missing_fields: [] };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => Promise.resolve(
      path.endsWith("/clarifications") ? jsonResponse({ brief_revision: 1, questions: [{ field_key: "quantity", question: "How many totes do you need?", reason: "Needed for sourcing." }] }) :
      init?.method === "PATCH" ? jsonResponse(ready) : jsonResponse(saved),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("How many totes do you need?"), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    await waitFor(() => expect(screen.getByText("No required information is missing.")).toBeInTheDocument());
    const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    const body = JSON.parse(String(saveCall?.[1]?.body));
    expect(body).toMatchObject({ quantity: 1000, expected_brief_revision: 1, product_name: "Tote", destination: "Sydney" });
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief/clarifications", expect.objectContaining({ method: "POST" }));
  });

  it("reloads the latest Brief after an answer conflict, retains answers, and retries with the refreshed revision", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", category: "Totes", brief_revision: 1, can_analyze: false,
      missing_fields: [{ field_key: "destination", reason: "Enter the delivery destination." }],
    };
    const latest = { ...saved, product_name: "Updated tote", quantity: 500, brief_revision: 2 };
    const completed = { ...latest, destination: "Sydney", brief_revision: 3, missing_fields: [] };
    let reads = 0;
    let saves = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/clarifications")) return Promise.resolve(jsonResponse({ brief_revision: 1, questions: [{ field_key: "destination", question: "Where should these be delivered?", reason: "Needed for sourcing." }] }));
      if (init?.method === "PATCH") {
        saves += 1;
        return Promise.resolve(saves === 1 ? jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed. Reload it before saving." } }, 409) : jsonResponse(completed));
      }
      reads += 1;
      return Promise.resolve(jsonResponse(reads === 1 ? saved : latest));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Where should these be delivered?"), { target: { value: "Sydney" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This Brief changed");
    await waitFor(() => expect(reads).toBe(2));
    expect(screen.getByLabelText("Where should these be delivered?")).toHaveValue("Sydney");
    expect(screen.getByLabelText("Product name")).toHaveValue("Updated tote");
    expect(screen.getByLabelText("Requested quantity")).toHaveValue(500);
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    await waitFor(() => expect(saves).toBe(2));
    const patches = fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patches[1][1]?.body))).toMatchObject({
      expected_brief_revision: 2, product_name: "Updated tote", quantity: 500, destination: "Sydney",
    });
    expect(await screen.findByText("No required information is missing.")).toBeInTheDocument();
  });

  it("drops an answer for a field resolved by another edit before retrying remaining answers", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", category: "Totes", brief_revision: 1, can_analyze: false,
      missing_fields: [
        { field_key: "destination", reason: "Enter the delivery destination." },
        { field_key: "quantity", reason: "Enter a positive requested quantity." },
      ],
    };
    const latest = {
      ...saved, destination: "Melbourne", brief_revision: 2,
      missing_fields: [{ field_key: "quantity", reason: "Enter a positive requested quantity." }],
    };
    const completed = { ...latest, quantity: 1000, brief_revision: 3, missing_fields: [] };
    const questions = [
      { field_key: "destination", question: "Where should these be delivered?", reason: "Needed for sourcing." },
      { field_key: "quantity", question: "How many totes do you need?", reason: "Needed for sourcing." },
    ];
    let reads = 0;
    let saves = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/clarifications")) return Promise.resolve(jsonResponse({ brief_revision: 1, questions }));
      if (init?.method === "PATCH") {
        saves += 1;
        return Promise.resolve(saves === 1
          ? jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed. Reload it before saving." } }, 409)
          : jsonResponse(completed));
      }
      reads += 1;
      return Promise.resolve(jsonResponse(reads === 1 ? saved : latest));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Where should these be delivered?"), { target: { value: "Sydney" } });
    fireEvent.change(screen.getByLabelText("How many totes do you need?"), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));

    await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Melbourne"));
    expect(screen.queryByLabelText("Where should these be delivered?")).not.toBeInTheDocument();
    expect(screen.getByLabelText("How many totes do you need?")).toHaveValue(1000);
    expect(screen.getByText("Enter a positive requested quantity.")).toBeInTheDocument();
    expect(screen.queryByText("Enter the delivery destination.")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    await waitFor(() => expect(saves).toBe(2));
    const patches = fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patches[1][1]?.body))).toMatchObject({
      expected_brief_revision: 2, destination: "Melbourne", quantity: 1000,
    });
    expect(await screen.findByText("No required information is missing.")).toBeInTheDocument();
  });

  it("removes the retry when another edit resolves the only pending answer", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", brief_revision: 1, can_analyze: false,
      missing_fields: [{ field_key: "destination", reason: "Enter the delivery destination." }],
    };
    const latest = { ...saved, destination: "Melbourne", brief_revision: 2, missing_fields: [] };
    let reads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/clarifications")) return Promise.resolve(jsonResponse({ brief_revision: 1, questions: [{ field_key: "destination", question: "Where should these be delivered?", reason: "Needed for sourcing." }] }));
      if (init?.method === "PATCH") return Promise.resolve(jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed. Reload it before saving." } }, 409));
      reads += 1;
      return Promise.resolve(jsonResponse(reads === 1 ? saved : latest));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Where should these be delivered?"), { target: { value: "Sydney" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));

    await waitFor(() => expect(screen.getByLabelText("Destination")).toHaveValue("Melbourne"));
    expect(screen.queryByRole("form", { name: "Clarification questions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save answers" })).not.toBeInTheDocument();
    expect(screen.getByText("No required information is missing.")).toBeInTheDocument();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });

  it("manual save after an answer conflict uses the refreshed Brief and revision", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", category: "Totes", brief_revision: 1, can_analyze: false,
      missing_fields: [{ field_key: "destination", reason: "Enter the delivery destination." }],
    };
    const latest = { ...saved, product_name: "Server edit", quantity: 700, brief_revision: 2 };
    let reads = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/clarifications")) return Promise.resolve(jsonResponse({ brief_revision: 1, questions: [{ field_key: "destination", question: "Where should these be delivered?", reason: "Needed for sourcing." }] }));
      if (init?.method === "PATCH") return Promise.resolve(jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed. Reload it before saving." } }, 409));
      reads += 1;
      return Promise.resolve(jsonResponse(reads === 1 ? saved : latest));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Where should these be delivered?"), { target: { value: "Sydney" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    await waitFor(() => expect(screen.getByLabelText("Product name")).toHaveValue("Server edit"));
    fireEvent.change(screen.getByLabelText("Destination"), { target: { value: "Melbourne" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    await waitFor(() => expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(2));
    const patches = fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(patches[1][1]?.body))).toMatchObject({
      expected_brief_revision: 2, product_name: "Server edit", quantity: 700, destination: "Melbourne",
    });
  });

  it("maps delivery, material, and branding answers into one existing Brief snapshot", async () => {
    const saved = {
      ...emptyBrief, product_name: "Cosmetic bag", category: "Cosmetic bags", quantity: 1000,
      destination: "Sydney", brief_revision: 1, can_analyze: false,
      missing_fields: [
        { field_key: "delivery_target", reason: "Enter a valid delivery target." },
        { field_key: "requirement.material", reason: "Specify the material." },
        { field_key: "requirement.custom_branding", reason: "State whether branding is required." },
      ],
    };
    const questions = [
      { field_key: "delivery_target", question: "When should the bags arrive?", reason: "Needed for sourcing." },
      { field_key: "requirement.material", question: "What material should the bags use?", reason: "Needed for sourcing." },
      { field_key: "requirement.custom_branding", question: "Do the bags need custom branding?", reason: "Needed for sourcing." },
    ];
    const fetchMock = vi.fn((path: string, init?: RequestInit) => Promise.resolve(
      path.endsWith("/clarifications") ? jsonResponse({ brief_revision: 1, questions }) :
      init?.method === "PATCH" ? jsonResponse({ ...saved, brief_revision: 2, missing_fields: [] }) : jsonResponse(saved),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Delivery answer type"), { target: { value: "PERIOD" } });
    fireEvent.change(screen.getByLabelText("Delivery answer"), { target: { value: "Early 2027" } });
    fireEvent.change(screen.getByLabelText("What material should the bags use?"), { target: { value: "Cotton" } });
    fireEvent.change(screen.getByLabelText("Do the bags need custom branding?"), { target: { value: "no" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));

    await waitFor(() => expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PATCH")).toBe(true));
    const body = JSON.parse(String(fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH")?.[1]?.body));
    expect(body.delivery_target).toEqual({ kind: "PERIOD", label: "Early 2027", start_date: null, end_date: null });
    expect(body.requirements).toEqual([
      { kind: "MATERIAL", importance: null, expected_value: { value: "Cotton" }, notes: null },
      { kind: "CAPABILITY", importance: null, expected_value: { capability_key: "CUSTOM_BRANDING", value: false }, notes: null },
    ]);
    expect(body.expected_brief_revision).toBe(1);
  });

  it("requires existing Brief edits to be saved before generating questions", async () => {
    const saved = {
      ...emptyBrief, product_name: "Tote", category: "Totes", brief_revision: 1, can_analyze: false,
      missing_fields: [{ field_key: "quantity", reason: "Enter a positive requested quantity." }],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(saved));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);
    const generate = await screen.findByRole("button", { name: "Get clarification questions" });
    fireEvent.change(screen.getByLabelText("Product name"), { target: { value: "Canvas tote" } });
    expect(generate).toBeDisabled();
    expect(screen.getByText("Save your Brief edits before generating questions.")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
