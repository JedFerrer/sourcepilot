"""Age only the designated abandoned browser fixture; no application test endpoint."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sourcepilot.persistence.models import Quote, QuoteDocument
from tests.e2e_support.database import safe_database_url
from tests.e2e_support.server import ABANDONED_FILENAME


def age_attempt(project_id: UUID, quote_id: UUID) -> None:
    engine = create_engine(safe_database_url())
    try:
        with Session(engine) as session, session.begin():
            document = session.scalar(select(QuoteDocument).join(Quote).where(
                Quote.project_id == project_id, Quote.id == quote_id,
                Quote.status == "PROCESSING", QuoteDocument.is_active.is_(True),
                QuoteDocument.original_filename == ABANDONED_FILENAME,
                QuoteDocument.processing_status == "PROCESSING",
                QuoteDocument.processing_attempts == 1,
                QuoteDocument.processing_completed_at.is_(None),
            ).with_for_update())
            if document is None:
                raise RuntimeError("Only the designated abandoned first E2E attempt may be aged.")
            document.processing_started_at = datetime.now(UTC) - timedelta(seconds=601)
    finally:
        engine.dispose()


def verify_recovery(project_id: UUID, quote_id: UUID, document_id: UUID) -> None:
    """Read-only proof that retry used the original document without duplicate records."""
    engine = create_engine(safe_database_url())
    try:
        with Session(engine) as session:
            quotes = session.scalars(select(Quote).where(Quote.project_id == project_id)).all()
            documents = session.scalars(select(QuoteDocument).where(QuoteDocument.quote_id == quote_id)).all()
            if (len(quotes) != 1 or quotes[0].id != quote_id or quotes[0].status != "NEEDS_REVIEW"
                    or len(documents) != 1 or documents[0].id != document_id
                    or not documents[0].is_active or documents[0].processing_attempts != 2
                    or documents[0].processing_completed_at is None):
                raise AssertionError("Retry did not complete the same quote/document exactly once.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("project_id", type=UUID)
    parser.add_argument("quote_id", type=UUID)
    parser.add_argument("--verify-document", type=UUID)
    arguments = parser.parse_args()
    if arguments.verify_document is not None:
        verify_recovery(arguments.project_id, arguments.quote_id, arguments.verify_document)
    else:
        age_attempt(arguments.project_id, arguments.quote_id)
