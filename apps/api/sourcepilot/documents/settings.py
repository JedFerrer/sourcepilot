"""Configuration for PDF quote uploads."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from sourcepilot.session.settings import positive_integer_from_environment

MULTIPART_OVERHEAD_BYTES = 65_536
DEFAULT_LOCAL_DIRECTORY = Path(__file__).resolve().parents[2] / ".local-quote-documents"
DEFAULT_PROCESSING_STALE_SECONDS = 600


def processing_stale_seconds_from_environment() -> int:
    return positive_integer_from_environment(
        "QUOTE_PROCESSING_STALE_SECONDS", DEFAULT_PROCESSING_STALE_SECONDS
    )


@dataclass(frozen=True)
class DocumentSettings:
    backend: str
    local_directory: Path
    s3_bucket: str | None
    s3_endpoint_url: str | None
    s3_region: str | None
    max_file_bytes: int
    max_pages: int
    inspection_timeout_seconds: int

    @property
    def max_request_bytes(self) -> int:
        return self.max_file_bytes + MULTIPART_OVERHEAD_BYTES


def document_settings_from_environment() -> DocumentSettings:
    backend = os.environ.get("DOCUMENT_STORAGE_BACKEND", "local").lower()
    if backend not in {"local", "s3"}:
        raise RuntimeError("DOCUMENT_STORAGE_BACKEND must be local or s3.")
    bucket = os.environ.get("DOCUMENT_STORAGE_S3_BUCKET") or None
    if backend == "s3" and not bucket:
        raise RuntimeError("DOCUMENT_STORAGE_S3_BUCKET is required for s3 storage.")
    directory = os.environ.get("DOCUMENT_STORAGE_LOCAL_DIR")
    return DocumentSettings(
        backend=backend,
        local_directory=Path(directory).resolve() if directory else DEFAULT_LOCAL_DIRECTORY,
        s3_bucket=bucket,
        s3_endpoint_url=os.environ.get("DOCUMENT_STORAGE_S3_ENDPOINT_URL") or None,
        s3_region=os.environ.get("DOCUMENT_STORAGE_S3_REGION") or None,
        max_file_bytes=positive_integer_from_environment("QUOTE_PDF_MAX_BYTES", 10_000_000),
        max_pages=positive_integer_from_environment("QUOTE_PDF_MAX_PAGES", 15),
        inspection_timeout_seconds=positive_integer_from_environment(
            "QUOTE_PDF_INSPECTION_TIMEOUT_SECONDS", 10
        ),
    )
