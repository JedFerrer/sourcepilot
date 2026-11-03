import json,sys
from pathlib import Path
from uuid import UUID
from dotenv import dotenv_values
from sqlalchemy import create_engine,select,text
from sqlalchemy.orm import Session
sys.path.insert(0,str(Path.cwd()))
from sourcepilot.ai import eval_baseline as b
from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis,validate_analysis,_current_snapshot
from sourcepilot.ai.comparison_advice import ComparisonAdvice,validate_advice
from sourcepilot.persistence.models import AIRun
out=Path(__file__).resolve().parent
root=Path.cwd().parents[1]
report=json.loads((out/'baseline/results.json').read_text())
old=json.loads((root/'docs/implementation/evidence/M6-U1/final-full-live-2026-11-03-01/baseline/results.json').read_text())
prior={(c['category'],c['id']):c for c in old['cases']}
engine=create_engine(dotenv_values(root/'.env',interpolate=False)['EVAL_DATABASE_URL'])
rows=[]
with Session(engine) as session:
    session.execute(text('SET TRANSACTION READ ONLY'))
    for c in report['cases']:
        row={'category':c['category'],'id':c['id'],'baseline_status':prior[c['category'],c['id']]['status'],'status':c['status'],'air_run':c.get('air_run'),'failed_assertions':[a for a in c['assertions'] if b.check_failed(a)]}
        if c.get('air_run'):
            run=session.get(AIRun,UUID(c['air_run']['id']))
            row['steps']=[{'sequence':s.sequence,'kind':s.kind,'outcome':s.outcome,'name':s.name} for s in sorted(run.supplier_explanation_steps,key=lambda s:s.sequence)]
            row['repairs']=sum(s['outcome']=='REPAIR' for s in row['steps'])
            snapshot=_current_snapshot(session,demo_session_id=run.demo_session_id,project_id=run.project_id)
            model,validate=(TradeoffAnalysis,validate_analysis) if c['category']=='comparison' else (ComparisonAdvice,validate_advice)
            row['final_validations']=[]
            for response in c['model_responses']:
                if response.get('tool_calls'):continue
                entry={}
                try:
                    parsed=model.model_validate_json(response['output_text'])
                    entry['schema']='PASS'
                    validate(parsed,snapshot)
                    entry['semantic']='PASS'
                except ValueError as error:
                    entry['result']='FAIL';entry['reason']=str(error)
                row['final_validations'].append(entry)
        rows.append(row)
engine.dispose()
assert b.hash_files(b.consumed_files(b.load_scope(['comparison','suggestion']),'live'))==report['provenance']['files']
assert old['human_review']['case_count']==10 and old['human_review']['status']=='PENDING' and all(c['review_result'] is None for c in old['human_review']['cases'])
result={'cases':rows,'source_hashes_unchanged':True,'human_review':'10 PENDING/null; filtered report retains its selected subset','historical_baseline':'final-full-live-2026-11-03-01','status_counts':report['status_counts']}
with (out/'inspection.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
print(json.dumps(result,indent=2))
