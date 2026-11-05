import { test, expect, type Page } from '../../../../../apps/web/node_modules/@playwright/test';
import { writeFileSync } from 'node:fs';
import { createAndApprove, upload, confirm, comparison, readApi, quoteCard, approveShortlist } from '../../../../../apps/web/e2e/helpers';
const region = (p: Page) => p.getByRole('region',{name:'Comparison',exact:true});
const output = (p: Page) => p.getByRole('region',{name:'Comparison analysis',exact:true});
const button = (p: Page, name: string) => region(p).getByRole('button',{name,exact:true});
let requests: {method:string;path:string}[];
test.beforeEach(async ({page}) => {
  requests=[];
  await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});
  page.on('request',r=>{const u=new URL(r.url()); if(u.pathname.startsWith('/api/')) requests.push({method:r.method(),path:u.pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/g,':id')});});
  await page.addInitScript(()=>{
    (window as any).__focus=[];
    for(const type of ['focus','blur']) window.addEventListener(type,e=>(window as any).__focus.push({type,trusted:e.isTrusted,focused:document.hasFocus()}));
  });
});
test.afterEach(async ({page},info)=>{
  const counts: Record<string,number>={}; for(const r of requests){const k=r.method+' '+r.path;counts[k]=(counts[k]??0)+1;}
  writeFileSync(info.outputPath('sanitized-network.json'),JSON.stringify({counts,sequence:requests},null,2));
  if(!page.isClosed()) {
    await page.bringToFront();
    writeFileSync(info.outputPath('focus.json'),JSON.stringify(await page.evaluate(()=>(window as any).__focus),null,2));
    await page.screenshot({path:info.outputPath('final.png'),fullPage:true});
    await region(page).scrollIntoViewIfNeeded();
    await page.screenshot({path:info.outputPath('comparison-viewport.png')});
    if(await output(page).isVisible()) await output(page).screenshot({path:info.outputPath('analysis.png')});
    writeFileSync(info.outputPath('visible-text.txt'),await page.locator('body').innerText());
  }
});
for(const outcome of ['success','failure'])test(`held ${outcome} survives failed pending verification and repeated reads`,async({page})=>{
  const id=await setup(page),g=gate(),readGate=gate();let posts=0,reads=0;
  await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const result=outcome==='success'?await r.fetch():null;await g.promise;if(result)await r.fulfill({response:result});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;await readGate.promise;await r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Freshness verification failed.'}}});});
  await nativeFocus(page);await nativeFocus(page);expect(reads).toBe(2);expect(posts).toBe(1);await expect(region(page)).toContainText('Analysis is pending while we verify');await expect(output(page)).toBeHidden();
  g.release();readGate.release();await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  await page.screenshot({path:test.info().outputPath('unverified.png')});
  await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();
  if(outcome==='success')await expect(output(page)).toBeVisible();else {await expect(region(page)).toContainText('could not be validated');await expect(button(page,'Retry analysis')).toBeEnabled();}
  expect(posts).toBe(1);
});
test('regeneration while analysis pending rejects late success',async({page})=>{
  const id=await setup(page),g=gate();let posts=0;
  await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{}});
  await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();await comparison(page,true);g.release();await nativeFocus(page);await expect(output(page)).toBeHidden();await expect(button(page,'Analyze Comparison')).toBeEnabled();expect(posts).toBe(1);
  await page.unroute(`**/api/projects/${id}/comparison/advice`);await analyze(page);
});
async function setup(p:Page){const project=await createAndApprove(p);for(const i of [0,1]){await quoteCard(p,i).getByLabel('Upload PDF quote').setInputFiles(require('node:path').resolve(__dirname, '../../../../../apps/api/tests/fixtures/quote_pdfs', ['harbor_primary.pdf','willow_primary.pdf'][i]));await expect(quoteCard(p,i)).toContainText('Status: NEEDS REVIEW');await confirm(p,i);}await comparison(p);return project.id;}
async function nativeFocus(p:Page){
  const cdp=await p.context().newCDPSession(p);await cdp.send('Emulation.setFocusEmulationEnabled',{enabled:false});
  const other=await p.context().newPage();await other.goto('about:blank');await other.bringToFront();
  await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(false);
  await p.bringToFront();await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(true);await other.close();
  const events=await p.evaluate(()=>(window as any).__focus);
  expect(events.some((e:any)=>e.type==='blur'&&e.trusted)).toBe(true);
  expect(events.some((e:any)=>e.type==='focus'&&e.trusted)).toBe(true);
}
async function analyze(p:Page){await button(p,'Analyze Comparison').click();await expect(output(p)).toBeVisible();}
async function invariant(p:Page,id:string,before:any){expect(await readApi(p,`/projects/${id}/comparison`)).toEqual(before);expect((await readApi<any>(p,`/projects/${id}`)).preferred_supplier_id).toBeNull();}
function gate(){let release!:()=>void;const promise=new Promise<void>(r=>release=r);return {promise,release};}
for(const outcome of ['success','failure']) test(`native focus pending ${outcome}, repeated focus and keyboard retry`,async({page})=>{
  const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`),g=gate();let posts=0;
  await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=outcome==='success'?await r.fetch():null;await g.promise;if(response)await r.fulfill({response});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  await nativeFocus(page);await nativeFocus(page);await expect(button(page,'Analyzing…')).toBeDisabled();expect(posts).toBe(1);g.release();
  if(outcome==='success')await expect(output(page)).toBeVisible();else {await expect(button(page,'Retry analysis')).toBeEnabled();await button(page,'Retry analysis').scrollIntoViewIfNeeded();await page.screenshot({path:test.info().outputPath('retry-error.png')});}
  await nativeFocus(page);await nativeFocus(page);
  if(outcome==='success')await expect(output(page)).toBeVisible();else {
    await expect(region(page)).toContainText('could not be validated');expect(posts).toBe(1);
    await page.unroute(`**/api/projects/${id}/comparison/advice`);
    // Real Tab navigation, not locator.focus(), reaches Retry and Enter activates it.
    let reached=false;for(let i=0;i<350;i++){await page.keyboard.press('Tab');if(await button(page,'Retry analysis').evaluate(el=>el===document.activeElement)){reached=true;break;}}
    expect(reached).toBe(true);await page.keyboard.press('Enter');await expect(output(page)).toBeVisible();
  }
  expect(posts).toBe(1);await invariant(page,id,before);
});
test('failed freshness hides advice and GET-only recovery retains success',async({page})=>{
  const id=await setup(page);await analyze(page);let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++;});
  await page.route(`**/api/projects/${id}/comparison`,r=>r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Comparison verification unavailable. Retry.'}}}));
  await nativeFocus(page);await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  await page.screenshot({path:test.info().outputPath('verification-failed.png'),fullPage:true});
  await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();await expect(output(page)).toBeVisible();expect(posts).toBe(0);
});
test('competing focus and post-result reads cannot restore stale advice',async({page})=>{
  const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`),old=gate(),analysis=gate();let reads=0,posts=0;
  await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await analysis.promise;await r.fulfill({response});});
  await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;if(reads===1){await old.promise;await r.fulfill({json:before});}else await r.fulfill({json:{...before,stale:true}});});
  await nativeFocus(page);await expect.poll(()=>reads).toBe(1);analysis.release();await expect(region(page)).toContainText('Comparison outdated');old.release();
  await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');expect(posts).toBe(1);
});
for(const change of ['quote','brief','shortlist','regeneration']) test(`${change} invalidation and replacement`,async({page})=>{
  const id=await setup(page);await analyze(page);const old=await readApi<any>(page,`/projects/${id}/comparison`);
  if(change==='quote'){const c=quoteCard(page,0);await c.getByRole('button',{name:'Edit confirmed PDF quote',exact:true}).click();await c.getByLabel('Unit price',{exact:true}).fill('4.65');await c.getByRole('button',{name:'Save quote',exact:true}).click();}
  if(change==='brief'){const b=page.getByRole('region',{name:'Sourcing Brief',exact:true});await b.getByLabel('Destination',{exact:true}).fill('Melbourne');await b.getByRole('button',{name:'Save Brief',exact:true}).click();}
  if(change==='shortlist'){const s=page.getByRole('region',{name:'Suppliers',exact:true});await s.getByRole('article').filter({has:page.getByRole('heading',{name:'Moss Thread Bags',exact:true})}).getByRole('button',{name:'Remove from shortlist',exact:true}).click();}
  if(change!=='regeneration'){await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');}
  if(change==='brief'){await page.getByRole('button',{name:'Re-discover and re-evaluate',exact:true}).click();await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  if(change==='shortlist'){await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  await comparison(page,true);await expect(output(page)).toBeHidden();const current=await readApi<any>(page,`/projects/${id}/comparison`);expect(current.id).not.toBe(old.id);
  await analyze(page);if(change==='quote')await expect(region(page).getByRole('table')).toContainText('USD 4.65');
  expect((await readApi<any>(page,`/projects/${id}`)).preferred_supplier_id).toBeNull();
});
test('project switch A to B to A rejects late result',async({page})=>{
  const b=await setup(page);const a=await setup(page),g=gate();let posts=0;
  await page.route(`**/api/projects/${a}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{/* Browser aborted the old navigation-owned request. */}});
  await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${b}']`).first().click();await expect(output(page)).toBeHidden();
  await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${a}']`).first().click();g.release();
  await expect(button(page,'Analyze Comparison')).toBeEnabled();await nativeFocus(page);await expect(output(page)).toBeHidden();expect(posts).toBe(1);
});
test('backend deadline envelope permits explicit retry only',async({page})=>{
  const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  await page.route(`**/api/projects/${id}/comparison/advice`,r=>{posts++;return r.fulfill({status:504,json:{error:{code:'COMPARISON_ANALYSIS_TIMEOUT',message:'Analysis took too long. Please retry.'}}});});
  await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('Analysis took too long');await expect(button(page,'Retry analysis')).toBeEnabled();await nativeFocus(page);expect(posts).toBe(1);
  await page.unroute(`**/api/projects/${id}/comparison/advice`);await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();await invariant(page,id,before);
});
test('proxy disconnect envelope cooldown and no automatic retry',async({page})=>{
  const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  await page.clock.install();
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'disconnect'});
  await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('may still be finishing');await expect(button(page,'Retry analysis')).toBeDisabled();await button(page,'Retry analysis').scrollIntoViewIfNeeded();await page.screenshot({path:test.info().outputPath('disconnect-cooldown.png')});await nativeFocus(page);expect(posts).toBe(1);
  await expect(button(page,'Retry analysis')).toBeDisabled();
  await page.clock.fastForward(170000);await expect(button(page,'Retry analysis')).toBeDisabled();await page.clock.fastForward(10100);await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
});
test('real backend deadline through actual proxy and explicit recovery',async({page})=>{
  test.setTimeout(240000);
  const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'deadline'});
  const response=page.waitForResponse(r=>r.url().endsWith('/comparison/advice'),{timeout:210000});
  const start=Date.now();await button(page,'Analyze Comparison').click();const result=await response;
  const body=await result.json();expect(result.status()).toBe(504);expect(body.error.code).toBe('COMPARISON_ANALYSIS_TIMEOUT');
  writeFileSync(test.info().outputPath('deadline.json'),JSON.stringify({elapsed_ms:Date.now()-start,status:result.status(),code:body.error.code,posts},null,2));
  await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  await page.screenshot({path:test.info().outputPath('deadline-error.png'),fullPage:true});
  await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
});
test('existing human preference survives advice and failures',async({page})=>{
  const id=await setup(page),d=page.getByRole('region',{name:'Decision',exact:true});
  await d.getByRole('combobox',{name:/Preferred supplier/}).selectOption({label:'Willow Stitch Studio'});await d.getByLabel('Decision notes').fill('QA human choice');await d.getByRole('button',{name:'Mark as Preferred Supplier',exact:true}).click();await expect(d).toContainText('Preferred supplier saved.');
  const before=await readApi<any>(page,`/projects/${id}`);await analyze(page);await nativeFocus(page);await expect(output(page)).toBeVisible();
  await page.route(`**/api/projects/${id}/comparison/advice`,r=>r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis unavailable. Please retry.'}}}));
  await button(page,'Analyze Comparison').click();await expect(button(page,'Retry analysis')).toBeEnabled();
  const after=await readApi<any>(page,`/projects/${id}`);expect(after.preferred_supplier_id).toBe(before.preferred_supplier_id);expect(after.decision_notes).toBe(before.decision_notes);await expect(d).toContainText('Willow Stitch Studio');
});
for(const suggestion of [false,true])test(`${suggestion?'suggestion':'null-success'} disclosures sources facts and preference`,async({page})=>{
  const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`);
  if(suggestion)await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{const response=await r.fetch(),body=await response.json();body.suggestion.supplier_id=before.comparison_payload.suppliers[0].supplier_id;body.suggestion.supporting_reasons=[body.analysis.supplier_summaries[0]];body.suggestion.tradeoffs=[body.analysis.key_tradeoffs[0]];body.suggestion.uncertainties[0].text='Review the documented gaps before choosing a preferred supplier; this synthetic suggestion remains advisory.';await r.fulfill({json:body});});
  await analyze(page);await expect(output(page)).toContainText(suggestion?'Suggested Supplier to Investigate First':'No supplier suggested yet');await expect(output(page)).toContainText('You remain responsible for the supplier decision');await expect(output(page)).toContainText('Important unknowns');await expect(region(page).getByRole('table')).toBeVisible();
  await output(page).getByText('Source details',{exact:true}).first().click();await expect(output(page)).toContainText('Supporting PDF evidence: page 1, block 5');await invariant(page,id,before);
});






