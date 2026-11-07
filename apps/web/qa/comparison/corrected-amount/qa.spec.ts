import { test, expect } from '@playwright/test';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { comparison, readApi } from '../../../e2e/helpers';

type SupplierChoice = { id: string; name: string; shortlisted: boolean };
type Evidence = { id: string; value: string };
type QuoteField = { field_key: string; current_value: string | number | null;
  ai_extracted_value: string | null; source_reference: string; evidence: Evidence[] };
type Snapshot = { comparison_payload: {
  suppliers: { supplier_id: string; supplier_name: string; quote_id: string; quote_fields: QuoteField[] }[];
  brief: { requirements: { id: string; expected_value: { value: string } }[] };
} };
type AnalysisPoint = { text: string; supplier_ids: string[]; requirement_ids: string[];
  evidence_ids: string[]; quote_fields: { quote_id: string; field_key: string }[] };
type Advice = { analysis: { key_tradeoffs: AnalysisPoint[] };
  suggestion: { supplier_id: string | null; tradeoffs: AnalysisPoint[] } };
function required<T>(value: T | undefined): T {
  if (value === undefined) throw new Error('Required synthetic fixture item is missing.');
  return value;
}

for (const mode of ['suggestion', 'null']) test(`${mode}: corrected amount and provenance`, async ({page}) => {
  writeFileSync(path.join(process.env.SOURCEPILOT_QA_OUTPUT_DIR!, 'mode.txt'), mode);
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Your sourcing projects'})).toBeVisible();
  await expect(page.getByText('Loading projects…',{exact:true})).toBeHidden();
  async function request<T = unknown>(method: string, url: string, data?: Record<string, unknown>): Promise<T> {
    const response = await page.request.fetch('/api'+url,{method,data});
    expect(response.ok(), await response.text()).toBeTruthy();
    return response.json();
  }
  const project = await request<{ id: string }>('POST','/projects',{name:`Isolated corrected amount QA ${mode}`,original_request:'Synthetic equivalent fixture; provider-free QA'});
  const id = project.id;
  const brief = await request<{ brief_revision: number }>('PATCH',`/projects/${id}/brief`,{
    product_name:'Cosmetic travel bags',category:'cosmetic travel bag',quantity:2000,destination:'Manila',
    delivery_target:{kind:'DATE',date:'2027-03-01'},target_unit_price:null,requirements:[
      {kind:'MATERIAL',importance:'REQUIRED',expected_value:{value:'recycled polyester'}},
      {kind:'CAPABILITY',importance:'REQUIRED',expected_value:{capability_key:'CUSTOM_BRANDING',value:true}},
      {kind:'CERTIFICATION',importance:'PREFERRED',expected_value:{value:'grs'}}]});
  await request('POST',`/projects/${id}/brief/approve`,{expected_brief_revision:brief.brief_revision});
  await request('POST',`/projects/${id}/suppliers/discover`);
  const suppliers = (await readApi<{ suppliers: SupplierChoice[] }>(page,`/projects/${id}/suppliers`)).suppliers;
  const harbor = required(suppliers.find((s)=>s.name==='Harbor Pouch Works'));
  const moss = required(suppliers.find((s)=>s.name==='Moss Thread Bags'));
  for(const s of [harbor,moss]) await request('PATCH',`/projects/${id}/suppliers/${s.id}`,{shortlisted:true});
  await request('POST',`/projects/${id}/shortlist/approve`);
  const upload=await page.request.post(`/api/projects/${id}/quotes/upload`,{multipart:{supplier_id:harbor.id,
    file:{name:'isolated-currency-conflict.pdf',mimeType:'application/pdf',buffer:readFileSync(path.join(__dirname,'../../../../../apps/api/tests/fixtures/comparison_advice/currency-conflict.pdf'))}}});
  expect(upload.ok(),await upload.text()).toBeTruthy(); const qid=(await upload.json()).quote.id;
  await expect.poll(async()=> (await readApi<{ status: string }>(page,`/quotes/${qid}`)).status).toBe('NEEDS_REVIEW');
  await request('PATCH',`/quotes/${qid}`,{values:{unit_price:'4.50'}});
  await request('POST',`/quotes/${qid}/confirm`);
  const manual=await request<{ id: string }>('POST',`/projects/${id}/quotes/manual`,{supplier_id:moss.id,values:{unit_price:'4.10',currency:'USD',quoted_quantity:5000,moq:800,production_lead_time:'37 days',packaging_cost:'0'}});
  await request('POST',`/quotes/${manual.id}/confirm`);
  await page.goto(`/projects/${id}`); await comparison(page);
  const before=await readApi<Snapshot>(page,`/projects/${id}/comparison`);
  const quotes=await readApi(page,`/projects/${id}/quotes`);
  const projectBefore=await readApi(page,`/projects/${id}`);
  const owner=required(before.comparison_payload.suppliers.find((s)=>s.supplier_id===harbor.id));
  const price=required(owner.quote_fields.find((f)=>f.field_key==='unit_price'));
  const currency=required(owner.quote_fields.find((f)=>f.field_key==='currency'));
  expect(price.current_value).toBe('4.50');expect(price.ai_extracted_value).toBe('4.22');
  expect(currency.current_value).toBeNull();expect(currency.evidence.map((e)=>e.value).sort()).toEqual(['EUR','USD']);
  const pending=page.waitForResponse(r=>r.url().endsWith('/comparison/advice')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Analyze Comparison',exact:true}).click();
  const response=await pending;expect(response.ok(),await response.text()).toBeTruthy();const advice: Advice=await response.json();
  const output=page.getByRole('region',{name:'Comparison analysis',exact:true});await expect(output).toBeVisible();
  const point=required(advice.analysis.key_tradeoffs.find((p)=>p.text.includes('Reconcile')&&p.text.includes('unit price')));
  expect(point.text).toContain('Current user-corrected amount: 4.50 (no currency assigned).');
  expect(point.text).toContain('currency is CONFLICT.');expect(point.text).not.toMatch(/4\.22|USD|EUR/);
  expect(point.quote_fields).toEqual([{quote_id:qid,field_key:'unit_price'},{quote_id:qid,field_key:'currency'}]);
  expect(point.evidence_ids).toEqual([...new Set([...price.evidence,...currency.evidence].map((e)=>e.id))]);
  const li=output.locator('li').filter({has:page.getByText(point.text,{exact:true})}).first();
  await li.scrollIntoViewIfNeeded();await expect(li.getByText(point.text,{exact:true})).toBeInViewport();
  await li.screenshot({path:test.info().outputPath('current-collapsed.png')});
  expect(await li.innerText()).not.toContain('4.22');
  for(const detail of await li.locator('details').all()) await detail.locator('summary').click();
  await expect(li.getByText('Current user-corrected value: 4.50',{exact:true})).toBeVisible();
  await expect(li.getByText('Original extracted value: 4.22',{exact:true})).toBeVisible();
  await expect(li).toContainText('Currency conflict remains unresolved; no currency is assigned to this amount.');
  await expect(li).toContainText('does not verify the correction');
  for(const f of [price,currency]) {await expect(li).toContainText(f.source_reference);for(const e of f.evidence) await expect(li).toContainText(e.id);}
  for(const p of await li.locator('p').all()) if((await p.innerText()).includes('4.22')) expect(await p.innerText()).toMatch(/^Original (extracted value|PDF provenance):/);
  await li.screenshot({path:test.info().outputPath('current-expanded.png')});
  const visible=await output.innerText();expect(visible).not.toMatch(/(?:USD|EUR) 4\.50|4\.50 (?:USD|EUR)/);
  expect(visible).toContain('Do not treat these prices as equivalent quantities');expect(visible).toContain('No currency conversion has been performed');
  expect(visible).toContain('2000');expect(visible).toContain('5000');
  await expect(output).toContainText(mode==='null'?'No supplier suggested yet':'Suggested Supplier to Investigate First');
  expect(await readApi(page,`/projects/${id}/comparison`)).toEqual(before);
  expect(await readApi(page,`/projects/${id}/quotes`)).toEqual(quotes);
  expect(await readApi(page,`/projects/${id}`)).toEqual(projectBefore);expect(errors).toEqual([]);
  writeFileSync(test.info().outputPath('evidence.json'),JSON.stringify({mode,snapshot:before,advice,inputs_unchanged:true,console_errors:errors},null,2));
  writeFileSync(test.info().outputPath('analysis.txt'),visible);
});
