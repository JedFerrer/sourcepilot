"""Explicit offline/live V1 baseline command. Never imported by application startup."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from sourcepilot.ai import (
    brief_eval,
    clarification_eval,
    comparison_advice_eval,
    quote_extraction_eval,
    supplier_explanation_eval,
    tradeoff_analysis_eval,
)
from sourcepilot.ai.client import (
    AnalystModelInvocation,
    ModelInvocation,
    ModelProviderError,
    OpenAIResponsesClient,
    StructuredModelClient,
    ai_settings_from_environment,
)
from sourcepilot.ai.eval_live import API_ROOT, preflight_database, run_case
from sourcepilot.ai.eval_scoring import assertion, check_failed, measurements, score_output
from sourcepilot.ai.quote_extractor import INSTRUCTIONS as QUOTE_INSTRUCTIONS
from sourcepilot.ai.structured import structured_input_hash
from sourcepilot.briefs.domain import validate_requirement_expected_value
from sourcepilot.comparison.service import comparison_is_stale
from sourcepilot.documents.parse_pdf import (
    NoExtractableTextError,
    PdfParseError,
    parse_pdf_snapshot,
)
from sourcepilot.persistence.models import AIRun

CATEGORIES = (
    "brief",
    "clarification",
    "supplier_explanation",
    "quote_extraction",
    "comparison",
    "suggestion",
)
ROOT = API_ROOT.parents[1]
PDFS = API_ROOT / "tests/fixtures/quote_pdfs"
DATA = API_ROOT / "evals"
HUMAN_REVIEW = DATA / "human_review/narrative_cases.json"
# Small explicit input lists; no repository-wide discovery or source manifest.
SOURCES = [
    "__init__.py",
    "ai/__init__.py",
    "persistence/__init__.py",
    "ai/eval_baseline.py",
    "ai/eval_scoring.py",
    "ai/client.py",
    "ai/structured.py",
    "ai/tracing.py",
    "persistence/base.py",
    "persistence/models.py",
]
BRIEF_SOURCES = [
    "briefs/__init__.py",
    "briefs/domain.py",
]
SESSION_SOURCES = ["session/__init__.py", "session/service.py", "session/settings.py"]
ANALYST_SOURCES = [
    *BRIEF_SOURCES,
    "ai/analyst_tools.py",
    "ai/supplier_explanation.py",
    "comparison/__init__.py",
    "comparison/advice.py",
    "comparison/evaluation.py",
    "comparison/facts.py",
    "comparison/service.py",
    "comparison/source_resolution.py",
    "quotes/__init__.py",
    "quotes/domain.py",
    "suppliers/__init__.py",
    "suppliers/evaluation.py",
]
CATEGORY_SOURCES = {
    "brief": [
        *BRIEF_SOURCES, *SESSION_SOURCES,
        "ai/brief_eval.py", "ai/brief_interpreter.py",
        "projects/__init__.py", "projects/service.py", "projects/decision.py",
        "projects/schemas.py",
    ],
    "clarification": [
        *BRIEF_SOURCES,
        "ai/clarification_eval.py", "ai/clarification.py",
        "briefs/readiness.py", "briefs/schemas.py",
    ],
    "supplier_explanation": [*ANALYST_SOURCES, "ai/supplier_explanation_eval.py"],
    "quote_extraction": [
        *SESSION_SOURCES,
        "ai/quote_extraction_eval.py", "ai/quote_extractor.py",
        "documents/__init__.py", "documents/parse_pdf.py",
        "quotes/__init__.py", "quotes/domain.py",
    ],
    "comparison": [
        *ANALYST_SOURCES,
        "ai/tradeoff_analysis_eval.py", "ai/tradeoff_analysis.py",
        "ai/comparison_advice_eval.py", "ai/comparison_advice.py",
    ],
    "suggestion": [
        *ANALYST_SOURCES,
        "ai/tradeoff_analysis_eval.py", "ai/tradeoff_analysis.py",
        "ai/comparison_advice_eval.py", "ai/comparison_advice.py",
    ],
}
LIVE_FIXTURE_SOURCES = [
    "ai/eval_live.py",
    *BRIEF_SOURCES,
    "ai/clarification.py",
    "briefs/readiness.py",
    "briefs/schemas.py",
]
DATA_FILES = {
    "brief": ["brief/cases.json", "brief/model_outputs.json"],
    "clarification": ["clarification/cases.json"],
    "supplier_explanation": ["supplier_explanation/cases.json",
                             "human_review/narrative_cases.json"],
    "quote_extraction": [
        "quote_extraction/cases.json", "quote_extraction/model_outputs.json",
        "quote_extraction/parser_cases.json",
    ],
    "comparison": [
        "tradeoff_analysis/cases.json", "tradeoff_analysis/model_outputs.json",
        "comparison_advice/cases.json", "comparison_advice/model_outputs.json",
        "comparison_advice/guard_cases.json", "human_review/narrative_cases.json",
    ],
    "suggestion": ["comparison_advice/cases.json", "comparison_advice/model_outputs.json",
                   "human_review/narrative_cases.json"],
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def paired_outputs(cases: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    outputs = read_json(path)
    if set(outputs) != {case["id"] for case in cases}:
        raise ValueError("Dataset and recorded output IDs disagree.")
    return outputs


def load_scope(categories: list[str]) -> dict[str, list[dict[str, Any]]]:
    result = {}
    advice_cases = (
        comparison_advice_eval.load_cases()
        if {"comparison", "suggestion"} & set(categories)
        else []
    )
    for category in categories:
        if category == "brief":
            originals = brief_eval.load_cases()
            outputs = paired_outputs(
                originals, brief_eval.CASES_PATH.with_name("model_outputs.json")
            )
            cases = [
                {**case, "output": outputs[case["id"]], "expected_valid": True}
                for case in originals
            ]
        elif category == "clarification":
            cases = [
                {**case, "output": {"questions": case["questions"]}, "expected_valid": True}
                for case in clarification_eval.load_cases()
            ]
        elif category == "supplier_explanation":
            cases = supplier_explanation_eval.load_cases()
            for case in cases:
                for finding in case["findings"]:
                    validate_requirement_expected_value(finding["kind"], finding["expected_value"])
        elif category == "quote_extraction":
            outputs = paired_outputs(
                quote_extraction_eval.load_cases(), DATA / "quote_extraction/model_outputs.json"
            )
            cases = [
                {**case, "output": outputs[case["id"]], "expected_valid": True}
                for case in quote_extraction_eval.load_cases()
            ]
            cases += read_json(DATA / "quote_extraction/parser_cases.json")
        elif category == "comparison":
            paired_outputs(
                tradeoff_analysis_eval.load_cases(), DATA / "tradeoff_analysis/model_outputs.json"
            )
            cases = [
                {
                    **case,
                    "output": tradeoff_analysis_eval.recorded_analysis(case).model_dump(
                        mode="json"
                    ),
                    "expected_valid": case["expected_grounded"],
                }
                for case in tradeoff_analysis_eval.load_cases()
            ]
            cases += [
                {
                    **case,
                    "topic": "references-only",
                    "output": comparison_advice_eval.recorded_advice(case).analysis.model_dump(
                        mode="json"
                    ),
                    "expected_valid": True,
                }
                for case in advice_cases
                if "payload" in case
            ]
            cases += read_json(DATA / "comparison_advice/guard_cases.json")
        else:
            paired_outputs(advice_cases, DATA / "comparison_advice/model_outputs.json")
            cases = [
                {
                    **case,
                    "output": comparison_advice_eval.recorded_advice(case).model_dump(mode="json"),
                    "expected_valid": case["expected_grounded"],
                }
                for case in advice_cases
            ]
        if len({case["id"] for case in cases}) != len(cases):
            raise ValueError(f"Duplicate case IDs in {category}.")
        result[category] = cases
    return result


def consumed_files(scope: dict[str, list[dict[str, Any]]], mode: str = "offline") -> list[Path]:
    sources = SOURCES + [name for category in scope for name in CATEGORY_SOURCES[category]]
    if mode == "live":
        sources += LIVE_FIXTURE_SOURCES
    paths = [API_ROOT / "sourcepilot" / name for name in sources]
    paths += [API_ROOT / "uv.lock", API_ROOT / "pyproject.toml"]
    paths.extend(DATA / name for category in scope for name in DATA_FILES[category])
    if "quote_extraction" in scope:
        paths.append(PDFS / "expected_blocks.json")
        paths.extend(PDFS / case["pdf"] for case in scope["quote_extraction"])
    if mode == "live":
        # Preflight reads Alembic revisions; it never executes them.
        paths.extend(sorted((API_ROOT / "alembic/versions").glob("*.py")))
    return sorted(set(paths))


def hash_files(paths: list[Path]) -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def provenance(scope: dict[str, list[dict[str, Any]]], mode: str = "offline") -> dict[str, Any]:
    from sourcepilot.ai import (
        brief_interpreter,
        clarification,
        comparison_advice,
        quote_extractor,
        supplier_explanation,
        tradeoff_analysis,
    )

    prompts = {
        "brief": brief_interpreter,
        "clarification": clarification,
        "supplier_explanation": supplier_explanation,
        "quote_extraction": quote_extractor,
        "comparison": tradeoff_analysis,
        "suggestion": comparison_advice,
    }

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, check=True, text=True, capture_output=True
        ).stdout.strip()

    return {
        "pre_run_head": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "files": hash_files(consumed_files(scope, mode)),
        "prompts": {
            category: {
                "version": module.PROMPT_VERSION,
                "sha256": hashlib.sha256(module.INSTRUCTIONS.encode("utf-8")).hexdigest(),
            }
            for category, module in prompts.items()
            if category in scope
        },
    }


def parser_result(
    case: dict[str, Any], temporary: Path
) -> tuple[list[Any] | None, list[dict[str, Any]]]:
    case.pop("_scoring_document", None)
    expected_error = case.get("expected_error")
    try:
        blocks = parse_pdf_snapshot(
            PDFS / case["pdf"],
            temporary / f"{case['id']}.json",
            timeout_seconds=10,
            max_pages=15,
            expected_pages=None,
        )
    except NoExtractableTextError:
        return None, [assertion("parser_rejection", expected_error == "NoExtractableTextError")]
    except PdfParseError:
        return None, [assertion("parser_rejection", expected_error == "PdfParseError")]
    if expected_error:
        return None, [assertion("parser_rejection", False)]
    expected_blocks = read_json(PDFS / "expected_blocks.json")[case["pdf"]]["blocks"]
    input_text = json.dumps(
        {"document_blocks": [{"id": block.reference, "text": block.text} for block in blocks]},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    quote_extraction_eval.bind_document(case, PDFS / case["pdf"], blocks)
    return blocks, [
        assertion("parser_blocks", [[b.reference, b.text] for b in blocks] == expected_blocks),
        assertion(
            "extraction_input_hash",
            structured_input_hash(instructions=QUOTE_INSTRUCTIONS, input_text=input_text)
            == case["request_hash"],
        ),
    ]


def offline_case(category: str, case: dict[str, Any], temporary: Path) -> dict[str, Any]:
    if "guard" in case:
        # Runtime guard is additionally verified with real PostgreSQL fixtures in tests.
        checks = [
            assertion(
                "stale_comparison_predicate",
                comparison_is_stale(
                    stored_stale=True,
                    stage="QUOTES",
                    brief_revision=1,
                    snapshot_brief_revision=1,
                    quote_snapshot={},
                    active_revisions={},
                ),
            )
        ]
        status = "PASS" if not any(check_failed(item) for item in checks) else "REGRESSION_FAILED"
    elif "expected_error" in case:
        _, checks = parser_result(case, temporary)
        status = (
            "EXPECTED_REJECTION" if not any(check_failed(item) for item in checks) else "REGRESSION_FAILED"
        )
    else:
        checks = []
        if category == "quote_extraction":
            _, checks = parser_result(case, temporary)
        scored = score_output(category, case, case["output"])
        valid = not any(check_failed(item) for item in scored)
        expected = case.get("expected_valid", True)
        checks.extend(scored)
        if expected:
            status = (
                "PASS" if valid and not any(check_failed(item) for item in checks) else "REGRESSION_FAILED"
            )
        else:
            status = "EXPECTED_REJECTION" if not valid else "REGRESSION_FAILED"
            checks.append(assertion("negative_control_rejected", not valid))
    return {
        "category": category,
        "id": case["id"],
        "status": status,
        "assertions": checks,
        "output": case.get("output"),
        "control": not case.get("expected_valid", True),
        "measurements": measurements(category, case, case["output"])
        if "output" in case and case.get("expected_valid", True)
        else {},
    }


def run_metadata(run: AIRun | None) -> dict[str, Any] | None:
    if run is None:
        return None
    return {
        key: str(getattr(run, key)) if key == "id" else getattr(run, key)
        for key in (
            "id",
            "operation",
            "model",
            "prompt_version",
            "input_hash",
            "status",
            "attempts",
            "validation_status",
            "error_type",
            "latency_ms",
            "input_tokens",
            "output_tokens",
            "model_turn_count",
            "tool_call_count",
        )
    }


def classify_live(
    output: Any, run: AIRun | None, responses: list[dict[str, Any]] | None = None
) -> str | None:
    if run is not None and run.status in {"VALIDATION_FAILED", "FAILED_LIMIT_REACHED"}:
        analyst = run.operation in {"supplier_explanation", "tradeoff_analysis", "comparison_advice"}
        terminal = None
        if analyst:
            steps = sorted(run.supplier_explanation_steps, key=lambda step: step.sequence)
            # Usage availability is terminal metadata, not the cause of the outcome.
            terminal = next((step for step in reversed(steps) if step.kind not in {"run", "usage"}), None)
        if run.status == "FAILED_LIMIT_REACHED":
            model_caused = analyst and terminal is not None and (
                (terminal.kind, terminal.outcome, terminal.name) == ("limit", "REACHED", "model_turns")
                or (terminal.kind, terminal.outcome) == ("tool", "LIMIT_REACHED")
            )
        else:
            # The production runtime also records post_validate and integration
            # ValueErrors as VALIDATION_FAILED. Only the captured final response
            # failing its declared schema positively attributes model output.
            model_caused = False
            if run.validation_status == "INVALID" and responses and (
                not analyst or terminal is not None
                and (terminal.kind, terminal.outcome) == ("validation", "INVALID")
            ):
                from pydantic import ValidationError

                from sourcepilot.ai.brief_interpreter import ExtractedBrief
                from sourcepilot.ai.clarification import ClarificationSet
                from sourcepilot.ai.comparison_advice import ComparisonAdvice
                from sourcepilot.ai.quote_extractor import QuoteExtraction
                from sourcepilot.ai.supplier_explanation import ModelSupplierExplanation
                from sourcepilot.ai.tradeoff_analysis import TradeoffAnalysis

                models = {
                    "brief_interpreter": ExtractedBrief,
                    "clarification_generator": ClarificationSet,
                    "quote_extractor": QuoteExtraction,
                    "supplier_explanation": ModelSupplierExplanation,
                    "tradeoff_analysis": TradeoffAnalysis,
                    "comparison_advice": ComparisonAdvice,
                }
                response = responses[-1]
                model = models.get(run.operation)
                if model is not None and response.get("schema_name") == model.__name__:
                    try:
                        model.model_validate_json(response["output_text"])
                    except ValidationError:
                        model_caused = True
        return "QUALITY_FINDING" if model_caused else "RUNTIME_ERROR"
    if run is not None and run.status != "COMPLETED":
        return "PROVIDER_ERROR" if run.status == "PROVIDER_FAILED" else "RUNTIME_ERROR"
    return None if output is not None else "ADAPTER_ERROR"


class CapturingClient:
    """Capture synthetic model responses through the existing client seam only.

    Delegates calls unchanged; the production runtime owns all execution decisions.
    """

    # Deliberately finite: unfamiliar provider text must never become diagnostic content.
    _ERROR_TYPES = frozenset({
        "invalid_request_error", "authentication_error", "permission_error",
        "not_found_error", "rate_limit_error", "insufficient_quota", "server_error",
        "api_error",
    })
    _ERROR_CODES = frozenset({
        "invalid_api_key", "invalid_request_error", "permission_denied", "model_not_found",
        "invalid_json_schema", "unsupported_parameter", "invalid_value", "missing_required_parameter",
        "rate_limit_exceeded", "insufficient_quota", "server_error", "internal_server_error",
    })
    _ERROR_PARAMETERS = frozenset({
        "model", "instructions", "input", "store", "text", "text.format",
        "text.format.type", "text.format.name", "text.format.strict", "text.format.schema",
    })

    def __init__(
        self, client: StructuredModelClient, responses: list[dict[str, Any]], *,
        provider_error_directory: Path | None = None, case_id: str | None = None,
    ) -> None:
        self.client = client
        self.model = client.model
        self.responses = responses
        self._provider_error_directory = provider_error_directory
        self._case_id = case_id
        self._invocations = 0

    def _capture_provider_error(self, error: ModelProviderError) -> None:
        """Best-effort quote-eval sidecar; never inspect messages, bodies or headers.

        Opt-in is constructor-only for a separately authorized evaluation. Each failed
        wrapper invocation gets an exclusively created file in the ignored eval tree.
        SDK HTTP retries inside one invocation are intentionally not counted here.
        """
        if self._provider_error_directory is None:
            return
        try:
            from openai import APIError

            if type(self._case_id) is not str or self._case_id not in {
                case["id"] for case in quote_extraction_eval.load_cases()
            }:
                return
            directory = self._provider_error_directory.resolve()
            if not directory.is_relative_to((API_ROOT / ".eval-results").resolve()):
                return
            cause = error.__cause__
            sdk_error = cause if isinstance(cause, APIError) else None
            status = getattr(sdk_error, "status_code", None)

            def allowed(value: object, choices: frozenset[str]) -> str | None:
                if value is None:
                    return None
                return value if type(value) is str and value in choices else "UNRECOGNIZED"

            record = {
                "case_id": self._case_id,
                "invocation": self._invocations,
                "http_status": status if type(status) is int and 100 <= status <= 599 else None,
                "provider_error_type": allowed(getattr(sdk_error, "type", None), self._ERROR_TYPES),
                "provider_error_code": allowed(getattr(sdk_error, "code", None), self._ERROR_CODES),
                "rejected_parameter": allowed(
                    getattr(sdk_error, "param", None), self._ERROR_PARAMETERS
                ),
            }
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", prefix="provider-error-", suffix=".json",
                dir=directory, delete=False,
            ) as sidecar:
                json.dump(record, sidecar, ensure_ascii=True)
                sidecar.write("\n")
        except Exception:  # noqa: BLE001 - Optional diagnostics must preserve the provider error.
            # Diagnostics are optional. Never replace the provider error or log its data.
            return

    def invoke(
        self, *, instructions: str, input_text: str, schema_name: str, schema: dict[str, Any]
    ) -> ModelInvocation:
        self._invocations += 1
        try:
            result = self.client.invoke(
                instructions=instructions, input_text=input_text, schema_name=schema_name, schema=schema
            )
        except ModelProviderError as error:
            self._capture_provider_error(error)
            raise
        self.responses.append({"schema_name": schema_name, "output_text": result.output_text})
        return result

    def invoke_with_tools(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> AnalystModelInvocation:
        self._invocations += 1
        try:
            result = self.client.invoke_with_tools(
                instructions=instructions,
                input_items=input_items,
                tools=tools,
                schema_name=schema_name,
                schema=schema,
            )
        except ModelProviderError as error:
            self._capture_provider_error(error)
            raise
        self.responses.append(
            {
                "schema_name": schema_name,
                "output_text": result.output_text,
                "tool_calls": [
                    {key: item.get(key) for key in ("name", "arguments")}
                    for item in result.output_items
                    if item.get("type") == "function_call"
                ],
            }
        )
        return result


def summarize(report: dict[str, Any]) -> int:
    cases = report["cases"]
    errors = [case for case in cases if case["status"].endswith("ERROR")]
    actual = Counter((case["category"], case["id"]) for case in cases)
    required = {
        (category, identifier)
        for category, ids in report["required_cases"].items()
        for identifier in ids
    }
    unexpected = any(
        case["status"] not in {"PASS", "EXPECTED_REJECTION", "QUALITY_FINDING", "REGRESSION_FAILED"}
        and not case["status"].endswith("ERROR")
        for case in cases
    )
    complete = (
        set(actual) == required and all(count == 1 for count in actual.values()) and not unexpected
    )
    report["complete"] = complete
    report["executed_case_count"] = len(cases)
    report["expected_case_count"] = len(required)
    report["status_counts"] = dict(Counter(case["status"] for case in cases))
    report["critical_findings"] = [
        {
            "category": case["category"],
            "id": case["id"],
            "assertion": item["name"],
            "kind": item["kind"],
            "detail": item["detail"],
        }
        for case in cases
        if case["status"] in {"QUALITY_FINDING", "REGRESSION_FAILED"}
        for item in case["assertions"]
        if check_failed(item) and item["critical"]
    ]
    report["metrics"] = {}
    report["measurements"] = {}
    for category in report["selected_categories"]:
        checks = [
            item
            for case in cases
            if case["category"] == category and not case.get("control")
            for item in case["assertions"]
            if item["kind"] == "exact"
        ]
        names = sorted({item["name"] for item in checks})
        report["metrics"][category] = {
            name: {
                "numerator": sum(item["passed"] for item in checks if item["name"] == name),
                "denominator": sum(item["name"] == name for item in checks),
            }
            for name in names
        }
        signals = [item for case in cases if case["category"] == category
                   and not case.get("control") for item in case["assertions"]
                   if item["kind"] == "heuristic"]
        report.setdefault("heuristic_signals", {})[category] = {
            name: {
                "triggered": sum(item["triggered"] for item in signals if item["name"] == name),
                "inspected": sum(item["name"] == name for item in signals),
                "interpretation": "No signal is not proof of narrative groundedness.",
            }
            for name in sorted({item["name"] for item in signals})
        }
        metrics = [
            case.get("measurements", {})
            for case in cases
            if case["category"] == category and not case.get("control")
        ]
        report["measurements"][category] = {
            name: {
                "kind": next(value[name].get("kind", "exact") for value in metrics if name in value),
                "numerator": sum(value.get(name, {}).get("numerator", 0) for value in metrics),
                "denominator": sum(value.get(name, {}).get("denominator", 0) for value in metrics),
                "measured_case_count": sum(name in value for value in metrics),
            }
            for name in sorted({name for value in metrics for name in value})
        }
    if errors or report.get("error") or not complete:
        report["status"] = "ERROR" if complete else "INCOMPLETE"
        return 2
    if any(case["status"] == "REGRESSION_FAILED" for case in cases):
        report["status"] = "REGRESSION_FAILED"
        return 1
    report["status"] = (
        "COMPLETED_WITH_FINDINGS"
        if any(case["status"] == "QUALITY_FINDING" for case in cases)
        else "COMPLETED"
    )
    return 0


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    lines = [
        f"# SourcePilot {report['mode']} eval baseline",
        "",
        f"Status: **{report['status']}**; exit {report['exit_code']}.",
        f"Scope: {', '.join(report['selected_categories'])}. Full scope: {report['full_scope']}.",
        f"Accounted for: {report['executed_case_count']}/{report['expected_case_count']}; complete: {report['complete']}.",
        "",
        "Exit zero is execution completion, not live model-quality approval.",
        "Automated completion does not prove free-text narrative groundedness.",
        "",
        "| Category | Case | Status | Exact failures / heuristic signals |",
        "| --- | --- | --- | --- |",
    ]
    for case in report["cases"]:
        failures = ", ".join(f"{item['kind']}: {item['name']}" for item in case["assertions"]
                             if check_failed(item))
        lines.append(f"| {case['category']} | {case['id']} | {case['status']} | {failures} |")
    lines += [
        "",
        "## Exact deterministic assertions (passed / checked)",
        "",
        "| Category | Assertion | Counts |",
        "| --- | --- | --- |",
    ]
    for category, metrics in report["metrics"].items():
        for name, value in metrics.items():
            lines.append(f"| {category} | {name} | {value['numerator']} / {value['denominator']} |")
    lines += [
        "",
        "## Measured metrics (numerator / denominator)",
        "",
        "| Category | Metric | Kind | Counts | Measured cases |",
        "| --- | --- | --- | --- | --- |",
    ]
    for category, metrics in report["measurements"].items():
        for name, value in metrics.items():
            lines.append(
                f"| {category} | {name} | {value['kind']} | {value['numerator']} / {value['denominator']} | {value['measured_case_count']} |"
            )
    lines += [
        "",
        "Zero denominators are not applicable. Exact assertion pass counts are separate in results.json.",
        "Failed runtime cases remain in case/status totals even when extracted-value metrics are unavailable.",
        "",
        "## Heuristic signals (triggered / inspected)",
        "",
        "A non-trigger is not a factual-groundedness pass. These are bounded warning cues.",
        "",
        "| Category | Signal | Counts |",
        "| --- | --- | --- |",
    ]
    for category, signals in report["heuristic_signals"].items():
        for name, value in signals.items():
            lines.append(f"| {category} | {name} | {value['triggered']} / {value['inspected']} |")
    lines += [
        "",
        "## Critical findings",
        "",
    ]
    lines += [
        f"- {item['category']}/{item['id']} [{item['kind']}]: {item['assertion']} — {item['detail'] or 'See case output.'}"
        for item in report["critical_findings"]
    ]
    if not report["critical_findings"]:
        lines.append("- None in accepted recorded outputs; expected negative controls remain in the case table.")
    if report.get("error"):
        lines += [f"- Execution error: {report['error']}"]
    lines += [
        "",
        f"## Human review required — {report['human_review']['status']}",
        "",
        f"{report['human_review']['case_count']} difficult narrative examples require a person's judgment. No result has been recorded.",
        "",
        "| Example | Review criterion |",
        "| --- | --- |",
    ]
    for case in report["human_review"]["cases"]:
        lines.append(f"| {case['id']} | {case['review_criteria']} |")
    lines += [
        "",
        "Source: apps/api/evals/human_review/narrative_cases.json.",
        "No production tuning or release acceptance is implied by this baseline.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def execute(mode: str, categories: list[str], output: Path) -> tuple[dict[str, Any], int]:
    report: dict[str, Any] = {
        "mode": mode,
        "selected_categories": categories,
        "full_scope": set(categories) == set(CATEGORIES),
        "started_at": datetime.now(UTC).isoformat(),
        "cases": [],
        "required_cases": {},
        "human_review": {"status": "PENDING", "case_count": 0, "cases": []},
        "narrative_groundedness": "NOT_ESTABLISHED_BY_AUTOMATED_SCORING",
        "model": "recorded fixtures (no provider)" if mode == "offline" else None,
    }
    engine = None
    try:
        if (
            not categories
            or len(set(categories)) != len(categories)
            or not set(categories) <= set(CATEGORIES)
        ):
            raise ValueError("Select unique known categories.")
        scope = load_scope(categories)
        review_cases = read_json(HUMAN_REVIEW)
        if not isinstance(review_cases, list) or any(
            not isinstance(case, dict) or not {"id", "category", "review_criteria",
                                               "why_automation_is_insufficient"} <= case.keys()
            for case in review_cases
        ):
            raise ValueError("Human review set is invalid.")
        if (len({case["id"] for case in review_cases}) != len(review_cases)
                or any(case["category"] not in CATEGORIES for case in review_cases)):
            raise ValueError("Human review set has duplicate IDs or unknown categories.")
        selected_review = [case for case in review_cases if case["category"] in categories]
        report["human_review"] = {
            "status": "PENDING", "case_count": len(selected_review),
            "cases": [{**case, "review_result": None} for case in selected_review],
        }
        report["required_cases"] = {
            category: [case["id"] for case in cases] for category, cases in scope.items()
        }
        report["provenance"] = provenance(scope, mode)
        with tempfile.TemporaryDirectory(prefix="sourcepilot-eval-") as directory:
            temporary = Path(directory)
            controls = []
            for category, cases in scope.items():
                for case in cases:
                    try:
                        result = offline_case(category, case, temporary)
                    except Exception as error:  # noqa: BLE001 - report scorer faults and continue independent cases
                        result = {
                            "category": category,
                            "id": case["id"],
                            "status": "SCORER_ERROR",
                            "assertions": [
                                assertion("scorer_execution", False, detail=type(error).__name__)
                            ],
                        }
                    controls.append(result)
            if mode == "offline":
                report["cases"] = controls
            else:
                # All selected fixture/scorer controls validated before provider calls or writes.
                if any(case["status"] not in {"PASS", "EXPECTED_REJECTION"} for case in controls):
                    report["cases"] = controls
                    raise RuntimeError("Fixture/scorer preflight failed.")
                engine = preflight_database()
                report["model"] = ai_settings_from_environment().model
                for category, cases in scope.items():
                    for case in cases:
                        if not case.get("expected_valid", True) or "expected_error" in case:
                            report["cases"].append(
                                next(
                                    item
                                    for item in controls
                                    if item["category"] == category and item["id"] == case["id"]
                                )
                            )
                            continue
                        with Session(engine, expire_on_commit=False) as session:
                            responses: list[dict[str, Any]] = []

                            def client_factory(
                                captured: list[dict[str, Any]] = responses,
                            ) -> CapturingClient:
                                return CapturingClient(
                                    OpenAIResponsesClient.from_environment(), captured
                                )

                            try:
                                blocks = None
                                if category == "quote_extraction":
                                    # Parsing already passed preflight; reuse exact reviewed blocks.
                                    with tempfile.TemporaryDirectory() as parsed_dir:
                                        blocks, _ = parser_result(case, Path(parsed_dir))
                                actual, run = run_case(
                                    session, category, case, client_factory, blocks
                                )
                                if "guard" in case:
                                    raise RuntimeError(
                                        "Stale guard unexpectedly permitted analysis."
                                    )
                                status = classify_live(actual, run, responses)
                                checks = (
                                    [
                                        assertion(
                                            "runtime_completion",
                                            False,
                                            detail=run.status if run else "missing result",
                                        )
                                    ]
                                    if status
                                    else score_output(category, case, actual)
                                )
                                status = status or (
                                    "PASS"
                    if not any(check_failed(item) for item in checks)
                                    else "QUALITY_FINDING"
                                )
                                result = {
                                    "category": category,
                                    "id": case["id"],
                                    "status": status,
                                    "assertions": checks,
                                    "output": actual,
                                    "air_run": run_metadata(run),
                                    "measurements": measurements(category, case, actual)
                                    if actual is not None
                                    else {},
                                }
                            except Exception as error:  # noqa: BLE001 - case boundary preserves partial evidence
                                from sourcepilot.ai.tradeoff_analysis import TradeoffNotReadyError

                                if (
                                    "guard" in case
                                    and isinstance(error, TradeoffNotReadyError)
                                    and error.code == "COMPARISON_STALE"
                                ):
                                    result = {
                                        "category": category,
                                        "id": case["id"],
                                        "status": "EXPECTED_REJECTION",
                                        "assertions": [assertion("stale_no_model", True)],
                                        "air_run": None,
                                    }
                                else:
                                    result = {
                                        "category": category,
                                        "id": case["id"],
                                        "status": "SCORER_ERROR"
                                        if isinstance(error, quote_extraction_eval.QuoteScorerContextError)
                                        else "HARNESS_ERROR",
                                        "assertions": [
                                            assertion(
                                                "case_execution", False, detail=type(error).__name__
                                            )
                                        ],
                                    }
                            result["model_responses"] = responses
                            report["cases"].append(result)
        if report["provenance"]["files"] != hash_files(consumed_files(scope, mode)):
            raise RuntimeError("Consumed files changed during evaluation; report invalid.")
    except Exception as error:  # noqa: BLE001 - command boundary reports sanitized execution failures
        # Only sanitized known messages/types, never DB/provider exception strings containing credentials.
        from sourcepilot.ai.eval_live import EvalPreflightError

        report["error"] = (
            str(error) if isinstance(error, EvalPreflightError) else type(error).__name__
        )
    finally:
        if engine is not None:
            engine.dispose()
    code = summarize(report)
    report["completed_at"] = datetime.now(UTC).isoformat()
    report["exit_code"] = code
    try:
        write_report(report, output)
    except Exception as error:  # noqa: BLE001 - report failures must return exit 2
        report["status"] = "ERROR"
        report["complete"] = False
        report["exit_code"] = code = 2
        report["error"] = f"Report generation failed ({type(error).__name__})."
        # A prior or partially written results.json must never claim success.
        # Keep an inspectable machine result when possible, otherwise remove it.
        results_path = output / "results.json"
        try:
            output.mkdir(parents=True, exist_ok=True)
            results_path.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        except OSError:
            try:
                results_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            (output / "summary.md").unlink(missing_ok=True)
        except OSError:
            pass
    return report, code


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("offline", "live"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--categories", nargs="+", choices=CATEGORIES, default=list(CATEGORIES))
    args = parser.parse_args()
    report, code = execute(args.mode, args.categories, args.output)
    print(
        f"{report['status']}: {report['executed_case_count']}/{report['expected_case_count']} cases; exit {code}"
    )
    if report.get("error"):
        print(report["error"])
    raise SystemExit(code)


if __name__ == "__main__":
    main()
