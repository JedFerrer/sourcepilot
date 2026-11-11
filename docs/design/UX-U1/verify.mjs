// Prototype-only checks. Uses the already-installed repository Playwright package.
// Generated captures/results must remain under the ignored investigation root.
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';
import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../../..');
const require=createRequire(path.join(root,'apps/web/package.json'));
const {chromium}=require('@playwright/test');
const output=path.resolve(process.argv[2]||path.join(root,'.local-investigation-artifacts/UX-U1',`design-review-${new Date().toISOString().replace(/[:.]/g,'-')}`));
const permitted=path.join(root,'.local-investigation-artifacts')+path.sep;
assert(output.startsWith(permitted),'Generated artifacts must be under the ignored root');
assert(!(await fs.access(path.join(output,'report.json')).then(()=>true,()=>false)),'Use a new output directory; do not overwrite a prior review report');
await fs.mkdir(output,{recursive:true});
const browser=await chromium.launch({headless:true,channel:'chrome'});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[], network=[], checks=[], captures=[];
page.on('pageerror',error=>errors.push(String(error)));
page.on('request',request=>{if(/^https?:/.test(request.url()))network.push(request.url());});
page.on('dialog',dialog=>dialog.accept());
const url=(stage,scenario='normal')=>pathToFileURL(path.join(here,'index.html')).href+`?stage=${stage}&scenario=${scenario}`;
const go=async(stage,scenario='normal')=>{await page.goto(url(stage,scenario));await page.locator('h1').waitFor();};
const switchSupplier=async id=>{if(await page.locator('#quote-supplier').isVisible())await page.locator('#quote-supplier').selectOption(id);else await page.locator(`[data-action="supplier"][data-id="${id}"]`).click();};
const record=(name)=>checks.push({name,status:'PASS'});
try {
  // Independent-review corrections: exercise the complete review path, not only extraction.
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});await go('quotes','empty');
    for(const action of ['upload-choice','sample-upload','finish-processing'])await page.locator(`[data-action="${action}"]`).click();
    assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.50');
    await page.getByRole('button',{name:'View source evidence for Unit price',exact:true}).click();
    assert((await page.locator('dialog .paper').innerText()).includes('Unit price: USD 4.50'));
    await page.keyboard.press('Escape');
    await page.getByRole('button',{name:'Review saved quote',exact:true}).click();
    const provenance=page.locator('dialog .issue-copy');
    assert((await provenance.innerText()).includes('Original source price remains USD 4.50'));
    assert(!(await page.getByRole('dialog').innerText()).includes('4.22'));
    await provenance.scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,`moss-confirmation-${width}.png`)});
    await page.getByRole('button',{name:'Confirm quote',exact:true}).click();
    assert((await page.locator('.quote-fields').first().innerText()).includes('Confirmed'));
  }
  record('Moss source USD 4.50 survives extraction, evidence and confirmation review at desktop/mobile widths');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});await go('comparison');
    assert.equal(await page.locator('dialog[open]').count(),0);
    for(const [label,amount] of [['Unit price','USD 4.22'],['Tooling cost','USD 220.00']]){
      const row=width>=768?page.locator('tbody tr').filter({has:page.getByRole('rowheader',{name:label,exact:true})}):page.locator('.mobile-comparison .card').filter({has:page.getByRole('heading',{name:label,exact:true})});
      const harbor=width>=768?row.locator('td').first():row.locator('.finding').first();
      assert((await harbor.innerText()).includes(amount));
      assert((await harbor.innerText()).includes('Currency conflict: source says USD / EUR; unresolved.'));
      const cedar=width>=768?row.locator('td').nth(1):row.locator('.finding').nth(1);
      assert(!(await cedar.innerText()).includes('Currency conflict'));
      await harbor.evaluate(el=>el.scrollIntoView({block:'start'}));
      assert(await harbor.locator('.issue-copy').isVisible());
      assert(await page.locator('.notice.no-bottom').evaluate(el=>el.getBoundingClientRect().bottom<=0));
      await page.screenshot({path:path.join(output,`comparison-${label==='Unit price'?'price':'tooling'}-local-${width}.png`)});
    }
    assert.equal(await page.locator('dialog[open]').count(),0);
  }
  record('Comparison price/tooling retain local currency conflicts with summary scrolled away and evidence closed');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});await go('brief','review');
    await page.getByLabel('Delivery period',{exact:true}).fill('December 2028');
    assert(await page.getByRole('button',{name:'Review saved Brief',exact:true}).isDisabled());
    await page.getByRole('button',{name:'Save Brief',exact:true}).click();
    assert(await page.getByRole('button',{name:'Review saved Brief',exact:true}).isDisabled());
    await page.waitForTimeout(900);
    await page.getByRole('button',{name:'Review saved Brief',exact:true}).click();
    const review=page.getByRole('dialog');
    for(const value of ['Recycled cosmetic travel bag','Bags & accessories','2000','5.00','Sydney, Australia','December 2028','Recycled polyester','Printed logo','GRS certification','Material · Required','Custom branding · Required','Certification · Preferred','Neutral colors; recyclable packaging preferred.','Target currency is unknown'])assert((await review.innerText()).includes(value),`Missing saved Brief detail: ${value}`);
    await review.locator('summary').click();
    assert((await review.innerText()).includes('Target below $5 each, delivered to Sydney in November.'));
    await page.screenshot({path:path.join(output,`brief-complete-review-top-${width}.png`)});
    await review.getByRole('button',{name:'Approve Brief',exact:true}).scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,`brief-complete-review-bottom-${width}.png`)});
    await review.getByRole('button',{name:'Approve Brief',exact:true}).click();
    assert((await page.locator('.stage-heading').innerText()).includes('Approved'));
  }
  await go('brief','review');
  await page.getByLabel('Target unit price (optional)',{exact:true}).fill('');
  await page.getByRole('button',{name:'Save Brief',exact:true}).click();await page.waitForTimeout(900);
  await page.getByRole('button',{name:'Review saved Brief',exact:true}).click();
  assert((await page.locator('dialog .review-summary div').filter({hasText:'Target unit price'}).innerText()).includes('Not provided'));
  assert(await page.getByRole('button',{name:'Approve Brief',exact:true}).isEnabled());
  await page.keyboard.press('Escape');
  await go('brief','blocked');
  await page.getByRole('button',{name:'Review saved Brief',exact:true}).click();
  assert((await page.getByRole('dialog').innerText()).includes('must be provided before approval'));
  assert(await page.getByRole('button',{name:'Approve Brief',exact:true}).isDisabled());
  await page.keyboard.press('Escape');
  record('Complete saved Brief approval review includes delivery, context, original request, uncertainty and omission/gating states');
  for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:900});await go('quotes');
    assert(await page.locator('.quote-attention').isVisible());
    assert((await page.locator('.quote-attention').innerText()).includes('Currency conflict'));
    assert((await page.getByLabel('Original currency',{exact:true}).locator('..').innerText()).includes('Conflict:'));
    if(width<768){
      const box=await page.getByLabel('Quoted quantity',{exact:true}).boundingBox();
      assert(box.y+box.height<=900,`First quote input below viewport at ${width}: ${box.y+box.height}`);
      await page.screenshot({path:path.join(output,`quotes-first-viewport-${width}.png`)});
    }
    await switchSupplier('cedar');
    assert(!(await page.locator('.quote-attention').innerText()).includes('Shipping cost unknown'));
    assert(!(await page.locator('.quote-attention').innerText()).includes('Certification evidence unknown'));
    await page.getByRole('button',{name:'View source evidence for Unit price',exact:true}).click();
    const source=await page.getByRole('dialog').innerText();
    assert(source.includes('Tooling: USD 150.00')&&source.includes('Shipping: USD 650.00'));
    await page.keyboard.press('Escape');
  }
  await go('quotes','empty');
  await page.getByRole('button',{name:/Upload PDF/}).click();
  await page.getByRole('button',{name:'Use sample PDF',exact:true}).click();
  await page.getByRole('button',{name:'Finish simulated extraction',exact:true}).click();
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.50');
  await page.getByRole('button',{name:'View source evidence for Unit price',exact:true}).click();
  assert((await page.getByRole('dialog').innerText()).includes('USD 4.50'));
  await page.keyboard.press('Escape');
  record('Review corrections: visible currency conflicts, supplier-specific sources and first mobile viewport');
  await go('brief');
  assert.equal(await page.getByLabel('Product name',{exact:true}).count(),0);
  assert.equal(await page.getByRole('button',{name:'Save Brief',exact:true}).count(),0);
  await page.getByRole('button',{name:'Edit Brief',exact:true}).click();
  assert(await page.getByRole('button',{name:'Save Brief',exact:true}).isDisabled());
  await page.getByLabel('Product name',{exact:true}).fill('Deliberate edit');
  assert(await page.getByRole('button',{name:'Save Brief',exact:true}).isEnabled());
  assert(!(await page.getByRole('button',{name:'Save Brief',exact:true}).getAttribute('class')).includes('secondary'));
  record('Approved Brief opens as saved summary; deliberate editing changes action emphasis');
  for(const width of [1440,768,390,320]){
    await page.setViewportSize({width,height:width<768?900:1100});
    for(const stage of ['dashboard','brief','suppliers','quotes','comparison','decision']){
      await go(stage);
      assert.equal(await page.locator('h1').count(),1);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${stage} overflows at ${width}`);
      const filename=`${stage}-${width}.png`;
      await page.screenshot({path:path.join(output,filename),fullPage:true});
      captures.push({stage,width,scenario:'normal',file:filename});
    }
  }
  record('24 normal layouts: one heading and no page-level horizontal overflow');
  await page.setViewportSize({width:390,height:900});
  for(const [stage,scenario] of [['dashboard','empty'],['dashboard','loading'],['dashboard','failed'],['brief','review'],['brief','blocked'],['suppliers','empty'],['suppliers','stale'],['quotes','empty'],['quotes','failed'],['quotes','blocked'],['comparison','stale'],['comparison','failed'],['comparison','empty'],['decision','blocked']]){
    await go(stage,scenario);
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${stage}/${scenario} overflow`);
    const filename=`${stage}-${scenario}-390.png`;
    await page.screenshot({path:path.join(output,filename),fullPage:true});
    captures.push({stage,width:390,scenario,file:filename});
  }
  record('14 representative empty/loading/failed/blocked/review/stale layouts');
  for(const width of [1440,768,390,320]){
    await page.setViewportSize({width,height:900});await go('comparison','three');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    assert((await page.locator('main').innerText()).includes('Does not meet'));
    const filename=`comparison-three-${width}.png`;await page.screenshot({path:path.join(output,filename),fullPage:true});captures.push({stage:'comparison',width,scenario:'three',file:filename});
  }
  record('Three-supplier comparison retains required failure at all four widths');
  await page.setViewportSize({width:390,height:900});
  await go('quotes');
  await page.getByLabel('Unit price',{exact:true}).fill('4.50');
  await switchSupplier('cedar');
  await switchSupplier('harbor');
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.50');
  await page.getByRole('button',{name:'View source evidence for Unit price',exact:true}).click();
  await page.getByRole('dialog').waitFor();
  for(let i=0;i<12;i++){await page.keyboard.press('Tab');assert(await page.evaluate(()=>document.getElementById('modal').contains(document.activeElement)),'Dialog lost keyboard focus');}
  assert((await page.getByRole('dialog').innerText()).includes('USD 4.22'));
  assert((await page.getByRole('dialog').innerText()).includes('USD 4.50'));
  await page.screenshot({path:path.join(output,'quote-evidence-sheet-390.png')});
  await page.keyboard.press('Escape');
  assert.equal(await page.evaluate(()=>document.activeElement.dataset.action),'evidence');
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.50');
  record('Quote switching and evidence sheet preserve correction and original evidence');
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.locator('#external').click();
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  assert.equal(await page.getByLabel('Original currency',{exact:true}).inputValue(),'USD');
  await page.getByRole('button',{name:'Review saved and draft values'}).click();
  assert((await page.getByRole('dialog').innerText()).includes('EUR'));
  await page.getByRole('button',{name:'Review my complete draft'}).click();
  await page.getByRole('button',{name:'Keep this draft for editing'}).click();
  assert.equal(await page.getByLabel('Original currency',{exact:true}).inputValue(),'USD');
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.50');
  record('Amount/currency conflict requires explicit complete-record review');
  await go('brief');
  await page.getByRole('button',{name:'Edit Brief',exact:true}).click();
  await page.getByLabel('Product name',{exact:true}).fill('Local draft');
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.locator('#external').click();
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.getByRole('button',{name:'Review saved and draft values'}).click();
  await page.getByRole('button',{name:'Review my complete draft'}).click();
  await page.getByRole('button',{name:'Keep this draft for editing'}).click();
  assert((await page.getByRole('dialog').innerText()).includes('Requirement membership changed'));
  record('Requirement add/delete conflict cannot silently restore deleted IDs');
  await page.getByRole('button',{name:'Use saved record'}).click();
  assert.equal(await page.getByLabel('Destination',{exact:true}).inputValue(),'Melbourne, Australia');
  await go('suppliers','review');
  await page.locator('summary').filter({hasText:'Private notes'}).first().click();
  await page.getByLabel('Private notes for Harbor Pouch Works',{exact:true}).fill('Retain this private note');
  // Fixture makes Brief ready for review; explicitly approve it first.
  await page.locator('nav [data-nav="brief"]').click();
  await page.getByRole('button',{name:'Review saved Brief'}).click();
  await page.getByRole('button',{name:'Approve Brief',exact:true}).click();
  await page.locator('nav [data-nav="suppliers"]').click();
  await page.getByRole('button',{name:'Review shortlist',exact:true}).last().click();
  await page.getByRole('button',{name:'Approve shortlist',exact:true}).click();
  assert.equal(await page.getByLabel('Private notes for Harbor Pouch Works',{exact:true}).inputValue(),'Retain this private note');
  record('Unsaved private notes survive shortlist approval without being saved');
  await go('quotes');
  await page.getByLabel('Unit price',{exact:true}).fill('4.50');
  await page.getByRole('button',{name:'Save quote changes',exact:true}).click();
  await page.getByLabel('Unit price',{exact:true}).fill('4.75');
  await page.waitForTimeout(900);
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.75');
  assert((await page.locator('[data-status="harbor"]').innerText()).includes('Unsaved'));
  record('Typing during a pending save retains later unsaved changes');
  await go('quotes');
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.locator('#save-mode').selectOption('failed');
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.getByLabel('Unit price',{exact:true}).fill('4.60');
  await page.getByRole('button',{name:'Save quote changes',exact:true}).click();
  await page.waitForTimeout(900);
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.60');
  assert((await page.locator('[data-status="harbor"]').innerText()).includes('failed'));
  record('Failed save retains local correction');
  await go('quotes');
  await page.getByLabel('Unit price',{exact:true}).fill('4.50');
  await page.getByRole('button',{name:'Save quote changes',exact:true}).click();
  await page.waitForTimeout(900);
  await page.locator('nav [data-nav="comparison"]').click();
  assert(await page.locator('.mobile-comparison').getByText('USD 4.22',{exact:true}).isVisible());
  await page.locator('[data-action="generate"]').click();
  assert(await page.locator('.mobile-comparison').getByText('USD 4.50',{exact:true}).isVisible());
  record('Stale comparison retains its old snapshot until explicit refresh');
  await go('quotes');
  await switchSupplier('moss');
  await page.locator('[data-action="manual-choice"]').click();
  assert(await page.getByRole('button',{name:'Review saved quote',exact:true}).isDisabled());
  assert.equal(await page.locator('[data-action="evidence"]').count(),0);
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.waitForTimeout(900);
  await page.getByRole('button',{name:'Review saved quote',exact:true}).click();
  assert((await page.getByRole('dialog').innerText()).includes('no original PDF evidence'));
  await page.getByRole('button',{name:'Confirm quote',exact:true}).click();
  record('Manual entry requires saving before review and does not invent PDF evidence');
  await go('quotes');
  await page.clock.install();
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.locator('#save-mode').selectOption('pending');
  await page.locator('summary').filter({hasText:'Review controls'}).click();
  await page.getByLabel('Unit price',{exact:true}).fill('4.90');
  await page.getByRole('button',{name:'Save quote changes',exact:true}).click();
  await page.getByRole('button',{name:'All projects',exact:false}).click();
  assert(await page.getByRole('button',{name:'Leave anyway',exact:true}).isEnabled());
  await page.clock.fastForward(11000);
  assert((await page.getByRole('dialog').innerText()).includes('Save outcome not yet confirmed'));
  await page.getByRole('button',{name:'Leave anyway',exact:true}).click();
  await page.clock.fastForward(10000);
  await page.getByRole('button',{name:'Open project',exact:false}).click();
  await page.locator('nav [data-nav="quotes"]').click();
  assert.equal(await page.getByLabel('Unit price',{exact:true}).inputValue(),'4.90');
  record('Pending-save departure is immediate; bounded notice and later saved-state reload work');
  await go('decision','blocked');
  await page.getByLabel('Proposed preference',{exact:false}).selectOption('cedar');
  await page.getByRole('button',{name:'Mark as preferred supplier',exact:true}).click();
  await page.getByRole('button',{name:'Save preferred supplier',exact:true}).click();
  await page.clock.fastForward(1000);
  assert((await page.locator('.selected-preference').innerText()).includes('Cedar Textile Studio'));
  assert((await page.locator('.notice.info').last().innerText()).includes('Harbor'));
  record('Human preference can disagree with AI before comparison');
  await page.getByLabel('Proposed preference',{exact:false}).selectOption('harbor');
  await page.getByLabel('Decision notes (optional)',{exact:true}).fill('Saved notes only');
  await page.getByRole('button',{name:'Save decision notes',exact:true}).click();
  await page.clock.fastForward(1000);
  assert((await page.locator('.selected-preference').innerText()).includes('Cedar Textile Studio'));
  assert.equal(await page.getByLabel('Proposed preference',{exact:false}).inputValue(),'harbor');
  record('Notes-only save preserves saved preference and unsaved replacement');
  await go('brief');
  await page.getByRole('button',{name:'Rename',exact:true}).click();
  await page.getByRole('dialog').getByLabel('Project name',{exact:true}).fill('Unsaved name');
  await page.keyboard.press('Escape');
  assert((await page.getByRole('dialog').innerText()).includes('Discard the unsaved project name'));
  await page.getByRole('button',{name:'Discard name edit'}).click();
  record('Closing a dirty rename editor requires an explicit discard choice');
  await go('brief');
  await page.locator('nav [data-nav="quotes"]').click();
  await page.goBack();
  assert((await page.locator('h1').innerText()).includes('brief'));
  await page.goForward();
  assert((await page.locator('h1').innerText()).includes('quotes'));
  record('Stage Back/Forward restores viewed stage');
  // A real Chrome default page-zoom preference, not CSS zoom or device emulation.
  const zoomProfile=path.join(output,'chrome-400-profile');
  await fs.mkdir(path.join(zoomProfile,'Default'),{recursive:true});
  await fs.writeFile(path.join(zoomProfile,'Default','Preferences'),JSON.stringify({partition:{default_zoom_level:{x:Math.log(4)/Math.log(1.2)}}}));
  const zoomContext=await chromium.launchPersistentContext(zoomProfile,{channel:'chrome',headless:true,viewport:null,args:['--window-size=1280,1024']});
  const zoomPage=zoomContext.pages()[0];
  await zoomPage.goto(url('quotes'));
  const zoomMetrics=await zoomPage.evaluate(()=>({outerWidth,innerWidth,dpr:devicePixelRatio,scrollWidth:document.documentElement.scrollWidth}));
  await fs.writeFile(path.join(output,'zoom-metrics.json'),JSON.stringify(zoomMetrics,null,2));
  if(zoomMetrics.dpr>=3.9&&zoomMetrics.innerWidth<=330){
    assert(zoomMetrics.scrollWidth<=zoomMetrics.innerWidth+1);
    for(const stage of ['dashboard','brief','suppliers','quotes','comparison','decision']){
      await zoomPage.goto(url(stage));
      assert(await zoomPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${stage} overflows at actual 400% zoom`);
      await zoomPage.screenshot({path:path.join(output,`${stage}-browser-400-percent.png`),fullPage:true});
    }
    record('Chrome 400% page zoom: six screens at 1280 outer width, approximately 320 CSS-pixel reflow');
  }else checks.push({name:'Actual 400% browser zoom',status:'NOT_VERIFIED',detail:zoomMetrics});
  await zoomContext.close();
  await page.setViewportSize({width:1440,height:1100});
  await page.goto(pathToFileURL(path.join(here,'layouts.html')).href);
  await page.locator('iframe').first().waitFor();
  await page.screenshot({path:path.join(output,'atlas-desktop.png'),fullPage:true});
  assert.equal(errors.length,0,errors.join('\n'));
  assert.equal(network.length,0,'Prototype must not call external services');
  record('No browser JavaScript errors or HTTP service requests');
} catch(error){checks.push({name:'Verification interrupted',status:'FAIL',detail:String(error)});await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});process.exitCode=1;}
finally {
  const hashes={};for(const file of ['index.html','prototype.css','prototype.js','layouts.html','verify.mjs'])hashes[file]=crypto.createHash('sha256').update(await fs.readFile(path.join(here,file))).digest('hex');
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify({scope:'Synthetic prototype only; not application QA or human usability testing',checks,captures,errors,network,hashes},null,2));
  console.log(JSON.stringify({output,checks,captures:captures.length,errors},null,2));
  await browser.close();
}
