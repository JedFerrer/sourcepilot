"""Validated PDF upload and owned storage lifecycle."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from fastapi import UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from sourcepilot.documents.inspect_pdf import InvalidPdfError, inspect_page_count
from sourcepilot.documents.settings import DocumentSettings
from sourcepilot.documents.storage import DocumentStorage, new_storage_key
from sourcepilot.persistence.models import Project, ProjectSupplier, Quote, QuoteDocument
from sourcepilot.quotes.domain import QuoteEntryType, QuoteStatus
from sourcepilot.quotes.schemas import QuoteResponse
from sourcepilot.quotes.service import create_quote, quote_snapshot

logger = logging.getLogger(__name__)
CHUNK_BYTES = 1024 * 1024


class PdfUploadError(ValueError):
    """A client PDF upload is invalid or conflicts with the current quote."""

    def __init__(self, code: str, message: str, status_code: int = 422) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class PdfStorageError(RuntimeError):
    """Storage failed before database commit."""


class PdfCommitUncertainError(RuntimeError):
    """The database commit result is unknown; preserve the uploaded object."""


class QuoteDocumentResponse(BaseModel):
    id: UUID
    original_filename: str
    sha256: str
    page_count: int
    processing_status: str
    processing_attempts: int
    processing_started_at: None = None
    processing_completed_at: None = None
    last_error: None = None


class PdfQuoteUploadResponse(BaseModel):
    quote: QuoteResponse
    document: QuoteDocumentResponse


def _display_filename(filename: str | None) -> str:
    name = (filename or "").replace("\\", "/").split("/")[-1]
    name = "".join(character for character in name if character.isprintable()).strip()
    if not name.lower().endswith(".pdf") or len(name) > 255:
        raise PdfUploadError("INVALID_PDF", "Upload a file with a .pdf extension.")
    return name


def stage_pdf_upload(
    upload: UploadFile, settings: DocumentSettings,
) -> tuple[TemporaryDirectory[str], Path, str, str, int]:
    """Copy bounded bytes to a private temporary file and inspect page count."""
    try:
        filename = _display_filename(upload.filename)
        temporary = TemporaryDirectory(prefix="sourcepilot-quote-")
        path = Path(temporary.name) / "original.pdf"
        digest = hashlib.sha256()
        size = 0
        try:
            with path.open("xb") as output:
                while chunk := upload.file.read(CHUNK_BYTES):
                    size += len(chunk)
                    if size > settings.max_file_bytes:
                        raise PdfUploadError(
                            "PDF_TOO_LARGE",
                            f"PDF exceeds the {settings.max_file_bytes}-byte file limit.", 413,
                        )
                    digest.update(chunk)
                    output.write(chunk)
            with path.open("rb") as source:
                if source.read(5) != b"%PDF-":
                    raise PdfUploadError("INVALID_PDF", "File does not have PDF magic bytes.")
            try:
                page_count = inspect_page_count(
                    path, timeout_seconds=settings.inspection_timeout_seconds,
                    max_pages=settings.max_pages,
                )
            except InvalidPdfError as error:
                raise PdfUploadError("INVALID_PDF", str(error)) from error
            return temporary, path, filename, digest.hexdigest(), page_count
        except Exception:
            temporary.cleanup()
            raise
    finally:
        upload.file.close()


def _cleanup_owned_key(storage: DocumentStorage, key: str) -> None:
    try:
        storage.delete(key)
    except Exception:
        logger.exception("PDF upload cleanup failed for owned key %s", key)


def store_pdf_quote(
    database_session: Session, project: Project, supplier_id: UUID, *, path: Path,
    filename: str, sha256: str, page_count: int, storage: DocumentStorage,
) -> PdfQuoteUploadResponse:
    """Serialize quote creation and compensate only for confirmed rollback."""
    locked = database_session.scalars(
        select(Project).where(Project.id == project.id).with_for_update()
        .execution_options(populate_existing=True)
    ).one()
    if locked.stage != "QUOTES":
        raise PdfUploadError("QUOTE_NOT_AVAILABLE", "Approve the shortlist first.", 409)
    candidate = database_session.get(ProjectSupplier, (project.id, supplier_id))
    if candidate is None or not candidate.shortlisted or candidate.dismissed:
        raise PdfUploadError("QUOTE_NOT_AVAILABLE", "Supplier is not shortlisted.", 409)
    existing = database_session.scalar(select(Quote).where(
        Quote.project_id == project.id, Quote.supplier_id == supplier_id,
    ))
    if existing is not None:
        if existing.entry_type == QuoteEntryType.PDF and any(
            document.sha256 == sha256 for document in existing.documents
        ):
            raise PdfUploadError("DUPLICATE_PDF", "This PDF is already uploaded.", 409)
        raise PdfUploadError("QUOTE_ALREADY_EXISTS", "A quote already exists for this supplier.", 409)

    key = new_storage_key()
    try:
        storage.put(key, path)
    except Exception as error:
        _cleanup_owned_key(storage, key)
        raise PdfStorageError("PDF storage failed.") from error
    try:
        quote = create_quote(
            database_session, project_id=project.id, supplier_id=supplier_id,
            entry_type=QuoteEntryType.PDF, status=QuoteStatus.PROCESSING,
        )
        document = QuoteDocument(
            storage_key=key, original_filename=filename, sha256=sha256,
            page_count=page_count, processing_status=QuoteStatus.PROCESSING.value,
            processing_attempts=0,
        )
        quote.documents.append(document)
        database_session.flush()
        result = PdfQuoteUploadResponse(
            quote=quote_snapshot(quote),
            document=QuoteDocumentResponse(
                id=document.id, original_filename=filename, sha256=sha256,
                page_count=page_count, processing_status=document.processing_status,
                processing_attempts=0,
            ),
        )
    except Exception:
        database_session.rollback()
        _cleanup_owned_key(storage, key)
        raise
    try:
        database_session.commit()
    except IntegrityError:
        database_session.rollback()
        _cleanup_owned_key(storage, key)
        raise
    except Exception as error:
        logger.exception("PDF quote commit outcome uncertain; retained key %s", key)
        database_session.rollback()
        raise PdfCommitUncertainError("PDF quote commit outcome is uncertain.") from error
    return result
