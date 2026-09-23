from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker


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
