import sys,json,tempfile,hashlib
from pathlib import Path
from decimal import Decimal
sys.path.insert(0,str(Path.cwd()))
from sourcepilot.ai import eval_baseline as b,quote_extraction_eval as q
from sourcepilot.ai.quote_extractor import QuoteExtraction,validate_source_references
from sourcepilot.quotes.domain import QUOTE_INTEGER_FIELDS,QUOTE_MONEY_FIELDS
out=Path(__file__).resolve().parent
report=json.loads((out/'baseline/results.json').read_text(encoding='utf-8'))
scope=b.load_scope(['quote_extraction'])
lookup={c['id']:c for c in scope['quote_extraction']}
inspection={'cases':[],'measurements':report['measurements'],'critical_findings':report['critical_findings']}
for item in report['cases']:
    case=lookup[item['id']]
    entry={'id':item['id'],'status':item['status'],'air_run':item.get('air_run'),'response_count':len(item.get('model_responses',[])),'exact_assertions_passed':sum(a['passed'] for a in item['assertions'] if a['kind']=='exact'),'exact_assertions_total':sum(a['kind']=='exact' for a in item['assertions']),'failed_assertions':[a for a in item['assertions'] if b.check_failed(a)]}
    if item.get('output') is not None and 'fields' in item['output']:
        with tempfile.TemporaryDirectory() as temp:
            blocks,checks=b.parser_result(case,Path(temp))
        assert blocks and not any(b.check_failed(c) for c in checks)
        draft=QuoteExtraction.model_validate(item['output'])
        texts=q.document_blocks(case)
        validate_source_references(draft,set(texts))
        entry.update({'structured_domain_validation':'PASS','complete_document_membership':'PASS','input_hash_matches_case':item['air_run']['input_hash']==case['request_hash'],'pdf_sha256':hashlib.sha256((b.PDFS/case['pdf']).read_bytes()).hexdigest(),'request_hash':case['request_hash'],'parsed_block_count':len(blocks),'fields':{}})
        evaluated=q.field_evaluations(draft,case)
        for key,field in item['output']['fields'].items():
            values=([field['extracted_value']] if field['state']=='KNOWN' else [a['value'] for a in field['conflicting_values']])
            numeric=[]
            for value in values:
                if key in QUOTE_INTEGER_FIELDS:
                    assert type(value) is int and value>0
                    numeric.append({'value':value,'positive_json_integer':True})
                elif key in QUOTE_MONEY_FIELDS:
                    assert isinstance(value,str) and Decimal(value).is_finite()
                    numeric.append({'value':value,'finite_decimal_string':True})
            entry['fields'][key]={'actual':field,'expected':case['known'].get(key,case['conflicts'].get(key,'UNKNOWN')),'expected_unknown_sources':case.get('unknown_sources',{}).get(key,[]),'evaluation':evaluated[key],'sources':{ref:texts[ref] for ref in field['source_block_ids']},'alternative_sources':[{ref:texts[ref] for ref in a['source_block_ids']} for a in field['conflicting_values']],'numeric_inspection':numeric}
    inspection['cases'].append(entry)
assert b.hash_files(b.consumed_files(scope,'live'))==report['provenance']['files']
inspection['consumed_source_fingerprints_unchanged']=True
old=json.loads((b.ROOT/'docs/implementation/evidence/M6-U1/live-2026-11-01-01/results.json').read_text(encoding='utf-8'))
review=old['human_review']
assert review['status']=='PENDING' and review['case_count']==10 and all(c['review_result'] is None for c in review['cases'])
inspection['historical_human_review']={'status':'PENDING','case_count':10,'null_verdicts':10,'filtered_report_review_count':report['human_review']['case_count']}
inspection['usage']={key:sum((c.get('air_run') or {}).get(key) or 0 for c in report['cases']) for key in ['input_tokens','output_tokens','latency_ms','attempts']}
with (out/'inspection.json').open('x',encoding='utf-8') as target:json.dump(inspection,target,indent=2,ensure_ascii=False)
print(json.dumps({'status':report['status'],'counts':report['status_counts'],'usage':inspection['usage'],'assertions':[(c['id'],c['exact_assertions_passed'],c['exact_assertions_total']) for c in inspection['cases']],'measurements':report['measurements']},indent=2))
