import { defineConfig } from '../../../../../apps/web/node_modules/@playwright/test';
export default defineConfig({
  testDir: '.', testMatch: 'qa.spec.ts', workers: 1, retries: 0, timeout: 120000,
  expect: { timeout: 15000 }, reporter: [['list'], ['json', { outputFile: 'results.json' }]],
  outputDir: 'artifacts',
  use: { baseURL: 'http://127.0.0.1:13000', headless: false, channel: 'chrome', viewport: { width: 1440, height: 1000 }, screenshot: 'only-on-failure' },
  webServer: [
    { command: '.venv\\Scripts\\python.exe ../../docs/implementation/evidence/M4-U7/browser-qa/qa_server.py', cwd: '../../../../../apps/api', env: { PYTHONPATH: '.' }, url: 'http://127.0.0.1:18000/health', timeout: 120000, reuseExistingServer: false },
    { command: 'node fault-proxy.mjs', url: 'http://127.0.0.1:18001/__qa/health', timeout: 30000, reuseExistingServer: false },
    { command: 'pnpm exec next start --hostname 127.0.0.1 --port 13000', cwd: '../../../../../apps/web', url: 'http://127.0.0.1:13000', env: { API_ORIGIN: 'http://127.0.0.1:18001' }, timeout: 180000, reuseExistingServer: false },
  ],
});



