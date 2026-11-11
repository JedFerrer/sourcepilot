import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { BriefEditor } from "./brief-editor";
import { jsonResponse } from "../test/api-responses";
import userEvent from "@testing-library/user-event";

const emptyBrief = {
  product_name: null, category: null, quantity: null, destination: null,
  delivery_target: null, target_unit_price: null, requirements: [],
  status: "IN_PROGRESS", brief_revision: 0, can_analyze: true,
  missing_fields: [{ field_key: "product_name", reason: "Name the product to source." }],
  uncertainties: [],
};

const readyBrief = {
  ...emptyBrief, product_name: "Desk lamp", category: "Lighting", quantity: 100,
  destination: "Manila", delivery_target: { kind: "DATE", date: "2027-01-01" },
  status: "READY_FOR_REVIEW", missing_fields: [], brief_revision: 1, can_analyze: false,
  approved_at: null,
};

describe("BriefEditor", () => {
  it("focuses server errors and links to retained fields, including a collapsed attribute", async () => {
    const user = userEvent.setup();
    const saved = { ...readyBrief, requirements: [{ id: "attribute-1", kind: "INFORMATIONAL", importance: "INFORMATIONAL", expected_value: { subject: "OTHER_CONTEXT", text: "Original context" }, notes: null }] };
    vi.stubGlobal("fetch", vi.fn((_: string, init?: RequestInit) => Promise.resolve(init?.method === "PATCH" ? jsonResponse({ error: { code: "VALIDATION_ERROR", message: "Invalid", fields: [
      { field: "body.quantity", message: "Quantity is too large" },
      { field: "body.requirements.0.expected_value.text", message: "Context is too long" },
    ] } }, 422) : jsonResponse(saved))));
    render(<BriefEditor projectId="p" />);
    const quantity = await screen.findByLabelText("Requested quantity");
    fireEvent.change(quantity, { target: { value: "2147483648" } });
    await user.click(screen.getByRole("button", { name: "Save Brief" }));
    const summary = await screen.findByRole("alert");
    expect(summary).toHaveFocus();
    expect(quantity).toHaveAttribute("aria-invalid", "true");
    expect(quantity).toHaveAccessibleDescription("Requested quantity: Quantity is too large");
    const link = within(summary).getByRole("link", { name: /Context is too long/ });
    link.focus(); await user.keyboard("{Enter}");
    const context = screen.getByLabelText("Context");
    expect(context.closest("details")).toHaveAttribute("open");
    expect(context).toHaveFocus();
    expect(context).toHaveAttribute("aria-invalid", "true");
    expect(context).toHaveAccessibleDescription(/Context is too long/);
    expect(context).toHaveValue("Original context");
    expect(quantity).toHaveValue(2147483648);
  });

  it("links a requirement-level server error to its value and does not steal focus after leaving the stage", async () => {
    let finish!: (value: Response) => void;
    vi.stubGlobal("fetch", vi.fn((_: string, init?: RequestInit) => init?.method === "PATCH" ? new Promise<Response>(resolve => { finish = resolve; }) : Promise.resolve(jsonResponse(emptyBrief))));
    const view = render(<div><button>Other stage</button><div data-testid="stage"><BriefEditor projectId="p" /></div></div>);
    fireEvent.click(await screen.findByRole("button", { name: "Add requirement" }));
    fireEvent.change(screen.getByLabelText("Value"), { target: { value: "   " } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    screen.getByTestId("stage").hidden = true;
    screen.getByRole("button", { name: "Other stage" }).focus();
    await act(async () => { finish(jsonResponse({ error: { code: "VALIDATION_ERROR", message: "Invalid", fields: [{ field: "body.requirements.0", message: "Value error, value must not be blank" }] } }, 422)); });
    expect(screen.getByRole("button", { name: "Other stage" })).toHaveFocus();
    screen.getByTestId("stage").hidden = false;
    fireEvent.click(screen.getByRole("link", { name: "Requirement 1: value must not be blank" }));
    expect(screen.getByLabelText("Value")).toHaveFocus();
    expect(screen.getByLabelText("Value")).toHaveValue("   ");
    view.unmount();
  });
  it.each(["2000", ""])("retains post-submission answer %s after its question disappears without replay", async (later) => {
    let finish!: (value: Response) => void;
    const saved = { ...readyBrief, quantity: null, status: "IN_PROGRESS", missing_fields: [{ field_key: "quantity", reason: "Quantity needed" }] };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return new Promise<Response>((resolve) => { finish = resolve; });
      return Promise.resolve(jsonResponse(path.endsWith("/clarifications") ? { brief_revision: 1, questions: [{ field_key: "quantity", question: "How many?", reason: "Needed" }] } : saved));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("How many?"), { target: { value: "1000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    fireEvent.change(screen.getByLabelText("How many?"), { target: { value: later } });
    await act(async () => { finish(jsonResponse({ ...readyBrief, quantity: 1000, brief_revision: 2 })); });
    expect(screen.queryByLabelText("How many?")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Requested quantity")).toHaveValue(1000);
    const recovery = screen.getByRole("region", { name: "Unsaved clarification answers" });
    expect(within(recovery).getByText(later || "Empty answer (cleared)")).toBeInTheDocument();
    expect(screen.getAllByText("Unsaved changes").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Review saved Brief" })).toBeDisabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
    fireEvent.click(within(recovery).getByRole("button", { name: /Discard retained answer/ }));
    expect(screen.getByRole("button", { name: "Review saved Brief" })).toBeEnabled();
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(1);
  });

  it("retains delivery type with later answer edits and preserves edits on failed saves", async () => {
    let finish!: (value: Response) => void;
    const saved = { ...readyBrief, delivery_target: null, status: "IN_PROGRESS", missing_fields: [{ field_key: "delivery_target", reason: "Delivery needed" }] };
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (init?.method === "PATCH") return new Promise<Response>((resolve) => { finish = resolve; });
      return Promise.resolve(jsonResponse(path.endsWith("/clarifications") ? { brief_revision: 1, questions: [{ field_key: "delivery_target", question: "When?", reason: "Needed" }] } : saved));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Get clarification questions" }));
    fireEvent.change(await screen.findByLabelText("Delivery answer"), { target: { value: "2027-01-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    fireEvent.change(screen.getByLabelText("Delivery answer type"), { target: { value: "PERIOD" } });
    fireEvent.change(screen.getByLabelText("Delivery answer"), { target: { value: "Spring 2027" } });
    await act(async () => { finish(jsonResponse({ error: { code: "UNAVAILABLE", message: "Try later" } }, 503)); });
    expect(screen.getByLabelText("Delivery answer")).toHaveValue("Spring 2027");
    expect(screen.getByLabelText("Delivery answer type")).toHaveValue("PERIOD");
    fireEvent.click(screen.getByRole("button", { name: "Save answers" }));
    fireEvent.change(screen.getByLabelText("Delivery answer"), { target: { value: "Summer 2027" } });
    await act(async () => { finish(jsonResponse({ ...readyBrief, delivery_target: { kind: "PERIOD", label: "Spring 2027" }, brief_revision: 2 })); });
    const recovery = screen.getByRole("region", { name: "Unsaved clarification answers" });
    expect(recovery).toHaveTextContent("Period");
    expect(recovery).toHaveTextContent("Summer 2027");
    expect(fetchMock.mock.calls.filter(([, init]) => init?.method === "PATCH")).toHaveLength(2);
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("opens a saved-value review without approving and returns to the retained editor", async () => {
    const fetchMock = vi.fn(() => Promise.resolve(jsonResponse({ ...readyBrief, uncertainties: ["Check delivery timing."] })));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" originalRequest="Source lamps for Manila." />);
    fireEvent.click(await screen.findByRole("button", { name: "Review saved Brief" }));
    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveTextContent("January 1, 2027");
    expect(dialog).toHaveTextContent("Check delivery timing.");
    expect(dialog).not.toHaveTextContent("kind: DATE");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Continue editing" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Product name")).toHaveValue("Desk lamp");
  });

  it("requires saved edits before approval and refreshes the project after success", async () => {
    const onProjectChange = vi.fn().mockResolvedValue(undefined);
    const fetchMock = vi.fn((path: string, init?: RequestInit) => Promise.resolve(
      path.endsWith("/approve") && init?.method === "POST"
        ? jsonResponse({ ...readyBrief, status: "APPROVED", approved_at: "2026-09-24T00:00:00Z" })
        : jsonResponse(readyBrief),
    ));
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" onProjectChange={onProjectChange} />);
    const review = await screen.findByRole("button", { name: "Review saved Brief" });
    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "200" } });
    expect(review).toBeDisabled();
    expect(screen.getByText("Save your Brief edits before approving.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Requested quantity"), { target: { value: "100" } });
    fireEvent.click(review);
    fireEvent.click(screen.getByRole("button", { name: "Approve Brief" }));
    await waitFor(() => expect(screen.getByText("Readiness: Approved")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief/approve", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ expected_brief_revision: 1 }),
      credentials: "same-origin",
    });
    expect(onProjectChange).toHaveBeenCalledOnce();
  });

  it("retains the draft when approval fails", async () => {
    vi.stubGlobal("fetch", vi.fn((path: string) => Promise.resolve(
      path.endsWith("/approve")
        ? jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed." } }, 409)
        : jsonResponse(readyBrief),
    )));
    render(<BriefEditor projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Review saved Brief" }));
    fireEvent.click(screen.getByRole("button", { name: "Approve Brief" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("This Brief changed.");
    expect(screen.getByLabelText("Product name")).toHaveValue("Desk lamp");
    expect(screen.getByRole("button", { name: "Reload Brief" })).toBeInTheDocument();
  });

  it("clears a stale approval error after reloading the latest ready Brief and allows approval", async () => {
    const latest = { ...readyBrief, quantity: 220, brief_revision: 2 };
    const approved = { ...latest, status: "APPROVED", approved_at: "2026-09-24T00:00:00Z" };
    let reads = 0;
    let approvals = 0;
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.endsWith("/approve") && init?.method === "POST") {
        approvals += 1;
        return Promise.resolve(approvals === 1
          ? jsonResponse({ error: { code: "BRIEF_CONFLICT", message: "This Brief changed. Reload it before approving." } }, 409)
          : jsonResponse(approved));
      }
      reads += 1;
      return Promise.resolve(jsonResponse(reads === 1 ? readyBrief : latest));
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<BriefEditor projectId="project-1" />);

    fireEvent.click(await screen.findByRole("button", { name: "Review saved Brief" }));
    const approve = screen.getByRole("button", { name: "Approve Brief" });
    fireEvent.click(approve);
    expect(await screen.findByRole("alert")).toHaveTextContent("Saved Brief changed. Review the latest saved values before approving again.");
    expect(approvals).toBe(0);
    await waitFor(() => expect(screen.getByLabelText("Requested quantity")).toHaveValue(220));
    fireEvent.click(approve);
    expect(await screen.findByRole("alert")).toHaveTextContent("This Brief changed. Reload it before approving.");
    expect(approve).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Reload Brief" }));
    await waitFor(() => expect(screen.getByLabelText("Requested quantity")).toHaveValue(220));
    expect(screen.getByRole("dialog", { name: "Review saved Brief before approval" })).toHaveTextContent("220");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reload Brief" })).not.toBeInTheDocument();
    expect(approve).toBeEnabled();
    expect(reads).toBe(4);

    fireEvent.click(approve);
    await waitFor(() => expect(screen.getByText("Readiness: Approved")).toBeInTheDocument());
    expect(approvals).toBe(2);
    const approvalCalls = fetchMock.mock.calls.filter(([path, init]) => path.endsWith("/approve") && init?.method === "POST");
    expect(JSON.parse(String(approvalCalls[0][1]?.body))).toEqual({ expected_brief_revision: 2 });
    expect(JSON.parse(String(approvalCalls[1][1]?.body))).toEqual({ expected_brief_revision: 2 });
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

  it("keeps an extracted uncertainty visible for approval after save and reload", async () => {
    const extracted = {
      ...readyBrief, product_name: "Cosmetic bag", brief_revision: 1, can_analyze: false,
      requirements: [{ id: "req-1", kind: "MATERIAL", importance: null, expected_value: { value: "recycled polyester" }, notes: null }],
      ambiguities: ["Branding method was not stated."],
      uncertainties: ["Branding method was not stated."],
    };
    let saved: object = emptyBrief;
    const fetchMock = vi.fn((_: string, init?: RequestInit) => Promise.resolve(
      init?.method === "POST" ? jsonResponse(extracted) :
      init?.method === "PATCH" ? (saved = { ...extracted, requirements: [{ ...extracted.requirements[0], importance: "REQUIRED" }] }, jsonResponse(saved)) :
      jsonResponse(saved),
    ));
    vi.stubGlobal("fetch", fetchMock);
    const first = render(<BriefEditor projectId="project-1" />);
    fireEvent.click(await screen.findByRole("button", { name: "Analyze request" }));
    expect(await screen.findByRole("region", { name: "Uncertainties to review" })).toHaveTextContent("Branding method was not stated.");
    expect(screen.getByLabelText("Importance")).toHaveValue("");
    fireEvent.change(screen.getByLabelText("Importance"), { target: { value: "REQUIRED" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Brief" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("/api/projects/project-1/brief", expect.objectContaining({ method: "PATCH" })));
    const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
    expect(JSON.parse(String(saveCall?.[1]?.body)).requirements[0].importance).toBe("REQUIRED");
    await waitFor(() => expect(screen.getByRole("region", { name: "Uncertainties to review" })).toHaveTextContent("Branding method was not stated."));
    first.unmount();
    render(<BriefEditor projectId="project-1" />);
    expect(await screen.findByRole("region", { name: "Uncertainties to review" })).toHaveTextContent("Branding method was not stated.");
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
    expect(await screen.findByText(/Additional context/, { selector: "summary" })).toBeInTheDocument();
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
    await waitFor(() => expect(screen.getByText("Readiness: Ready for review")).toBeInTheDocument());
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
    await waitFor(() => expect(screen.queryByRole("region", { name: "Missing information" })).not.toBeInTheDocument());
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
    await waitFor(() => expect(screen.queryByRole("region", { name: "Missing information" })).not.toBeInTheDocument());
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
    expect(screen.queryByRole("region", { name: "Missing information" })).not.toBeInTheDocument();
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
