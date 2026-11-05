import os
import sys
import json
import time
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
API = ROOT / 'apps/api'
OUT = ROOT / 'docs/implementation/evidence/M4-U7/linux-corrections'
for key in list(os.environ):
    if key.startswith(('OPENAI_', 'LANGFUSE_')):
        os.environ.pop(key)
for line in (ROOT / '.env').read_text().splitlines():
    key, _, value = line.partition('=')
    if key in {'DATABASE_URL', 'TEST_DATABASE_URL'}:
        os.environ[key] = value.strip().strip('\"').strip("'")
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.environ['PYTHONPATH'] = str(API)
if sys.platform != 'win32':
    os.environ['PATH'] = str(Path.home() / '.cache/sourcepilot-m4u7-linux/node22/bin') + ':' + os.environ['PATH']
os.chdir(API)
name, *args = sys.argv[1:]
start = time.monotonic()
with (OUT / (name + '.txt')).open('w') as log:
    result = subprocess.run([sys.executable, *args], stdout=log, stderr=subprocess.STDOUT)
(OUT / (name + '.json')).write_text(json.dumps({
    'command': [sys.executable, *args], 'exit_code': result.returncode,
    'seconds': time.monotonic() - start, 'platform': platform.platform(),
}, indent=2))
print(name, result.returncode, time.monotonic() - start, flush=True)
sys.exit(result.returncode)
