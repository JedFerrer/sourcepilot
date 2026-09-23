from __future__ import annotations

import hashlib
import json
import random
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from sourcepilot.ai.client import ModelProviderError, StructuredModelClient
from sourcepilot.ai.tracing import AIRunTracer, NoOpAIRunTracer
from sourcepilot.persistence.models import AIRun, DemoSession

MAX_PROVIDER_INVOCATIONS = 3
RUNNING = "RUNNING"
COMPLETED = "COMPLETED"
VALIDATION_FAILED = "VALIDATION_FAILED"
PROVIDER_FAILED = "PROVIDER_FAILED"
FAILED = "FAILED"
VALID = "VALID"
REPAIRED = "REPAIRED"
INVALID = "INVALID"

ResultModel = TypeVar("ResultModel", bound=BaseModel)


def structured_input_hash(*, instructions: str, input_text: str) -> str:
    payload = json.dumps(
        {"input": input_text, "instructions": instructions},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def provider_retry_delay_seconds(attempt_number: int) -> float:
    """Return the one bounded provider retry delay with a small jitter."""
    return (0.25 * (2 ** (attempt_number - 1))) + random.uniform(0, 0.1)


def run_structured_operation(
    database_session: Session,
    *,
    demo_session: DemoSession,
    project_id: UUID | None,
    operation: str,
    prompt_version: str,
    instructions: str,
    input_text: str,
    result_model: type[ResultModel],
    client: StructuredModelClient,
    tracer: AIRunTracer | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[ResultModel | None, AIRun]:
    """Use one provider retry and one schema repair, with one trace record."""
    air_run = AIRun(
        demo_session_id=demo_session.id,
        project_id=project_id,
        operation=operation,
        model=client.model,
        prompt_version=prompt_version,
        input_hash=structured_input_hash(instructions=instructions, input_text=input_text),
        status=RUNNING,
        attempts=0,
    )
    database_session.add(air_run)
    database_session.commit()

    active_tracer = tracer or NoOpAIRunTracer()
    started = time.monotonic()
    current_instructions = instructions
    final_result: ResultModel | None = None
    provider_retry_used = False
    schema_repair_used = False
    provider_failure_seen = False

    try:
        for invocation_number in range(1, MAX_PROVIDER_INVOCATIONS + 1):
            air_run.attempts = invocation_number
            database_session.commit()
            try:
                response = client.invoke(
                    instructions=current_instructions,
                    input_text=input_text,
                    schema_name=result_model.__name__,
                    schema=result_model.model_json_schema(),
                )
            except ModelProviderError as error:
                provider_failure_seen = True
                air_run.error_type = type(error).__name__
                if error.retryable and not provider_retry_used:
                    provider_retry_used = True
                    sleep(provider_retry_delay_seconds(invocation_number))
                    continue
                air_run.status = PROVIDER_FAILED
                break

            air_run.input_tokens = response.input_tokens
            air_run.output_tokens = response.output_tokens
            try:
                final_result = result_model.model_validate_json(response.output_text)
            except ValidationError as error:
                air_run.validation_status = INVALID
                air_run.error_type = type(error).__name__
                if not schema_repair_used:
                    schema_repair_used = True
                    current_instructions = f"{instructions}\nRepair the JSON schema failure: {error.errors()}"
                    continue
                air_run.status = VALIDATION_FAILED
                break
            else:
                air_run.status = COMPLETED
                air_run.validation_status = (
                    REPAIRED if air_run.validation_status == INVALID else VALID
                )
                air_run.error_type = ModelProviderError.__name__ if provider_failure_seen else None
                break
    except Exception as error:
        air_run.status = FAILED
        air_run.error_type = type(error).__name__
        air_run.latency_ms = int((time.monotonic() - started) * 1000)
        air_run.completed_at = datetime.now(UTC)
        database_session.commit()
        raise

    air_run.latency_ms = int((time.monotonic() - started) * 1000)
    air_run.completed_at = datetime.now(UTC)
    database_session.commit()
    active_tracer.record(air_run)
    return final_result, air_run
