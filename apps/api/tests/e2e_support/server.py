"""Explicit test server: safe reset, real app/worker, deterministic models."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import uvicorn

from sourcepilot.persistence.models import QuoteDocument
from tests.e2e_support.database import reset_database, validated_database
from tests.e2e_support.model import install_model_boundary

ABANDONED_FILENAME = "e2e-abandoned-harbor.pdf"


def main() -> None:
    directory = os.environ.get("E2E_DOCUMENT_STORAGE_DIR")
    if not directory or not Path(directory).is_dir():
        raise RuntimeError("Use the root E2E command to own temporary storage and cleanup.")
    with validated_database() as target:
        reset_database(target)
        database_url = target.url
    os.environ["DATABASE_URL"] = database_url
    os.environ["DOCUMENT_STORAGE_BACKEND"] = "local"
    os.environ["DEMO_SESSION_COOKIE_SECURE"] = "false"
    os.environ["DEMO_SESSION_TTL_SECONDS"] = "86400"
    os.environ["QUOTE_PROCESSING_STALE_SECONDS"] = "600"
    os.environ["SOURCEPILOT_ANALYST_MAX_MODEL_TURNS"] = "4"
    os.environ["SOURCEPILOT_ANALYST_MAX_TOOL_CALLS"] = "6"
    install_model_boundary()
    from sourcepilot.documents.processing import run_pdf_quote_processing
    from sourcepilot.main import app
    from sourcepilot.persistence.database import application_engine, application_session_factory

    def schedule(document_id: UUID, attempt: int) -> None:
        with application_session_factory()() as session:
            document = session.get(QuoteDocument, document_id)
            if document is None:
                raise AssertionError("Scheduled E2E document is missing.")
            abandoned = document.original_filename == ABANDONED_FILENAME and attempt == 1
        if abandoned:
            print("E2E fixture abandoned the designated first PDF attempt.", flush=True)
            return
        run_pdf_quote_processing(document_id, attempt)

    os.environ["DOCUMENT_STORAGE_LOCAL_DIR"] = directory
    with patch("sourcepilot.main.run_pdf_quote_processing", schedule):
        try:
            uvicorn.run(app, host="127.0.0.1", port=18000)
        finally:
            application_engine().dispose()


if __name__ == "__main__":
    main()
