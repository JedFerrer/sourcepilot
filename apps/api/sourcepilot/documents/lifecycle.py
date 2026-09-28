"""Deterministic PDF processing state shared by reads and recovery actions."""

from datetime import UTC, datetime, timedelta

from sourcepilot.persistence.models import QuoteDocument


def effective_processing_status(
    document: QuoteDocument, *, now: datetime, stale_seconds: int,
) -> str:
    if (
        document.processing_status == "PROCESSING"
        and document.processing_started_at is not None
        and document.processing_completed_at is None
        and now > document.processing_started_at + timedelta(seconds=stale_seconds)
    ):
        return "STALE_PROCESSING"
    return document.processing_status


def current_processing_status(document: QuoteDocument, stale_seconds: int) -> str:
    return effective_processing_status(document, now=datetime.now(UTC), stale_seconds=stale_seconds)
