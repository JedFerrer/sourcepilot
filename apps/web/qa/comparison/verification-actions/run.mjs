import { readFileSync, writeFileSync, mkdirSync, mkdtempSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { spawnSync, execFileSync } from 'node:child_process';
import path from 'node:path';
const root = process.cwd();
const source = path.join(root, 'apps/web/qa/comparison/verification-actions');
const archive = path.join(root, '.local-investigation-artifacts/M4-U7/reusable-qa/verification-actions');
mkdirSync(archive, {recursive:true});
const out = mkdtempSync(path.join(archive, 'run-'));
const paths=execFileSync('git',['ls-files','--cached','--others','--exclude-standard'],{cwd:root,encoding:'utf8'}).trim().split('\n').filter(p=>p.startsWith('apps/api/tests/fixtures/comparison_advice/')||p.startsWith('apps/web/qa/comparison/verification-actions/')||p.startsWith('apps/api/sourcepilot/')||p.startsWith('apps/web/app/')||p.startsWith('apps/web/components/')||p.startsWith('apps/web/lib/')||p.startsWith('apps/api/tests/e2e_support/'));
const files = Object.fromEntries(paths.map(p=>[p,true]));
const hashes = Object.fromEntries(Object.keys(files).map(p => [p,createHash('sha256').update(readFileSync(path.join(root,p))).digest('hex')]));
writeFileSync(path.join(out,'source-identity.json'),JSON.stringify({head:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),source_sha256:hashes,paid_calls:0},null,2));
const env = {...process.env, SOURCEPILOT_QA_OUTPUT_DIR: out};
for (const key of Object.keys(env)) if (/OPENAI|LANGSMITH|LANGFUSE|OTEL|SOURCEPILOT_AI|SOURCEPILOT_ANALYSIS|NEXT_PUBLIC_SOURCEPILOT_ANALYSIS/.test(key)) delete env[key];
const content = readFileSync(path.join(root,'.env'),'utf8');
for (const key of ['DATABASE_URL','TEST_DATABASE_URL','E2E_DATABASE_URL']) {
  const match = content.match(new RegExp('^'+key+'=(.*)$','m'));
  env[key] = match ? match[1].trim().replace(/^['"]|['"]$/g,'') : `postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/${key==='DATABASE_URL'?'sourcepilot':key==='TEST_DATABASE_URL'?'sourcepilot_test':'sourcepilot_e2e'}`;
}
env.E2E_DOCUMENT_STORAGE_DIR = path.join(out, 'documents');
mkdirSync(env.E2E_DOCUMENT_STORAGE_DIR,{recursive:true});
const args = ['../../../../../apps/web/node_modules/@playwright/test/cli.js','test','--config=qa.config.ts','--max-failures=1', ...process.argv.slice(2)];
const result = spawnSync(process.execPath,args,{cwd:source,env,encoding:'utf8',stdio:'pipe'});
writeFileSync(path.join(out,'stdout.log'), result.stdout ?? '');
writeFileSync(path.join(out,'stderr.log'), result.stderr ?? '');
process.stdout.write(result.stdout ?? '');
process.stderr.write(result.stderr ?? '');
writeFileSync(path.join(out,'source-after.json'),JSON.stringify({unchanged: Object.entries(hashes).every(([p,h])=> createHash('sha256').update(readFileSync(path.join(root,p))).digest('hex')===h), exit:result.status},null,2));
process.exitCode=result.status ?? 1;


