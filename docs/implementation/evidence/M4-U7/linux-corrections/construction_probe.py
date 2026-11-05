import gc
import json
import time
import sys
from pathlib import Path
import httpx
import pytest
from openai import AsyncOpenAI

events = []
active = False
original = httpx.AsyncClient.__init__
sdk_original = AsyncOpenAI.__init__

def sdk_initialize(self, *args, **kwargs):
    started = time.monotonic()
    try:
        return sdk_original(self, *args, **kwargs)
    finally:
        if active:
            events.append({'kind': 'sdk', 'seconds': time.monotonic() - started})

def initialize(self, *args, **kwargs):
    started = time.monotonic()
    try:
        return original(self, *args, **kwargs)
    finally:
        if active:
            events.append({'kind': 'client', 'seconds': time.monotonic() - started,
                           'verify': type(kwargs.get('verify')).__name__,
                           'transport': type(kwargs.get('transport')).__name__})

def collection(phase, info):
    if active:
        events.append({'kind': 'gc', 'phase': phase, 'time': time.monotonic(), **info})

class Probe:
    def pytest_collection_modifyitems(self, items):
        if '--full' in sys.argv or '--retained-prefix' in sys.argv:
            return
        last = next(i for i, item in enumerate(items) if item.nodeid.endswith(
            'test_sdk_attempt_cancels_transport_and_never_retries[headers]'))
        del items[last + 1:]

    def pytest_runtest_setup(self, item):
        global active
        active = 'test_comparison_transport.py' in item.nodeid

    def pytest_runtest_logreport(self, report):
        if ('--retained-prefix' in sys.argv and report.when == 'teardown'
                and report.nodeid.endswith('test_sdk_attempt_cancels_transport_and_never_retries[headers]')):
            pytest.exit('Intentional diagnostic stop after header; full collection retained.', returncode=0)

    def pytest_sessionfinish(self):
        name = ('construction-full.json' if '--full' in sys.argv else
                'construction-retained.json' if '--retained-prefix' in sys.argv else 'construction.json')
        Path('../../docs/implementation/evidence/M4-U7/linux-corrections', name).write_text(
            json.dumps(events, indent=2))

httpx.AsyncClient.__init__ = initialize
AsyncOpenAI.__init__ = sdk_initialize
gc.callbacks.append(collection)
raise SystemExit(pytest.main(['-q', '--maxfail=0'], plugins=[Probe()]))
