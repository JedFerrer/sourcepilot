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
    expect(JSON.parse(String(saveCall?.[1]?.body)).product_name).toBe("Manual bag");
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
});
