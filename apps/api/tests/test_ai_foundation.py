from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import BaseModel
from sqlalchemy import Engine, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.ai.client import (
    AISettings,
    AnalystModelInvocation,
    ModelInvocation,
    ModelProviderError,
    OpenAIResponsesClient,
    ai_settings_from_environment,
)
from sourcepilot.ai.smoke import FOUNDATION_SMOKE_PROMPT_VERSION
from sourcepilot.ai.structured import (
    COMPLETED,
    FAILED,
    PROVIDER_FAILED,
    REPAIRED,
    VALIDATION_FAILED,
    run_structured_operation,
    structured_input_hash,
)
from sourcepilot.persistence.models import AIRun, DemoSession
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


class Answer(BaseModel):
    answer: str


class FakeClient:
    model = "test-model"

    def __init__(
        self,
        outcomes: list[ModelInvocation | Exception],
        on_call: Callable[[], None] | None = None,
    ) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, object]] = []
        self.on_call = on_call

    def invoke(self, **kwargs: object) -> ModelInvocation:
        self.calls.append(kwargs)
        if self.on_call is not None:
            self.on_call()
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def invoke_with_tools(self, **kwargs: object) -> AnalystModelInvocation:
        raise AssertionError("Tool calls are outside these structured-operation tests.")


@pytest.fixture(scope="module")
def test_database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def test_engine(test_database_url: str) -> Iterator[Engine]:
    engine = create_test_engine(test_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(autouse=True)
def reset_ai_database(test_database_url: str) -> Iterator[None]:
    reset_test_database(test_database_url)
    yield
    reset_test_database(test_database_url)


@pytest.fixture
def database_session(test_engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=test_engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


def demo_session(database_session: Session) -> DemoSession:
    now = datetime.now(UTC)
    session = DemoSession(
        opaque_token="ai-foundation-session",
        last_seen_at=now,
        expires_at=now + timedelta(hours=1),
    )
    database_session.add(session)
    database_session.commit()
    return session


def run_for_test(
    database_session: Session, client: FakeClient
) -> tuple[Answer | None, AIRun]:
    return run_structured_operation(
        database_session,
        demo_session=demo_session(database_session),
        project_id=None,
        operation="test_operation",
        prompt_version="test-v1",
        instructions="Return an answer.",
        input_text="Hello",
        result_model=Answer,
        client=client,
        sleep=lambda _: None,
    )


def test_success_persists_one_complete_ai_run(database_session: Session) -> None:
    result, air_run = run_for_test(
        database_session,
        FakeClient([ModelInvocation('{"answer":"ok"}', input_tokens=3, output_tokens=2)]),
    )
    database_session.expire_all()
    stored = database_session.get(AIRun, air_run.id)

    assert result == Answer(answer="ok")
    assert stored is not None
    assert stored.status == COMPLETED
    assert stored.attempts == 1
    assert stored.validation_status == "VALID"
    assert stored.completed_at is not None
    assert stored.model_turn_count is None
    assert stored.tool_call_count is None
    assert stored.input_hash == structured_input_hash(
        instructions="Return an answer.", input_text="Hello"
    )


def test_air_run_is_committed_as_running_before_the_first_provider_call(
    database_session: Session, test_engine: Engine
) -> None:
    observed_statuses: list[str] = []

    def inspect_before_response() -> None:
        with Session(test_engine) as inspection_session:
            status = inspection_session.scalar(select(AIRun.status))
            assert status is not None
            observed_statuses.append(status)

    run_for_test(
        database_session,
        FakeClient(
            [ModelInvocation('{"answer":"ok"}', input_tokens=1, output_tokens=1)],
            on_call=inspect_before_response,
        ),
    )

    assert observed_statuses == ["RUNNING"]


def test_invalid_first_response_uses_schema_repair(database_session: Session) -> None:
    client = FakeClient(
        [
            ModelInvocation("not json", input_tokens=1, output_tokens=1),
            ModelInvocation('{"answer":"repaired"}', input_tokens=2, output_tokens=2),
        ]
    )
    result, air_run = run_for_test(database_session, client)

    assert result == Answer(answer="repaired")
    assert air_run.status == COMPLETED
    assert air_run.attempts == 2
    assert air_run.validation_status == REPAIRED
    assert air_run.error_type is None
    assert len(client.calls) == 2
    assert "Repair the JSON schema failure" in str(client.calls[1]["instructions"])


def test_provider_retry_then_invalid_output_uses_schema_repair(database_session: Session) -> None:
    client = FakeClient(
        [
            ModelProviderError("temporary", retryable=True),
            ModelInvocation("not json", input_tokens=1, output_tokens=1),
            ModelInvocation('{"answer":"repaired"}', input_tokens=2, output_tokens=2),
        ]
    )
    result, air_run = run_for_test(database_session, client)

    assert result == Answer(answer="repaired")
    assert air_run.status == COMPLETED
    assert air_run.validation_status == REPAIRED
    assert air_run.error_type == ModelProviderError.__name__
    assert air_run.attempts == 3
    assert len(client.calls) == 3


def test_repair_provider_failure_uses_provider_retry(database_session: Session) -> None:
    client = FakeClient(
        [
            ModelInvocation("not json", input_tokens=1, output_tokens=1),
            ModelProviderError("temporary", retryable=True),
            ModelInvocation('{"answer":"repaired"}', input_tokens=2, output_tokens=2),
        ]
    )
    result, air_run = run_for_test(database_session, client)

    assert result == Answer(answer="repaired")
    assert air_run.status == COMPLETED
    assert air_run.validation_status == REPAIRED
    assert air_run.attempts == 3
    assert len(client.calls) == 3
    assert "Repair the JSON schema failure" in str(client.calls[2]["instructions"])


def test_second_invalid_output_exhausts_repair_budget(database_session: Session) -> None:
    client = FakeClient(
        [
            ModelInvocation("not json", input_tokens=1, output_tokens=1),
            ModelInvocation("still not json", input_tokens=2, output_tokens=2),
        ]
    )
    result, air_run = run_for_test(database_session, client)

    assert result is None
    assert air_run.status == VALIDATION_FAILED
    assert air_run.validation_status == "INVALID"
    assert air_run.attempts == 2
    assert len(client.calls) == 2


def test_two_provider_failures_persist_one_terminal_run(database_session: Session) -> None:
    client = FakeClient(
        [
            ModelProviderError("temporary", retryable=True),
            ModelProviderError("temporary", retryable=True),
        ]
    )
    result, air_run = run_for_test(database_session, client)

    assert result is None
    assert air_run.status == PROVIDER_FAILED
    assert air_run.attempts == 2
    assert len(client.calls) == 2


def test_successful_provider_retry_preserves_its_retryable_failure(
    database_session: Session,
) -> None:
    result, air_run = run_for_test(
        database_session,
        FakeClient(
            [
                ModelProviderError("temporary", retryable=True),
                ModelInvocation('{"answer":"ok"}', input_tokens=2, output_tokens=1),
            ]
        ),
    )

    assert result == Answer(answer="ok")
    assert air_run.status == COMPLETED
    assert air_run.attempts == 2
    assert air_run.validation_status == "VALID"
    assert air_run.error_type == ModelProviderError.__name__


def test_unexpected_error_finalizes_the_running_air_run_before_propagating(
    database_session: Session,
) -> None:
    with pytest.raises(RuntimeError, match="unexpected"):
        run_for_test(database_session, FakeClient([RuntimeError("unexpected")]))

    database_session.expire_all()
    stored = database_session.scalar(select(AIRun))

    assert stored is not None
    assert stored.status == FAILED
    assert stored.error_type == RuntimeError.__name__
    assert stored.completed_at is not None


def test_migration_includes_nullable_ai_run_counts(test_engine: Engine) -> None:
    columns = {column["name"]: column for column in inspect(test_engine).get_columns("ai_runs")}

    assert columns["model_turn_count"]["nullable"] is True
    assert columns["tool_call_count"]["nullable"] is True


def test_openai_wrapper_uses_structured_responses_without_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs: object) -> object:
            captured.update(kwargs)
            return type(
                "Response",
                (),
                {"output_text": '{"answer":"ok"}', "usage": type("Usage", (), {"input_tokens": 1, "output_tokens": 1})()},
            )()

    class FakeOpenAI:
        def __init__(self, *, api_key: str) -> None:
            self.responses = FakeResponses()

    monkeypatch.setattr("sourcepilot.ai.client.OpenAI", FakeOpenAI)
    client = OpenAIResponsesClient(AISettings(api_key="test-key", model="test-model"))
    client.invoke(
        instructions="Return JSON.",
        input_text="hello",
        schema_name="Answer",
        schema=Answer.model_json_schema(),
    )

    assert captured["store"] is False
    assert captured["model"] == "test-model"
    assert captured["text"] == {
        "format": {
            "type": "json_schema",
            "name": "Answer",
            "strict": True,
            "schema": Answer.model_json_schema(),
        }
    }


def test_pytest_guard_blocks_an_accidental_openai_responses_invocation() -> None:
    client = OpenAIResponsesClient(AISettings(api_key="test-key", model="test-model"))

    with pytest.raises(ModelProviderError, match="forbidden in pytest"):
        client.invoke(
            instructions="Return JSON.",
            input_text="hello",
            schema_name="Answer",
            schema=Answer.model_json_schema(),
        )


def test_ai_settings_are_required_only_when_an_ai_operation_constructs_a_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("SOURCEPILOT_AI_MODEL", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        ai_settings_from_environment()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="SOURCEPILOT_AI_MODEL"):
        ai_settings_from_environment()


def test_foundation_smoke_uses_the_approved_prompt_identifier() -> None:
    assert FOUNDATION_SMOKE_PROMPT_VERSION == "foundation-smoke-v1"
