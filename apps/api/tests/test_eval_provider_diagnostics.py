"""Provider-free verification of the opt-in quote-eval diagnostic sidecars."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import httpx
import pytest
from openai import APIConnectionError, APIError, APIStatusError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sourcepilot.ai import eval_baseline as baseline
from sourcepilot.ai.client import ModelInvocation, ModelProviderError, OpenAIResponsesClient
from sourcepilot.ai.structured import run_structured_operation

SECRET = "synthetic-sensitive-sentinel"
FIELDS = {
    "case_id", "invocation", "http_status", "provider_error_type",
    "provider_error_code", "rejected_parameter",
}


@pytest.fixture
def directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(baseline, "API_ROOT", tmp_path)
    return tmp_path / ".eval-results" / "explicitly-authorized-synthetic"


def sdk_error(status: int | None = 400, **fields: Any) -> APIError:
    request = httpx.Request(
        "POST", "https://example.invalid/" + SECRET,
        headers={"Authorization": SECRET}, content=SECRET,
    )
    if status is None:
        return APIConnectionError(message=SECRET, request=request)
    return APIStatusError(
        SECRET, response=httpx.Response(status, request=request, headers={"x-request-id": SECRET}),
        body={"type": "invalid_request_error", "code": "invalid_json_schema",
              "param": "text.format.schema", "message": SECRET, "extra": SECRET, **fields},
    )


def wrapper(error: Exception) -> OpenAIResponsesClient:
    """Use the actual production exception normalization, with no SDK invocation."""
    client = OpenAIResponsesClient.__new__(OpenAIResponsesClient)
    client.model = "synthetic-model"
    client._client = Mock()
    client._client.responses.create.side_effect = error
    return client


def invoke(client: baseline.CapturingClient, tools: bool = False) -> Any:
    if tools:
        return client.invoke_with_tools(
            instructions=SECRET, input_items=[], tools=[], schema_name="Synthetic", schema={}
        )
    return client.invoke(
        instructions=SECRET, input_text=SECRET, schema_name="Synthetic", schema={}
    )


def records(directory: Path) -> list[dict[str, Any]]:
    result = []
    for path in directory.glob("*.json"):
        content = path.read_text(encoding="utf-8")
        assert SECRET not in content
        record = json.loads(content)
        assert set(record) == FIELDS
        result.append(record)
    return sorted(result, key=lambda row: row["invocation"])


@pytest.mark.parametrize("status", [400, 401, 403, 404, 422, None])
@pytest.mark.parametrize("tools", [False, True])
def test_actual_exception_chain_and_exact_diagnostic_fields(
    directory: Path, status: int | None, tools: bool,
) -> None:
    original = sdk_error(status)
    client = baseline.CapturingClient(
        wrapper(original), [], provider_error_directory=directory, case_id="harbor-primary"
    )
    with pytest.raises(ModelProviderError) as caught:
        invoke(client, tools)
    assert caught.value.__cause__ is original
    assert caught.value.retryable is (status is None)
    assert client.responses == []
    assert records(directory) == [{
        "case_id": "harbor-primary", "invocation": 1, "http_status": status,
        "provider_error_type": "invalid_request_error" if status else None,
        "provider_error_code": "invalid_json_schema" if status else None,
        "rejected_parameter": "text.format.schema" if status else None,
    }]


@pytest.mark.parametrize("value", [SECRET, "new_provider_value", "", [], {}, True, 42])
def test_unfamiliar_strings_and_unexpected_shapes_are_not_serialized(
    directory: Path, value: Any,
) -> None:
    error = sdk_error(type=value, code=value, param=value)
    client = baseline.CapturingClient(
        wrapper(error), [], provider_error_directory=directory, case_id="harbor-primary"
    )
    with pytest.raises(ModelProviderError):
        invoke(client)
    row = records(directory)[0]
    assert [row[k] for k in ("provider_error_type", "provider_error_code", "rejected_parameter")] == [
        "UNRECOGNIZED", "UNRECOGNIZED", "UNRECOGNIZED",
    ]


@pytest.mark.parametrize("status", [True, "401", -1, 600, None])
def test_malformed_status_is_null(directory: Path, status: Any) -> None:
    error = sdk_error()
    error.status_code = status  # type: ignore[attr-defined]
    delegate = Mock(model="synthetic")
    normalized = ModelProviderError(SECRET, retryable=False)
    normalized.__cause__ = error
    delegate.invoke.side_effect = normalized
    with pytest.raises(ModelProviderError) as caught:
        invoke(baseline.CapturingClient(
            delegate, [], provider_error_directory=directory, case_id="harbor-primary"
        ))
    assert caught.value is normalized
    assert records(directory)[0]["http_status"] is None


@pytest.mark.parametrize("cause", [None, ValueError(SECRET)])
def test_missing_or_non_sdk_cause_has_null_metadata(
    directory: Path, cause: Exception | None,
) -> None:
    normalized = ModelProviderError(SECRET, retryable=False)
    normalized.__cause__ = cause
    delegate = Mock(model="synthetic")
    delegate.invoke.side_effect = normalized
    with pytest.raises(ModelProviderError) as caught:
        invoke(baseline.CapturingClient(
            delegate, [], provider_error_directory=directory, case_id="harbor-primary"
        ))
    assert caught.value is normalized and caught.value.__cause__ is cause
    assert records(directory) == [{
        "case_id": "harbor-primary", "invocation": 1, "http_status": None,
        "provider_error_type": None, "provider_error_code": None, "rejected_parameter": None,
    }]


def test_missing_sdk_fields_are_null(directory: Path) -> None:
    client = baseline.CapturingClient(
        wrapper(sdk_error(type=None, code=None, param=None)), [],
        provider_error_directory=directory, case_id="harbor-primary",
    )
    with pytest.raises(ModelProviderError):
        invoke(client)
    row = records(directory)[0]
    assert all(row[k] is None for k in (
        "provider_error_type", "provider_error_code", "rejected_parameter",
    ))


@pytest.mark.parametrize("kind,code,param", [
    ("authentication_error", "invalid_api_key", None),
    ("permission_error", "permission_denied", "model"),
    ("not_found_error", "model_not_found", "model"),
    ("invalid_request_error", "invalid_json_schema", "text.format.schema"),
    ("server_error", "internal_server_error", None),
])
def test_allowlisted_provider_identifiers_are_preserved_without_inference(
    directory: Path, kind: str, code: str, param: str | None,
) -> None:
    with pytest.raises(ModelProviderError):
        invoke(baseline.CapturingClient(
            wrapper(sdk_error(type=kind, code=code, param=param)), [],
            provider_error_directory=directory, case_id="harbor-primary",
        ))
    row = records(directory)[0]
    assert (row["provider_error_type"], row["provider_error_code"], row["rejected_parameter"]) == (
        kind, code, param,
    )


def test_disabled_diagnostics_do_not_inspect_exception_or_write(
    directory: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = Mock(side_effect=AssertionError("disabled capture must not write"))
    monkeypatch.setattr(baseline.tempfile, "NamedTemporaryFile", writer)
    original = ModelProviderError(SECRET, retryable=False)
    delegate = Mock(model="synthetic")
    delegate.invoke.side_effect = original
    with pytest.raises(ModelProviderError) as caught:
        invoke(baseline.CapturingClient(delegate, []))
    assert caught.value is original
    writer.assert_not_called()
    assert not directory.exists()


@pytest.mark.parametrize("case_id", [None, SECRET, "harbor-primary\n" + SECRET])
def test_case_identifier_must_be_a_known_local_quote_case(
    directory: Path, case_id: str | None,
) -> None:
    with pytest.raises(ModelProviderError):
        invoke(baseline.CapturingClient(
            wrapper(sdk_error()), [], provider_error_directory=directory, case_id=case_id,
        ))
    assert not directory.exists()


def test_sidecar_cannot_write_outside_ignored_eval_tree(directory: Path) -> None:
    outside = directory.parents[1] / "historical-baseline"
    with pytest.raises(ModelProviderError):
        invoke(baseline.CapturingClient(
            wrapper(sdk_error()), [], provider_error_directory=outside, case_id="harbor-primary",
        ))
    assert not outside.exists()


def test_fresh_files_and_counter_include_successes_and_both_invocation_methods(
    directory: Path,
) -> None:
    delegate = Mock(model="synthetic")
    success = ModelInvocation("{}", 1, 1)
    error = ModelProviderError(SECRET, retryable=False)
    delegate.invoke.side_effect = [success, error]
    delegate.invoke_with_tools.side_effect = error
    client = baseline.CapturingClient(
        delegate, [], provider_error_directory=directory, case_id="harbor-primary"
    )
    assert invoke(client) is success
    assert not directory.exists()
    for tools in (False, True):
        with pytest.raises(ModelProviderError) as caught:
            invoke(client, tools)
        assert caught.value is error
    first_files = {p: p.read_bytes() for p in directory.glob("*.json")}
    assert [row["invocation"] for row in records(directory)] == [2, 3]
    another = baseline.CapturingClient(
        delegate, [], provider_error_directory=directory, case_id="willow-primary"
    )
    delegate.invoke.side_effect = error
    with pytest.raises(ModelProviderError):
        invoke(another)
    assert len(list(directory.glob("*.json"))) == 3
    assert all(p.read_bytes() == content for p, content in first_files.items())


@pytest.mark.parametrize("failure", ["create", "write", "metadata", "mkdir"])
def test_diagnostic_failures_never_replace_original_exception(
    directory: Path, monkeypatch: pytest.MonkeyPatch, failure: str,
) -> None:
    error = sdk_error()
    normalized = ModelProviderError(SECRET, retryable=False)
    normalized.__cause__ = error
    delegate = Mock(model="synthetic")
    delegate.invoke.side_effect = normalized
    if failure == "create":
        monkeypatch.setattr(baseline.tempfile, "NamedTemporaryFile", Mock(side_effect=OSError(SECRET)))
    elif failure == "write":
        monkeypatch.setattr(baseline.json, "dump", Mock(side_effect=OSError(SECRET)))
    elif failure == "mkdir":
        monkeypatch.setattr(Path, "mkdir", Mock(side_effect=OSError(SECRET)))
    else:
        class BrokenSDKError(APIError):
            def __getattribute__(self, name: str) -> Any:
                if name == "code":
                    raise RuntimeError(SECRET)
                return super().__getattribute__(name)
        normalized.__cause__ = BrokenSDKError(
            SECRET, httpx.Request("POST", "https://example.invalid"), body=None
        )
    with pytest.raises(ModelProviderError) as caught:
        invoke(baseline.CapturingClient(
            delegate, [], provider_error_directory=directory, case_id="harbor-primary"
        ))
    assert caught.value is normalized
    assert not any(SECRET in p.read_text() for p in directory.glob("*.json"))


class SyntheticOutput(BaseModel):
    value: int


@pytest.mark.parametrize("behavior", ["reject", "retry", "repair", "repair_exhausted"])
@pytest.mark.parametrize("write_fails", [False, True])
def test_runtime_and_eval_classification_identical_enabled_or_disabled(
    directory: Path, monkeypatch: pytest.MonkeyPatch, behavior: str, write_fails: bool,
) -> None:
    if write_fails:
        monkeypatch.setattr(baseline.tempfile, "NamedTemporaryFile", Mock(side_effect=OSError(SECRET)))
    outcomes = []
    for enabled in (False, True):
        failure = ModelProviderError(SECRET, retryable=behavior == "retry")
        failure.__cause__ = sdk_error(429 if behavior == "retry" else 401)
        valid = ModelInvocation('{"value":1}', 1, 2)
        invalid = ModelInvocation("{}", 1, 2)
        sequence = {
            "reject": [failure], "retry": [failure, valid],
            "repair": [invalid, valid], "repair_exhausted": [invalid, invalid],
        }[behavior]
        delegate = Mock(model="synthetic")
        delegate.invoke.side_effect = sequence
        captured: list[dict[str, Any]] = []
        client = baseline.CapturingClient(
            delegate, captured, provider_error_directory=directory if enabled else None,
            case_id="harbor-primary",
        )
        sleeps = Mock()
        result, run = run_structured_operation(
            Mock(spec=Session), demo_session=SimpleNamespace(id=None),  # type: ignore[arg-type]
            project_id=None, operation="synthetic", prompt_version="synthetic",
            instructions=SECRET, input_text=SECRET, result_model=SyntheticOutput,
            client=client, sleep=sleeps,
        )
        status = baseline.classify_live(result, run, captured) or "PASS"
        report = {"selected_categories": ["quote_extraction"],
                  "required_cases": {"quote_extraction": ["harbor-primary"]},
                  "cases": [{"category": "quote_extraction", "id": "harbor-primary",
                             "status": status, "assertions": []}]}
        code = baseline.summarize(report)
        outcomes.append((result, run.status, run.attempts, run.validation_status,
                         run.error_type, run.input_tokens, run.output_tokens,
                         captured, delegate.invoke.call_args_list, sleeps.call_count,
                         code, report))
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][2] == (1 if behavior == "reject" else 2)


def test_non_provider_exception_is_not_captured(directory: Path) -> None:
    original = ValueError(SECRET)
    delegate = Mock(model="synthetic")
    delegate.invoke.side_effect = original
    with pytest.raises(ValueError) as caught:
        invoke(baseline.CapturingClient(
            delegate, [], provider_error_directory=directory, case_id="harbor-primary"
        ))
    assert caught.value is original and not directory.exists()
