# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: qa.spec.ts >> null-success disclosures sources facts and preference
- Location: qa.spec.ts:102:42

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: getByRole('region', { name: 'Comparison analysis', exact: true })
Expected substring: "Confirmed"
Received string:    "Tradeoff analysisSupplier summariesWillow Stitch Studio quotes 4.20 USD per unit. Review its requirement findings.Source detailsUnit Price source: quote-value:b5ad7fe3-0cd9-4088-b5c9-b09ff8a01b6bUnit Price current origin: Ai ExtractedOriginal extracted value: 4.20Supporting PDF evidence: page 1, block 5; extracted 4.20 · 89bac0e4-c999-43c2-80cf-650f32a4f104Harbor Pouch Works quotes 4.60 USD per unit. Review its requirement findings.Source detailsUnit Price source: quote-value:ad503096-a50e-4df9-a011-b0fa89e8e47eUnit Price current origin: Ai ExtractedOriginal extracted value: 4.60Supporting PDF evidence: page 1, block 5; extracted 4.60 · f6b67c78-52ca-4a25-80f1-3efffbb69101Key tradeoffsWillow Stitch Studio: compare the stated production lead time with the other quotations.Source detailsProduction Lead Time source: quote-value:d99d667d-5d8c-4bed-8e22-e9d1087b1956Production Lead Time current origin: Ai ExtractedOriginal extracted value: 40 days after sample approvalSupporting PDF evidence: page 1, block 10; extracted 40 days after sample approval · 8b1cbddd-ce62-4959-b831-79c3bd9b689fHarbor Pouch Works: compare the stated production lead time with the other quotations.Source detailsProduction Lead Time source: quote-value:fd7ba201-3724-461d-9f75-91b05994411eProduction Lead Time current origin: Ai ExtractedOriginal extracted value: 32 days after sample approvalSupporting PDF evidence: page 1, block 10; extracted 32 days after sample approval · b648cabe-24ef-4215-a511-471ebd01734dImportant unknownsThe requirement state is UNKNOWN.Willow Stitch Studio: Certification — Unknowncertifications is unknown.Source detailsCertifications source: quote-value:8fdd266b-5bcd-4de3-917e-e269046d0343Certifications current origin: Ai ExtractedSupporting PDF evidence: page 1, block 13; extracted Unknown · 462cc3e3-532c-4ad7-822a-8184fc793d76compliance notes is unknown.Source detailsCompliance Notes source: quote-value:c3ab1614-4fba-462f-ba1a-8ce5b0687c52Compliance Notes current origin: Ai Extracteddelivery date is unknown.exclusions is unknown.Source detailsExclusions source: quote-value:b997978d-1b7a-4dee-a1cf-eb8a6bf5b0c9Exclusions current origin: Ai Extractedincoterm is unknown.Source detailsIncoterm source: quote-value:131df399-80ff-410b-b378-eec1c50a4bc0Incoterm current origin: Ai Extractedpackaging cost is unknown.Source detailsPackaging Cost source: quote-value:87eb5218-78ac-40e2-9fcc-3ba30c571f63Packaging Cost current origin: Ai Extractedspecial conditions is unknown.Source detailsSpecial Conditions source: quote-value:81a5c822-42f9-4e68-a863-a3c53bd130c0Special Conditions current origin: Ai Extractedsupplier notes is unknown.Source detailsSupplier Notes source: quote-value:874669ef-ab01-43fd-9e23-b2d0b874a980Supplier Notes current origin: Ai Extractedtotal lead time is unknown.Source detailsTotal Lead Time source: quote-value:98419261-4c37-4b65-a64e-91ab94832bc9Total Lead Time current origin: Ai Extractedwarranty is unknown.Source detailsWarranty source: quote-value:9bcd9251-af61-4505-b5a5-cd181291a410Warranty current origin: Ai Extractedcompliance notes is unknown.Source detailsCompliance Notes source: quote-value:5a6d476d-93a5-4f30-a2bc-76c6ca2b7462Compliance Notes current origin: Ai Extracteddelivery date is unknown.incoterm is unknown.Source detailsIncoterm source: quote-value:80b46e31-bbc1-4834-aec3-fbd517f94727Incoterm current origin: Ai Extractedpackaging cost is unknown.Source detailsPackaging Cost source: quote-value:b37d2955-3046-4d4a-8894-92a5979c1f73Packaging Cost current origin: Ai Extractedspecial conditions is unknown.Source detailsSpecial Conditions source: quote-value:a5c89c5a-31d9-46e1-ac7c-885af3e685c1Special Conditions current origin: Ai Extractedsupplier notes is unknown.Source detailsSupplier Notes source: quote-value:65679344-f10c-4779-b19c-14b7d118a484Supplier Notes current origin: Ai Extractedtotal lead time is unknown.Source detailsTotal Lead Time source: quote-value:97f5a895-64e0-49c5-a2b7-7e61a9f68f03Total Lead Time current origin: Ai Extractedwarranty is unknown.Source detailsWarranty source: quote-value:7763b0cc-eba3-4932-91b0-0b52b4ba2717Warranty current origin: Ai ExtractedNo supplier suggested yetThis advice supports your review. You remain responsible for the supplier decision.UncertaintiesReview the documented gaps before choosing a preferred supplier. No single supplier is suggested by this deterministic fixture."
Timeout: 15000ms

Call log:
  - Expect "toContainText" getByRole('region', { name: 'Comparison analysis', exact: true }) with timeout 15000ms
  - waiting for getByRole('region', { name: 'Comparison analysis', exact: true })
    33 × locator resolved to <section aria-label="Comparison analysis">…</section>
       - unexpected value "Tradeoff analysisSupplier summariesWillow Stitch Studio quotes 4.20 USD per unit. Review its requirement findings.Source detailsUnit Price source: quote-value:b5ad7fe3-0cd9-4088-b5c9-b09ff8a01b6bUnit Price current origin: Ai ExtractedOriginal extracted value: 4.20Supporting PDF evidence: page 1, block 5; extracted 4.20 · 89bac0e4-c999-43c2-80cf-650f32a4f104Harbor Pouch Works quotes 4.60 USD per unit. Review its requirement findings.Source detailsUnit Price source: quote-value:ad503096-a50e-4df9-a011-b0fa89e8e47eUnit Price current origin: Ai ExtractedOriginal extracted value: 4.60Supporting PDF evidence: page 1, block 5; extracted 4.60 · f6b67c78-52ca-4a25-80f1-3efffbb69101Key tradeoffsWillow Stitch Studio: compare the stated production lead time with the other quotations.Source detailsProduction Lead Time source: quote-value:d99d667d-5d8c-4bed-8e22-e9d1087b1956Production Lead Time current origin: Ai ExtractedOriginal extracted value: 40 days after sample approvalSupporting PDF evidence: page 1, block 10; extracted 40 days after sample approval · 8b1cbddd-ce62-4959-b831-79c3bd9b689fHarbor Pouch Works: compare the stated production lead time with the other quotations.Source detailsProduction Lead Time source: quote-value:fd7ba201-3724-461d-9f75-91b05994411eProduction Lead Time current origin: Ai ExtractedOriginal extracted value: 32 days after sample approvalSupporting PDF evidence: page 1, block 10; extracted 32 days after sample approval · b648cabe-24ef-4215-a511-471ebd01734dImportant unknownsThe requirement state is UNKNOWN.Willow Stitch Studio: Certification — Unknowncertifications is unknown.Source detailsCertifications source: quote-value:8fdd266b-5bcd-4de3-917e-e269046d0343Certifications current origin: Ai ExtractedSupporting PDF evidence: page 1, block 13; extracted Unknown · 462cc3e3-532c-4ad7-822a-8184fc793d76compliance notes is unknown.Source detailsCompliance Notes source: quote-value:c3ab1614-4fba-462f-ba1a-8ce5b0687c52Compliance Notes current origin: Ai Extracteddelivery date is unknown.exclusions is unknown.Source detailsExclusions source: quote-value:b997978d-1b7a-4dee-a1cf-eb8a6bf5b0c9Exclusions current origin: Ai Extractedincoterm is unknown.Source detailsIncoterm source: quote-value:131df399-80ff-410b-b378-eec1c50a4bc0Incoterm current origin: Ai Extractedpackaging cost is unknown.Source detailsPackaging Cost source: quote-value:87eb5218-78ac-40e2-9fcc-3ba30c571f63Packaging Cost current origin: Ai Extractedspecial conditions is unknown.Source detailsSpecial Conditions source: quote-value:81a5c822-42f9-4e68-a863-a3c53bd130c0Special Conditions current origin: Ai Extractedsupplier notes is unknown.Source detailsSupplier Notes source: quote-value:874669ef-ab01-43fd-9e23-b2d0b874a980Supplier Notes current origin: Ai Extractedtotal lead time is unknown.Source detailsTotal Lead Time source: quote-value:98419261-4c37-4b65-a64e-91ab94832bc9Total Lead Time current origin: Ai Extractedwarranty is unknown.Source detailsWarranty source: quote-value:9bcd9251-af61-4505-b5a5-cd181291a410Warranty current origin: Ai Extractedcompliance notes is unknown.Source detailsCompliance Notes source: quote-value:5a6d476d-93a5-4f30-a2bc-76c6ca2b7462Compliance Notes current origin: Ai Extracteddelivery date is unknown.incoterm is unknown.Source detailsIncoterm source: quote-value:80b46e31-bbc1-4834-aec3-fbd517f94727Incoterm current origin: Ai Extractedpackaging cost is unknown.Source detailsPackaging Cost source: quote-value:b37d2955-3046-4d4a-8894-92a5979c1f73Packaging Cost current origin: Ai Extractedspecial conditions is unknown.Source detailsSpecial Conditions source: quote-value:a5c89c5a-31d9-46e1-ac7c-885af3e685c1Special Conditions current origin: Ai Extractedsupplier notes is unknown.Source detailsSupplier Notes source: quote-value:65679344-f10c-4779-b19c-14b7d118a484Supplier Notes current origin: Ai Extractedtotal lead time is unknown.Source detailsTotal Lead Time source: quote-value:97f5a895-64e0-49c5-a2b7-7e61a9f68f03Total Lead Time current origin: Ai Extractedwarranty is unknown.Source detailsWarranty source: quote-value:7763b0cc-eba3-4932-91b0-0b52b4ba2717Warranty current origin: Ai ExtractedNo supplier suggested yetThis advice supports your review. You remain responsible for the supplier decision.UncertaintiesReview the documented gaps before choosing a preferred supplier. No single supplier is suggested by this deterministic fixture."

```

```yaml
- region "Comparison analysis":
  - heading "Tradeoff analysis" [level=3]
  - heading "Supplier summaries" [level=4]
  - list:
    - listitem:
      - paragraph: Willow Stitch Studio quotes 4.20 USD per unit. Review its requirement findings.
      - group:
        - text: Source details
        - paragraph: "Unit Price source: quote-value:b5ad7fe3-0cd9-4088-b5c9-b09ff8a01b6b"
        - paragraph: "Unit Price current origin: Ai Extracted"
        - paragraph: "Original extracted value: 4.20"
        - paragraph: "Supporting PDF evidence: page 1, block 5; extracted 4.20 · 89bac0e4-c999-43c2-80cf-650f32a4f104"
    - listitem:
      - paragraph: Harbor Pouch Works quotes 4.60 USD per unit. Review its requirement findings.
      - group: Source details
  - heading "Key tradeoffs" [level=4]
  - list:
    - listitem:
      - paragraph: "Willow Stitch Studio: compare the stated production lead time with the other quotations."
      - group: Source details
    - listitem:
      - paragraph: "Harbor Pouch Works: compare the stated production lead time with the other quotations."
      - group: Source details
  - heading "Important unknowns" [level=4]
  - list:
    - listitem:
      - paragraph: The requirement state is UNKNOWN.
      - paragraph: "Willow Stitch Studio: Certification — Unknown"
    - listitem:
      - paragraph: certifications is unknown.
      - group: Source details
    - listitem:
      - paragraph: compliance notes is unknown.
      - group: Source details
    - listitem:
      - paragraph: delivery date is unknown.
    - listitem:
      - paragraph: exclusions is unknown.
      - group: Source details
    - listitem:
      - paragraph: incoterm is unknown.
      - group: Source details
    - listitem:
      - paragraph: packaging cost is unknown.
      - group: Source details
    - listitem:
      - paragraph: special conditions is unknown.
      - group: Source details
    - listitem:
      - paragraph: supplier notes is unknown.
      - group: Source details
    - listitem:
      - paragraph: total lead time is unknown.
      - group: Source details
    - listitem:
      - paragraph: warranty is unknown.
      - group: Source details
    - listitem:
      - paragraph: compliance notes is unknown.
      - group: Source details
    - listitem:
      - paragraph: delivery date is unknown.
    - listitem:
      - paragraph: incoterm is unknown.
      - group: Source details
    - listitem:
      - paragraph: packaging cost is unknown.
      - group: Source details
    - listitem:
      - paragraph: special conditions is unknown.
      - group: Source details
    - listitem:
      - paragraph: supplier notes is unknown.
      - group: Source details
    - listitem:
      - paragraph: total lead time is unknown.
      - group: Source details
    - listitem:
      - paragraph: warranty is unknown.
      - group: Source details
  - heading "No supplier suggested yet" [level=3]
  - paragraph: This advice supports your review. You remain responsible for the supplier decision.
  - heading "Uncertainties" [level=4]
  - list:
    - listitem:
      - paragraph: Review the documented gaps before choosing a preferred supplier. No single supplier is suggested by this deterministic fixture.
```

# Test source

```ts
  6   | const button = (p: Page, name: string) => region(p).getByRole('button',{name,exact:true});
  7   | let requests: {method:string;path:string}[];
  8   | test.beforeEach(async ({page}) => {
  9   |   requests=[];
  10  |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});
  11  |   page.on('request',r=>{const u=new URL(r.url()); if(u.pathname.startsWith('/api/')) requests.push({method:r.method(),path:u.pathname.replace(/[0-9a-f]{8}-[0-9a-f-]{27,}/g,':id')});});
  12  |   await page.addInitScript(()=>{
  13  |     (window as any).__focus=[];
  14  |     for(const type of ['focus','blur']) window.addEventListener(type,e=>(window as any).__focus.push({type,trusted:e.isTrusted,focused:document.hasFocus()}));
  15  |   });
  16  | });
  17  | test.afterEach(async ({page},info)=>{
  18  |   const counts: Record<string,number>={}; for(const r of requests){const k=r.method+' '+r.path;counts[k]=(counts[k]??0)+1;}
  19  |   writeFileSync(info.outputPath('sanitized-network.json'),JSON.stringify({counts,sequence:requests},null,2));
  20  |   if(!page.isClosed()) {
  21  |     await page.bringToFront();
  22  |     writeFileSync(info.outputPath('focus.json'),JSON.stringify(await page.evaluate(()=>(window as any).__focus),null,2));
  23  |     await page.screenshot({path:info.outputPath('final.png'),fullPage:true});
  24  |     writeFileSync(info.outputPath('visible-text.txt'),await page.locator('body').innerText());
  25  |   }
  26  | });
  27  | async function setup(p:Page){const project=await createAndApprove(p);for(const i of [0,1]){await quoteCard(p,i).getByLabel('Upload PDF quote').setInputFiles(require('node:path').resolve(__dirname, '../../../../../apps/api/tests/fixtures/quote_pdfs', ['harbor_primary.pdf','willow_primary.pdf'][i]));await expect(quoteCard(p,i)).toContainText('Status: NEEDS REVIEW');await confirm(p,i);}await comparison(p);return project.id;}
  28  | async function nativeFocus(p:Page){
  29  |   const cdp=await p.context().newCDPSession(p);await cdp.send('Emulation.setFocusEmulationEnabled',{enabled:false});
  30  |   const other=await p.context().newPage();await other.goto('about:blank');await other.bringToFront();
  31  |   await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(false);
  32  |   await p.bringToFront();await expect.poll(()=>p.evaluate(()=>document.hasFocus())).toBe(true);await other.close();
  33  |   const events=await p.evaluate(()=>(window as any).__focus);
  34  |   expect(events.some((e:any)=>e.type==='blur'&&e.trusted)).toBe(true);
  35  |   expect(events.some((e:any)=>e.type==='focus'&&e.trusted)).toBe(true);
  36  | }
  37  | async function analyze(p:Page){await button(p,'Analyze Comparison').click();await expect(output(p)).toBeVisible();}
  38  | async function invariant(p:Page,id:string,before:any){expect(await readApi(p,`/projects/${id}/comparison`)).toEqual(before);expect((await readApi<any>(p,`/projects/${id}`)).preferred_supplier_id).toBeNull();}
  39  | function gate(){let release!:()=>void;const promise=new Promise<void>(r=>release=r);return {promise,release};}
  40  | for(const outcome of ['success','failure']) test(`native focus pending ${outcome}, repeated focus and keyboard retry`,async({page})=>{
  41  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`),g=gate();let posts=0;
  42  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=outcome==='success'?await r.fetch():null;await g.promise;if(response)await r.fulfill({response});else await r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis could not be validated. Please retry.'}}});});
  43  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  44  |   await nativeFocus(page);await nativeFocus(page);await expect(button(page,'Analyzing…')).toBeDisabled();expect(posts).toBe(1);g.release();
  45  |   if(outcome==='success')await expect(output(page)).toBeVisible();else await expect(button(page,'Retry analysis')).toBeEnabled();
  46  |   await nativeFocus(page);await nativeFocus(page);
  47  |   if(outcome==='success')await expect(output(page)).toBeVisible();else {
  48  |     await expect(region(page)).toContainText('could not be validated');expect(posts).toBe(1);
  49  |     await page.unroute(`**/api/projects/${id}/comparison/advice`);
  50  |     // Real Tab navigation, not locator.focus(), reaches Retry and Enter activates it.
  51  |     let reached=false;for(let i=0;i<350;i++){await page.keyboard.press('Tab');if(await button(page,'Retry analysis').evaluate(el=>el===document.activeElement)){reached=true;break;}}
  52  |     expect(reached).toBe(true);await page.keyboard.press('Enter');await expect(output(page)).toBeVisible();
  53  |   }
  54  |   expect(posts).toBe(1);await invariant(page,id,before);
  55  | });
  56  | test('failed freshness hides advice and GET-only recovery retains success',async({page})=>{
  57  |   const id=await setup(page);await analyze(page);let posts=0;page.on('request',r=>{if(r.method()==='POST')posts++;});
  58  |   await page.route(`**/api/projects/${id}/comparison`,r=>r.fulfill({status:503,json:{error:{code:'UNAVAILABLE',message:'Comparison verification unavailable. Retry.'}}}));
  59  |   await nativeFocus(page);await expect(button(page,'Retry comparison')).toBeVisible();await expect(output(page)).toBeHidden();
  60  |   await page.screenshot({path:test.info().outputPath('verification-failed.png'),fullPage:true});
  61  |   await page.unroute(`**/api/projects/${id}/comparison`);await button(page,'Retry comparison').click();await expect(output(page)).toBeVisible();expect(posts).toBe(0);
  62  | });
  63  | test('competing focus and post-result reads cannot restore stale advice',async({page})=>{
  64  |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`),old=gate(),analysis=gate();let reads=0,posts=0;
  65  |   await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await analysis.promise;await r.fulfill({response});});
  66  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  67  |   await page.route(`**/api/projects/${id}/comparison`,async r=>{reads++;if(reads===1){await old.promise;await r.fulfill({json:before});}else await r.fulfill({json:{...before,stale:true}});});
  68  |   await nativeFocus(page);await expect.poll(()=>reads).toBe(1);analysis.release();await expect(region(page)).toContainText('Comparison outdated');old.release();
  69  |   await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');expect(posts).toBe(1);
  70  | });
  71  | for(const change of ['quote','brief','shortlist','regeneration']) test(`${change} invalidation and replacement`,async({page})=>{
  72  |   const id=await setup(page);await analyze(page);const old=await readApi<any>(page,`/projects/${id}/comparison`);
  73  |   if(change==='quote'){const c=quoteCard(page,0);await c.getByRole('button',{name:'Edit confirmed PDF quote',exact:true}).click();await c.getByLabel('Unit price',{exact:true}).fill('4.65');await c.getByRole('button',{name:'Save quote',exact:true}).click();}
  74  |   if(change==='brief'){const b=page.getByRole('region',{name:'Sourcing Brief',exact:true});await b.getByLabel('Destination',{exact:true}).fill('Melbourne');await b.getByRole('button',{name:'Save Brief',exact:true}).click();}
  75  |   if(change==='shortlist'){const s=page.getByRole('region',{name:'Suppliers',exact:true});await s.getByRole('article').filter({has:page.getByRole('heading',{name:'Moss Thread Bags',exact:true})}).getByRole('button',{name:'Remove from shortlist',exact:true}).click();}
  76  |   if(change!=='regeneration'){await expect(output(page)).toBeHidden();await expect(region(page)).toContainText('Comparison outdated');}
  77  |   if(change==='brief'){await page.getByRole('button',{name:'Re-discover and re-evaluate',exact:true}).click();await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  78  |   if(change==='shortlist'){await page.getByRole('button',{name:'Review selected suppliers',exact:true}).click();await page.getByRole('button',{name:'Approve Shortlist',exact:true}).click();}
  79  |   await comparison(page,true);await expect(output(page)).toBeHidden();const current=await readApi<any>(page,`/projects/${id}/comparison`);expect(current.id).not.toBe(old.id);
  80  |   await analyze(page);if(change==='quote')await expect(region(page).getByRole('table')).toContainText('USD 4.65');
  81  |   expect((await readApi<any>(page,`/projects/${id}`)).preferred_supplier_id).toBeNull();
  82  | });
  83  | test('project switch A to B to A rejects late result',async({page})=>{
  84  |   const b=await setup(page);const a=await setup(page),g=gate();let posts=0;
  85  |   await page.route(`**/api/projects/${a}/comparison/advice`,async r=>{posts++;const response=await r.fetch();await g.promise;try{await r.fulfill({response});}catch{/* Browser aborted the old navigation-owned request. */}});
  86  |   await button(page,'Analyze Comparison').click();await expect(button(page,'Analyzing…')).toBeDisabled();
  87  |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${b}']`).first().click();await expect(output(page)).toBeHidden();
  88  |   await page.getByRole('link',{name:'Back to projects',exact:true}).click();await page.locator(`a[href='/projects/${a}']`).first().click();g.release();
  89  |   await expect(button(page,'Analyze Comparison')).toBeEnabled();await nativeFocus(page);await expect(output(page)).toBeHidden();expect(posts).toBe(1);
  90  | });
  91  | test('backend deadline envelope permits explicit retry only',async({page})=>{
  92  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  93  |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>{posts++;return r.fulfill({status:504,json:{error:{code:'COMPARISON_ANALYSIS_TIMEOUT',message:'Analysis took too long. Please retry.'}}});});
  94  |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('Analysis took too long');await expect(button(page,'Retry analysis')).toBeEnabled();await nativeFocus(page);expect(posts).toBe(1);
  95  |   await page.unroute(`**/api/projects/${id}/comparison/advice`);await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();await invariant(page,id,before);
  96  | });
  97  | test('proxy disconnect envelope cooldown and no automatic retry',async({page})=>{
  98  |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  99  |   await page.clock.install();
  100 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  101 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'disconnect'});
  102 |   await button(page,'Analyze Comparison').click();await expect(region(page)).toContainText('may still be finishing');await expect(button(page,'Retry analysis')).toBeDisabled();await nativeFocus(page);expect(posts).toBe(1);
  103 |   await page.clock.fastForward(179000);await expect(button(page,'Retry analysis')).toBeDisabled();await page.clock.fastForward(1100);await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  104 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  105 | });
> 106 | test('real backend deadline through actual proxy and explicit recovery',async({page})=>{
      |                                                                                                          ^ Error: expect(locator).toContainText(expected) failed
  107 |   test.setTimeout(240000);
  108 |   const id=await setup(page),before=await readApi(page,`/projects/${id}/comparison`);let posts=0;
  109 |   page.on('request',r=>{if(r.method()==='POST'&&r.url().endsWith('/comparison/advice'))posts++;});
  110 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'deadline'});
  111 |   const response=page.waitForResponse(r=>r.url().endsWith('/comparison/advice'),{timeout:210000});
  112 |   const start=Date.now();await button(page,'Analyze Comparison').click();const result=await response;
  113 |   const body=await result.json();expect(result.status()).toBe(504);expect(body.error.code).toBe('COMPARISON_ANALYSIS_TIMEOUT');
  114 |   writeFileSync(test.info().outputPath('deadline.json'),JSON.stringify({elapsed_ms:Date.now()-start,status:result.status(),code:body.error.code,posts},null,2));
  115 |   await expect(button(page,'Retry analysis')).toBeEnabled();expect(posts).toBe(1);
  116 |   await page.screenshot({path:test.info().outputPath('deadline-error.png'),fullPage:true});
  117 |   await page.request.post('http://127.0.0.1:18001/__qa/control',{data:'normal'});await button(page,'Retry analysis').click();await expect(output(page)).toBeVisible();expect(posts).toBe(2);await invariant(page,id,before);
  118 | });
  119 | test('existing human preference survives advice and failures',async({page})=>{
  120 |   const id=await setup(page),d=page.getByRole('region',{name:'Decision',exact:true});
  121 |   await d.getByLabel('Preferred supplier',{exact:true}).selectOption({label:'Willow Stitch Studio'});await d.getByLabel('Decision notes').fill('QA human choice');await d.getByRole('button',{name:'Mark as Preferred Supplier',exact:true}).click();await expect(d).toContainText('Preferred supplier saved.');
  122 |   const before=await readApi<any>(page,`/projects/${id}`);await analyze(page);await nativeFocus(page);await expect(output(page)).toBeVisible();
  123 |   await page.route(`**/api/projects/${id}/comparison/advice`,r=>r.fulfill({status:503,json:{error:{code:'COMPARISON_ADVICE_UNAVAILABLE',message:'Analysis unavailable. Please retry.'}}}));
  124 |   await button(page,'Analyze Comparison').click();await expect(button(page,'Retry analysis')).toBeEnabled();
  125 |   const after=await readApi<any>(page,`/projects/${id}`);expect(after.preferred_supplier_id).toBe(before.preferred_supplier_id);expect(after.decision_notes).toBe(before.decision_notes);await expect(d).toContainText('Willow Stitch Studio');
  126 | });
  127 | for(const suggestion of [false,true])test(`${suggestion?'suggestion':'null-success'} disclosures sources facts and preference`,async({page})=>{
  128 |   const id=await setup(page),before=await readApi<any>(page,`/projects/${id}/comparison`);
  129 |   if(suggestion)await page.route(`**/api/projects/${id}/comparison/advice`,async r=>{const response=await r.fetch(),body=await response.json();body.suggestion.supplier_id=before.comparison_payload.suppliers[0].supplier_id;body.suggestion.supporting_reasons=[body.analysis.supplier_summaries[0]];body.suggestion.tradeoffs=[body.analysis.key_tradeoffs[0]];await r.fulfill({json:body});});
  130 |   await analyze(page);await expect(output(page)).toContainText(suggestion?'Suggested Supplier to Investigate First':'No supplier suggested yet');await expect(output(page)).toContainText('You remain responsible for the supplier decision');await expect(output(page)).toContainText('Important unknowns');await expect(region(page).getByRole('table')).toBeVisible();
  131 |   await output(page).getByText('Source details',{exact:true}).first().click();await expect(output(page)).toContainText('Confirmed');await invariant(page,id,before);
  132 | });
  133 | 
  134 | 
  135 | 
  136 | 
```