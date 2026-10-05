"""Contract and destructive-reset guards for the test-only browser harness."""

import json
import socket
from typing import Any, cast
from unittest.mock import MagicMock, Mock

import pytest
from psycopg import Connection as PsycopgConnection

from sourcepilot.ai.brief_interpreter import ExtractedBrief
from sourcepilot.ai.clarification import ClarificationSet
from sourcepilot.ai.client import OpenAIResponsesClient
from sourcepilot.ai.comparison_advice import ComparisonAdvice, validate_advice
from sourcepilot.ai.quote_extractor import QuoteExtraction, validate_source_references
from sourcepilot.ai.supplier_explanation import ModelSupplierExplanation
from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis, validate_analysis
from sourcepilot.ai.tradeoff_analysis_eval import fixture_snapshot
from tests.e2e_support.database import safe_database_url, validate_urls
from tests.e2e_support.model import (
    API,
    PDFS,
    SCENARIO,
    BlockedOpenAI,
    DeterministicModel,
    comparison_output,
)


def environment() -> dict[str, str]:
    prefix = "postgresql+psycopg://sourcepilot:sourcepilot@127.0.0.1:5432/"
    return {"DATABASE_URL": prefix + "sourcepilot", "TEST_DATABASE_URL": prefix + "sourcepilot_test",
            "E2E_DATABASE_URL": prefix + "sourcepilot_e2e"}


@pytest.mark.parametrize("key", ["DATABASE_URL", "TEST_DATABASE_URL", "E2E_DATABASE_URL"])
def test_missing_database_configuration_never_connects(key: str, monkeypatch: pytest.MonkeyPatch) -> None:
    values = environment()
    del values[key]
    connect = Mock(side_effect=AssertionError("must not connect"))
    monkeypatch.setattr("tests.e2e_support.database.create_engine", connect)
    with pytest.raises(RuntimeError, match=key):
        safe_database_url(values)
    connect.assert_not_called()


@pytest.mark.parametrize("key", ["DATABASE_URL", "TEST_DATABASE_URL"])
@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_protected_aliases_are_rejected(key: str, host: str) -> None:
    values = environment()
    values[key] = f"postgresql+psycopg://sourcepilot:sourcepilot@{host}:5432/sourcepilot_e2e"
    with pytest.raises(RuntimeError, match="separation|separate"):
        validate_urls(values)


@pytest.mark.parametrize("url", ["sqlite:///sourcepilot_e2e", "postgresql+psycopg:///sourcepilot_e2e",
    "postgresql+psycopg://localhost/sourcepilot", "postgresql+psycopg://localhost/sourcepilot_e2e?host=elsewhere"])
def test_invalid_or_overridden_targets_are_rejected(url: str) -> None:
    values = environment()
    values["E2E_DATABASE_URL"] = url
    with pytest.raises(RuntimeError):
        validate_urls(values)


def test_resolution_error_aborts_even_for_protected_host(monkeypatch: pytest.MonkeyPatch) -> None:
    resolve = socket.getaddrinfo

    def failing(host: str, *args: object, **kwargs: object) -> list:
        if host == "unresolvable.invalid":
            raise socket.gaierror("fixture resolution failure")
        return resolve(host, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(socket, "getaddrinfo", failing)
    values = environment()
    values["DATABASE_URL"] = values["DATABASE_URL"].replace("127.0.0.1", "unresolvable.invalid")
    with pytest.raises(RuntimeError, match="Could not resolve"):
        validate_urls(values)


def test_nonloopback_target_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 5432)),
    ])
    with pytest.raises(RuntimeError, match="loopback"):
        validate_urls(environment())


def test_connection_error_is_not_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = Mock()
    engine.begin.side_effect = RuntimeError("cannot connect")
    monkeypatch.setattr("tests.e2e_support.database.create_engine", lambda *args, **kwargs: engine)
    with pytest.raises(RuntimeError, match="cannot connect"):
        safe_database_url(environment())
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("result", [None, True])
def test_indeterminate_or_same_identity_never_resets(result: bool | None, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from tests.e2e_support.server import main

    for key, value in environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr("tests.e2e_support.database.targets_same_postgres_database", lambda *args: result)
    reset = Mock()
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    with pytest.raises(RuntimeError, match="establish separation"):
        main()
    reset.assert_not_called()


@pytest.mark.parametrize("addresses", [[], [
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 5432)),
    (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.1", 5432)),
]])
def test_empty_or_mixed_resolution_never_resets(addresses: list, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from tests.e2e_support.server import main

    for key, value in environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: addresses)
    reset = Mock()
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    with pytest.raises(RuntimeError, match="loopback"):
        main()
    reset.assert_not_called()


@pytest.mark.parametrize("actual", [
    ("sourcepilot", "127.0.0.1", 5432, "sourcepilot"),
    ("sourcepilot_e2e", "192.0.2.1", 5432, "sourcepilot"),
    ("sourcepilot_e2e", "127.0.0.2", 5432, "sourcepilot"),
    ("sourcepilot_e2e", "127.0.0.1", 5433, "sourcepilot"),
    ("sourcepilot_e2e", None, None, "sourcepilot"),
    ("sourcepilot_e2e", "127.0.0.1", 5432, "other_user"),
    (None, None, None, None),
    ("sourcepilot_e2e", "127.0.0.1", 5432, "sourcepilot"),
])
def test_connection_identity_must_match_before_reset(
    actual: tuple, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    from tests.e2e_support.server import main

    for key, value in environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.one.return_value = (actual[0], actual[3])
    driver = MagicMock(spec=PsycopgConnection)
    driver.info.dbname, driver.info.hostaddr, driver.info.port, driver.info.user = actual
    connection.connection.driver_connection = driver
    create = Mock(return_value=engine)
    monkeypatch.setattr("tests.e2e_support.database.create_engine", create)
    reset = Mock(side_effect=RuntimeError("stop after validated reset boundary"))
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    expected = ("sourcepilot_e2e", "127.0.0.1", 5432, "sourcepilot")
    if actual == expected:
        with pytest.raises(RuntimeError, match="stop after validated"):
            main()
        target = reset.call_args.args[0]
        assert target.connection is connection
        assert target.url == environment()["E2E_DATABASE_URL"]
        assert create.call_args.kwargs["connect_args"]["hostaddr"] == "127.0.0.1"
    else:
        with pytest.raises(RuntimeError, match="Connected database identity"):
            main()
        reset.assert_not_called()
    engine.dispose.assert_called_once()


@pytest.mark.parametrize("key", [
    "PGHOSTADDR", "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD",
    "PGPASSFILE", "PGSERVICE", "PGSERVICEFILE", "PGSYSCONFDIR", "PGOPTIONS",
    "PGTARGETSESSIONATTRS", "PGLOADBALANCEHOSTS", "PGSSLMODE", "PGAPPNAME",
    "PGFUTURE_ROUTING_SETTING", "pghostaddr",
])
def test_inherited_libpq_settings_never_connect_or_reset(
    key: str, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    from tests.e2e_support.server import main

    for name, value in environment().items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv(key, "redirected or ambiguous fixture")
    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    connect = Mock()
    reset = Mock()
    monkeypatch.setattr("tests.e2e_support.database.create_engine", connect)
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    with pytest.raises(RuntimeError, match="libpq"):
        main()
    # An explicit mapping cannot conceal inherited process settings either.
    with pytest.raises(RuntimeError, match="libpq"):
        safe_database_url(environment())
    connect.assert_not_called()
    reset.assert_not_called()


def test_reset_uses_only_the_validated_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.e2e_support.database import ValidatedDatabase, reset_database

    connection = MagicMock()
    monkeypatch.setattr("tests.e2e_support.database.inspect", lambda value: Mock(get_table_names=lambda: ["requirements"]))
    downgrade, upgrade, seed = Mock(), Mock(), Mock()
    monkeypatch.setattr("tests.e2e_support.database.command.downgrade", downgrade)
    monkeypatch.setattr("tests.e2e_support.database.command.upgrade", upgrade)
    monkeypatch.setattr("tests.e2e_support.database.seed_suppliers", seed)
    session = MagicMock()
    session_factory = Mock(return_value=session)
    monkeypatch.setattr("tests.e2e_support.database.Session", session_factory)
    create = Mock(side_effect=AssertionError("reset must never reconnect"))
    monkeypatch.setattr("tests.e2e_support.database.create_engine", create)
    reset_database(ValidatedDatabase(environment()["E2E_DATABASE_URL"], connection))
    connection.execute.assert_called_once()
    for migration in (downgrade, upgrade):
        assert migration.call_args.args[0].attributes["connection"] is connection
    session_factory.assert_called_once_with(connection)
    seed.assert_called_once_with(session.__enter__.return_value)
    create.assert_not_called()


def test_libpq_override_introduced_after_validation_blocks_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.e2e_support.database import ValidatedDatabase, reset_database

    connection = MagicMock()
    monkeypatch.setenv("PGSERVICE", "redirect")
    with pytest.raises(RuntimeError, match="libpq"):
        reset_database(ValidatedDatabase(environment()["E2E_DATABASE_URL"], connection))
    connection.execute.assert_not_called()


@pytest.mark.parametrize("server_identity", [("sourcepilot", "sourcepilot"), (None, None),
                                           ("sourcepilot_e2e", "other_user")])
def test_server_identity_disagreement_blocks_launcher_writes(
    server_identity: tuple, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    from tests.e2e_support.server import main

    for key, value in environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    driver = MagicMock(spec=PsycopgConnection)
    driver.info.dbname = "sourcepilot_e2e"
    driver.info.hostaddr = "127.0.0.1"
    driver.info.port = 5432
    driver.info.user = "sourcepilot"
    connection.connection.driver_connection = driver
    connection.execute.return_value.one.return_value = server_identity
    monkeypatch.setattr("tests.e2e_support.database.create_engine", lambda *args, **kwargs: engine)
    reset = Mock()
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    with pytest.raises(RuntimeError, match="identity"):
        main()
    reset.assert_not_called()


def test_e2e_migrations_never_fall_back_to_a_new_connection() -> None:
    from pathlib import Path

    from alembic import command
    from tests.database_test_support import API_DIRECTORY, alembic_config

    config = alembic_config(environment()["E2E_DATABASE_URL"])
    config.set_main_option("script_location", str(Path(__file__).parent / "e2e_support/migrations"))
    config.set_main_option("version_locations", str(API_DIRECTORY / "alembic/versions"))
    with pytest.raises(RuntimeError, match="validated connection and transaction"):
        command.upgrade(config, "head")


def invoke(name: str, data: str, schema: dict | None = None) -> str:
    model = {"ExtractedBrief": ExtractedBrief, "ClarificationSet": ClarificationSet,
             "QuoteExtraction": QuoteExtraction}.get(name)
    return DeterministicModel().invoke(instructions="fixture", input_text=data, schema_name=name,
        schema=schema if schema is not None else model.model_json_schema() if model else {}).output_text


def test_brief_and_clarification_contracts() -> None:
    assert json.loads(invoke("ExtractedBrief", SCENARIO["request"])) == SCENARIO["brief"]
    output = invoke("ClarificationSet", json.dumps({"unresolved_fields": [{"field_key": "delivery_target"}]}))
    assert ClarificationSet.model_validate_json(output).questions[0].field_key == "delivery_target"
    with pytest.raises(AssertionError, match="request"):
        invoke("ExtractedBrief", "unrecognized request")
    with pytest.raises(AssertionError, match="fields"):
        invoke("ClarificationSet", json.dumps({"unresolved_fields": [{"field_key": "quantity"}]}))


@pytest.mark.parametrize("filename,case", [("harbor_primary.pdf", "harbor-primary"),
    ("willow_primary.pdf", "willow-primary"), ("moss_primary.pdf", "moss-primary")])
def test_quote_extractor_reuses_exact_recorded_contract(filename: str, case: str) -> None:
    parsed = json.loads((PDFS / "expected_blocks.json").read_text())[filename]["blocks"]
    data = {"document_blocks": [{"id": reference, "text": content} for reference, content in parsed]}
    output = invoke("QuoteExtraction", json.dumps(data))
    expected = json.loads((API / "evals/quote_extraction/model_outputs.json").read_text())[case]
    assert json.loads(output) == expected
    validate_source_references(QuoteExtraction.model_validate_json(output), {row[0] for row in parsed})


@pytest.mark.parametrize("name", ["UnknownOperation", "SuggestedSupplierResult", "ComparisonAdvice"])
def test_wrong_or_separate_unsupported_operation_fails_closed(name: str) -> None:
    with pytest.raises(AssertionError, match="Unsupported"):
        invoke(name, "{}")


def test_unknown_pdf_and_changed_schema_fail_closed() -> None:
    with pytest.raises(AssertionError, match="document blocks"):
        invoke("QuoteExtraction", '{"document_blocks":[]}')
    with pytest.raises(AssertionError, match="schema"):
        invoke("ExtractedBrief", SCENARIO["request"], {})
    with pytest.raises(AssertionError, match="forbidden"):
        BlockedOpenAI(api_key="unused")


def test_live_sdk_is_blocked_even_when_model_factory_is_bypassed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sourcepilot.ai.client.OpenAI", BlockedOpenAI)
    monkeypatch.setenv("OPENAI_API_KEY", "unused")
    monkeypatch.setenv("SOURCEPILOT_AI_MODEL", "unused")
    with pytest.raises(AssertionError, match="forbidden"):
        OpenAIResponsesClient.from_environment()


def test_advice_and_standalone_tradeoff_contracts_use_real_references() -> None:
    snapshot = fixture_snapshot()
    assert snapshot.comparison_payload is not None
    # The eval's minimal payload omits ordinary fields present in browser snapshots.
    for supplier in cast(list[dict[str, Any]], snapshot.comparison_payload["suppliers"]):
        supplier["quote_fields"].extend([
            {"field_key": "currency", "current_value": "USD", "evidence": []},
            {"field_key": "production_lead_time", "current_value": "30 days", "evidence": []},
        ])
    output = comparison_output(snapshot.comparison_payload)
    advice = ComparisonAdvice.model_validate(output)
    validate_advice(advice, snapshot)
    validate_analysis(TradeoffAnalysis.model_validate(output["analysis"]), snapshot)
    assert advice.suggestion.supplier_id == SCENARIO["advisory"]["supplier_id"] is None
    assert "preferred_supplier_id" not in output


def test_analyst_wrong_operation_and_sequence_fail_closed() -> None:
    model = DeterministicModel()
    with pytest.raises(AssertionError, match="Unsupported"):
        model.invoke_with_tools(instructions="", input_items=[], tools=[], schema_name="SuggestedSupplierResult", schema={})
    initial = {"supplier_id": "fixture"}
    tools = [{"name": "get_supplier_snapshot"}, {"name": "get_supplier_evidence"}]
    with pytest.raises(AssertionError, match="sequence"):
        model.invoke_with_tools(instructions="", input_items=[{"content": json.dumps(initial)}, {}], tools=tools,
            schema_name="ModelSupplierExplanation", schema=ModelSupplierExplanation.model_json_schema())


@pytest.mark.parametrize("failure", [RuntimeError("missing URL"), RuntimeError("identity unknown"),
                                    RuntimeError("connection failed")])
def test_launcher_never_resets_when_safety_cannot_be_established(
    failure: RuntimeError, monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    from tests.e2e_support.server import main

    monkeypatch.setenv("E2E_DOCUMENT_STORAGE_DIR", str(tmp_path))
    guard = Mock(side_effect=failure)
    reset = Mock()
    monkeypatch.setattr("tests.e2e_support.server.validated_database", guard)
    monkeypatch.setattr("tests.e2e_support.server.reset_database", reset)
    with pytest.raises(RuntimeError, match=str(failure)):
        main()
    reset.assert_not_called()
