"""Controlled diagnosis of the historical pre-header failure, not a regression pass."""
import json
import time
from pathlib import Path

import pytest
from openai import AsyncOpenAI
from sourcepilot.comparison.deadline import current_deadline

original = AsyncOpenAI.__init__
events = []

def delayed(self, *args, **kwargs):
    original(self, *args, **kwargs)
    deadline = current_deadline.get()
    if deadline is not None:
        started = time.monotonic()
        time.sleep(1)
        events.append({'injected_seconds': time.monotonic() - started,
                       'work_budget': deadline.settings.total - deadline.settings.cleanup})

AsyncOpenAI.__init__ = delayed
code = pytest.main(['tests/test_comparison_transport.py::test_sdk_attempt_cancels_transport_and_never_retries[headers]', '-q'])
Path('../../docs/implementation/evidence/M4-U7/linux-corrections/controlled-construction.json').write_text(
    json.dumps({'intentional_injection': True, 'pytest_exit': int(code), 'events': events}, indent=2))
raise SystemExit(code)
