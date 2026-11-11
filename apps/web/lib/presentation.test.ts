import { describe, expect, it } from "vitest";
import { displayRequirement, requirementLabel } from "./presentation";

describe("saved requirement presentation", () => {
  it("retains false capability values and distinguishes missing currency", () => {
    expect(requirementLabel("CAPABILITY", { capability_key: "CUSTOM_BRANDING" })).toBe("Custom branding");
    expect(displayRequirement({ value: false })).toBe("No");
    expect(displayRequirement({ amount: 5, currency: "USD" })).toBe("5 USD");
    expect(displayRequirement({ amount: 5 })).toContain("Currency not provided");
  });
  it("retains delivery bounds and literal uncertainty text without raw field keys", () => {
    expect(displayRequirement({ kind: "DATE", date: "2026-12-15" })).toBe("December 15, 2026");
    expect(displayRequirement({ kind: "PERIOD", label: "Holiday season", start_date: "2026-12-01", end_date: "2026-12-31" })).toBe("Holiday season · From December 1, 2026 · Until December 31, 2026");
    expect(displayRequirement({ subject: "OTHER_CONTEXT", text: "Delivery timing is not decided yet." })).toBe("Delivery timing is not decided yet.");
  });
});
