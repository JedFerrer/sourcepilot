"""Read-only assertion of real model/run/tool persistence for the golden path."""

import argparse
from collections import Counter
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import AIRun, SupplierExplanationRunStep
from tests.e2e_support.database import safe_database_url
from tests.e2e_support.model import DeterministicModel


def verify_trace(project_id: UUID) -> None:
    engine = create_engine(safe_database_url())
    try:
        with Session(engine) as session:
            runs = session.scalars(select(AIRun).where(AIRun.project_id == project_id)).all()
            expected = {"brief_interpreter": 1, "clarification_generator": 1, "quote_extractor": 3,
                        "supplier_explanation": 1, "comparison_advice": 1}
            if Counter(run.operation for run in runs) != expected:
                raise AssertionError("Golden path did not exercise all expected model operations.")
            if any(run.status != "COMPLETED" or run.model != DeterministicModel.model for run in runs):
                raise AssertionError("Golden path has failed or non-fixture model runs.")
            tools = session.scalars(select(SupplierExplanationRunStep.name).join(AIRun).where(
                AIRun.project_id == project_id, SupplierExplanationRunStep.kind == "tool",
                SupplierExplanationRunStep.outcome == "SUCCESS",
            )).all()
            if set(tools) != {"get_supplier_snapshot", "get_supplier_evidence", "get_comparison_snapshot", "get_quote_evidence"}:
                raise AssertionError("Golden path did not execute the expected real read-only tools.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", type=UUID)
    verify_trace(parser.parse_args().project_id)
