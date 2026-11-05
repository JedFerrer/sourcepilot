import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
const root = process.cwd();
const out = path.join(root, 'docs/implementation/evidence/M4-U7/browser-qa');
const reference = JSON.parse(readFileSync(path.join(out, '../linux-corrections/final-source-manifest.json')));
const hashes = Object.fromEntries(Object.keys(reference.source_sha256).map(p => [p, createHash('sha256').update(readFileSync(path.join(root,p))).digest('hex')]));
const mismatch = Object.keys(hashes).filter(p => hashes[p] !== reference.source_sha256[p]);
writeFileSync(path.join(out,'source-identity.json'), JSON.stringify({ base_commit: reference.base_commit, source_sha256: hashes, mismatches_with_reviewed_final: mismatch, paid_calls: 0 }, null, 2));
if(mismatch.length) throw new Error('Reviewed source mismatch: '+mismatch.join(', '));
const env = {...process.env};
for (const key of Object.keys(env)) if (/OPENAI|LANGSMITH|LANGFUSE|OTEL|SOURCEPILOT_AI|SOURCEPILOT_ANALYSIS|NEXT_PUBLIC_SOURCEPILOT_ANALYSIS/.test(key)) delete env[key];
const content = readFileSync(path.join(root,'.env'),'utf8');
for (const key of ['DATABASE_URL','TEST_DATABASE_URL','E2E_DATABASE_URL']) {
  const match = content.match(new RegExp('^'+key+'=(.*)$','m'));
  env[key] = match ? match[1].trim().replace(/^['"]|['"]$/g,'') : `postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/${key==='DATABASE_URL'?'sourcepilot':key==='TEST_DATABASE_URL'?'sourcepilot_test':'sourcepilot_e2e'}`;
}
env.E2E_DOCUMENT_STORAGE_DIR = path.join(root,'apps/web/.qa-documents');
mkdirSync(env.E2E_DOCUMENT_STORAGE_DIR,{recursive:true});
const args = ['../../../../../apps/web/node_modules/@playwright/test/cli.js','test','--config=qa.config.ts', ...process.argv.slice(2)];
const result = spawnSync(process.execPath,args,{cwd:out,env,stdio:'inherit'});
writeFileSync(path.join(out,'source-after.json'),JSON.stringify({unchanged: Object.entries(hashes).every(([p,h])=> createHash('sha256').update(readFileSync(path.join(root,p))).digest('hex')===h), exit:result.status},null,2));
process.exitCode=result.status ?? 1;

