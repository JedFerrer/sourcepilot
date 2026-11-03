"""One authorized invocation of the existing filtered baseline runner; no outer retry."""
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from alembic.config import Config
from alembic.script import ScriptDirectory
from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai.eval_live import preflight_database, validate_database_isolation, run_case
from sourcepilot.ai.client import OpenAIResponsesClient, ai_settings_from_environment
from sourcepilot.persistence.base import Base
import sourcepilot.persistence.models

logging.disable(logging.CRITICAL)
root = Path.cwd().parents[1]
out = Path(__file__).resolve().parent
with (out / 'execution-started').open('x') as marker:
    marker.write(datetime.now(UTC).isoformat())

def save(name, value):
    with (out / name).open('x', encoding='utf-8') as target:
        json.dump(value, target, indent=2)
        target.write('\n')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

def snapshot(engine):
    result = {}
    with engine.connect() as connection:
        connection.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY'))
        for table in Base.metadata.sorted_tables:
            result[table.name] = {
                tuple(str(row[col.name]) for col in table.primary_key): digest(dict(row))
                for row in connection.execute(select(table)).mappings()
            }
    return result

env_bytes = (root / '.env').read_bytes()
config = dotenv_values(root / '.env', interpolate=False)
for key in ('DATABASE_URL', 'TEST_DATABASE_URL', 'EVAL_DATABASE_URL', 'SOURCEPILOT_AI_MODEL', 'OPENAI_API_KEY'):
    if not config.get(key):
        raise SystemExit('Required root configuration missing; no live execution.')
    os.environ[key] = config[key]
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard'], cwd=root, text=True).splitlines()
files_before = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths if (root / p).is_file()}
record = {'started_at': datetime.now(UTC).isoformat(), 'status': 'PENDING', 'databases': {}, 'provider_calls_before_preflight': 0, 'fixture_writes_before_preflight': 0}
engines = {}
snapshots = {}
try:
    assert ai_settings_from_environment().model == 'gpt-6-luna'
    assert make_url(os.environ['EVAL_DATABASE_URL']).database == 'sourcepilot_eval'
    validate_database_isolation(make_url(os.environ['EVAL_DATABASE_URL']))
    cfg = Config()
    cfg.set_main_option('script_location', str(Path.cwd() / 'alembic'))
    heads = set(ScriptDirectory.from_config(cfg).get_heads())
    assert heads
    record['repository_heads'] = sorted(heads)
    engines['eval'] = preflight_database()
    connected = []
    for label, key in [('app', 'DATABASE_URL'), ('test', 'TEST_DATABASE_URL'), ('eval', 'EVAL_DATABASE_URL')]:
        url = make_url(os.environ[key])
        engine = engines.get(label)
        if engine is None:
            engine = create_engine(url, connect_args={'connect_timeout': 5}, pool_pre_ping=True)
            engines[label] = engine
        with engine.connect() as connection:
            connection.execute(text('SET TRANSACTION READ ONLY'))
            identity = connection.execute(text('SELECT current_database(), oid FROM pg_database WHERE datname=current_database()')).one()
            assert identity[0] == url.database
            connected.append(identity[1])
            assert set(connection.scalars(text('SELECT version_num FROM alembic_version'))) == heads
            inspector = inspect(connection)
            for table in Base.metadata.sorted_tables:
                assert set(table.columns.keys()) <= {col['name'] for col in inspector.get_columns(table.name)}
            assert connection.scalar(text('SHOW transaction_read_only')) == 'on'
            record['databases'][label] = {'connectivity': 'PASS', 'identity_matches': True, 'read_only': True, 'schema': 'PASS', 'required_tables': len(Base.metadata.tables), 'heads_match': True}
        snapshots[label] = snapshot(engine)
    assert len(set(connected)) == 3
    record['connected_isolation'] = 'PASS'

    scope = baseline.load_scope(['quote_extraction'])
    assert len(scope['quote_extraction']) == 12
    assert sum('expected_error' in case for case in scope['quote_extraction']) == 2
    from sourcepilot.ai.quote_extractor import QuoteExtraction
    schema_hash = hashlib.sha256(json.dumps(QuoteExtraction.model_json_schema(), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    assert schema_hash == '79906b87def4657c4e7c5b9327f4c0f6791051e79c039a485d44e804396139fb'
    record['corrected_schema_sha256'] = schema_hash
    record['model'] = ai_settings_from_environment().model
    record['selected_case_ids'] = [case['id'] for case in scope['quote_extraction']]
    record['status'] = 'PASS'
except Exception as error:
    record['status'] = 'BLOCKED'
    record['error_type'] = type(error).__name__
finally:
    record['completed_at'] = datetime.now(UTC).isoformat()
    save('preflight.json', record)
if record['status'] != 'PASS':
    for engine in engines.values(): engine.dispose()
    print('Preflight BLOCKED. Zero provider calls; zero fixture writes.')
    raise SystemExit(2)
print('Read-only preflight PASS. Running the existing filtered runner once.', flush=True)
try:
    report, code = baseline.execute('live', ['quote_extraction'], out / 'baseline')
finally:
    preservation = {'databases': {}}
    for label, before in snapshots.items():
        after = snapshot(engines[label])
        preservation['databases'][label] = {
            'existing_rows_unchanged': all(after[t].get(pk) == value for t, rows in before.items() for pk, value in rows.items()),
            'existing_shared_suppliers_unchanged': all(after[sourcepilot.persistence.models.Supplier.__tablename__].get(pk) == value for pk, value in before[sourcepilot.persistence.models.Supplier.__tablename__].items()),
            'additions': {t: len(set(after[t]) - set(rows)) for t, rows in before.items() if set(after[t]) - set(rows)},
        }
        engines[label].dispose()
    preservation['files'] = {'inventoried': len(files_before), 'changed_or_missing': [p for p, value in files_before.items() if not (root / p).is_file() or hashlib.sha256((root / p).read_bytes()).hexdigest() != value]}
    preservation['root_env_unchanged'] = (root / '.env').read_bytes() == env_bytes
    save('preservation.json', preservation)
print(json.dumps({key: report.get(key) for key in ('status','complete','full_scope','executed_case_count','expected_case_count','status_counts','exit_code','error')}), flush=True)
raise SystemExit(code)
