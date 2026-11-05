import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[5]
out = root / 'docs/implementation/evidence/M4-U7/linux-corrections'
prior = json.loads((out.parent / 'linux-verification/manifest.json').read_text())
hashes = next(value for value in prior.values() if isinstance(value, dict)
              and 'apps/api/uv.lock' in value)
current = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in hashes}
for name in ['apps/api/tests/test_eval_baseline.py', 'apps/api/tests/test_eval_live.py']:
    current[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
if sys.argv[1] in {'start', 'windows'}:
    import psycopg.pq
    result = {
        'source_sha256': current,
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'python': sys.version, 'platform': platform.platform(), 'executable': sys.executable,
        'dependencies': {d.metadata['Name']: d.version for d in importlib.metadata.distributions()},
        'libpq': psycopg.pq.version(),
        'changed_since_historical_linux_manifest': [name for name, digest in current.items()
                                                   if hashes.get(name) != digest],
        'paid_calls': 0,
    }
    name = 'windows-runtime-manifest.json' if sys.argv[1] == 'windows' else 'final-source-manifest.json'
    (out / name).write_text(json.dumps(result, indent=2))
else:
    start = json.loads((out / 'final-source-manifest.json').read_text())['source_sha256']
    changed = [name for name, digest in current.items() if start.get(name) != digest]
    previous = json.loads((out.parent / 'linux-verification/completion.json').read_text())
    historical_changes = [name for name, digest in previous['artifact_sha256'].items()
                          if hashlib.sha256((out.parent / 'linux-verification' / name).read_bytes()).hexdigest() != digest]
    (out / 'source-confirmation.json').write_text(json.dumps({
        'unchanged': not changed, 'changed': changed,
        'historical_linux_artifacts_unchanged': not historical_changes,
        'historical_changes': historical_changes,
    }, indent=2))
    assert not changed, changed
    assert not historical_changes, historical_changes
