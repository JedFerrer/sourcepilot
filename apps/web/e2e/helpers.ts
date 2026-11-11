import { expect, test, type Locator, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import scenario from "../../api/tests/e2e_support/scenario.json";

export { scenario };
export const suppliers = ["Harbor Pouch Works", "Willow Stitch Studio", "Moss Thread Bags"];
export const pdfNames = ["harbor_primary.pdf", "willow_primary.pdf", "moss_primary.pdf"];
export const pdfDirectory = path.resolve("../api/tests/fixtures/quote_pdfs");

export type Quote = {
  id: string; supplier_id: string; status: string; entry_type: string;
  processing: { attempts: number; status: string } | null;
  values: Record<string, { current_value: string | number | null; current_origin: string;
    ai_extracted_value: string | number | null }>;
};
export type Project = {
  preferred_supplier_id: string | null; preferred_supplier_name: string | null;
  decision_notes: string | null;
  workflow: { suppliers_stale: boolean; comparison_stale: boolean; comparison_ready: boolean };
};

export async function readApi<T>(page: Page, route: string): Promise<T> {
  const response = await page.request.get(`/api${route}`);
  expect(response.ok(), `Read ${route}: ${response.status()}`).toBeTruthy();
  return response.json() as Promise<T>;
}

export function quoteCard(page: Page, index: number): Locator {
  return page.getByRole("region", { name: "Quotes", exact: true }).getByRole("article")
    .filter({ has: page.getByRole("heading", { name: suppliers[index], exact: true }) });
}

export async function viewStage(page: Page, name: string): Promise<void> {
  const navigation = page.getByRole("navigation", { name: "Sourcing workflow stages" });
  const selector = navigation.getByRole("combobox", { name: "Stage", exact: true });
  if (await selector.isVisible()) await selector.selectOption(name.toUpperCase());
  else await navigation.getByRole("link", { name, exact: true }).click();
}
export async function selectQuote(page: Page, index: number): Promise<void> {
  await viewStage(page, "Quotes");
  if (await page.getByLabel("Quote supplier", { exact: true }).isVisible()) await page.getByLabel("Quote supplier", { exact: true }).selectOption({ label: suppliers[index] });
  else await page.getByRole("button", { name: new RegExp(`^${suppliers[index]}`) }).click();
}
export async function inspectQuoteSource(page: Page, index: number, field = "Unit price"): Promise<Locator> {
  await quoteCard(page, index).getByRole("button", { name: `View source evidence for ${field}`, exact: true }).first().click();
  return page.getByRole("dialog").or(page.getByRole("complementary", { name: "Original document evidence" }));
}
export async function closeQuoteSource(page: Page): Promise<void> {
  const modal = page.getByRole("dialog");
  if (await modal.isVisible()) await modal.getByRole("button", { name: "Close", exact: true }).click();
  else await page.getByRole("button", { name: "Close evidence", exact: true }).click();
}

export async function createAndApprove(page: Page, inspectSupplier = false): Promise<{ id: string; name: string }> {
  const name = `E2E ${test.info().title} ${test.info().repeatEachIndex}`;
  await test.step("Anonymous session and project creation", async () => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Your sourcing projects" })).toBeVisible();
    await expect(page.getByText("Loading projects…", { exact: true })).toBeHidden();
    await page.getByRole("button", { name: "New project", exact: true }).click();
    await page.getByLabel("Project name", { exact: true }).fill(name);
    await page.getByLabel("What do you want to source?").fill(scenario.request);
    await page.getByRole("button", { name: "Create project", exact: true }).click();
    await expect(page).toHaveURL(/\/projects\/[0-9a-f-]+(?:\?stage=brief)?$/);
    await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
    await expect(page.locator(".project-context")).toContainText("No Decision Yet");
  });
  const id = new URL(page.url()).pathname.split("/").at(-1)!;
  const brief = page.getByRole("region", { name: "Sourcing Brief", exact: true });
  await test.step("Analyze request and clarify missing delivery timing", async () => {
    await brief.getByRole("button", { name: "Analyze request", exact: true }).click();
    await expect(brief.getByLabel("Requested quantity", { exact: true })).toHaveValue("2000");
    await expect(brief.getByLabel("Destination", { exact: true })).toHaveValue("Sydney");
    await expect(brief).toContainText("Readiness: In progress");
    await expect(page.getByRole("link", { name: "Next: Complete the Brief", exact: true })).toBeVisible();
    await brief.getByRole("button", { name: "Get clarification questions", exact: true }).click();
    await expect(brief.getByRole("form", { name: "Clarification questions" })).toBeVisible();
    await brief.getByLabel("Delivery answer", { exact: true }).fill(scenario.delivery_answer);
    await brief.getByRole("button", { name: "Save answers", exact: true }).click();
    await expect(brief).toContainText("Readiness: Ready for review");
    await expect(page.getByRole("link", { name: "Next: Approve Brief", exact: true })).toBeVisible();
  });
  await test.step("Review importance and explicitly approve Brief", async () => {
    await brief.getByRole("group", { name: "Requirement 1", exact: true }).getByLabel("Importance").selectOption("REQUIRED");
    if (await brief.getByRole("button", { name: "Save Brief", exact: true }).isEnabled()) await brief.getByRole("button", { name: "Save Brief", exact: true }).click();
    await expect(brief.getByRole("button", { name: "Review saved Brief", exact: true })).toBeEnabled();
    if (test.info().title.startsWith("UX-U1 responsive")) {
      const previous = page.viewportSize();
      for (const width of [1440, 390, 320]) {
        await page.setViewportSize({ width, height: 900 });
        await page.screenshot({ path: test.info().outputPath(`brief-editor-${width}.png`), fullPage: true });
      }
      if (previous) await page.setViewportSize(previous);
    }
    await brief.getByRole("button", { name: "Review saved Brief", exact: true }).click();
    await captureReview(page, "brief");
    await page.getByRole("dialog").getByRole("button", { name: "Approve Brief", exact: true }).click();
    await expect(brief).toContainText("Readiness: Approved");
  });
  await test.step("Discover suppliers and approve shortlist of three", async () => {
    await viewStage(page, "Suppliers");
    const section = page.getByRole("region", { name: "Suppliers", exact: true });
    await section.getByRole("button", { name: "Discover Suppliers", exact: true }).click();
    await expect(section.getByRole("article")).toHaveCount(5);
    if (inspectSupplier) {
      await test.step("Inspect supplier evidence and bounded analyst explanation", async () => {
        const card = section.getByRole("article")
          .filter({ has: page.getByRole("heading", { name: suppliers[0], exact: true }) });
        await card.getByText("Available evidence", { exact: true }).click();
        await expect(card).toContainText("Synthetic current GRS record");
        await card.getByRole("button", { name: "Explain this supplier", exact: true }).click();
        await expect(card.getByRole("heading", { name: "Supplier explanation", exact: true })).toBeVisible();
        await expect(card).toContainText("Material (recycled polyester): Meets.");
      });
    }
    for (const supplier of suppliers) {
      const card = section.getByRole("article").filter({ has: page.getByRole("heading", { name: supplier, exact: true }) });
      await expect(card).toBeVisible();
      await card.getByRole("button", { name: "Add to shortlist", exact: true }).click();
      await expect(card.getByRole("button", { name: "Remove from shortlist", exact: true })).toBeVisible();
    }
    await approveShortlist(page);
  });
  return { id, name };
}


export async function captureReview(page: Page, stage: string): Promise<void> {
  if (!test.info().title.startsWith("UX-U1 responsive")) return;
  const previous = page.viewportSize();
  await page.addScriptTag({ path: createRequire(path.resolve("package.json")).resolve("axe-core/axe.min.js") });
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByRole("dialog")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
    const violations = await page.evaluate(async () => {
      const axe = (window as unknown as { axe: { run: (options: object) => Promise<{ violations: unknown[] }> } }).axe;
      return (await axe.run({ runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } })).violations;
    });
    expect(violations).toEqual([]);
    await page.screenshot({ path: test.info().outputPath(`${stage}-review-${width}.png`) });
  }
  if (previous) await page.setViewportSize(previous);
}

export async function approveShortlist(page: Page): Promise<void> {
  await viewStage(page, "Suppliers");
  const section = page.getByRole("region", { name: "Suppliers", exact: true });
  await section.getByRole("button", { name: "Review selected suppliers", exact: true }).click();
  await captureReview(page, "shortlist");
  await page.getByRole("dialog").getByRole("button", { name: "Approve Shortlist", exact: true }).click();
  await expect(section).toContainText("Shortlist approved");
  await selectQuote(page, 0);
  await expect(quoteCard(page, 0).getByRole("button", { name: "Upload PDF", exact: true })).toBeEnabled();
}

export async function upload(page: Page, index: number, filename = pdfNames[index], abandoned = false): Promise<void> {
  await selectQuote(page, index);
  const card = quoteCard(page, index);
  await card.getByRole("button", { name: "Upload PDF", exact: true }).click();
  await card.getByLabel("Upload PDF quote").setInputFiles(abandoned ? {
    name: "e2e-abandoned-harbor.pdf", mimeType: "application/pdf",
    buffer: readFileSync(path.join(pdfDirectory, filename)),
  } : path.join(pdfDirectory, filename));
  await expect(card).toContainText(abandoned ? "Status: PROCESSING" : filename === "image_only.pdf"
    ? "Status: FAILED" : "Status: NEEDS REVIEW", { timeout: 30_000 });
}

export async function confirm(page: Page, index: number): Promise<void> {
  await selectQuote(page, index);
  const card = quoteCard(page, index);
  await card.getByRole("button", { name: "Review for confirmation", exact: true }).click();
  await captureReview(page, `quote-${index}`);
  await page.getByRole("dialog").getByRole("button", { name: "Confirm Quote", exact: true }).click();
  await expect(card).toContainText("Status: CONFIRMED");
}

export async function comparison(page: Page, regenerate = false): Promise<void> {
  await viewStage(page, "Comparison");
  const section = page.getByRole("region", { name: "Comparison", exact: true });
  await section.getByRole("button", { name: regenerate ? "Regenerate Comparison" : "Generate Comparison", exact: true }).click();
  await expect(section).toContainText("Comparison is current.");
  await expect(section.getByRole("table")).toBeVisible();
}

export async function advice(page: Page, id: string): Promise<void> {
  expect((await readApi<Project>(page, `/projects/${id}`)).preferred_supplier_id).toBeNull();
  const section = page.getByRole("region", { name: "Comparison", exact: true });
  const response = page.waitForResponse((item) => item.url().endsWith(`/api/projects/${id}/comparison/advice`)
    && item.request().method() === "POST");
  await section.getByRole("button", { name: "Analyze Comparison", exact: true }).click();
  const result = await response;
  expect(result.ok(), `Comparison analyst status ${result.status()}`).toBeTruthy();
  const body = await result.json();
  expect(body.suggestion.supplier_id).toBe(scenario.advisory.supplier_id);
  expect(body.suggestion.supporting_reasons).toEqual(scenario.advisory.supporting_reasons);
  expect(body.suggestion.tradeoffs).toEqual(scenario.advisory.tradeoffs);
  expect(body.suggestion.uncertainties.map((item: { text: string }) => item.text)).toContain("No single supplier is suggested; review the cited tradeoffs before choosing.");
  expect(body).not.toHaveProperty("preferred_supplier_id");
  const region = section.getByRole("region", { name: "Comparison analysis", exact: true });
  await expect(region.getByRole("heading", { name: "No supplier suggested yet", exact: true })).toBeVisible();
  await expect(region).toContainText("No single supplier is suggested; review the cited tradeoffs before choosing.");
  await expect(region).toContainText("Important unknowns");
  expect((await readApi<Project>(page, `/projects/${id}`)).preferred_supplier_id).toBeNull();
  await expect(page.locator(".project-context")).toContainText("No Decision Yet");
}
