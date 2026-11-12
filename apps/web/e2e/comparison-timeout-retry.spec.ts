import { expect, test, type Request, type Route } from "@playwright/test";
import { writeFile } from "node:fs/promises";
import { setTimeout as delay } from "node:timers/promises";
import {
  comparison, confirm, createAndApprove, readApi, suppliers, upload, viewStage, type Project,
} from "./helpers";

test("comparison timeout and explicit retry", async ({ page }, info) => {
  const { id } = await createAndApprove(page);
  for (const index of [0, 1]) {
    await upload(page, index);
    await confirm(page, index);
  }
  await comparison(page);
  await viewStage(page, "Decision");
  const decision = page.getByRole("region", { name: "Decision", exact: true });
  const notes = "Keep Harbor as the preferred supplier.";
  await decision.getByRole("combobox", { name: /Preferred supplier/ }).selectOption({ label: suppliers[0] });
  await decision.getByLabel("Decision notes").fill(notes);
  await decision.getByRole("button", { name: "Mark as Preferred Supplier", exact: true }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Save preferred supplier", exact: true }).click();
  await expect(decision).toContainText("Preferred supplier saved.");
  await viewStage(page, "Comparison");
  await expect(page).toHaveURL(url => url.searchParams.get("stage") === "comparison");
  await page.reload();
  const section = page.getByRole("region", { name: "Comparison", exact: true });
  await expect(section.getByText("Comparison is current.", { exact: true })).toBeVisible();

  const projectPath = `/projects/${id}`;
  const comparisonPath = `${projectPath}/comparison`;
  const snapshot = await readApi<{ id: string; stale: boolean }>(page, comparisonPath);
  expect(snapshot.id).toMatch(/^[0-9a-f-]{36}$/);
  expect(snapshot.stale).toBe(false);
  const preference = await readApi<Project>(page, projectPath);
  expect(preference.preferred_supplier_id).toMatch(/^[0-9a-f-]{36}$/);
  expect(preference.preferred_supplier_name).toBe(suppliers[0]);
  expect(preference.decision_notes).toBe(notes);
  const table = section.getByRole("table");
  for (const name of suppliers.slice(0, 2)) {
    await expect(table.getByRole("columnheader", { name, exact: true })).toBeVisible();
  }
  const facts = await table.innerText();
  const advice = section.getByRole("region", { name: "Comparison analysis", exact: true });
  const alert = section.getByRole("alert");
  const retry = section.getByRole("button", { name: "Retry analysis", exact: true });
  async function checkPreservation() {
    await expect(table).toBeVisible();
    expect(await table.innerText()).toBe(facts);
    expect(await readApi(page, comparisonPath)).toEqual(snapshot);
    expect(await readApi<Project>(page, projectPath)).toMatchObject({
      preferred_supplier_id: preference.preferred_supplier_id,
      preferred_supplier_name: suppliers[0], decision_notes: notes,
    });
    await expect(page.locator(".project-context")).toContainText(`Saved preference: ${suppliers[0]}`);
  }

  const url = new URL(`/api${comparisonPath}/advice`, page.url()).href;
  const isAdvice = (r: Request) => r.method() === "POST" && r.url() === url;
  const posts: Request[] = [];
  const observe = (r: Request) => { if (isAdvice(r)) posts.push(r); };
  const timeout = { error: { code: "COMPARISON_ANALYSIS_TIMEOUT", message: "Analysis took too long. Please retry." } };
  const requestBody = { snapshot_id: snapshot.id };
  let fulfilled = 0;
  const intercept = async (route: Route) => {
    if (!isAdvice(route.request())) return route.continue();
    expect(route.request().postDataJSON()).toEqual(requestBody);
    fulfilled++;
    await route.fulfill({ status: 504, contentType: "application/json", json: timeout });
  };
  const idleMs = 3000;
  page.on("request", observe);
  try {
    await page.route(url, intercept, { times: 1 });
    try {
      const [failure] = await Promise.all([
        page.waitForResponse(r => isAdvice(r.request())),
        section.getByRole("button", { name: "Analyze Comparison", exact: true }).click(),
      ]);
      expect(failure.status()).toBe(504);
      expect(await failure.json()).toEqual(timeout);
      expect(fulfilled).toBe(1);
      await expect(alert).toBeVisible();
      await expect(alert).toHaveText(timeout.error.message);
      await expect(retry).toBeEnabled();
      await expect(advice).toHaveCount(0);
      await checkPreservation();
      // Traverse with actual keyboard input, even if the renamed button retained focus.
      await page.keyboard.press("Shift+Tab");
      for (let i = 0; i < 80; i++) {
        await page.keyboard.press("Tab");
        if (await retry.evaluate(el => el === document.activeElement)) break;
      }
      await expect(retry).toBeFocused();
      expect(await retry.evaluate(el => el.matches(":focus-visible"))).toBe(true);
      await expect(retry).toHaveCSS("outline-style", "solid");
      await page.screenshot({ path: info.outputPath("synthetic-504-focus.png") });
      await delay(idleMs);
      expect(posts).toHaveLength(1);
      expect(posts[0]).toBe(failure.request());
      await expect(alert).toHaveText(timeout.error.message);
      await expect(advice).toHaveCount(0);
    } finally {
      await page.unroute(url, intercept);
    }

    await expect(retry).toBeFocused();
    expect(posts).toHaveLength(1);
    const [success] = await Promise.all([
      page.waitForResponse(r => isAdvice(r.request())),
      page.keyboard.press("Enter"),
    ]);
    expect(success.status()).toBe(200);
    expect(success.fromServiceWorker()).toBe(false);
    const body = await success.json();
    expect(body.snapshot_id).toBe(snapshot.id);
    expect(body.run_id).toMatch(/^[0-9a-f-]{36}$/);
    await expect(advice.getByRole("heading", { name: "No supplier suggested yet" })).toBeVisible();
    await expect(advice).toContainText("No single supplier is suggested; review the cited tradeoffs before choosing.");
    await expect(alert).toHaveCount(0);
    await checkPreservation();
    await page.screenshot({ path: info.outputPath("real-retry.png") });
    await delay(idleMs);
    expect(posts).toHaveLength(2);
    expect(posts[1]).toBe(success.request());
    expect(posts.map(r => r.postDataJSON())).toEqual([requestBody, requestBody]);
    expect(fulfilled).toBe(1);
    await writeFile(info.outputPath("observations.json"), JSON.stringify({
      snapshot: snapshot.id, preference: preference.preferred_supplier_id, idleMs,
      synthetic: { status: 504, ...timeout, postsBeforeRetry: 1, keyboardFocus: true },
      real: { status: success.status(), run: body.run_id, postsAfterRetry: posts.length },
      preserved: ["comparison response", "displayed table", "saved supplier and notes"],
    }, null, 2));
  } finally {
    page.off("request", observe);
  }
});
