import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { connect, type Socket } from "node:net";
import path from "node:path";
import { advice, approveShortlist, comparison, confirm, createAndApprove, pdfDirectory, quoteCard, readApi, upload, type Project, type Quote } from "./helpers";

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
  await upload(page, 0);
  const quote = (await readApi<Quote[]>(page, `/projects/${id}/quotes`))[0];
  await test.step("Independent visitor receives no project and cannot fetch it", async () => {
    const other = await browser.newContext();
    try {
      const second = await other.newPage();
      await second.goto("http://127.0.0.1:13000/");
      await expect(second.getByText("No projects yet.", { exact: true })).toBeVisible();
      await expect(second.getByRole("link").filter({ hasText: name })).toBeHidden();
      const response = await second.request.get(`http://127.0.0.1:13000/api/projects/${id}`);
      expect(response.status()).toBe(404);
      expect((await second.request.patch(`/api/projects/${id}`, { data: { name: "Denied" } })).status()).toBe(404);
      expect((await second.request.get(`/api/projects/${id}/quotes`)).status()).toBe(404);
      expect((await second.request.get(`/api/quotes/${quote.id}`)).status()).toBe(404);
      expect((await second.request.patch(`/api/quotes/${quote.id}`, { data: { notes: "Denied" } })).status()).toBe(404);
      expect((await second.request.post(`/api/quotes/${quote.id}/confirm`)).status()).toBe(404);
      await second.goto(`http://127.0.0.1:13000/projects/${id}`);
      await expect(second.getByText("Project not found in this demo session.", { exact: true })).toBeVisible();
    } finally { await other.close(); }
  });
});


test("security request rejection preserves state and manual entry", async ({ page }) => {
  const { id } = await createAndApprove(page);
  const before = await readApi<Project>(page, `/projects/${id}`);
  const oversized = await page.request.patch(`/api/projects/${id}`, {
    headers: { "Content-Type": "application/json" }, data: JSON.stringify({ name: "x".repeat(1_000_001) }),
  });
  expect.soft(oversized.status()).toBe(413);
  if (oversized.status() === 413) {
    expect(await oversized.json()).toEqual({ error: { code: "REQUEST_TOO_LARGE", message: "Request body is too large." } });
  }
  expect(await readApi<Project>(page, `/projects/${id}`)).toEqual(before);
  const suppliers = await readApi<{ suppliers: { id: string; shortlisted: boolean }[] }>(page, `/projects/${id}/suppliers`);
  const supplier = suppliers.suppliers.find((item) => item.shortlisted)!;
  const malformed = await page.request.post(`/api/projects/${id}/quotes/upload`, { multipart: {
    supplier_id: supplier.id, file: { name: "quote.pdf", mimeType: "application/pdf", buffer: Buffer.from("%PDF-broken") },
  } });
  expect(malformed.status()).toBe(422);
  expect((await malformed.json()).error.code).toBe("INVALID_PDF");
  expect(await readApi<Quote[]>(page, `/projects/${id}/quotes`)).toEqual([]);
  await expect(quoteCard(page, 0).getByRole("button", { name: "Create manual quote", exact: true })).toBeEnabled();
  const valid = await page.request.patch(`/api/projects/${id}`, { data: { name: "Still usable" } });
  expect(valid.status()).toBe(200);
});

test("expired isolated session cannot recover its old project", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("No projects yet.", { exact: true })).toBeVisible();
  const created = await page.request.post("/api/projects", { data: {
    name: "M6-U3 designated expiry fixture", original_request: "Isolated expiry regression",
  } });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  execFileSync("uv", ["run", "--no-sync", "python", "-m", "tests.e2e_support.expire_session", id],
    { cwd: "../api", stdio: "pipe", timeout: 20_000 });
  expect((await page.request.get(`/api/projects/${id}`)).status()).toBe(401);
  expect((await page.request.post("/api/demo-session")).status()).toBe(204);
  expect((await page.request.get(`/api/projects/${id}`)).status()).toBe(404);
  expect((await page.request.patch(`/api/projects/${id}`, { data: { name: "Denied" } })).status()).toBe(404);
  expect(await readApi<Project[]>(page, "/projects")).toEqual([]);
});

test("real proxy accepts POST and PDF upload with and without Expect", async ({ page }) => {
  const projectBody = JSON.stringify({ name: "Expect transport regression", original_request: "Source bags" });
  const oversizedBody = JSON.stringify({ name: "x".repeat(1_000_001), original_request: "Source bags" });
  const pdf = readFileSync(path.join(pdfDirectory, "harbor_primary.pdf"));
  let uploadBody: Buffer | undefined;
  let uploadSupplier: string | undefined;
  for (const withExpect of [false, true]) {
    // Separate approved projects avoid duplicate-upload rejection; payload bytes stay identical.
    const { id } = await createAndApprove(page);
    const headers: Record<string, string> = withExpect ? { Expect: "100-continue" } : {};
    const created = await page.request.post("/api/projects", {
      headers: { ...headers, "Content-Type": "application/json" }, data: projectBody,
    });
    expect(created.status()).toBe(201);
    expect(await created.json()).toMatchObject(JSON.parse(projectBody));
    const candidates = await readApi<{ suppliers: { id: string; name: string }[] }>(page, `/projects/${id}/suppliers`);
    const supplierId = candidates.suppliers.find((item) => item.name === "Harbor Pouch Works")!.id;
    if (!uploadBody) {
      uploadSupplier = supplierId;
      uploadBody = Buffer.concat([
        Buffer.from(`--expect-boundary\r\nContent-Disposition: form-data; name="supplier_id"\r\n\r\n${supplierId}\r\n` +
          '--expect-boundary\r\nContent-Disposition: form-data; name="file"; filename="harbor_primary.pdf"\r\nContent-Type: application/pdf\r\n\r\n'),
        pdf, Buffer.from("\r\n--expect-boundary--\r\n"),
      ]);
    }
    expect(supplierId).toBe(uploadSupplier);
    const uploaded = await page.request.post(`/api/projects/${id}/quotes/upload`, {
      headers: { ...headers, "Content-Type": "multipart/form-data; boundary=expect-boundary" }, data: uploadBody,
    });
    expect(uploaded.status()).toBe(201);
    expect(uploaded.headers()["content-type"]).toContain("application/json");
    const quoteId = (await uploaded.json()).quote.id;
    await expect.poll(async () => (await readApi<Quote>(page, `/quotes/${quoteId}`)).status).toBe("NEEDS_REVIEW");
    const before = await readApi<Project[]>(page, "/projects");
    for (let attempt = 0; attempt < 3; attempt++) {
      const oversized = await page.request.post("/api/projects", {
        headers: { ...headers, "Content-Type": "application/json" }, data: oversizedBody,
      });
      expect(oversized.status()).toBe(413);
      expect(oversized.headers()["connection"]).toBe("close");
      expect(await oversized.json()).toEqual({ error: { code: "REQUEST_TOO_LARGE", message: "Request body is too large." } });
      expect(await readApi<Project[]>(page, "/projects")).toEqual(before);
    }
  }
});

for (const withExpect of [false, true]) {
  test(`incomplete oversized uploads close the real socket and recover (Expect: ${withExpect})`, async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("No projects yet.", { exact: true })).toBeVisible();
    const cookies = await page.context().cookies();
    const cookie = cookies.map(({ name, value }) => `${name}=${value}`).join("; ");
    let socket: Socket | undefined;
    try {
      for (let attempt = 0; attempt < 3; attempt++) {
        await new Promise<void>((resolve, reject) => {
          let received = "";
          let continued = false;
          socket = connect(13000, "127.0.0.1", () => {
            socket!.write("POST /api/projects HTTP/1.1\r\nHost: 127.0.0.1:13000\r\n" +
              `Cookie: ${cookie}\r\nContent-Type: application/json\r\nContent-Length: 1000002\r\n` +
              "Connection: keep-alive\r\n" + (withExpect ? "Expect: 100-continue\r\n" : "") +
              "\r\n" + (withExpect ? "" : "{"));
          });
          socket.setEncoding("utf8");
          socket.on("error", reject);
          socket.on("data", (chunk: string) => {
            received += chunk;
            if (withExpect && !continued && received.includes("HTTP/1.1 100 Continue\r\n\r\n")) {
              continued = true;
              socket!.write("{");
            }
          });
          // A raw socket observes the server's FIN without the HTTP client's
          // automatic disposal on Connection: close. Never finish the upload.
          socket.on("end", () => {
            try {
              if (withExpect) expect(continued).toBe(true);
              const response = received.replace(/^HTTP\/1\.1 100 Continue\r\n\r\n/, "");
              const boundary = response.indexOf("\r\n\r\n");
              const headers = response.slice(0, boundary);
              const body = response.slice(boundary + 4);
              expect(headers).toMatch(/^HTTP\/1\.1 413 /);
              expect(headers).toMatch(/\r\nconnection: close\r\n/i);
              expect(headers).toMatch(/\r\ncontent-type: application\/json\r\n/i);
              expect(JSON.parse(body)).toEqual({
                error: { code: "REQUEST_TOO_LARGE", message: "Request body is too large." },
              });
              resolve();
            } catch (error) { reject(error); }
          });
        });
        // Retain the same Playwright request context and its normal connection pool.
        expect(await readApi<Project[]>(page, "/projects")).toEqual([]);
      }
    } finally { socket?.destroy(); }
  });
}
