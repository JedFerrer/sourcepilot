"""M6 runner statuses, scope, provenance, preflight and scorer sensitivity."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai import eval_live
from sourcepilot.ai.eval_scoring import assertion, check_failed, heuristic_signal, score_output


def parsed_quote_case(case: dict[str, Any]) -> dict[str, Any]:
    with TemporaryDirectory() as directory:
        baseline.parser_result(case, Path(directory))
    return case


def test_missing_parsed_quote_context_reports_scorer_error_and_keeps_parser_rejections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = baseline.parser_result

    def omit_context(case: dict[str, Any], temporary: Path) -> Any:
        result = original(case, temporary)
        if case["id"] == "harbor-primary":
            case.pop("_scoring_document")
        return result

    monkeypatch.setattr(baseline, "parser_result", omit_context)
    provider = Mock(side_effect=AssertionError("No provider allowed"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    result, code = baseline.execute("offline", ["quote_extraction"], tmp_path)
    assert code == 2 and result["complete"]
    assert result["status_counts"] == {"SCORER_ERROR": 1, "PASS": 9, "EXPECTED_REJECTION": 2}
    assert result["cases"][0]["assertions"][0]["detail"] == "QuoteScorerContextError"
    provider.assert_not_called()


def test_runner_reuses_parsed_context_for_extraction_scoring_and_measurements(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import document_blocks

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-functional-credential")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "synthetic-test-model")
    engine = Mock()
    monkeypatch.setattr(baseline, "preflight_database", lambda: engine)
    monkeypatch.setattr(baseline, "Session", MagicMock())
    provider = Mock(side_effect=AssertionError("No provider allowed"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    called = []

    def retained_output(_session: Any, category: str, case: dict[str, Any],
                        _factory: Any, blocks: Any) -> tuple[Any, None]:
        assert category == "quote_extraction"
        assert document_blocks(case) == {block.reference: block.text for block in blocks}
        called.append(case["id"])
        if case["id"] == "harbor-primary":
            # Exercise the live scorer boundary after otherwise valid offline preflight.
            case.pop("_scoring_document")
        return case["output"], None

    monkeypatch.setattr(baseline, "run_case", retained_output)
    result, code = baseline.execute("live", ["quote_extraction"], tmp_path)
    assert code == 2 and result["complete"] and len(called) == 10
    assert result["status_counts"] == {"SCORER_ERROR": 1, "PASS": 9, "EXPECTED_REJECTION": 2}
    assert result["measurements"]["quote_extraction"]["field_accuracy"]["measured_case_count"] == 9
    provider.assert_not_called()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("operation,schema_name", [
    ("tradeoff_analysis", "TradeoffAnalysis"), ("comparison_advice", "ComparisonAdviceV1"),
])
@pytest.mark.parametrize("terminal,captured,expected", [
    ("validation", True, "QUALITY_FINDING"),
    ("validation", False, "RUNTIME_ERROR"),
    ("tool", True, "RUNTIME_ERROR"),
])
def test_validation_diagnostics_preserve_failure_attribution(
    operation: str, schema_name: str, terminal: str, captured: bool, expected: str,
) -> None:
    steps = [
        SimpleNamespace(sequence=1, kind="validation_phase", outcome="INVALID", name="schema_repair"),
        SimpleNamespace(sequence=2, kind=terminal, outcome="INVALID", name="SCHEMA_INVALID"),
        SimpleNamespace(sequence=3, kind="validation_schema", outcome="INVALID", name="schema_type_missing"),
        SimpleNamespace(sequence=4, kind="usage", outcome="COMPLETE", name="input_tokens"),
        SimpleNamespace(sequence=5, kind="run", outcome="VALIDATION_FAILED", name=None),
    ]
    run = SimpleNamespace(operation=operation, status="VALIDATION_FAILED",
                          validation_status="INVALID", supplier_explanation_steps=steps)
    responses = [{"schema_name": schema_name, "output_text": "{}"}] if captured else None
    assert baseline.classify_live(None, run, responses) == expected  # type: ignore[arg-type]


def test_retained_harbor_rescore_preserves_historical_evidence_and_named_counts(tmp_path: Path) -> None:
    from sourcepilot.ai.eval_scoring import measurements
    from sourcepilot.ai.quote_extraction_eval import METRIC_NAMES

    evidence = baseline.ROOT / "docs/implementation/evidence/M6-U1/corrected-production-single-2026-11-02-01"
    historical_bytes = {name: (evidence / name).read_bytes()
                        for name in ("extraction.json", "inspection.json", "outcome.json")}
    output = json.loads(historical_bytes["extraction.json"])
    historical = json.loads(historical_bytes["inspection.json"])
    case = parsed_quote_case(baseline.load_scope(["quote_extraction"])["quote_extraction"][0])
    checks = score_output("quote_extraction", case, output)
    counts = measurements("quote_extraction", case, output)
    by_name = {check["name"]: check for check in checks}
    assert historical["assertions"]["passed"] == 34
    assert historical["assertions"]["total"] == 43
    for name in METRIC_NAMES:
        measurement = counts[name]
        expected_pass = (measurement["numerator"] == 0 if name == "hallucination_rate"
                         else measurement["numerator"] == measurement["denominator"])
        assert by_name[name]["passed"] is expected_pass
    assert counts["field_accuracy"]["numerator"] == sum(
        check["passed"] for check in checks
        if check["name"].endswith((".value", ".unknown", ".conflict"))
    )
    assert counts["source_block_accuracy"] == {"kind": "exact", "numerator": 20, "denominator": 21}
    assert counts["hallucination_rate"] == {"kind": "exact", "numerator": 0, "denominator": 7}
    assert counts["expected_unknown_known_rate"] == {"kind": "exact", "numerator": 1, "denominator": 7}
    assert not by_name["field.supplier_notes.field_assignment"]["passed"]
    assert by_name["field.supplier_notes.field_assignment"]["critical"]
    result = {
        "mode": "offline", "selected_categories": ["quote_extraction"], "full_scope": False,
        "required_cases": {"quote_extraction": ["harbor-primary"]},
        "human_review": {"status": "PENDING", "case_count": 0, "cases": []},
        "cases": [{"category": "quote_extraction", "id": "harbor-primary",
                   "status": "QUALITY_FINDING", "assertions": checks, "measurements": counts}],
    }
    result["exit_code"] = baseline.summarize(result)
    baseline.write_report(result, tmp_path)
    persisted = baseline.read_json(tmp_path / "results.json")
    assert persisted["measurements"]["quote_extraction"]["hallucination_rate"]["numerator"] == 0
    assert persisted["measurements"]["quote_extraction"]["expected_unknown_known_rate"]["numerator"] == 1
    assert any(item["assertion"] == "field.supplier_notes.field_assignment"
               for item in persisted["critical_findings"])
    assert "field.supplier_notes.field_assignment" in (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert all((evidence / name).read_bytes() == content for name, content in historical_bytes.items())


def report(cases: list[dict[str, Any]], required: list[str]) -> dict[str, Any]:
    return {
        "mode": "live",
        "selected_categories": ["brief"],
        "cases": cases,
        "required_cases": {"brief": required},
    }


def item(identifier: str, status: str) -> dict[str, Any]:
    return {
        "category": "brief",
        "id": identifier,
        "status": status,
        "assertions": [assertion("truth", status == "PASS")],
    }


@pytest.mark.parametrize(
    "status,code,summary",
    [
        ("PASS", 0, "COMPLETED"),
        ("EXPECTED_REJECTION", 0, "COMPLETED"),
        ("QUALITY_FINDING", 0, "COMPLETED_WITH_FINDINGS"),
        ("REGRESSION_FAILED", 1, "REGRESSION_FAILED"),
        ("PROVIDER_ERROR", 2, "ERROR"),
        ("HARNESS_ERROR", 2, "ERROR"),
        ("SCORER_ERROR", 2, "ERROR"),
    ],
)
def test_exit_semantics(status: str, code: int, summary: str) -> None:
    result = report([item("one", status)], ["one"])
    assert baseline.summarize(result) == code
    assert result["status"] == summary and result["complete"]


def test_critical_heuristic_finding_is_prominent_without_execution_error() -> None:
    case = item("one", "QUALITY_FINDING")
    case["assertions"] = [heuristic_signal(
        "incomparable_price_ranking_signal", ["supplier_summaries[0]: B wins on price"])]
    result = report([case], ["one"])
    assert baseline.summarize(result) == 0
    assert result["status"] == "COMPLETED_WITH_FINDINGS" and result["complete"]
    assert result["critical_findings"] == [{
        "category": "brief", "id": "one", "assertion": "incomparable_price_ranking_signal",
        "kind": "heuristic", "detail": "supplier_summaries[0]: B wins on price",
    }]
    assert result["metrics"]["brief"] == {}
    assert result["heuristic_signals"]["brief"]["incomparable_price_ranking_signal"]["triggered"] == 1


def test_selected_scope_complete_and_missing_duplicate_cases_incomplete() -> None:
    result = report([item("one", "PASS")], ["one"])
    assert baseline.summarize(result) == 0
    assert result["expected_case_count"] == 1
    for cases in ([], [item("one", "PASS"), item("one", "PASS")]):
        partial = report(cases, ["one"])
        assert baseline.summarize(partial) == 2
        assert partial["status"] == "INCOMPLETE"


def test_execution_error_takes_precedence_over_regression() -> None:
    result = report(
        [item("one", "REGRESSION_FAILED"), item("two", "PROVIDER_ERROR")], ["one", "two"]
    )
    assert baseline.summarize(result) == 2


def test_unexpected_skip_is_incomplete() -> None:
    result = report([item("one", "SKIPPED")], ["one"])
    assert baseline.summarize(result) == 2 and not result["complete"]


@pytest.mark.parametrize(
    "runtime_status,error_type,expected",
    [
        ("VALIDATION_FAILED", "ValidationError", "RUNTIME_ERROR"),
        ("VALIDATION_FAILED", None, "RUNTIME_ERROR"),
        ("FAILED_LIMIT_REACHED", None, "RUNTIME_ERROR"),
        ("PROVIDER_FAILED", None, "PROVIDER_ERROR"),
        ("FAILED", None, "RUNTIME_ERROR"),
        ("COMPLETED", None, None),
    ],
)
def test_runtime_termination_is_distinct_from_transport_error(
    runtime_status: str, error_type: str | None, expected: str | None
) -> None:
    run = SimpleNamespace(status=runtime_status, error_type=error_type,
                          validation_status="INVALID", operation="brief_interpreter")
    assert baseline.classify_live({}, run) == expected  # type: ignore[arg-type]


def test_offline_filtered_scope_cannot_construct_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = Mock(side_effect=AssertionError("offline must not construct provider"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    result, code = baseline.execute("offline", ["brief"], tmp_path)
    assert code == 0 and result["complete"] and not result["full_scope"]
    assert result["expected_case_count"] == 24
    assert (tmp_path / "results.json").exists() and (tmp_path / "summary.md").exists()
    provider.assert_not_called()


def test_full_offline_scope_includes_all_categories(tmp_path: Path) -> None:
    result, code = baseline.execute("offline", list(baseline.CATEGORIES), tmp_path)
    assert code == 0 and result["full_scope"] and result["complete"]
    assert set(result["required_cases"]) == set(baseline.CATEGORIES)
    assert result["expected_case_count"] == 90
    assert result["status_counts"]["EXPECTED_REJECTION"] == 17


def test_live_preflight_failure_prevents_provider_and_fixture_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("EVAL_DATABASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")
    provider = Mock(side_effect=AssertionError("no provider"))
    fixture = Mock(side_effect=AssertionError("no fixture writes"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    monkeypatch.setattr(baseline, "run_case", fixture)
    result, code = baseline.execute("live", ["brief"], tmp_path)
    assert code == 2 and result["status"] == "INCOMPLETE"
    assert result["error"] == "EVAL_DATABASE_URL is required for live evals."
    provider.assert_not_called()
    fixture.assert_not_called()


def test_scorer_error_is_reported_and_remaining_cases_continue(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = baseline.score_output

    def broken(category: str, case: dict[str, Any], output: Any) -> list[dict[str, Any]]:
        if case["id"] == "complete-demo":
            raise RuntimeError("intentional scorer defect")
        return original(category, case, output)

    monkeypatch.setattr(baseline, "score_output", broken)
    result, code = baseline.execute("offline", ["brief"], tmp_path)
    assert code == 2 and result["complete"]
    assert result["status_counts"] == {"SCORER_ERROR": 1, "PASS": 23}


def test_failed_report_generation_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(baseline, "write_report", Mock(side_effect=OSError("disk fault")))
    result, code = baseline.execute("offline", ["clarification"], tmp_path)
    assert code == 2 and result["status"] == "ERROR"
    assert "Report generation" in result["error"]


@pytest.mark.parametrize("failed_artifact", ["results.json", "summary.md"])
def test_partial_report_write_never_leaves_completed_machine_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failed_artifact: str
) -> None:
    (tmp_path / "results.json").write_text('{"status":"COMPLETED","exit_code":0}')
    original = Path.write_text

    def fail_one(path: Path, data: str, *args: Any, **kwargs: Any) -> int:
        if path.name == failed_artifact:
            raise OSError("injected report write failure")
        return original(path, data, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_one)
    result, code = baseline.execute("offline", ["clarification"], tmp_path)
    assert code == 2 and result["status"] == "ERROR"
    if (tmp_path / "results.json").exists():
        persisted = json.loads((tmp_path / "results.json").read_text())
        assert persisted["status"] == "ERROR" and persisted["exit_code"] == 2
    assert not (tmp_path / "summary.md").exists()


def test_live_runner_reports_actual_quality_and_runtime_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    engine = Mock()
    monkeypatch.setattr(baseline, "preflight_database", lambda: engine)
    monkeypatch.setattr(baseline, "Session", MagicMock())
    provider = Mock(side_effect=AssertionError("fake case must not construct provider"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", provider)
    called = []

    def actual_run(
        _session: Any, category: str, case: dict[str, Any], _factory: Any, _blocks: Any
    ) -> tuple[Any, Any]:
        called.append(case["id"])
        run = SimpleNamespace(
            id="synthetic-run",
            operation="brief_interpreter",
            model="configured-test-model",
            prompt_version="brief-interpreter-v1",
            input_hash="synthetic",
            status="COMPLETED",
            attempts=1,
            validation_status="VALID",
            error_type=None,
            latency_ms=1,
            input_tokens=1,
            output_tokens=1,
            model_turn_count=None,
            tool_call_count=None,
        )
        if case["id"] == "complete-demo":
            output = {**case["output"], "quantity": 999}
            return output, run
        if case["id"] == "missing-destination":
            run.status = "VALIDATION_FAILED"
            run.error_type = "ValidationError"
            run.validation_status = "INVALID"
            return None, run
        return case["output"], run

    monkeypatch.setattr(baseline, "run_case", actual_run)
    result, code = baseline.execute("live", ["brief"], tmp_path)
    assert code == 2 and result["status"] == "ERROR" and result["complete"]
    assert len(called) == 24 and result["status_counts"]["QUALITY_FINDING"] == 1
    assert result["status_counts"]["RUNTIME_ERROR"] == 1
    assert any(finding["assertion"] == "brief.quantity" for finding in result["critical_findings"])
    provider.assert_not_called()
    engine.dispose.assert_called_once()


def test_capturing_client_preserves_invocations_and_records_rejected_output() -> None:
    from sourcepilot.ai.client import AnalystModelInvocation, ModelInvocation

    delegate = Mock(model="configured-model")
    delegate.invoke.return_value = ModelInvocation("invalid JSON", 1, 1)
    delegate.invoke_with_tools.return_value = AnalystModelInvocation("{}", (), 1, 1)
    responses: list[dict[str, Any]] = []
    client = baseline.CapturingClient(delegate, responses)
    assert (
        client.invoke(instructions="same", input_text="same", schema_name="Brief", schema={})
        is delegate.invoke.return_value
    )
    assert (
        client.invoke_with_tools(
            instructions="same", input_items=[], tools=[], schema_name="Advice", schema={}
        )
        is delegate.invoke_with_tools.return_value
    )
    assert responses == [
        {"schema_name": "Brief", "output_text": "invalid JSON"},
        {"schema_name": "Advice", "output_text": "{}", "tool_calls": []},
    ]


def test_changed_consumed_source_invalidates_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = baseline.hash_files
    calls = 0

    def hashes(paths: list[Path]) -> dict[str, str]:
        nonlocal calls
        calls += 1
        result = original(paths)
        if calls > 1:
            result[next(iter(result))] = "changed"
        return result

    monkeypatch.setattr(baseline, "hash_files", hashes)
    result, code = baseline.execute("offline", ["brief"], tmp_path)
    assert code == 2 and result["error"] == "RuntimeError"


def test_fingerprint_only_lists_consumed_inputs_and_locks() -> None:
    scope = baseline.load_scope(["brief"])
    files = baseline.hash_files(baseline.consumed_files(scope))
    assert "apps/api/uv.lock" in files and "pnpm-lock.yaml" not in files
    assert "apps/api/evals/brief/cases.json" in files
    assert "apps/api/sourcepilot/ai/brief_interpreter.py" in files
    assert "apps/api/sourcepilot/ai/quote_extractor.py" not in files
    assert "apps/api/sourcepilot/ai/eval_live.py" not in files
    assert not any("alembic/versions/" in path for path in files)
    assert not any(
        "docs/" in path or ".env" in path or "apps/web/components" in path for path in files
    )


def test_fingerprint_scopes_data_and_live_preflight_inputs() -> None:
    scope = baseline.load_scope(["suggestion"])
    offline = baseline.hash_files(baseline.consumed_files(scope))
    live = baseline.hash_files(baseline.consumed_files(scope, "live"))
    assert "apps/api/evals/comparison_advice/model_outputs.json" in offline
    assert "apps/api/evals/comparison_advice/guard_cases.json" not in offline
    assert "apps/api/evals/tradeoff_analysis/model_outputs.json" not in offline
    assert "apps/api/sourcepilot/ai/eval_live.py" in live
    assert "pnpm-lock.yaml" not in live
    assert any("alembic/versions/" in path for path in live)
    assert "apps/api/evals/brief/cases.json" not in live


def test_invented_brief_field_is_detected() -> None:
    case = next(
        case for case in baseline.load_scope(["brief"])["brief"] if case["id"] == "non-invention"
    )
    assert all(not check_failed(check) for check in score_output("brief", case, case["output"]))
    actual = {**case["output"], "destination": "Sydney"}
    assert any(
        check_failed(item) and item["name"] == "brief.destination"
        for item in score_output("brief", case, actual)
    )


@pytest.mark.parametrize("field,value", [("unit_price", "99.99"), ("currency", "EUR")])
def test_invented_prices_and_wrong_currency_detected(field: str, value: str) -> None:
    case = parsed_quote_case(baseline.load_scope(["quote_extraction"])["quote_extraction"][0])
    output = deepcopy(case["output"])
    assert all(not check_failed(check) for check in score_output("quote_extraction", case, output))
    output["fields"][field]["extracted_value"] = value
    assert any(
        check_failed(item) and item["name"] == f"field.{field}.value"
        for item in score_output("quote_extraction", case, output)
    )


def test_wrong_quote_evidence_detected() -> None:
    case = parsed_quote_case(baseline.load_scope(["quote_extraction"])["quote_extraction"][0])
    output = deepcopy(case["output"])
    assert all(not check_failed(check) for check in score_output("quote_extraction", case, output))
    output["fields"]["unit_price"]["source_block_ids"] = ["p1-b4"]
    assert any(
        check_failed(item) and item["name"] == "field.unit_price.sources"
        for item in score_output("quote_extraction", case, output)
    )


@pytest.mark.parametrize(
    "identifier,section",
    [("required-failure", "required_failures"), ("unknown", "unknowns"), ("conflict", "conflicts")],
)
def test_hidden_required_failures_and_lost_unknown_conflict_detected(
    identifier: str, section: str
) -> None:
    case = next(
        case
        for case in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
        if case["id"] == identifier
    )
    output = deepcopy(case["output"])
    assert all(not check_failed(check) for check in score_output("supplier_explanation", case, output))
    output[section] = []
    assert any(
        check_failed(item) and item["name"] == "states_and_evidence"
        for item in score_output("supplier_explanation", case, output)
    )


@pytest.mark.parametrize("mutation", ["correction-provenance", "forced-suggestion", "numeric-score"])
def test_correction_provenance_forced_suggestions_numeric_scores_detected(mutation: str) -> None:
    cases = baseline.load_scope(["suggestion"])["suggestion"]
    identifier = "critical-unknown" if mutation == "forced-suggestion" else "clear-suggestion"
    case = next(case for case in cases if case["id"] == identifier)
    output = deepcopy(case["output"])
    assert all(not check_failed(check) for check in score_output("suggestion", case, output))
    if mutation == "forced-suggestion":
        output["suggestion"]["supplier_id"] = "11111111-1111-1111-1111-111111111111"
    elif mutation == "numeric-score":
        output["suggestion"]["supporting_reasons"][0]["text"] = "Supplier A has a score of 92."
    else:
        point = output["suggestion"]["supporting_reasons"][0]
        point["text"] = "Supplier A confirmed current unit price is USD 4.22."
    assert any(
        check_failed(check) and check["name"] in {
            "allowed_suggestion_choice", "bounded_suggestion_narrative_signal"
        }
        for check in score_output("suggestion", case, output)
    )


def test_bounded_aliases_and_order_equivalence_preserve_exact_facts() -> None:
    case = baseline.load_scope(["brief"])["brief"][0]
    actual = deepcopy(case["output"])
    actual["category"] = "cosmetic bags"
    actual["requirements"].reverse()
    actual["target_unit_price"] = "5.0000"
    assert all(not check_failed(item) for item in score_output("brief", case, actual))
    actual["quantity"] = 2001
    assert not all(not check_failed(item) for item in score_output("brief", case, actual))


def test_numeric_requirement_decimal_equivalence_preserves_other_semantics() -> None:
    case = next(value for value in baseline.load_scope(["brief"])["brief"]
                if any(item["kind"] == "UNIT_PRICE" for item in value["output"]["requirements"]))
    output = deepcopy(case["output"])
    requirement = next(item for item in output["requirements"] if item["kind"] == "UNIT_PRICE")
    requirement["expected_value"]["amount"] = "6.00"
    assert next(item for item in score_output("brief", case, output)
                if item["name"] == "brief.requirements")["passed"]
    requirement["expected_value"]["currency"] = "EUR"
    assert not next(item for item in score_output("brief", case, output)
                    if item["name"] == "brief.requirements")["passed"]


def test_preflight_never_falls_back_to_application_or_test_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("EVAL_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://demo:demo@localhost/application")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://demo:demo@localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")
    engine = Mock()
    monkeypatch.setattr(eval_live, "create_engine", engine)
    with pytest.raises(eval_live.EvalPreflightError, match="EVAL_DATABASE_URL"):
        eval_live.preflight_database()
    engine.assert_not_called()


@pytest.mark.parametrize("failure", [None, "connection", "database", "revision", "columns"])
def test_database_preflight_is_read_only_and_requires_readiness(
    failure: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_DATABASE_URL", "postgresql+psycopg://demo:demo@localhost/eval_only")
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:other@localhost/application")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql://test:other@localhost/test")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    for key in list(os.environ):
        if key.startswith("PG"):
            monkeypatch.delenv(key)
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.scalar.return_value = "unexpected" if failure == "database" else "eval_only"
    connection.scalars.return_value = ["old" if failure == "revision" else "current"]
    if failure == "connection":
        engine.connect.side_effect = OSError("private credential must not be reported")
    inspector = Mock()

    def columns(name: str) -> list[dict[str, str]]:
        return (
            []
            if failure == "columns"
            else [{"name": column.name} for column in eval_live.Base.metadata.tables[name].columns]
        )

    inspector.get_columns.side_effect = columns
    monkeypatch.setattr(eval_live, "inspect", lambda _connection: inspector)
    monkeypatch.setattr(eval_live, "create_engine", lambda *_args, **_kwargs: engine)
    script = Mock()
    script.get_heads.return_value = ["current"]
    monkeypatch.setattr(eval_live.ScriptDirectory, "from_config", lambda _config: script)
    if failure:
        with pytest.raises(eval_live.EvalPreflightError) as caught:
            eval_live.preflight_database()
        assert "private credential" not in str(caught.value)
        engine.dispose.assert_called_once()
    else:
        assert eval_live.preflight_database() is engine
    commands = [str(call.args[0]) for call in connection.execute.call_args_list]
    assert commands in ([], ["SET TRANSACTION READ ONLY"])
    engine.begin.assert_not_called()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite:///eval",
        "postgresql+psycopg:///eval",
        "postgresql+psycopg://localhost/eval?host=other",
    ],
)
def test_invalid_eval_configuration_cannot_connect(
    url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("EVAL_DATABASE_URL", url)
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "configured-test-model")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-test-only")
    engine = Mock()
    monkeypatch.setattr(eval_live, "create_engine", engine)
    with pytest.raises(eval_live.EvalPreflightError):
        eval_live.preflight_database()
    engine.assert_not_called()


def test_wrong_narrative_currency_and_general_price_claim_detected() -> None:
    case = next(
        case
        for case in baseline.load_scope(["suggestion"])["suggestion"]
        if case["id"] == "clear-suggestion"
    )
    output = deepcopy(case["output"])
    output["suggestion"]["supporting_reasons"][0]["text"] = (
        "Supplier A confirmed current unit price is EUR 4.50."
    )
    assert not all(not check_failed(item) for item in score_output("suggestion", case, output))
    case = next(
        case
        for case in baseline.load_scope(["comparison"])["comparison"]
        if case["id"] == "general-vs-project"
    )
    output = deepcopy(case["output"])
    output["key_tradeoffs"][-1]["text"] = output["key_tradeoffs"][-1]["text"].replace(
        "is 50", "is 999"
    )
    assert not all(not check_failed(item) for item in score_output("comparison", case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
@pytest.mark.parametrize("wording", [
    "Supplier B is cheaper than Supplier A.",
    "Supplier B has a lower unit cost than Supplier A.",
    "Supplier A has a higher price than Supplier B.",
    "Supplier B costs less than Supplier A.",
    "Supplier A has the highest unit price.",
    "Supplier B offers a better unit price than Supplier A.",
    "Supplier B undercuts Supplier A on unit price.",
    "Supplier A offers a worse unit price than Supplier B.",
    "Supplier B's price is lower than Supplier A's.",
    "Supplier A has a more expensive unit cost than Supplier B.",
    "Supplier B is lower-priced than Supplier A.",
    "Supplier A costs more per unit than Supplier B.",
    "Supplier B is better priced than Supplier A.",
    "Supplier B is priced below Supplier A.",
    "Supplier B charges less per unit than Supplier A.",
])
def test_incomparable_prices_reject_price_ranking(
    category: str, identifier: str, wording: str
) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == identifier)
    output = deepcopy(case["output"])
    assert all(not check_failed(item) for item in score_output(category, case, output))
    if category == "suggestion":
        output["suggestion"]["uncertainties"][0]["text"] = wording
        failure = "incomparable_price_ranking_signal"
    else:
        output["supplier_summaries"][0]["text"] = wording
        failure = "incomparable_price_ranking_signal"
    assert any(check_failed(item) and item["name"] == failure
               for item in score_output(category, case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
def test_incomparable_prices_allow_nonranking_factual_mention(
    category: str, identifier: str
) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == identifier)
    output = deepcopy(case["output"])
    point = (output["supplier_summaries"][0] if category == "comparison"
             else output["suggestion"]["uncertainties"][0])
    for wording in (
        "Supplier B has a quoted unit price; the quotes cannot be directly compared.",
        "Supplier B's unit price cannot be ranked against Supplier A's quote.",
    ):
        point["text"] = wording
        assert all(not check_failed(item) for item in score_output(category, case, output)), wording
    if identifier == "mixed-currencies":
        point["text"] = "Supplier B's confirmed unit price is AUD 3.90."
        point["supplier_ids"] = ["11111111-1111-1111-1111-111111111112"]
        point["quote_fields"] = [{"quote_id": "22222222-2222-2222-2222-222222222222",
                                  "field_key": "unit_price"}]
        assert all(not check_failed(item) for item in score_output(category, case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
@pytest.mark.parametrize("template", [
    "{winner} wins on price over {loser}.",
    "{winner} has a more competitive unit rate than {loser}.",
    "On unit cost, {winner} takes the lead over {loser}.",
])
@pytest.mark.parametrize("winner,loser", [
    ("Supplier A", "Supplier B"), ("Supplier B", "Supplier A"),
])
def test_incomparable_price_conclusions_fail_without_ranking_vocabulary(
    category: str, identifier: str, template: str, winner: str, loser: str,
) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == identifier)
    output = deepcopy(case["output"])
    point = (output["supplier_summaries"][0] if category == "comparison"
             else output["suggestion"]["uncertainties"][0])
    point["text"] = template.format(winner=winner, loser=loser)
    assert not all(not check_failed(item) for item in score_output(category, case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("identifier", ["mixed-currencies", "unequal-quantities"])
def test_incomparable_price_exact_facts_and_warning_pass(
    category: str, identifier: str,
) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == identifier)
    output = deepcopy(case["output"])
    point = (output["supplier_summaries"][0] if category == "comparison"
             else output["suggestion"]["uncertainties"][0])
    point["supplier_ids"] = ["11111111-1111-1111-1111-111111111111",
                             "11111111-1111-1111-1111-111111111112"]
    point["quote_fields"] = [
        {"quote_id": "22222222-2222-2222-2222-222222222221", "field_key": "unit_price"},
        {"quote_id": "22222222-2222-2222-2222-222222222222", "field_key": "unit_price"},
    ]
    second_currency = "AUD" if identifier == "mixed-currencies" else "USD"
    point["text"] = ("Supplier A's unit price is USD 4.50; "
                     f"Supplier B's unit price is {second_currency} 3.90.")
    assert all(not check_failed(item) for item in score_output(category, case, output))
    point["text"] = f"Supplier A: USD 4.50; Supplier B: {second_currency} 3.90."
    assert all(not check_failed(item) for item in score_output(category, case, output))
    point["quote_fields"].extend([
        {"quote_id": "22222222-2222-2222-2222-222222222221", "field_key": "quoted_quantity"},
        {"quote_id": "22222222-2222-2222-2222-222222222222", "field_key": "quoted_quantity"},
    ])
    point["text"] = ("Supplier A's unit price is USD 4.50; "
                     f"Supplier B's unit price is {second_currency} 3.90; "
                     "Supplier A's quoted quantity is 2000; "
                     "Supplier B's quoted quantity is 5000.")
    assert all(not check_failed(item) for item in score_output(category, case, output))
    point["text"] = "Supplier A and Supplier B prices cannot be directly compared."
    assert all(not check_failed(item) for item in score_output(category, case, output))
    point["text"] = "Direct price comparison is invalid for Supplier A and Supplier B."
    assert all(not check_failed(item) for item in score_output(category, case, output))


def test_general_and_quoted_lead_times_are_scored_separately() -> None:
    case = next(value for value in baseline.load_scope(["comparison"])["comparison"]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = output["key_tradeoffs"][0]
    point["text"] = (
        "Supplier A general catalog lead time is 50 days; "
        "quoted production lead time is 25 days."
    )
    assert all(not check_failed(item) for item in score_output("comparison", case, output))
    point["text"] = point["text"].replace("50 days", "25 days")
    assert any(check_failed(item) and item["name"] == "lead_time_context_signal"
               for item in score_output("comparison", case, output))
    point["text"] = "Supplier A catalog lead time is 25 days."
    assert any(check_failed(item) and item["name"] == "lead_time_context_signal"
               for item in score_output("comparison", case, output))


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("wording", [
    "Supplier A's general lead time is {days} days.",
    "Supplier A's catalog lead time is {days} days.",
    "Supplier A's typical lead time is {days} days.",
    "Supplier A's lead time is typically {days} days.",
    "Supplier A's usual production lead time is {days} days.",
    "Supplier A's lead time is normally {days} days.",
    "Supplier A's standard production lead time is {days} days.",
    "Supplier A typically has a lead time of {days} days.",
    "Normally, Supplier A's lead time is {days} days.",
])
def test_general_lead_context_paraphrases(
    category: str, wording: str
) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = (output["key_tradeoffs"][0] if category == "comparison"
             else output["analysis"]["key_tradeoffs"][0])
    for days, expected in ((50, True), (25, False)):
        point["text"] = wording.format(days=days)
        assert all(not check_failed(item) for item in score_output(category, case, output)) is expected, (
            wording, days
        )


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("wording", [
    "Supplier A's quoted production lead time is {days} days.",
    "Supplier A's quote lead time is {days} days.",
    "Supplier A's project-specific lead time is {days} days.",
    "Supplier A's lead time for this order is {days} days.",
    "For this order, Supplier A's lead time is {days} days.",
])
def test_project_lead_context_paraphrases(category: str, wording: str) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = (output["key_tradeoffs"][0] if category == "comparison"
             else output["analysis"]["key_tradeoffs"][0])
    for days, expected in ((25, True), (50, False)):
        point["text"] = wording.format(days=days)
        assert all(not check_failed(item) for item in score_output(category, case, output)) is expected, (
            wording, days
        )


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("wording", [
    "Supplier A's typical lead time for catalog orders is {days} days.",
    "Supplier A has a more usual production lead time of {days} days.",
    "Supplier A's normal catalog production lead time runs {days} days.",
])
def test_general_day_claims_use_local_context(category: str, wording: str) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = (output["key_tradeoffs"][0] if category == "comparison"
             else output["analysis"]["key_tradeoffs"][0])
    for days, expected in ((50, True), (25, False)):
        point["text"] = wording.format(days=days)
        assert all(not check_failed(item) for item in score_output(category, case, output)) is expected


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
@pytest.mark.parametrize("wording", [
    "The quote for Supplier A specifies a {days}-day production lead time.",
    "Supplier A's project order carries a production lead time of {days} days.",
    "Supplier A reports a {days}-day production lead time for this order.",
])
def test_quoted_day_claims_use_local_context(category: str, wording: str) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = (output["key_tradeoffs"][0] if category == "comparison"
             else output["analysis"]["key_tradeoffs"][0])
    for days, expected in ((25, True), (50, False)):
        point["text"] = wording.format(days=days)
        assert all(not check_failed(item) for item in score_output(category, case, output)) is expected


@pytest.mark.parametrize("category", ["comparison", "suggestion"])
def test_combined_and_ambiguous_day_claims(category: str) -> None:
    case = next(value for value in baseline.load_scope([category])[category]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    point = (output["key_tradeoffs"][0] if category == "comparison"
             else output["analysis"]["key_tradeoffs"][0])
    point["text"] = ("Supplier A's general catalog lead time is 50 days and "
                     "its quoted production lead time is 25 days.")
    assert all(not check_failed(item) for item in score_output(category, case, output))
    point["text"] = "Supplier A's typical lead time for this order is 50 days."
    checks = score_output(category, case, output)
    assert not any(check_failed(item) for item in checks)
    assert next(item for item in checks if item["name"] == "lead_time_context_signal") == {
        "name": "lead_time_context_signal", "kind": "heuristic", "triggered": False,
        "critical": True, "detail": None, "interpretation": "no_signal",
    }


def test_narrative_nonmatch_is_not_an_exact_groundedness_pass(tmp_path: Path) -> None:
    result, code = baseline.execute("offline", list(baseline.CATEGORIES), tmp_path)
    assert code == 0 and result["complete"] and result["expected_case_count"] == 90
    assert result["narrative_groundedness"] == "NOT_ESTABLISHED_BY_AUTOMATED_SCORING"
    assert result["human_review"]["status"] == "PENDING"
    assert result["human_review"]["case_count"] >= 10
    assert all(case["review_result"] is None for case in result["human_review"]["cases"])
    assert "incomparable_price_ranking_signal" not in result["metrics"]["comparison"]
    assert "lead_time_context_signal" not in result["metrics"]["comparison"]
    assert "supplier_free_text_capability_signal" not in result["metrics"]["supplier_explanation"]
    clean = next(case for case in result["cases"] if case["id"] == "mixed-currencies"
                 and case["category"] == "comparison")
    signal = next(item for item in clean["assertions"]
                  if item["name"] == "incomparable_price_ranking_signal")
    assert signal["kind"] == "heuristic" and signal["interpretation"] == "no_signal"
    assert "passed" not in signal
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "Automated completion does not prove free-text narrative groundedness" in summary
    assert "Human review required — PENDING" in summary


def test_warning_and_grounded_unfamiliar_paraphrase_are_not_rejected() -> None:
    case = next(value for value in baseline.load_scope(["comparison"])["comparison"]
                if value["id"] == "mixed-currencies")
    output = deepcopy(case["output"])
    output["supplier_summaries"][0]["text"] = (
        "Supplier A quotes USD 4.50, while Supplier B quotes AUD 3.90; "
        "these figures have no common currency basis."
    )
    output["supplier_summaries"][0]["supplier_ids"] = [
        "11111111-1111-1111-1111-111111111111",
        "11111111-1111-1111-1111-111111111112",
    ]
    output["supplier_summaries"][0]["quote_fields"] = [
        {"quote_id": "22222222-2222-2222-2222-222222222221", "field_key": "unit_price"},
        {"quote_id": "22222222-2222-2222-2222-222222222222", "field_key": "unit_price"},
    ]
    assert not any(check_failed(item) for item in score_output("comparison", case, output))
    output["supplier_summaries"][0]["text"] = (
        "Supplier B has a lower printed unit price than Supplier A, but the "
        "currencies differ and the figures have no common basis."
    )
    assert not any(check_failed(item) for item in score_output("comparison", case, output))

    case = next(value for value in baseline.load_scope(["comparison"])["comparison"]
                if value["id"] == "general-vs-project")
    output = deepcopy(case["output"])
    output["key_tradeoffs"][0]["text"] = (
        "Supplier A's ordinary catalogue schedule runs 50 days; "
        "the current project quotation promises 25 days."
    )
    assert not any(check_failed(item) for item in score_output("comparison", case, output))

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    output = deepcopy(case["output"])
    output["concerns"].append({
        "text": "The workshop crafts recycled polyester bags; confirm the current schedule.",
        "requirement_id": None, "evidence_ids": [case["fetched_evidence_ids"][0]],
    })
    assert not any(check_failed(item) for item in score_output(
        "supplier_explanation", case, output))


@pytest.mark.parametrize("wording", [
    "Supplier has an aerospace-engine production line.",
    "Supplier operates an aerospace-engine production line.",
    "Supplier's factory builds aircraft engines.",
    "Supplier specializes in aerospace engine manufacturing.",
    "The firm fabricates aircraft engines.",
    "The company designs surgical implants.",
    "This supplier assembles solar inverters.",
    "The factory molds automotive dashboards.",
    "The firm provides aerospace components.",
    "The company develops quantum processors.",
    "The supplier processes lithium batteries.",
])
def test_rendered_capability_paraphrases_fail_with_valid_evidence_id(wording: str) -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{"text": wording, "requirement_id": None,
                             "evidence_ids": [case["fetched_evidence_ids"][0]]}]
    assert not score_rendered(case, rendered)


def test_rendered_concern_requires_textual_capability_support() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    assert score_rendered(case, rendered)
    evidence_id = case["fetched_evidence_ids"][0]
    rendered["concerns"] = [{
        "text": "Supplier has aerospace-engine capability.",
        "requirement_id": None,
        "evidence_ids": [evidence_id],
    }]
    assert not score_rendered(case, rendered)
    supported = {**case, "evidence_texts": {
        evidence_id: "Supplier can produce recycled polyester bags."
    }}
    for wording in ("Supplier can produce recycled polyester bags.",
                    "Supplier manufactures recycled polyester bags.",
                    "The supplier's factory makes recycled polyester bags.",
                    "The firm fabricates recycled polyester bags.",
                    "Supplier supports recycled polyester."):
        rendered["concerns"][0]["text"] = wording
        assert score_rendered(supported, rendered)


@pytest.mark.parametrize("object_name", [
    "aircraft engines", "surgical implants", "solar inverters", "quantum processors",
])
@pytest.mark.parametrize("verb", ["designs", "assembles", "processes", "supplies"])
def test_unrelated_supplier_facts_fail_across_objects_and_verbs(
    object_name: str, verb: str,
) -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    supported = {**case, "evidence_texts": {
        case["fetched_evidence_ids"][0]: "Supplier produces recycled polyester bags."
    }}
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{
        "text": f"The supplier {verb} {object_name}.", "requirement_id": None,
        "evidence_ids": [case["fetched_evidence_ids"][0]],
    }]
    assert not score_rendered(supported, rendered)


def test_normalized_supplier_fact_and_grounded_evidence_paraphrases() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    evidence_id = case["fetched_evidence_ids"][0]
    supported = {**case,
                 "supplier_facts": {"capabilities": ["travel bags"]},
                 "evidence_texts": {evidence_id: "Supplier produces recycled polyester bags."}}
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{
        "text": "", "requirement_id": None, "evidence_ids": [evidence_id],
    }]
    for wording in ("Supplier supports travel bags.",
                    "Supplier fabricates recycled polyester bags.",
                    "The factory makes recycled polyester bags."):
        rendered["concerns"][0]["text"] = wording
        assert score_rendered(supported, rendered)
    rendered["concerns"][0]["text"] = "Supplier designs surgical implants."
    assert not score_rendered(supported, rendered)


def test_free_text_respects_deterministic_finding_status() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "required-failure")
    rendered = deepcopy(case["output"])
    rendered["required_failures"][0]["text"] = "Material (recycled polyester): Does Not Meet."
    rendered["concerns"] = [{
        "text": "Supplier does not meet the recycled polyester requirement.",
        "requirement_id": None,
        "evidence_ids": [case["fetched_evidence_ids"][0]],
    }]
    assert score_rendered(case, rendered)
    rendered["concerns"][0]["text"] = "Supplier meets the recycled polyester requirement."
    assert not score_rendered(case, rendered)
    rendered["concerns"][0]["text"] = "Supplier supports recycled polyester."
    assert not score_rendered(case, rendered)


def test_negated_evidence_cannot_support_positive_manufacturing_claim() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    evidence_id = case["fetched_evidence_ids"][0]
    unsupported = {**case, "evidence_texts": {
        evidence_id: "Supplier does not manufacture recycled polyester bags."
    }}
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{
        "text": "Supplier manufactures recycled polyester bags.",
        "requirement_id": None, "evidence_ids": [evidence_id],
    }]
    assert not score_rendered(unsupported, rendered)


@pytest.mark.parametrize("section", [
    "strengths", "required_failures", "preferred_findings", "unknowns", "conflicts", "concerns",
])
def test_all_supplier_narrative_fields_reject_unrelated_capability_claim(section: str) -> None:
    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    output = deepcopy(case["output"])
    output[section].append({
        "text": "The firm fabricates aircraft engines.", "requirement_id": None,
        "evidence_ids": [case["fetched_evidence_ids"][0]],
    })
    assert not all(not check_failed(item) for item in score_output("supplier_explanation", case, output))


def test_capability_evidence_must_match_cited_id() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    extra_id = "33333333-3333-3333-3333-333333333332"
    other = deepcopy(case)
    other["fetched_evidence_ids"].append(extra_id)
    other["evidence_texts"] = {extra_id: "Supplier fabricates travel bags."}
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{
        "text": "The supplier fabricates travel bags.",
        "requirement_id": None, "evidence_ids": [case["fetched_evidence_ids"][0]],
    }]
    assert not score_rendered(other, rendered)
    rendered["concerns"][0]["evidence_ids"] = [extra_id]
    rendered["evidence_ids"].append(extra_id)
    assert score_rendered(other, rendered)


def test_material_match_does_not_prove_manufacturing() -> None:
    from sourcepilot.ai.supplier_explanation_eval import score_rendered

    case = next(value for value in baseline.load_scope(["supplier_explanation"])["supplier_explanation"]
                if value["id"] == "clear-match")
    rendered = deepcopy(case["output"])
    rendered["strengths"][0]["text"] = "Material (recycled polyester): Meets."
    rendered["concerns"] = [{
        "text": "Supplier supports recycled polyester.",
        "requirement_id": None, "evidence_ids": [case["fetched_evidence_ids"][0]],
    }]
    assert score_rendered(case, rendered)
    rendered["concerns"][0]["text"] = "Supplier manufactures recycled polyester."
    assert not score_rendered(case, rendered)


def test_quote_metric_counts_and_money_order_equivalence() -> None:
    from sourcepilot.ai.quote_extraction_eval import metric_counts
    from sourcepilot.ai.quote_extractor import QuoteExtraction

    case = parsed_quote_case(baseline.load_scope(["quote_extraction"])["quote_extraction"][0])
    output = deepcopy(case["output"])
    output["fields"]["unit_price"]["extracted_value"] = "4.6000"
    assert all(not check_failed(item) for item in score_output("quote_extraction", case, output))
    counts = metric_counts(QuoteExtraction.model_validate(output), case)
    assert counts["field_accuracy"] == (21, 21)
    assert counts["currency_accuracy"] == (1, 1)
    case = next(
        case
        for case in baseline.load_scope(["quote_extraction"])["quote_extraction"]
        if case["id"] == "conflicting-lead-time"
    )
    output = deepcopy(case["output"])
    output["fields"]["production_lead_time"]["conflicting_values"].reverse()
    parsed_quote_case(case)
    output["fields"]["production_lead_time"]["source_block_ids"].reverse()
    assert all(not check_failed(item) for item in score_output("quote_extraction", case, output))


def rescore_retained_quotes(output: Path) -> dict[str, Any]:
    """Local analysis of retained v2 responses; no live runner/provider/DB path."""
    from sourcepilot.ai.eval_scoring import measurements

    evidence = next(
        (baseline.ROOT / "docs/implementation/evidence/M6-U1").glob(
            "quote-v2-filtered-live*/baseline/results.json"
        )
    )
    historical = baseline.read_json(evidence)
    cases = baseline.load_scope(["quote_extraction"])["quote_extraction"]
    retained = {item["id"]: item for item in historical["cases"]}
    result = {
        "mode": "offline",
        "analysis": "retained-output local rescore, not a live baseline",
        "origin": str(evidence.relative_to(baseline.ROOT)),
        "provenance": baseline.provenance({"quote_extraction": cases}, "offline"),
        "selected_categories": ["quote_extraction"],
        "full_scope": False,
        "required_cases": {"quote_extraction": [case["id"] for case in cases]},
        "human_review": deepcopy(historical["human_review"]),
        "cases": [],
    }
    with TemporaryDirectory() as directory:
        for case in cases:
            _, checks = baseline.parser_result(case, Path(directory))
            item = retained[case["id"]]
            if "expected_error" in case:
                status, counts = "EXPECTED_REJECTION", {}
            else:
                if any(check_failed(check) for check in checks):
                    raise ValueError("Retained rescore parser/request validation failed")
                # Match historical live assertion emission; parser checks are preflight.
                checks = score_output("quote_extraction", case, item["output"])
                counts = measurements("quote_extraction", case, item["output"])
                status = "QUALITY_FINDING" if any(check_failed(c) for c in checks) else "PASS"
            result["cases"].append(
                {
                    "category": "quote_extraction",
                    "id": case["id"],
                    "status": status,
                    "assertions": checks,
                    "measurements": counts,
                }
            )
    result["exit_code"] = baseline.summarize(result)
    baseline.write_report(result, output)
    return result


def test_all_twelve_retained_outputs_reconcile_without_provider_or_evidence_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sourcepilot.ai.quote_extraction_eval import METRIC_NAMES

    protected = list((baseline.ROOT / "docs/implementation/evidence/M6-U1").rglob("*"))
    protected += list((baseline.ROOT / "apps/api/evals").rglob("*"))
    before = baseline.hash_files([p for p in protected if p.is_file()])
    forbidden = Mock(side_effect=AssertionError("Provider/database/live execution forbidden"))
    monkeypatch.setattr(baseline.OpenAIResponsesClient, "from_environment", forbidden)
    monkeypatch.setattr(baseline, "preflight_database", forbidden)
    monkeypatch.setattr(baseline, "run_case", forbidden)
    historical_path = next((baseline.ROOT / "docs/implementation/evidence/M6-U1").glob(
        "quote-v2-filtered-live*/baseline/results.json"))
    historical = baseline.read_json(historical_path)
    old_checks = [c for case in historical["cases"] for c in case["assertions"] if c["kind"] == "exact"]
    assert (sum(c["passed"] for c in old_checks), len(old_checks)) == (359, 443)
    for item in historical["cases"]:
        if item["id"] in {"willow-primary", "quantity-mismatch"}:
            value = item["output"]["fields"]["supplier_notes"]["extracted_value"]
            assert "\u2014" in value
            captured = json.loads(item["model_responses"][0]["output_text"])
            assert captured["fields"]["supplier_notes"]["extracted_value"] == value
    report = rescore_retained_quotes(tmp_path)
    assert report["complete"] and report["executed_case_count"] == 12
    assert report["status_counts"] == {"QUALITY_FINDING": 10, "EXPECTED_REJECTION": 2}
    totals = report["measurements"]["quote_extraction"]
    assignments = []
    exact_checks = [c for case in report["cases"] for c in case["assertions"] if c["kind"] == "exact"]
    assert (sum(c["passed"] for c in exact_checks), len(exact_checks)) == (375, 427)
    # Compare independently emitted named assertions to report aggregation.
    metrics = report["metrics"]["quote_extraction"]
    assert sum(m["numerator"] for m in metrics.values()) == 375
    assert sum(m["denominator"] for m in metrics.values()) == 427
    assert len(report["critical_findings"]) == 52
    for case in report["cases"]:
        checks = {check["name"]: check for check in case["assertions"]}
        if case["status"] == "EXPECTED_REJECTION":
            assert checks["parser_rejection"]["passed"]
            continue
        for name in METRIC_NAMES:
            m = case["measurements"][name]
            assert checks[name]["passed"] == (
                m["numerator"] == 0
                if name == "hallucination_rate"
                else m["numerator"] == m["denominator"]
            )
        assert case["measurements"]["field_accuracy"]["numerator"] == sum(
            c["passed"]
            for name, c in checks.items()
            if name.endswith((".value", ".unknown", ".conflict"))
        )
        for name, check in checks.items():
            if name.endswith(".field_assignment"):
                assignments.append((case["id"], name))
                assert check["critical"] and not check["passed"]
            assert not name.endswith(
                (".unsupported_value", ".unresolved_support", ".misattributed_evidence")
            )
    assert len(assignments) == 11
    assert ("quantity-mismatch", "field.compliance_notes.field_assignment") in assignments
    for name, expected in {
        "field_accuracy": (199, 210),
        "source_block_accuracy": (199, 210),
        "numeric_accuracy": (55, 55),
        "currency_accuracy": (10, 10),
        "unknown_detection": (74, 85),
        "conflict_detection": (1, 1),
        "hallucination_rate": (0, 85),
        "expected_unknown_known_rate": (11, 85),
        "unsupported_value_rate": (0, 210),
        "unresolved_support_rate": (0, 210),
    }.items():
        assert (totals[name]["numerator"], totals[name]["denominator"]) == expected
    persisted = baseline.read_json(tmp_path / "results.json")
    assert persisted == report
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert all(name in summary for _, name in assignments)
    assert baseline.hash_files([baseline.ROOT / path for path in before]) == before
    forbidden.assert_not_called()
