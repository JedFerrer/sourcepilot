"""Test-only stalled model boundary; original app owns the actual deadline."""
import asyncio
from pathlib import Path
from sqlalchemy.util import await_only
from tests.e2e_support.model import DeterministicModel
from tests.e2e_support.server import main
from sourcepilot.ai.comparison_advice import ComparisonAdvice

mode = Path(__file__).with_name('fault-mode.txt')
original = DeterministicModel.invoke_with_tools
def controlled(self, **kwargs):
    if mode.exists() and mode.read_text() == 'deadline' and kwargs['schema_name'] == ComparisonAdvice.__name__:
        await_only(asyncio.sleep(3600))
    return original(self, **kwargs)
DeterministicModel.invoke_with_tools = controlled
if __name__ == '__main__':
    main()
