"""Opt-in live clarification eval; never run from pytest or CI."""

from __future__ import annotations

import argparse
import json
from uuid import UUID

from sourcepilot.ai.clarification import (
    INSTRUCTIONS,
    OPERATION,
    PROMPT_VERSION,
    ClarificationSet,
    validate_field_coverage,
)
from sourcepilot.ai.clarification_eval import load_cases, readiness_keys, score_questions
from sourcepilot.ai.client import OpenAIResponsesClient
from sourcepilot.ai.structured import run_structured_operation
from sourcepilot.briefs.readiness import ReadinessRequirement, evaluate_brief_readiness
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import DemoSession


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the opt-in live clarification eval.")
    parser.add_argument("--demo-session-id", required=True, type=UUID)
    args = parser.parse_args()

    client = OpenAIResponsesClient.from_environment()
    with application_session_factory()() as database_session:
        demo_session = database_session.get(DemoSession, args.demo_session_id)
        if demo_session is None:
            raise RuntimeError("The supplied demo session does not exist.")
        for case in load_cases():
            keys = readiness_keys(case)
            if not keys:
                print(f"{case['id']}: no unresolved fields; model skipped")
                continue
            brief = case["brief"]
            readiness = evaluate_brief_readiness(
                product_name=brief["product_name"],
                category=brief["category"],
                quantity=brief["quantity"],
                destination=brief["destination"],
                delivery_target=brief["delivery_target"],
                requirements=tuple(
                    ReadinessRequirement(kind=item["kind"], expected_value=item["expected_value"])
                    for item in brief["requirements"]
                ),
            )
            input_text = json.dumps(
                {
                    "brief": brief,
                    "unresolved_fields": [
                        {"field_key": field.field_key, "reason": field.reason}
                        for field in readiness.missing_fields[:5]
                    ],
                },
                sort_keys=True,
            )
            result, air_run = run_structured_operation(
                database_session,
                demo_session=demo_session,
                project_id=None,
                operation=OPERATION,
                prompt_version=PROMPT_VERSION,
                instructions=INSTRUCTIONS,
                input_text=input_text,
                result_model=ClarificationSet,
                client=client,
                post_validate=lambda output, expected=set(keys): validate_field_coverage(output, expected),
            )
            if result is None:
                print(f"{case['id']}: failed ({air_run.status}; AIRun {air_run.id})")
                continue
            print(f"{case['id']}: {score_questions(result.questions, keys)} (AIRun {air_run.id})")


if __name__ == "__main__":
    main()
