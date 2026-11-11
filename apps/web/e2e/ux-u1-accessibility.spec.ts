import { expect, test, type Locator, type Page } from "@playwright/test";
import { createAndApprove, upload, quoteCard, readApi, suppliers } from "./helpers";

async function expectVisibleFocus(page: Page, target: Locator) {
  await expect(target).toBeFocused();
  const bounds = await target.boundingBox();
  expect(bounds).not.toBeNull();
  const height = await page.evaluate(() => innerHeight);
  expect(bounds!.y).toBeGreaterThanOrEqual(0);
  expect(bounds!.y + bounds!.height).toBeLessThanOrEqual(height);
  expect(await target.evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
}

for (const width of [320, 390, 1440]) {
  test(`Brief server errors provide visible keyboard recovery at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    await page.getByRole("button", { name: "New project", exact: true }).click();
    await page.getByLabel("Project name", { exact: true }).fill("Accessibility regression");
    await page.getByLabel("What do you want to source?").fill("Synthetic validation project");
    await page.getByRole("button", { name: "Create project", exact: true }).click();
    await page.getByRole("button", { name: "Add requirement", exact: true }).click();
    const value = page.getByRole("textbox", { name: "Value", exact: true });
    await value.fill("   ");
    await page.getByRole("button", { name: "Save Brief", exact: true }).focus();
    await page.keyboard.press("Enter");
    const summary = page.getByRole("alert", { name: "Brief errors" });
    await expect(summary).toContainText("Requirement 1: value must not be blank");
    await expectVisibleFocus(page, summary);
    await page.screenshot({ path: test.info().outputPath("brief-summary.png") });
    await page.keyboard.press("Tab");
    await expect(summary.getByRole("link")).toBeFocused();
    await page.keyboard.press("Enter");
    await expectVisibleFocus(page, value);
    await expect(value).toHaveAttribute("aria-invalid", "true");
    await expect(value).toHaveAccessibleDescription("Requirement 1: value must not be blank");
    await expect(value).toHaveValue("   ");
    await page.screenshot({ path: test.info().outputPath("brief-field.png") });
  });

  test(`Saved quote recovery returns visible keyboard focus at ${width}px`, async ({ page }) => {
    const { id } = await createAndApprove(page);
    await upload(page, 0);
    await page.setViewportSize({ width, height: 900 });
    const card = quoteCard(page, 0);
    const [quote] = await readApi<{ id: string; notes: string | null }[]>(page, `/projects/${id}/quotes`);
    await card.getByRole("button", { name: "Edit PDF draft", exact: true }).click();
    await card.getByRole("textbox", { name: "Quote notes", exact: true }).fill("Unsaved recovery draft");
    let writes = 0;
    await page.route(`**/api/quotes/${quote.id}`, route => {
      if (route.request().method() === "PATCH") { writes++; return route.abort("failed"); }
      return route.continue();
    });
    await card.getByRole("button", { name: "Save draft", exact: true }).click();
    await card.getByRole("button", { name: "Check saved quote", exact: true }).click();
    const choice = card.getByRole("button", { name: "Use saved record", exact: true });
    await choice.focus();
    await page.keyboard.press("Enter");
    await expect(choice).toBeHidden();
    await expectVisibleFocus(page, card.getByRole("heading", { name: suppliers[0], exact: true }));
    await expect(card.getByRole("status", { name: "Quote recovery" })).toContainText("Saved record loaded");
    await expect(card.getByRole("textbox", { name: "Quote notes", exact: true })).toHaveValue(quote.notes ?? "");
    expect(writes).toBe(1);
    await page.screenshot({ path: test.info().outputPath("quote-recovered.png") });
    await page.keyboard.press("Tab");
    expect(await card.evaluate(element => element.contains(document.activeElement))).toBe(true);
  });
}
