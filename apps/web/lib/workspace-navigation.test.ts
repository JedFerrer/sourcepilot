import { describe, expect, it } from "vitest";
import { fragmentStage, resolveStage, stageUrl } from "./workspace-navigation";
describe("workspace location", () => {
  it("gives one valid stage precedence over a conflicting legacy fragment", () => {
    expect(resolveStage(new URL("https://test/projects/p?stage=decision#brief-complete"), "QUOTES")).toBe("DECISION");
  });
  it.each(["stage=no", "stage=brief&stage=quotes", ""])("falls back to recognized legacy actions for %s", (query) => {
    expect(resolveStage(new URL(`https://test/projects/p?${query}#shortlist-approve`), "QUOTES")).toBe("SUPPLIERS");
  });
  it("uses backend guidance or Brief when no recognized location exists", () => {
    expect(resolveStage(new URL("https://test/projects/p#unknown"), "QUOTES")).toBe("QUOTES");
    expect(resolveStage(new URL("https://test/projects/p"))).toBe("BRIEF");
    expect(fragmentStage("#unknown")).toBeNull();
  });
  it("canonicalizes duplicate values while preserving unrelated parameters", () => {
    expect(stageUrl(new URL("https://test/projects/p?filter=a&stage=no&stage=brief#old"), "QUOTES")).toBe("/projects/p?filter=a&stage=quotes");
  });
});
