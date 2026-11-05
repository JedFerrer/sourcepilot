from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.comparison.lifecycle import comparison_loop


@pytest.fixture(autouse=True)
def supported_test_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    original = TestClient.__init__

    def initialize(self: TestClient, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("backend_options", {"loop_factory": comparison_loop})
        original(self, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", initialize)


def database_session_for_engine(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def block_live_openai_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep pytest isolated from the OpenAI network boundary by default."""

    class BlockedResponses:
        def create(self, **kwargs: object) -> None:
            raise AssertionError("Live OpenAI Responses calls are forbidden in pytest.")

    class BlockedOpenAI:
        def __init__(self, *, api_key: str) -> None:
            self.responses = BlockedResponses()

    monkeypatch.setattr("sourcepilot.ai.client.OpenAI", BlockedOpenAI)

    class BlockedAsyncOpenAI:
        def __init__(self, **kwargs: object) -> None:
            raise AssertionError("Live async OpenAI calls are forbidden in pytest.")

    monkeypatch.setattr("sourcepilot.ai.client.AsyncOpenAI", BlockedAsyncOpenAI)
