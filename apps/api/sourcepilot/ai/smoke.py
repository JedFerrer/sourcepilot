from __future__ import annotations

import argparse
from uuid import UUID

from pydantic import BaseModel

from sourcepilot.ai.client import OpenAIResponsesClient
from sourcepilot.ai.structured import run_structured_operation
from sourcepilot.persistence.database import application_session_factory
from sourcepilot.persistence.models import DemoSession

FOUNDATION_SMOKE_PROMPT_VERSION = "foundation-smoke-v2"


class FoundationSmokeResponse(BaseModel):
    status: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the opt-in SourcePilot AI foundation smoke check.")
    parser.add_argument("--demo-session-id", required=True, type=UUID)
    args = parser.parse_args()

    with application_session_factory()() as database_session:
        demo_session = database_session.get(DemoSession, args.demo_session_id)
        if demo_session is None:
            raise RuntimeError("The supplied demo session does not exist.")
        _, air_run = run_structured_operation(
            database_session,
            demo_session=demo_session,
            project_id=None,
            operation="foundation_smoke",
            prompt_version=FOUNDATION_SMOKE_PROMPT_VERSION,
            instructions="Return JSON only.",
            input_text='Return {"status":"ok"}.',
            result_model=FoundationSmokeResponse,
            client=OpenAIResponsesClient.from_environment(),
        )
    print(f"AIRun {air_run.id} {air_run.status}")


if __name__ == "__main__":
    main()
