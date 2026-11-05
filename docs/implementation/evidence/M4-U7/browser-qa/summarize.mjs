import {readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
const out=path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/,'$1'));
const report=JSON.parse(readFileSync(path.join(out,'results.json')));
const scenarios=[];
function visit(suite){for(const spec of suite.specs??[])for(const t of spec.tests)scenarios.push({scenario:spec.title,status:t.results.every(r=>r.status==='passed')?'PASS':'FAIL',duration_ms:t.results.reduce((s,r)=>s+r.duration,0),attempts:t.results.length});for(const child of suite.suites??[])visit(child);}
for(const suite of report.suites)visit(suite);
writeFileSync(path.join(out,'result-summary.json'),JSON.stringify({scenarios,stats:report.stats},null,2));
const counts=[];
for(const entry of readdirSync(path.join(out,'artifacts'),{withFileTypes:true})){
  if(!entry.isDirectory()||entry.name.startsWith('.'))continue;
  const dir=path.join(out,'artifacts',entry.name);
  const network=JSON.parse(readFileSync(path.join(dir,'sanitized-network.json')));
  const focus=JSON.parse(readFileSync(path.join(dir,'focus.json')));
  counts.push({scenario_directory:entry.name,analysis_posts:network.counts['POST /api/projects/:id/comparison/advice']??0,comparison_gets:network.counts['GET /api/projects/:id/comparison']??0,trusted_blurs:focus.filter(e=>e.type==='blur'&&e.trusted&&!e.focused).length,trusted_focuses:focus.filter(e=>e.type==='focus'&&e.trusted&&e.focused).length});
}
writeFileSync(path.join(out,'request-counts.json'),JSON.stringify(counts,null,2));
const hashes={};
function hashDir(dir){for(const item of readdirSync(dir,{withFileTypes:true})){if(item.name.startsWith('.')||item.name==='artifact-sha256.json'||item.name==='__pycache__')continue;const p=path.join(dir,item.name);if(item.isDirectory())hashDir(p);else hashes[path.relative(out,p).replaceAll('\\','/')]=createHash('sha256').update(readFileSync(p)).digest('hex');}}
hashDir(out);writeFileSync(path.join(out,'artifact-sha256.json'),JSON.stringify(hashes,null,2));
console.log(JSON.stringify({passed:scenarios.filter(s=>s.status==='PASS').length,failed:scenarios.filter(s=>s.status==='FAIL').length,artifacts:Object.keys(hashes).length}));
