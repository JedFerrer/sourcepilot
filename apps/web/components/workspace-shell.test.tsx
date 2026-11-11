import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { WorkspaceShell } from "./workspace-shell";

afterEach(cleanup);

it("changes stages through the selector while preserving mounted drafts and browser history", () => {
  window.history.replaceState({}, "", "/projects/sample?stage=brief");
  render(<WorkspaceShell projectId="sample" name="Sample" preference={null}
    outdated={false} retry={() => {}} rename={null} stages={{
      BRIEF: <label>Sample draft<input /></label>, SUPPLIERS: <p>Supplier content</p>,
      QUOTES: <p>Quote content</p>, COMPARISON: <p>Comparison content</p>, DECISION: <p>Decision content</p>,
    }} />);
  const selector = screen.getByRole("combobox", { name: "Stage" });
  expect(within(selector).getAllByRole("option").map((option) => option.textContent?.trim())).toEqual([
    "1. Brief", "2. Suppliers", "3. Quotes", "4. Comparison", "5. Decision",
  ]);
  fireEvent.change(screen.getByLabelText("Sample draft"), { target: { value: "Keep my draft" } });
  fireEvent.change(selector, { target: { value: "QUOTES" } });
  expect(screen.getByText("Quote content")).toBeVisible();
  expect(window.location.search).toBe("?stage=quotes");
  fireEvent.change(selector, { target: { value: "BRIEF" } });
  expect(screen.getByLabelText("Sample draft")).toHaveValue("Keep my draft");
  window.history.replaceState({}, "", "/projects/sample?stage=decision");
  fireEvent.popState(window);
  expect(selector).toHaveValue("DECISION");
  expect(screen.getByText("Decision content")).toBeVisible();
});
