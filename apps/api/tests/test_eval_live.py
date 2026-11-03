"""Adapter integration on the existing test DB, under an outer rollback.

This is not a live baseline or EVAL_DATABASE_URL fallback. No migrations or resets.
The provider is replaced at the existing client seam; tools and runtime are real.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai import eval_live
from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation, ModelProviderError
from sourcepilot.ai.comparison_advice_eval import scenario_snapshot
from sourcepilot.ai.eval_scoring import check_failed, score_output
from sourcepilot.ai.tradeoff_analysis import TradeoffNotReadyError
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from sourcepilot.persistence.models import AIRun, DemoSession, Project
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_test_engine(persistence_test_database_url_from_environment())
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(
                    bind=connection,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as database_session:
                    yield database_session
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


class FixtureClient:
    model = "recorded-adapter-regression"

    def __init__(self, category: str, case: dict[str, Any], *, behavior: str = "valid") -> None:
        self.category, self.case, self.behavior = category, case, behavior
        self.calls = 0

    def invoke(
        self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any]
    ) -> ModelInvocation:
        self.calls += 1
        if self.behavior == "retry" and self.calls == 1:
            raise ModelProviderError("Synthetic transient transport", retryable=True)
        if self.behavior == "provider":
            raise ModelProviderError("Synthetic transport failure", retryable=False)
        return ModelInvocation(
            "{}" if self.behavior == "invalid" else json.dumps(self.case["output"]), 1, 1
        )

    def invoke_with_tools(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> AnalystModelInvocation:
        self.calls += 1
        initial = json.loads(input_items[0]["content"])
        if self.behavior == "retry" and self.calls == 1:
            raise ModelProviderError("Synthetic transient transport", retryable=True)
        if self.behavior == "provider":
            raise ModelProviderError("Synthetic transport failure", retryable=False)
        if self.behavior == "invalid":
            return AnalystModelInvocation("{}", (), 1, 1)
        if self.behavior == "limit":
            return AnalystModelInvocation(
                "",
                (
                    {
                        "type": "function_call",
                        "call_id": f"limit-{self.calls}",
                        "name": "get_comparison_snapshot",
                        "arguments": "{}",
                    },
                ),
                1,
                1,
            )
        if self.behavior == "cross_scope":
            return AnalystModelInvocation(
                "",
                (
                    {
                        "type": "function_call",
                        "call_id": "denied",
                        "name": "get_supplier_snapshot",
                        "arguments": json.dumps({"supplier_id": str(uuid4())}),
                    },
                ),
                1,
                1,
            )
        if self.category == "supplier_explanation":
            snapshot = initial["snapshot"]
            identities = {"11111111-1111-1111-1111-111111111111": initial["supplier_id"]}
            for old in self.case["findings"]:
                actual = next(
                    value for value in snapshot["evaluations"] if value["kind"] == old["kind"]
                )
                identities[old["requirement_id"]] = actual["requirement_id"]
                identities.update(zip(old["evidence_ids"], actual["evidence_ids"], strict=True))
            if self.calls == 1:
                return AnalystModelInvocation(
                    "",
                    (
                        {
                            "type": "function_call",
                            "call_id": "evidence",
                            "name": "get_supplier_evidence",
                            "arguments": json.dumps(
                                {"supplier_id": initial["supplier_id"], "claim_keys": None}
                            ),
                        },
                    ),
                    1,
                    1,
                )
        else:
            old_payload = cast(
                dict[str, Any],
                (
                    scenario_snapshot(self.case)
                    if "snapshot_id" in self.case
                    else fixture_snapshot()
                ).comparison_payload,
            )
            assert old_payload is not None
            payload = initial["comparison_payload"]
            identities = {}
            for old, actual in zip(
                old_payload["brief"]["requirements"], payload["brief"]["requirements"], strict=True
            ):
                identities[old["id"]] = actual["id"]
            for old, actual in zip(old_payload["suppliers"], payload["suppliers"], strict=True):
                identities[old["supplier_id"]] = actual["supplier_id"]
                identities[old["quote_id"]] = actual["quote_id"]
                for old_field, actual_field in zip(
                    old["quote_fields"], actual["quote_fields"], strict=True
                ):
                    for old_source, actual_source in zip(
                        old_field["evidence"], actual_field["evidence"], strict=True
                    ):
                        identities[old_source["id"]] = actual_source["id"]
            if self.calls == 1:
                return AnalystModelInvocation(
                    "",
                    (
                        {
                            "type": "function_call",
                            "call_id": "comparison",
                            "name": "get_comparison_snapshot",
                            "arguments": "{}",
                        },
                    ),
                    1,
                    1,
                )
        return AnalystModelInvocation(
            json.dumps(eval_live.remap(self.case["output"], identities)), (), 1, 1
        )


LIVE_CASES = [
    (category, case)
    for category, cases in baseline.load_scope(list(baseline.CATEGORIES)).items()
    for case in cases
    if case.get("expected_valid", True) and "guard" not in case and "expected_error" not in case
]


@pytest.mark.parametrize(
    "category,case", LIVE_CASES, ids=[f"{category}-{case['id']}" for category, case in LIVE_CASES]
)
def test_all_valid_adapters_use_real_runtime_and_scoped_tools(
    session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    category: str,
    case: dict[str, Any],
) -> None:
    provider = Mock(side_effect=AssertionError("live provider is forbidden in tests"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    client = FixtureClient(category, case)
    blocks = baseline.parser_result(case, tmp_path)[0] if category == "quote_extraction" else None
    actual, run = eval_live.run_case(session, category, case, lambda: client, blocks)
    assert actual is not None
    assert baseline.classify_live(actual, run) is None
    assert all(not check_failed(check) for check in score_output(category, case, actual)), (
        category,
        case["id"],
        actual,
    )
    if category == "clarification" and not case["expected_keys"]:
        assert run is None and client.calls == 0
    else:
        assert run is not None and run.status == "COMPLETED" and client.calls >= 1
        if category in {"comparison", "suggestion", "supplier_explanation"}:
            assert run.tool_call_count and run.tool_call_count >= 1
    provider.assert_not_called()


@pytest.mark.parametrize(
    "category,behavior,expected",
    [
        ("brief", "invalid", "QUALITY_FINDING"),
        ("brief", "provider", "PROVIDER_ERROR"),
        ("comparison", "invalid", "QUALITY_FINDING"),
        ("comparison", "limit", "QUALITY_FINDING"),
        ("comparison", "provider", "PROVIDER_ERROR"),
        ("comparison", "cross_scope", "RUNTIME_ERROR"),
    ],
)
def test_actual_runtime_termination_classification(
    session: Session, category: str, behavior: str, expected: str
) -> None:
    case = baseline.load_scope([category])[category][0]
    client = FixtureClient(category, case, behavior=behavior)
    responses: list[dict[str, Any]] = []
    actual, run = eval_live.run_case(
        session, category, case, lambda: baseline.CapturingClient(client, responses)
    )
    assert baseline.classify_live(actual, run, responses) == expected
    assert run is not None
    if behavior == "invalid":
        assert run.status == "VALIDATION_FAILED" and client.calls == 2
    if behavior == "limit":
        assert run.status == "FAILED_LIMIT_REACHED" and client.calls == 4


def test_injected_tool_value_error_is_execution_error(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sourcepilot.ai import tradeoff_analysis

    case = baseline.load_scope(["comparison"])["comparison"][0]
    client = FixtureClient("comparison", case)

    def broken_tool(*_args: Any, **_kwargs: Any) -> Any:
        raise ValueError("injected tool integration failure")

    monkeypatch.setattr(tradeoff_analysis, "_tool_output", broken_tool)
    actual, run = eval_live.run_case(session, "comparison", case, lambda: client)
    assert actual is None and run is not None
    assert run.status == "VALIDATION_FAILED" and run.validation_status == "INVALID"
    assert baseline.classify_live(actual, run) == "RUNTIME_ERROR"
    result = {
        "selected_categories": ["comparison"],
        "required_cases": {"comparison": [case["id"]]},
        "cases": [{"category": "comparison", "id": case["id"],
                   "status": "RUNTIME_ERROR", "assertions": []}],
    }
    assert baseline.summarize(result) == 2 and result["status"] == "ERROR"


def test_structured_post_validate_value_error_exits_two(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sourcepilot.ai import brief_interpreter
    from sourcepilot.ai.structured import run_structured_operation

    case = baseline.load_scope(["brief"])["brief"][0]
    client = FixtureClient("brief", case)
    responses: list[dict[str, Any]] = []

    def with_fault(*args: Any, **kwargs: Any) -> Any:
        def broken_post_validate(_output: Any) -> None:
            raise ValueError("injected internal callback failure")

        return run_structured_operation(
            *args, **kwargs, post_validate=broken_post_validate
        )

    monkeypatch.setattr(brief_interpreter, "run_structured_operation", with_fault)
    actual, run = eval_live.run_case(
        session, "brief", case, lambda: baseline.CapturingClient(client, responses)
    )
    assert actual is None and run is not None
    assert run.status == "VALIDATION_FAILED" and client.calls == 2
    assert baseline.classify_live(actual, run, responses) == "RUNTIME_ERROR"
    result = {
        "selected_categories": ["brief"],
        "required_cases": {"brief": [case["id"]]},
        "cases": [{"category": "brief", "id": case["id"],
                   "status": "RUNTIME_ERROR", "assertions": []}],
    }
    assert baseline.summarize(result) == 2 and result["status"] == "ERROR"


@pytest.mark.parametrize("category", ["brief", "comparison"])
def test_existing_provider_retry_succeeds(session: Session, category: str) -> None:
    case = baseline.load_scope([category])[category][0]
    client = FixtureClient(category, case, behavior="retry")
    actual, run = eval_live.run_case(session, category, case, lambda: client)
    assert actual is not None and run is not None and run.status == "COMPLETED"
    assert client.calls == 2 and run.attempts == 2


def test_stale_comparison_rejected_before_provider(session: Session) -> None:
    case = next(
        case for case in baseline.load_scope(["comparison"])["comparison"] if "guard" in case
    )
    factory = Mock(side_effect=AssertionError("must not construct provider"))
    before = session.scalars(select(AIRun.id)).all()
    with pytest.raises(TradeoffNotReadyError, match="Regenerate"):
        eval_live.run_case(session, "comparison", case, factory)
    factory.assert_not_called()
    assert session.scalars(select(AIRun.id)).all() == before


def test_existing_project_and_decision_unmodified(session: Session) -> None:
    owner = DemoSession(opaque_token=uuid4().hex, expires_at=datetime.now(UTC) + timedelta(hours=1))
    original = Project(
        demo_session=owner,
        name="Existing project sentinel",
        original_request="Keep me",
        decision_notes="Existing human notes",
    )
    session.add(original)
    session.commit()
    before = (
        original.name,
        original.original_request,
        original.stage,
        original.brief_revision,
        original.preferred_supplier_id,
        original.decision_notes,
        original.updated_at,
    )
    case = baseline.load_scope(["brief"])["brief"][0]
    client = FixtureClient("brief", case)
    eval_live.run_case(session, "brief", case, lambda: client)
    session.refresh(original)
    assert (
        original.name,
        original.original_request,
        original.stage,
        original.brief_revision,
        original.preferred_supplier_id,
        original.decision_notes,
        original.updated_at,
    ) == before
