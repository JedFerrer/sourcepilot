import { defineConfig } from '@playwright/test';
import path from 'node:path';
const output = process.env.SOURCEPILOT_QA_OUTPUT_DIR;
if (!output) throw new Error('Use this suite run.mjs launcher from the repository root.');
const archiveRoot = path.resolve(__dirname, '../../../../../.local-investigation-artifacts');
if (!path.resolve(output).startsWith(archiveRoot + path.sep)) {
  throw new Error('QA output must be inside the ignored investigation archive.');
}
export default defineConfig({
  testDir: '.', testMatch: 'qa.spec.ts', workers: 1, retries: 0, timeout: 120000,
  expect: { timeout: 15000 }, reporter: [['list'], ['json', { outputFile: path.join(output, 'results.json') }]],
  outputDir: path.join(output, 'artifacts'),
  use: { baseURL: 'http://127.0.0.1:13000', headless: false, channel: 'chrome', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure' },
  webServer: [
    { command: '.venv\\Scripts\\python.exe ../../apps/web/qa/comparison/verification-actions/qa_server.py', cwd: '../../../../../apps/api', env: { PYTHONPATH: '.' }, url: 'http://127.0.0.1:18000/health', timeout: 120000, reuseExistingServer: false },
    { command: 'pnpm exec next start --hostname 127.0.0.1 --port 13000', cwd: '../../../../../apps/web', url: 'http://127.0.0.1:13000', env: { API_ORIGIN: 'http://127.0.0.1:18000' }, timeout: 180000, reuseExistingServer: false },
  ],
});
