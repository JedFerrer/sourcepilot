import path from "node:path";
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { chromium, expect, test } from "@playwright/test";
import { captureReview, createAndApprove, viewStage, upload, quoteCard, confirm, comparison, selectQuote, inspectQuoteSource, closeQuoteSource } from "./helpers";

test("UX-U1 responsive stages, draft retention and guarded departure", async ({ page }) => {
  test.setTimeout(180_000);
  const project = await createAndApprove(page);
  await upload(page, 0);
  await confirm(page, 0);
  await upload(page, 1);
  await confirm(page, 1);
  await comparison(page);
  await selectQuote(page, 0);
  await page.addScriptTag({ path: createRequire(path.resolve("package.json")).resolve("axe-core/axe.min.js") });
  await quoteCard(page, 0).getByRole("button", { name: "Edit confirmed PDF quote", exact: true }).click();
  await quoteCard(page, 0).getByLabel("Unit price", { exact: true }).fill("4.75");
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    for (const stage of ["Brief", "Suppliers", "Quotes", "Comparison", "Decision"]) {
      await viewStage(page, stage);
      await expect(page.locator(".stage-panel:visible")).toHaveCount(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
      if (width === 1440 || width === 320) {
        const violations = await page.evaluate(async () => {
          const axe = (window as unknown as { axe: { run: (options: object) => Promise<{ violations: { id: string; impact: string; nodes: { target: string[] }[] }[] }> } }).axe;
          return (await axe.run({ runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] } })).violations;
        });
        await test.info().attach(`axe-${stage}-${width}`, { body: JSON.stringify(violations, null, 2), contentType: "application/json" });
        expect(violations).toEqual([]);
      }
      await page.screenshot({ path: test.info().outputPath(`${stage.toLowerCase()}-${width}.png`), fullPage: true });
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await viewStage(page, "Quotes");
  await inspectQuoteSource(page, 0);
  await page.screenshot({ path: test.info().outputPath("evidence-desktop.png"), fullPage: true });
  await closeQuoteSource(page);
  await page.setViewportSize({ width: 320, height: 900 });
  await inspectQuoteSource(page, 0);
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();
  await expect(quoteCard(page, 0).getByLabel("Unit price", { exact: true })).toHaveValue("4.75");
  await viewStage(page, "Decision");
  await page.getByRole("textbox", { name: "Decision notes", exact: true }).fill("Unsubmitted decision draft");
  await page.getByRole("combobox", { name: /Preferred supplier/ }).selectOption({ label: "Harbor Pouch Works" });
  await page.getByRole("button", { name: "Mark as Preferred Supplier", exact: true }).click();
  await captureReview(page, "decision");
  await page.getByRole("button", { name: "Keep reviewing", exact: true }).click();
  await page.getByRole("combobox", { name: /Preferred supplier/ }).selectOption("");

  await viewStage(page, "Brief");
  await page.goBack();
  await expect(page.getByRole("textbox", { name: "Decision notes", exact: true })).toHaveValue("Unsubmitted decision draft");
  await page.getByRole("link", { name: "All projects", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("dialog")).toContainText("Decision");
  await page.getByRole("button", { name: "Stay", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "Decision notes", exact: true })).toHaveValue("Unsubmitted decision draft");
  await page.getByRole("link", { name: "All projects", exact: true }).click();
  await page.getByRole("button", { name: /Discard.*leave/i }).click();
  await expect(page.getByRole("heading", { name: "Your sourcing projects" })).toBeVisible();
  await page.screenshot({ path: test.info().outputPath("dashboard-320.png"), fullPage: true });
  const profile = test.info().outputPath("chrome-400-profile");
  await mkdir(path.join(profile, "Default"), { recursive: true });
  await writeFile(path.join(profile, "Default", "Preferences"), JSON.stringify({ partition: { default_zoom_level: { x: Math.log(4) / Math.log(1.2) } } }));
  const zoom = await chromium.launchPersistentContext(profile, { channel: "chrome", headless: true, viewport: null, deviceScaleFactor: undefined, isMobile: undefined, args: ["--window-size=1280,1024"] });
  try {
    await zoom.addCookies(await page.context().cookies());
    const zoomPage = zoom.pages()[0];
    for (const stage of ["dashboard", "brief", "suppliers", "quotes", "comparison", "decision"]) {
      await zoomPage.goto(`http://127.0.0.1:13000${stage === "dashboard" ? "/" : `/projects/${project.id}?stage=${stage}`}`);
      await expect(zoomPage.getByRole("heading").first()).toBeVisible();
      const metrics = await zoomPage.evaluate(() => ({ width: innerWidth, dpr: devicePixelRatio, overflow: document.documentElement.scrollWidth > innerWidth + 1 }));
      expect(metrics.dpr).toBeGreaterThanOrEqual(3.9); expect(metrics.width).toBeLessThanOrEqual(330); expect(metrics.overflow).toBe(false);
      await test.info().attach(`zoom-${stage}`, { body: JSON.stringify(metrics), contentType: "application/json" });
      const capture = await (await zoom.newCDPSession(zoomPage)).send("Page.captureScreenshot", { format: "png", fromSurface: true, captureBeyondViewport: false });
      await writeFile(test.info().outputPath(`${stage}-400-percent.png`), Buffer.from(capture.data, "base64"));
    }
  } finally { await zoom.close(); }
  await page.goto(`/projects/${project.id}?stage=decision`);
  await page.getByRole("textbox", { name: "Decision notes", exact: true }).fill("Retain on browser Back");
  const nativeExit = page.waitForEvent("dialog");
  await page.evaluate(() => history.back());
  const warning = await nativeExit;
  expect(warning.type()).toBe("beforeunload");
  await warning.dismiss();
  await expect(page.getByRole("textbox", { name: "Decision notes", exact: true })).toHaveValue("Retain on browser Back");

});
