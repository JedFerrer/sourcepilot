// Keep the targeted suite independent, including when the golden path fails.
import { spawn } from "node:child_process";
import { createWriteStream, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const mode = process.argv[2];
if (!["all", "repeat", "targeted"].includes(mode)) {
  throw new Error("Use all, repeat, or targeted.");
}
async function run(args, label) {
  const storage = mkdtempSync(path.join(tmpdir(), "sourcepilot-e2e-documents-"));
  const logs = path.resolve("apps/web/e2e-logs");
  mkdirSync(logs, { recursive: true });
  const log = createWriteStream(path.join(logs, `${label}.log`));
  // pnpm.cmd needs a shell on Windows; these arguments are fixed, never user text.
  try {
    return await new Promise((resolve) => {
      const child = spawn("pnpm", ["--filter", "@sourcepilot/web", "exec", "playwright", "test", ...args,
        "--workers=1", "--retries=0"], {
        stdio: ["inherit", "pipe", "pipe"], shell: process.platform === "win32",
        env: { ...process.env, E2E_DOCUMENT_STORAGE_DIR: storage },
      });
      child.stdout.on("data", (data) => { process.stdout.write(data); log.write(data); });
      child.stderr.on("data", (data) => { process.stderr.write(data); log.write(data); });
      child.on("error", (error) => { console.error(error.message); log.write(error.message); resolve(1); });
      child.on("close", (code) => resolve(code ?? 1));
    });
  } finally {
    await new Promise((resolve) => log.end(resolve));
    // Only the exact directory returned by mkdtemp above can be removed.
    rmSync(storage, { recursive: true, force: true });
  }
}
let result = 0;
if (mode !== "targeted") {
  result = await run(["golden-path.spec.ts", ...(mode === "repeat" ? ["--repeat-each=3"] : [])], "golden");
}
if (mode !== "repeat") {
  const targeted = await run(["targeted.spec.ts"], "targeted");
  result = result || targeted;
}
process.exitCode = result;
