"""Verify a stored PDF, extract outside a write transaction, then replace blocks atomically."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid5

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from sourcepilot.documents.parse_pdf import ParsedBlock, parse_pdf_snapshot
from sourcepilot.documents.settings import DocumentSettings
from sourcepilot.documents.storage import DocumentStorage
from sourcepilot.persistence.models import DocumentBlock, QuoteDocument

logger = logging.getLogger(__name__)


class StoredDocumentError(ValueError):
    """The persisted document or its original bytes cannot be used for parsing."""


def _metadata(session_factory: Callable[[], Session], document_id: UUID) -> tuple[str, str, int | None]:
    with session_factory() as session:
        document = session.get(QuoteDocument, document_id)
        if document is None:
            raise StoredDocumentError("Quote document does not exist.")
        return document.storage_key, document.sha256, document.page_count


def _persist(
    session_factory: Callable[[], Session], document_id: UUID, key: str, sha256: str,
    blocks: list[ParsedBlock],
) -> None:
    with session_factory() as session, session.begin():
        document = session.scalar(
            select(QuoteDocument).where(QuoteDocument.id == document_id)
            .with_for_update().execution_options(populate_existing=True)
        )
        if document is None or (document.storage_key, document.sha256) != (key, sha256):
            raise StoredDocumentError("Quote document changed during parsing.")
        existing = session.scalars(
            select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)
            .order_by(DocumentBlock.page_number, DocumentBlock.block_number)
        ).all()
        if [(row.page_number, row.block_number, row.text) for row in existing] == [
            (block.page_number, block.block_number, block.text) for block in blocks
        ]:
            return
        session.execute(delete(DocumentBlock).where(DocumentBlock.quote_document_id == document_id))
        session.flush()
        session.add_all([
            DocumentBlock(
                id=uuid5(document_id, block.reference), quote_document_id=document_id,
                page_number=block.page_number, block_number=block.block_number, text=block.text,
            )
            for block in blocks
        ])
        session.flush()


def parse_and_persist_document(
    session_factory: Callable[[], Session], document_id: UUID, *,
    storage: DocumentStorage, settings: DocumentSettings,
) -> None:
    """Keep PDF I/O and child execution outside the short database write transaction."""
    key, sha256, expected_pages = _metadata(session_factory, document_id)
    pending_error = False
    temporary = TemporaryDirectory(prefix="sourcepilot-parse-")
    try:
        snapshot = Path(temporary.name) / "original.pdf"
        result = Path(temporary.name) / "blocks.json"
        actual_sha256 = storage.read_to(key, snapshot, max_bytes=settings.max_file_bytes)
        if actual_sha256 != sha256:
            raise StoredDocumentError("Stored PDF checksum mismatch.")
        blocks = parse_pdf_snapshot(
            snapshot, result, timeout_seconds=settings.inspection_timeout_seconds,
            max_pages=settings.max_pages, expected_pages=expected_pages,
        )
        _persist(session_factory, document_id, key, sha256, blocks)
    except BaseException:
        pending_error = True
        raise
    finally:
        try:
            temporary.cleanup()
        except Exception as error:
            logger.error("PDF parse temporary cleanup failed (%s)", type(error).__name__)
            if not pending_error:
                raise
