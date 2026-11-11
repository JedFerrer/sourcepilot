import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { viewStage, inspectQuoteSource, closeQuoteSource, advice, comparison, confirm, createAndApprove, quoteCard, readApi, scenario, suppliers, upload, type Project, type Quote } from "./helpers";

test("complete V1 golden path", async ({ page }) => {
  const project = await createAndApprove(page, true);
  await test.step("Upload, review and explicitly confirm three PDF quotes", async () => {
    for (let index = 0; index < suppliers.length; index++) {
      await upload(page, index);
      const source = await inspectQuoteSource(page, index);
      await expect(source.getByRole("blockquote").first()).toContainText(/./);
      await closeQuoteSource(page);
      await expect(quoteCard(page, index)).toContainText("Current origin: AI EXTRACTED");

      await expect(quoteCard(page, index)).toContainText("Unknown");
      await confirm(page, index);
    }
  });
  await test.step("Factual comparison and expected advisory result", async () => {
    await comparison(page);
    const section = page.getByRole("region", { name: "Comparison", exact: true });
    for (const supplier of suppliers) {
      await expect(section.getByRole("columnheader", { name: supplier, exact: true })).toBeVisible();
    }
    const quotes = await readApi<Quote[]>(page, `/projects/${project.id}/quotes`);
    expect(quotes).toHaveLength(3);
    expect(quotes.map((quote) => quote.values.unit_price.current_value).sort()).toEqual([...scenario.quote_prices].sort());
    const priceRow = section.getByRole("row").filter({ has: page.getByRole("rowheader", { name: "Unit price", exact: true }) });
    for (const quote of quotes) {
      expect(quote.status).toBe("CONFIRMED");
      expect(quote.values.currency.current_value).toBe("USD");
      await expect(priceRow).toContainText(`USD ${quote.values.unit_price.current_value}`);
    }
    await advice(page, project.id);
    execFileSync("uv", ["run", "--no-sync", "python", "-m", "tests.e2e_support.verify_trace", project.id],
      { cwd: "../api", stdio: "pipe", timeout: 20_000 });
  });
  await test.step("Human decision persists after reload and on dashboard", async () => {
    await viewStage(page, "Decision");
    const section = page.getByRole("region", { name: "Decision", exact: true });
    await section.getByRole("combobox", { name: /Preferred supplier/ }).selectOption({ label: suppliers[0] });
    await section.getByLabel("Decision notes").fill("Evidence reviewed; retain uncertainties for follow-up.");
    await section.getByRole("button", { name: "Mark as Preferred Supplier", exact: true }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Save preferred supplier", exact: true }).click();
    await expect(section).toContainText("Preferred supplier saved.");
    await page.reload();
    await expect(section).toContainText(`Current preference: ${suppliers[0]}`);
    await expect(section.getByLabel("Decision notes")).toHaveValue("Evidence reviewed; retain uncertainties for follow-up.");
    const saved = await readApi<Project>(page, `/projects/${project.id}`);
    expect(saved.preferred_supplier_name).toBe(suppliers[0]);
    expect(saved.decision_notes).toBe("Evidence reviewed; retain uncertainties for follow-up.");
    await page.getByRole("link", { name: "All projects", exact: true }).click();
    const card = page.getByRole("link").filter({ hasText: project.name });
    await expect(card).toContainText(`Preferred supplier: ${suppliers[0]}`);
    await expect(card).toContainText("Manage your preferred supplier");
    await expect(card).toContainText("Confirmed quotes: 3");
  });
});
