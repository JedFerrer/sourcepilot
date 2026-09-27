"""Isolated, time-bounded PDF page inspection."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


class InvalidPdfError(ValueError):
    """The file cannot be opened as a supported, unencrypted PDF."""


class PdfInspectionTimeoutError(InvalidPdfError):
    """PDF inspection exceeded its deadline."""


def inspect_page_count(path: Path, *, timeout_seconds: int, max_pages: int) -> int:
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "sourcepilot.documents.inspect_pdf", str(path)],
            capture_output=True, text=True, timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise PdfInspectionTimeoutError("PDF inspection timed out.") from error
    if completed.returncode != 0:
        raise InvalidPdfError("PDF is unreadable or encrypted.")
    try:
        page_count = int(completed.stdout.strip())
    except ValueError as error:
        raise InvalidPdfError("PDF page count is unavailable.") from error
    if page_count < 1:
        raise InvalidPdfError("PDF has no pages.")
    if page_count > max_pages:
        raise InvalidPdfError(f"PDF exceeds the {max_pages}-page limit.")
    return page_count


def _inspect_child(path: Path) -> int:
    import pymupdf

    try:
        with pymupdf.open(path) as document:
            if not document.is_pdf or document.needs_pass:
                return 1
            print(document.page_count)
            return 0
    except (pymupdf.FileDataError, pymupdf.EmptyFileError, RuntimeError, ValueError):
        return 1


if __name__ == "__main__":
    raise SystemExit(_inspect_child(Path(sys.argv[1])))
