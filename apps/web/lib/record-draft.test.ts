import { describe, expect, it } from "vitest";
import { createDraft, reduceDraft, sameRecord } from "./record-draft";

describe("record reconciliation", () => {
  const original = { amount: "4.22", currency: "USD", requirements: [{ id: "material", kind: "MATERIAL", importance: "REQUIRED", value: "cotton" }] };
  it("retains a complete amount/currency draft when another client changes currency", () => {
    const edited = reduceDraft(createDraft(original), { type: "edit", value: { ...original, amount: "4.50" } });
    const received = reduceDraft(edited, { type: "receive", value: { ...original, currency: "EUR" } });
    expect(received.draft).toEqual({ ...original, amount: "4.50" });
    expect(received.remote.currency).toBe("EUR");
    expect(received.conflict).toBe(true);
    expect(reduceDraft(received, { type: "submit" }).submitted).toBeNull();
  });
  it.each(["addition", "deletion", "kind", "importance", "reorder"])("does not guess a requirement merge on %s", (change) => {
    const local = { ...original, amount: "5" };
    const requirements = change === "deletion" ? [] : change === "addition" ? [...original.requirements, { ...original.requirements[0], id: "new" }] :
      change === "reorder" ? [{ ...original.requirements[0], id: "other" }, ...original.requirements] : [{ ...original.requirements[0], [change]: "CHANGED" }];
    const state = reduceDraft(reduceDraft(createDraft(original), { type: "edit", value: local }), { type: "receive", value: { ...original, requirements } });
    expect(state.draft).toEqual(local);
    expect(state.remote.requirements).toEqual(requirements);
    expect(state.conflict).toBe(true);
  });
  it("adopts clean reads and leaves unchanged dirty reads untouched", () => {
    expect(reduceDraft(createDraft(original), { type: "receive", value: { ...original, amount: "6" } }).draft.amount).toBe("6");
    const dirty = reduceDraft(createDraft(original), { type: "edit", value: { ...original, amount: "7" } });
    expect(reduceDraft(dirty, { type: "receive", value: original })).toBe(dirty);
  });
  it("acknowledges only the submitted snapshot, preserving typing during save", () => {
    const submitted = { ...original, amount: "5" };
    let state = reduceDraft(createDraft(original), { type: "edit", value: submitted });
    state = reduceDraft(state, { type: "submit" });
    state = reduceDraft(state, { type: "edit", value: { ...submitted, amount: "6" } });
    state = reduceDraft(state, { type: "saved", value: submitted });
    expect(state.draft.amount).toBe("6"); expect(state.baseline.amount).toBe("5"); expect(state.conflict).toBe(false);
  });
  it("requires review when normalization or assigned IDs make later edits ambiguous", () => {
    let state = reduceDraft(createDraft(original), { type: "submit" });
    state = reduceDraft(state, { type: "edit", value: { ...original, amount: "6" } });
    state = reduceDraft(state, { type: "saved", value: { ...original, amount: "4.2200" } });
    expect(state.conflict).toBe(true); expect(state.draft.amount).toBe("6");
  });
  it("preserves failed drafts, blocks uncertain replay, and makes discard explicit", () => {
    let state = reduceDraft(createDraft(original), { type: "edit", value: { ...original, currency: "EUR" } });
    state = reduceDraft(state, { type: "submit" });
    state = reduceDraft(state, { type: "failed", message: "Disconnected", uncertain: true });
    expect(state.draft.currency).toBe("EUR"); expect(reduceDraft(state, { type: "submit" }).submitted).toBeNull();
    state = reduceDraft(state, { type: "use-saved" }); expect(state.draft).toEqual(original);
  });
});

it("ignores object-key serialization order while preserving ordered collections", () => {
  expect(sameRecord({ delivery: { kind: "DATE", date: "2026-12-15" } }, { delivery: { date: "2026-12-15", kind: "DATE" } })).toBe(true);
  expect(sameRecord([{ id: "a" }, { id: "b" }], [{ id: "b" }, { id: "a" }])).toBe(false);
});
it.each(["add/add", "edit/delete", "delete/edit", "reorder", "assigned IDs"])("retains both complete requirement collections for %s", (scenario) => {
  const original = [{ id: "a", value: "cotton" }, { id: "b", value: "GRS" }];
  const local = scenario === "delete/edit" ? original.slice(1) : scenario === "add/add" || scenario === "assigned IDs" ? [...original, { id: "local", value: "logo" }] : [{ ...original[0], value: "recycled" }, original[1]];
  const remote = scenario === "edit/delete" ? original.slice(1) : scenario === "reorder" ? [...original].reverse() : scenario === "add/add" || scenario === "assigned IDs" ? [...original, { id: "server", value: "logo" }] : [{ ...original[0], value: "silk" }, original[1]];
  const state = reduceDraft(reduceDraft(createDraft(original), { type: "edit", value: local }), { type: "receive", value: remote });
  expect(state.draft).toEqual(local); expect(state.remote).toEqual(remote); expect(state.conflict).toBe(true);
});
