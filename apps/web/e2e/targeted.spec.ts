import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { advice, approveShortlist, comparison, confirm, createAndApprove, quoteCard, readApi, upload, type Project, type Quote } from "./helpers";

test("corrected quote retains PDF provenance", async ({ page }) => {
  const { id } = await createAndApprove(page);
  await test.step("Correct extracted price and retain original evidence", async () => {
    await upload(page, 0);
    const original = (await readApi<Quote[]>(page, `/projects/${id}/quotes`))[0].values.unit_price.current_value;
    const card = quoteCard(page, 0);
    await card.getByRole("button", { name: "Edit PDF draft", exact: true }).click();
    await card.getByLabel("Unit price", { exact: true }).fill("4.50");
    await card.getByRole("button", { name: "Save draft", exact: true }).click();
    const field = card.locator("dl > div").filter({ has: page.locator("dt").filter({ hasText: /^Unit price$/ }) });
    await expect(field).toContainText("Current draft value: 4.50");
    await expect(field).toContainText("Current origin: USER CORRECTED");
    await expect(field.getByRole("blockquote")).toContainText(`USD ${original}`);
    const changed = (await readApi<Quote[]>(page, `/projects/${id}/quotes`))[0].values.unit_price;
    expect(changed.current_value).toBe("4.50");
    expect(changed.ai_extracted_value).toBe(original);
    await confirm(page, 0);
    await upload(page, 1);
    await confirm(page, 1);
    await comparison(page);
    const row = page.getByRole("region", { name: "Comparison", exact: true }).getByRole("row")
      .filter({ has: page.getByRole("rowheader", { name: "Unit price", exact: true }) });
    await expect(row).toContainText("USD 4.50");
    await row.getByText("Source details", { exact: true }).first().click();
    await expect(row).toContainText("User Corrected");
    await expect(row).toContainText(`Original extracted value: ${original}`);
  });
});

test("failed PDF supports manual fallback and comparison", async ({ page }) => {
  await createAndApprove(page);
  await test.step("Unsupported scan fails and user enters a manual draft", async () => {
    await upload(page, 0, "image_only.pdf");
    const card = quoteCard(page, 0);
    await card.getByRole("button", { name: "Enter quote manually", exact: true }).click();
    await card.getByLabel("Quoted quantity", { exact: true }).fill("2000");
    await card.getByLabel("Unit price", { exact: true }).fill("4.50");
    await card.getByLabel("Original currency (three-letter code)", { exact: true }).fill("USD");
    await card.getByRole("button", { name: "Save manual draft", exact: true }).click();
    await expect(card).toContainText("Status: NEEDS REVIEW");
    await confirm(page, 0);
    await expect(card).toContainText("Confirmed manual quote");
    await upload(page, 1);
    await confirm(page, 1);
    await comparison(page);
    await expect(page.getByRole("region", { name: "Comparison", exact: true })).toContainText("USD 4.50");
  });
});

test("abandoned PROCESSING becomes retryable and succeeds", async ({ page }) => {
  const { id } = await createAndApprove(page);
  let quoteId: string;
  let documentId: string;
  await test.step("Abandon only the designated first processing attempt", async () => {
    const uploaded = page.waitForResponse((response) => response.url().endsWith(`/projects/${id}/quotes/upload`)
      && response.request().method() === "POST");
    await upload(page, 0, "harbor_primary.pdf", true);
    const body = await (await uploaded).json();
    documentId = body.document.id;
    quoteId = body.quote.id;
    const quotes = await readApi<Quote[]>(page, `/projects/${id}/quotes`);
    expect(quotes).toHaveLength(1);
    const quote = quotes[0];
    expect(quote.id).toBe(quoteId);
    expect(quote.status).toBe("PROCESSING");
    expect(quote.processing?.attempts).toBe(1);
    await expect(quoteCard(page, 0).getByRole("button", { name: "Retry processing", exact: true })).toBeHidden();
    execFileSync("uv", ["run", "--no-sync", "python", "-m", "tests.e2e_support.age_attempt", id, quote.id],
      { cwd: "../api", stdio: "pipe", timeout: 20_000 });
  });
  await test.step("Normal poll exposes stale state; browser retries the real worker", async () => {
    const card = quoteCard(page, 0);
    await expect(card).toContainText("Status: STALE PROCESSING");
    await expect(card.getByRole("alert")).toContainText("Processing was interrupted. Retry quote processing.");
    await card.getByRole("button", { name: "Retry processing", exact: true }).click();
    await expect(card).toContainText("Status: NEEDS REVIEW", { timeout: 30_000 });
    const quotes = await readApi<Quote[]>(page, `/projects/${id}/quotes`);
    expect(quotes).toHaveLength(1);
    const quote = quotes[0];
    expect(quote.id).toBe(quoteId);
    expect(quote.processing?.attempts).toBe(2);
    expect(quote.values.unit_price.current_origin).toBe("AI_EXTRACTED");
    execFileSync("uv", ["run", "--no-sync", "python", "-m", "tests.e2e_support.age_attempt", id, quoteId,
      "--verify-document", documentId], { cwd: "../api", stdio: "pipe", timeout: 20_000 });
    await confirm(page, 0);
    await expect(card).toContainText("Status: CONFIRMED");
  });
});

test("Brief edit routes stale suppliers through existing refresh", async ({ page }) => {
  const { id } = await createAndApprove(page);
  await test.step("Edit approved Brief, then rediscover and approve shortlist", async () => {
    const brief = page.getByRole("region", { name: "Sourcing Brief", exact: true });
    await brief.getByLabel("Destination", { exact: true }).fill("Melbourne");
    await brief.getByRole("button", { name: "Save Brief", exact: true }).click();
    // Existing complete edits retain Brief approval but invalidate supplier evaluations.
    await expect(brief).toContainText("Readiness: Approved");
    const section = page.getByRole("region", { name: "Suppliers", exact: true });
    await expect(section.getByText("Evaluations need refreshing after the Brief changed.").first()).toBeVisible();
    expect((await readApi<Project>(page, `/projects/${id}`)).workflow.suppliers_stale).toBe(true);
    await section.getByRole("button", { name: "Re-discover and re-evaluate", exact: true }).click();
    await expect(section.getByText("Evaluations need refreshing after the Brief changed.").first()).toBeHidden();
    await approveShortlist(page);
    expect((await readApi<Project>(page, `/projects/${id}`)).workflow.suppliers_stale).toBe(false);
  });
});

test("confirmed quote edit invalidates comparison and advice", async ({ page }) => {
  const { id } = await createAndApprove(page);
  for (const index of [0, 1]) { await upload(page, index); await confirm(page, index); }
  await comparison(page);
  await advice(page, id);
  await test.step("Correct confirmed quote and enforce comparison regeneration", async () => {
    const card = quoteCard(page, 0);
    await card.getByRole("button", { name: "Edit confirmed PDF quote", exact: true }).click();
    await card.getByLabel("Unit price", { exact: true }).fill("4.65");
    await card.getByRole("button", { name: "Save quote", exact: true }).click();
    // M3-U9 explicitly retains confirmation when the user saves a correction.
    await expect(card).toContainText("Current confirmed value: 4.65");
    await expect(card).toContainText("Status: CONFIRMED");
    const section = page.getByRole("region", { name: "Comparison", exact: true });
    await expect(section).toContainText("Comparison outdated");
    await expect(section.getByRole("region", { name: "Comparison analysis", exact: true })).toBeHidden();
    await expect(section.getByRole("button", { name: "Analyze Comparison", exact: true })).toBeDisabled();
    await expect(section.getByRole("button", { name: "Regenerate Comparison", exact: true })).toBeEnabled();
    await comparison(page, true);
    await expect(section).toContainText("USD 4.65");
    await advice(page, id);
  });
});

test("another anonymous visitor cannot access this project", async ({ page, browser }) => {
  const { id, name } = await createAndApprove(page);
  await test.step("Independent visitor receives no project and cannot fetch it", async () => {
    const other = await browser.newContext();
    try {
      const second = await other.newPage();
      await second.goto("http://127.0.0.1:13000/");
      await expect(second.getByText("No projects yet.", { exact: true })).toBeVisible();
      await expect(second.getByRole("link").filter({ hasText: name })).toBeHidden();
      const response = await second.request.get(`http://127.0.0.1:13000/api/projects/${id}`);
      expect(response.status()).toBe(404);
      await second.goto(`http://127.0.0.1:13000/projects/${id}`);
      await expect(second.getByText("Project not found in this demo session.", { exact: true })).toBeVisible();
    } finally { await other.close(); }
  });
});
