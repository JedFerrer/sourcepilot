"""Adapter integration on the existing test DB, under an outer rollback.

This is not a live baseline or EVAL_DATABASE_URL fallback. No migrations or resets.
The provider is replaced at the existing client seam; tools and runtime are real.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool

from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai import eval_live
from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation, ModelProviderError
from sourcepilot.ai.comparison_advice_eval import scenario_snapshot
from sourcepilot.ai.eval_scoring import check_failed, score_output
from sourcepilot.ai.tradeoff_analysis import TradeoffNotReadyError
from sourcepilot.ai.tradeoff_analysis_eval import CERT, LEAD, QA, QB, QC, A, B, C, fixture_snapshot
from sourcepilot.comparison.deadline import ComparisonDeadline, current_deadline
from sourcepilot.comparison.execution import comparison_cli_lifecycle
from sourcepilot.persistence.base import Base
from sourcepilot.persistence.models import AIRun, DemoSession, Project
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
)


@pytest.fixture(autouse=True)
def isolated_comparison_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run adapter setup and analysis in one async, rollback-owned transaction.

    Adapter tests exercise real authorization/tools, not the HTTP connection
    boundary (covered by comparison API/recovery tests). A synchronous outer
    transaction cannot publish its savepoints to a request-owned connection.
    Keep that production boundary unchanged and give this test's whole adapter
    invocation one async connection, including its fixture creation.
    """
    original = eval_live.run_case

    def run_case(session: Session, category: str, *args: Any, **kwargs: Any) -> Any:
        if category not in {"comparison", "suggestion"}:
            return original(session, category, *args, **kwargs)

        async def isolated() -> Any:
            engine = create_async_engine(
                persistence_test_database_url_from_environment(), poolclass=NullPool,
            )
            try:
                async with engine.connect() as connection:
                    transaction = await connection.begin()
                    try:
                        async with AsyncSession(
                            bind=connection, expire_on_commit=False,
                            join_transaction_mode="create_savepoint",
                        ) as owned:
                            deadline = ComparisonDeadline()
                            token = current_deadline.set(deadline)
                            try:
                                def invoke(scoped: Session) -> Any:
                                    actual, run = original(scoped, category, *args, **kwargs)
                                    if run is not None:
                                        # Classification reads ordered steps after this
                                        # isolated fixture has closed and rolled back.
                                        scoped.refresh(run, ["supplier_explanation_steps"])
                                    return actual, run

                                async with asyncio.timeout(deadline.remaining()):
                                    return await owned.run_sync(invoke)
                            finally:
                                current_deadline.reset(token)
                    finally:
                        await transaction.rollback()
            finally:
                await engine.dispose()

        with comparison_cli_lifecycle() as runner:
            return runner.run(isolated())

    monkeypatch.setattr(eval_live, "run_case", run_case)


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
def test_comparison_adapter_rolls_back_fixtures_and_trace(
    session: Session, category: str,
) -> None:
    def counts() -> dict[str, int | None]:
        return {
            table.name: session.scalar(select(func.count()).select_from(table))
            for table in Base.metadata.sorted_tables
        }

    before = counts()
    case = baseline.load_scope([category])[category][0]
    client = FixtureClient(category, case)
    actual, run = eval_live.run_case(session, category, case, lambda: client)
    assert actual is not None and run is not None and run.status == "COMPLETED"
    assert counts() == before
    # The returned trace is detached; neither its row nor fixture rows leaked.
    assert session.get(AIRun, run.id) is None


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


def unique_rows(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    result = {row[key]: row for row in rows}
    assert len(result) == len(rows), f"Duplicate {key}"
    return result


def comparison_identities(
    old_payload: dict[str, Any], initial: dict[str, Any], old_snapshot_id: str,
) -> dict[str, str]:
    """Bind by semantic identity, with exact owned field/evidence membership."""
    payload = initial["comparison_payload"]
    # Check both complete identity domains before dictionary insertion can hide
    # duplicate source keys or collisions between different kinds of identity.
    for data, snapshot_id in ((old_payload, old_snapshot_id), (payload, initial["snapshot_id"])):
        domain = [snapshot_id, *(r["id"] for r in data["brief"]["requirements"])]
        for supplier in data["suppliers"]:
            domain.extend((supplier["supplier_id"], supplier["quote_id"]))
            domain.extend(source["id"] for field in supplier["quote_fields"]
                          for source in field.get("evidence", []))
        assert len(domain) == len(set(domain)), "Duplicate or conflicting identity"

    # Legacy scenario owners are fixed independently of the payload under test.
    # Target owners come from persisted Quote rows via active_quote_revisions,
    # not from the projected payload or its positional fact catalogue.
    source_quotes = {A: QA, B: QB, C: QC}
    revisions = initial["quote_revision_snapshot"]
    assert isinstance(revisions, dict), "Missing authoritative quote owners"
    assert set(revisions) == {s["supplier_id"] for s in payload["suppliers"]}
    for supplier in old_payload["suppliers"]:
        assert source_quotes.get(supplier["supplier_id"]) == supplier["quote_id"], (
            "Source quote owner mismatch")
    for supplier in payload["suppliers"]:
        revision = revisions[supplier["supplier_id"]]
        assert isinstance(revision, dict) and revision.get("quote_id") == supplier["quote_id"], (
            "Projected quote owner mismatch")
    identities = {old_snapshot_id: initial["snapshot_id"]}
    old_requirements = unique_rows(old_payload["brief"]["requirements"], "kind")
    requirements = unique_rows(payload["brief"]["requirements"], "kind")
    assert old_requirements.keys() == requirements.keys()
    for kind, old in old_requirements.items():
        actual = requirements[kind]
        assert old["importance"] == actual["importance"]
        identities[old["id"]] = actual["id"]
    old_suppliers = unique_rows(old_payload["suppliers"], "supplier_name")
    suppliers = unique_rows(payload["suppliers"], "supplier_name")
    assert old_suppliers.keys() == suppliers.keys()
    seen_evidence: set[str] = set()
    for name, old in old_suppliers.items():
        actual = suppliers[name]
        identities[old["supplier_id"]] = actual["supplier_id"]
        identities[old["quote_id"]] = actual["quote_id"]
        fields = unique_rows(old["quote_fields"], "field_key")
        completeness = unique_rows(old["completeness"], "field_key")
        projected = unique_rows(actual["quote_fields"], "field_key")
        assert projected.keys() == fields.keys() | completeness.keys()
        for key, projected_field in projected.items():
            expected_completeness = (
                {k: v for k, v in completeness[key].items() if k != "field_key"}
                if key in completeness else None
            )
            assert projected_field.get("completeness") == expected_completeness
            if key not in fields:
                assert set(projected_field) <= {"field_key", "completeness", "currency_context"}
                continue
            expected = eval_live.canonical_quote_field(old, fields[key])
            for attribute in ("current_value", "origin", "ai_extracted_value"):
                assert projected_field[attribute] == expected[attribute]
            old_sources = unique_rows(expected["evidence"], "id")
            actual_sources = unique_rows(projected_field["evidence"], "id")
            assert len(old_sources) == len(actual_sources)
            for source_id, source in old_sources.items():
                matches = [item for item in actual_sources.values()
                           if {k: v for k, v in item.items() if k != "id"}
                           == {k: v for k, v in source.items() if k != "id"}]
                assert len(matches) == 1, "Ambiguous or mismatched owned evidence"
                target = matches[0]["id"]
                assert source_id not in identities and target not in seen_evidence
                identities[source_id] = target
                seen_evidence.add(target)
    assert len(set(identities.values())) == len(identities), "Identity collision"
    return identities


# Independent scenario intent: never search the runtime catalogue for an acceptable reason.
SUGGESTION_CHOICES = {
    "clear-suggestion": A, "tie": None, "critical-unknown": None,
    "required-failure": B, "incomplete-evidence": None, "user-correction": A,
    "incomparable-prices": None, "general-vs-project": A,
    "mixed-currencies": None, "unequal-quantities": None, "required-conflict": None,
}


def scenario_selection(case_id: str, initial: dict[str, Any], ids: dict[str, str]) -> dict[str, Any]:
    selected = SUGGESTION_CHOICES[case_id]

    def requirement(supplier: str, requirement_id: str) -> str:
        return f"R:{ids[supplier]}:{ids[requirement_id]}"

    def quote(quote_id: str, field: str) -> str:
        return f"Q:{ids[quote_id]}:{field}"

    reasons = ([quote(QA if selected == A else QB, "unit_price")] if selected else [])
    highlights = {
        "clear-suggestion": [requirement(A, CERT), quote(QA, "unit_price")],
        "tie": [requirement(A, CERT), requirement(B, CERT), requirement(C, CERT)],
        "critical-unknown": [requirement(A, CERT), requirement(B, CERT), requirement(C, CERT)],
        "required-failure": [quote(QB, "unit_price"), requirement(B, CERT), requirement(B, LEAD)],
        "incomplete-evidence": [requirement(C, CERT)],
        "user-correction": [quote(QA, "unit_price")],
        "incomparable-prices": [quote(QA, "unit_price"), quote(QB, "unit_price")],
        "general-vs-project": [quote(QA, "unit_price"), quote(QA, "production_lead_time")],
        "mixed-currencies": [quote(QA, "currency"), quote(QB, "currency")],
        "unequal-quantities": [quote(QA, "quoted_quantity"), quote(QB, "quoted_quantity")],
        "required-conflict": [requirement(B, CERT)],
    }[case_id]
    actions = {
        "critical-unknown": [("CONFIRM_MISSING", requirement(s, CERT)) for s in (A, B, C)],
        "incomplete-evidence": [("CONFIRM_MISSING", requirement(C, CERT))],
        "required-conflict": [("RESOLVE_CONFLICT", requirement(B, CERT))],
    }.get(case_id, [])
    result = {
        "version": "comparison-selection-v1", "snapshot_id": initial["snapshot_id"],
        "highlights": highlights, "tradeoffs": [],
        "verification_actions": [{"action": action, "fact_id": fact} for action, fact in actions],
        "suggestion": {"supplier_id": ids[selected] if selected else None,
                       "reason_fact_ids": reasons,
                       "no_suggestion_reason": None if selected else (
                           "VERIFY_BEFORE_CHOOSING" if actions else "NO_CLEAR_PREFERENCE")},
    }
    assert all(fact in initial["fact_catalogue"] for fact in highlights + reasons)
    return result


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
            identities = comparison_identities(
                old_payload, initial, self.case.get("snapshot_id", str(fixture_snapshot().snapshot_id)),
            )
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
        if self.category == "suggestion":
            assert schema_name == "ComparisonSelectionV1"
            return AnalystModelInvocation(
                json.dumps(scenario_selection(self.case["id"], initial, identities)), (), 1, 1,
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
    projects_before = session.scalars(select(Project.id)).all()
    owners_before = session.scalars(select(DemoSession.id)).all()
    with pytest.raises(TradeoffNotReadyError, match="Regenerate"):
        eval_live.run_case(session, "comparison", case, factory)
    factory.assert_not_called()
    assert session.scalars(select(AIRun.id)).all() == before
    assert session.scalars(select(Project.id)).all() == projects_before
    assert session.scalars(select(DemoSession.id)).all() == owners_before


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
