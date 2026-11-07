import { test, expect } from '@playwright/test';
import { writeFileSync } from 'node:fs';
import path from 'node:path';
import { createAndApprove, comparison, readApi, quoteCard } from '../../../e2e/helpers';

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

for (const mode of ['delivery','mixed','pdf']) test(`${mode} instructions and owned source disclosures`, async ({page}) => {
  writeFileSync(path.join(process.env.SOURCEPILOT_QA_OUTPUT_DIR!, 'mode.txt'),mode);
  const {id} = await createAndApprove(page);
  const list = await readApi<{ suppliers: SupplierChoice[] }>(page,`/projects/${id}/suppliers`);
  let selected = list.suppliers.filter((s)=>s.shortlisted);
  if(mode !== 'pdf') {
    const willow = required(selected.find((s)=>s.name==='Willow Stitch Studio'));
    const sunrise = required(list.suppliers.find((s)=>s.name==='Sunrise Textile Lab'));
    expect((await page.request.patch(`/api/projects/${id}/suppliers/${willow.id}`,{data:{shortlisted:false}})).ok()).toBeTruthy();
    expect((await page.request.patch(`/api/projects/${id}/suppliers/${sunrise.id}`,{data:{shortlisted:true}})).ok()).toBeTruthy();
    expect((await page.request.post(`/api/projects/${id}/shortlist/approve`,{data:{}})).ok()).toBeTruthy();
    selected = [...selected.filter((s)=>s.id!==willow.id),sunrise];
    for(const s of selected) {
      const response = await page.request.post(`/api/projects/${id}/quotes/manual`,{data:{supplier_id:s.id,values:{unit_price:'4.50',currency:'USD',quoted_quantity:2000,moq:500,production_lead_time:'25 days',packaging_cost:'0'}}});
      expect(response.ok()).toBeTruthy();const q=await response.json();
      expect((await page.request.post(`/api/quotes/${q.id}/confirm`,{data:{}})).ok()).toBeTruthy();
    }
  } else {
    for(const i of [0,1]) {
      await quoteCard(page,i).getByLabel('Upload PDF quote').setInputFiles(path.resolve(__dirname,'../../../../../apps/api/tests/fixtures/quote_pdfs',i===0?'harbor_primary.pdf':'willow_primary.pdf'));
      await expect(quoteCard(page,i)).toContainText('Status: NEEDS REVIEW');
    }
    const quotes=await readApi<{ id: string }[]>(page,`/projects/${id}/quotes`);
    for(const q of quotes) {
      expect((await page.request.patch(`/api/quotes/${q.id}`,{data:{values:{unit_price:'4.75',packaging_cost:'0'}}})).ok()).toBeTruthy();
      expect((await page.request.post(`/api/quotes/${q.id}/confirm`,{data:{}})).ok()).toBeTruthy();
    }
  }
  await page.reload();await comparison(page);
  const before=await readApi<Snapshot>(page,`/projects/${id}/comparison`);
  const project=await readApi(page,`/projects/${id}`),quotes=await readApi(page,`/projects/${id}/quotes`);
  const result=page.waitForResponse(r=>r.url().endsWith('/comparison/advice')&&r.request().method()==='POST');
  await page.getByRole('region',{name:'Comparison',exact:true}).getByRole('button',{name:'Analyze Comparison',exact:true}).click();
  const response=await result;expect(response.ok(),await response.text()).toBeTruthy();const advice: Advice=await response.json();
  const output=page.getByRole('region',{name:'Comparison analysis',exact:true});await expect(output).toBeVisible();
  const actions=advice.analysis.key_tradeoffs.filter((p)=> /^(Ask |Verify )/.test(p.text)||p.text.includes('Reconcile the source records'));
  expect(actions).toHaveLength(mode==='pdf'?4:6);
  expect(new Set(actions.map((p)=>p.text)).size).toBe(actions.length);
  const checked=[];
  for(const [i,p] of actions.entries()) {
    const owner=required(before.comparison_payload.suppliers.find((s)=>s.supplier_id===p.supplier_ids[0]));
    expect(p.supplier_ids).toHaveLength(1);expect(p.text).toContain(owner.supplier_name);
    const li=output.locator('li').filter({has:page.getByText(p.text,{exact:true})}).first();await expect(li).toBeVisible();
    const details=li.locator('details');
    for(const detail of await details.all()){await detail.locator('summary').click();await expect(detail).toHaveAttribute('open','');}
    for(const eid of p.evidence_ids) await expect(li).toContainText(eid);
    for(const ref of p.quote_fields) {
      expect(ref.quote_id).toBe(owner.quote_id);
      const field=owner.quote_fields.find((f)=>f.field_key===ref.field_key);
      if(field) await expect(li).toContainText(field.source_reference);
    }
    for(const rid of p.requirement_ids) {
      const req=required(before.comparison_payload.brief.requirements.find((r)=>r.id===rid));
      expect(p.text).toContain(req.expected_value.value);await expect(li).toContainText('Expected:');
    }
    if(p.text.startsWith('Verify ')) {
      if(p.text.includes('packaging cost')) expect(p.text).toContain('USD 0.');
      if(mode==='pdf'&&p.text.includes('unit price')) {
        expect(p.text).toContain('USD 4.75.');expect(p.text).toContain('Current user-corrected value');
        await expect(li).toContainText('Original PDF provenance');await expect(li).toContainText('provenance only');
      }
    }
    await li.screenshot({path:test.info().outputPath(`action-${i+1}.png`)});
    checked.push({text:p.text,source_disclosures:await details.count(),visible:await li.innerText(),references:p});
  }
  if(mode==='mixed') {
    expect(actions.some((p)=>p.text.includes('bsci'))).toBeTruthy();
    expect(actions.some((p)=>p.text.includes('iso 9001'))).toBeTruthy();
    expect(actions.some((p)=>p.text.includes('CONFLICT')&&p.text.includes('Reconcile'))).toBeTruthy();
  }
  if(mode==='pdf') {
    await expect(output).toContainText('Suggested Supplier to Investigate First');
    const suggestedId = advice.suggestion.supplier_id;
    if (suggestedId === null) throw new Error('The PDF fixture requires a suggested supplier.');
    for(const p of actions.filter((p)=>p.supplier_ids.includes(suggestedId))) {
      expect(advice.suggestion.tradeoffs).toContainEqual(p);
      await expect(output.getByText(p.text,{exact:true})).toHaveCount(2);
    }
  }
  expect(await readApi(page,`/projects/${id}/comparison`)).toEqual(before);
  expect(await readApi(page,`/projects/${id}`)).toEqual(project);
  expect(await readApi(page,`/projects/${id}/quotes`)).toEqual(quotes);
  writeFileSync(test.info().outputPath('evidence.json'),JSON.stringify({mode,snapshot:before,advice,checked,inputs_unchanged:true},null,2));
  writeFileSync(test.info().outputPath('analysis.txt'),await output.innerText());
});
