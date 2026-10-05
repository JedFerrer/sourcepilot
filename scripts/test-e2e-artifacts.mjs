// Generate a real failure with a known dummy cookie, then inspect the CI upload bundle.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const require = createRequire(path.resolve("apps/web/package.json"));
const directory = mkdtempSync(path.join(tmpdir(), "sourcepilot-artifact-regression-"));
function run(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, encoding: "utf8" });
  if (result.error) throw result.error;
  return result;
}
try {
  const playwright = require.resolve("@playwright/test");
  writeFileSync(path.join(directory, "playwright.config.cjs"), `module.exports = {
    testDir: '.', outputDir: './test-results', workers: 1, retries: 0,
    reporter: [['html', { outputFolder: './playwright-report', open: 'never' }]],
    use: { trace: 'retain-on-failure', screenshot: 'only-on-failure' }
  };`);
  writeFileSync(path.join(directory, "artifact.spec.cjs"), `
    const { test, expect } = require(${JSON.stringify(playwright)});
    const { createServer } = require('node:http');
    test('Artifact security probe failure', async ({ page }, info) => {
      const token = 'M5U3_DUMMY_' + 'x'.repeat(32);
      const server = createServer((req, res) => {
        res.setHeader('Set-Cookie', 'sourcepilot_demo_session=' + token + '; Path=/; HttpOnly');
        res.end('<html><body><h1>Artifact security probe</h1></body></html>');
      });
      await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
      try {
        const origin = 'http://127.0.0.1:' + server.address().port;
        await test.step('Anonymous session network diagnostics', async () => {
          await page.goto(origin);
          await page.request.get(origin);
          const state = await page.context().storageState();
          await info.attach('browser-cookie-storage', { body: JSON.stringify(state), contentType: 'application/json' });
          await info.attach('raw-headers', { body: 'Cookie: sourcepilot_demo_session=' + token + '\\nSet-Cookie: sourcepilot_demo_session=' + token + '; Path=/; HttpOnly', contentType: 'text/plain' });
          await info.attach('equivalent-token', { body: JSON.stringify({ sessionToken: token,
            encoded: Buffer.from(token).toString('base64') }), contentType: 'application/json' });
          await info.attach('encoded-buffer', { body: JSON.stringify({ buffer:
            Buffer.from('prefixed captured session: ' + token).toString('base64') }), contentType: 'application/json' });
        });
        expect(false, 'Artifact security probe failure').toBe(true);
      } finally { await new Promise(resolve => server.close(resolve)); }
    });
  `);
  const failure = run(process.execPath, [require.resolve("@playwright/test/cli"), "test", "--config", path.join(directory, "playwright.config.cjs")], directory);
  assert.equal(failure.status, 1, failure.stderr || "Expected a deliberately failed Playwright probe");
  for (const args of [
    ["tests.e2e_support.artifacts", "regression", "--web-directory", directory],
    ["tests.test_e2e_artifacts", directory],
  ]) {
    const result = run("uv", ["--no-cache", "run", "--no-sync", "python", "-m", ...args], path.resolve("apps/api"));
    if (result.status !== 0) process.stderr.write(failure.stdout + failure.stderr);
    assert.equal(result.status, 0, result.stderr);
    process.stdout.write(result.stdout);
  }
  const { chromium } = require("@playwright/test");
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.join(directory, "sanitized-preview/playwright-report/index.html")).href);
    await page.getByText("Artifact security probe failure", { exact: true }).first().waitFor();
    await page.getByRole("link", { name: /Artifact security probe failure/ }).first().click();
    await page.getByText("Anonymous session network diagnostics", { exact: false }).first().waitFor();
    process.stdout.write("Sanitized HTML report renders the failing stage and test steps.\n");
  } finally {
    await browser.close();
  }
} finally {
  // Only the exact freshly created temporary directory is removed.
  assert.equal(path.dirname(path.resolve(directory)), path.resolve(tmpdir()));
  assert.ok(path.basename(directory).startsWith("sourcepilot-artifact-regression-"));
  rmSync(directory, { recursive: true, force: true });
}
