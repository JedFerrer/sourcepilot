"""Preserve the exact historical transport test, checking its retained hash."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[5]
path = 'apps/api/tests/test_comparison_transport.py'
value = (root / path).read_text()
value = value.replace('from types import SimpleNamespace\n', '')
value = value.replace('from sourcepilot.comparison.deadline import (\n    ComparisonDeadline,\n    ComparisonDeadlineError,\n    ComparisonTimeouts,\n    current_deadline,\n)',
                      'from sourcepilot.comparison.deadline import ComparisonDeadline, ComparisonTimeouts, current_deadline')
value = value.replace('    sdk_clients = []\n', '')
value = value.replace('        assert kwargs["http_client"] is clients[0]\n        return sdk_clients[0]',
'''        http = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        clients.append(http)
        return SDKAsyncOpenAI(api_key="synthetic-test-key", max_retries=0,
                             timeout=0.05, http_client=http)''')
value = value.replace('    tls, _ = prepare_comparison_transport()', '    prepare_comparison_transport()')
start = value.index('        # This test isolates cancellation')
end = value.index('        deadline = ComparisonDeadline', start)
value = value[:start] + value[end:]
value = value.replace('            assert len(clients) == 1\n', '')
value = value.replace('            await sdk.close()\n', '', 1)
start = value.index('def test_request_time_construction_exhaustion')
end = value.index('def test_external_cancellation', start)
value = value[:start] + value[end:]
prior = json.loads((root / 'docs/implementation/evidence/M4-U7/linux-verification/manifest.json').read_text())
hashes = next(item for item in prior.values() if isinstance(item, dict) and path in item)
variants = [value.encode(), value.replace('\n', '\r\n').encode()]
exact = next((item for item in variants if hashlib.sha256(item).hexdigest() == hashes[path]), None)
assert exact is not None, 'Historical source reconstruction does not match the retained manifest'
out = root / 'docs/implementation/evidence/M4-U7/linux-corrections/transport-before-correction.py.txt'
out.write_bytes(exact)
print('Historical transport source matches retained SHA-256:', hashes[path])
