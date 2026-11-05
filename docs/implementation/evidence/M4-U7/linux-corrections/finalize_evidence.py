"""Verify retained results/source and write the correction evidence index."""
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path

out = Path(__file__).resolve().parent
root = out.parents[4]
manifest = json.loads((out / 'final-source-manifest.json').read_text())
windows = json.loads((out / 'windows-runtime-manifest.json').read_text())
assert manifest['source_sha256'] == windows['source_sha256']
for name, digest in manifest['source_sha256'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
confirmation = json.loads((out / 'source-confirmation.json').read_text())
assert confirmation['unchanged'] and confirmation['historical_linux_artifacts_unchanged']

checks = {}
for name in [
    'linux-targeted-final', 'linux-backend-final', 'linux-ruff-final',
    'linux-pyright-final', 'linux-offline-final', 'windows-targeted-final',
    'windows-harness-final', 'windows-ruff-final', 'windows-pyright-final',
]:
    record = json.loads((out / (name + '.json')).read_text())
    assert record['exit_code'] == 0, name
    checks[name] = record
for name, expected in [
    ('linux-targeted-final', 430), ('linux-backend-final', 3677),
    ('windows-targeted-final', 430), ('windows-harness-final', 68),
]:
    matches = re.findall(r'(\d+) passed', (out / (name + '.txt')).read_text())
    assert int(matches[-1]) == expected, name
    checks[name]['passed'] = expected
offline = json.loads((out / 'linux-offline-final/results.json').read_text())
assert offline['complete'] and offline['executed_case_count'] == 90
assert offline['status'] == 'COMPLETED'

result = {
    'recorded_at_utc': datetime.now(UTC).isoformat(),
    'disposition': 'Automated checks passed; independent review pending',
    'unit_status': 'IN_REVIEW',
    'source_files_verified': len(manifest['source_sha256']),
    'source_unchanged': True,
    'historical_linux_evidence_unchanged': True,
    'checks': checks,
    'frontend': {'tests_passed': 77, 'lint_exit': 0, 'typecheck_exit': 0, 'build_exit': 0,
                 'exit_evidence': 'Observed tool exits; retained windows-web/build logs'},
    'linux_node': '22.14.0',
    'offline_completed': 90,
    'natural_historical_transport_failure_reproduced': False,
    'controlled_construction_failure_reproduced': True,
    'transport_historical_delay_trigger': 'UNPROVEN',
    'browser_qa': 'PENDING', 'done_check': 'PENDING',
    'incident_rejection': 'UNRESOLVED', 'historical_live_quality': 'UNRESOLVED',
    'paid_ai_calls': 0, 'commits': 0,
    'artifact_sha256': {
        str(path.relative_to(out)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(out.rglob('*'))
        if path.is_file() and path.name != 'completion.json'
    },
}
(out / 'completion.json').write_text(json.dumps(result, indent=2) + '\n')
print('Verified', len(manifest['source_sha256']), 'source hashes and all final check records.')
