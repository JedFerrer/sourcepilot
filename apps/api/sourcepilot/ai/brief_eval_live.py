"""Opt-in live evaluation; never run from pytest or CI."""

from __future__ import annotations

import argparse
from uuid import UUID

from sourcepilot.ai.brief_eval import load_cases, score_case
from sourcepilot.ai.brief_interpreter import (
    INSTRUCTIONS,
    OPERATION,
    PROMPT_VERSION,
    ExtractedBrief,
)
from sourcepilot.ai.client import OpenAIResponsesClient
from sourcepilot.ai.structured import run_structured_operation
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import DemoSession


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the opt-in live brief extraction eval.")
    parser.add_argument("--demo-session-id", required=True, type=UUID)
    args = parser.parse_args()

    client = OpenAIResponsesClient.from_environment()
    total_matches = 0
    total_fields = 0
    with application_session_factory()() as database_session:
        demo_session = database_session.get(DemoSession, args.demo_session_id)
        if demo_session is None:
            raise RuntimeError("The supplied demo session does not exist.")
        for case in load_cases():
            result, air_run = run_structured_operation(
                database_session,
                demo_session=demo_session,
                project_id=None,
                operation=OPERATION,
                prompt_version=PROMPT_VERSION,
                instructions=INSTRUCTIONS,
                input_text=case["request"],
                result_model=ExtractedBrief,
                client=client,
            )
            matches, fields = score_case(
                result, case["expected"], partial=case.get("partial", False)
            )
            total_matches += matches
            total_fields += fields
            if result is None:
                print(f"{case['id']}: failed ({air_run.status}; {matches}/{fields}; AIRun {air_run.id})")
            else:
                print(f"{case['id']}: {matches}/{fields} (AIRun {air_run.id})")
    print(f"Total: {total_matches}/{total_fields} expected fields")


if __name__ == "__main__":
    main()
