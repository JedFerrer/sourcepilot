"""Bounded, isolated text-block extraction from an already verified PDF snapshot."""

from __future__ import annotations

import json
import math
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MAX_BLOCKS = 5_000
MAX_BLOCK_BYTES = 64_000
MAX_TEXT_BYTES = 4_000_000
MAX_OUTPUT_BYTES = 8_000_000


class PdfParseError(ValueError):
    """Stored PDF has no supported, valid, bounded text extraction."""


class PdfParseTimeoutError(PdfParseError):
    """The parser child exceeded its deadline."""


class NoExtractableTextError(PdfParseError):
    """The PDF has no usable text blocks; image-only PDFs are unsupported."""


@dataclass(frozen=True)
class ParsedBlock:
    page_number: int
    block_number: int
    text: str

    @property
    def reference(self) -> str:
        return f"p{self.page_number}-b{self.block_number}"


def _normalize_text(raw: str) -> str:
    return unicodedata.normalize("NFC", raw.replace("\r\n", "\n").replace("\r", "\n")).strip()


def _extract(path: Path, *, max_pages: int) -> tuple[int, list[ParsedBlock]]:
    import pymupdf

    result: list[ParsedBlock] = []
    raw_total = normalized_total = 0
    with pymupdf.open(path) as document:
        if not document.is_pdf or document.needs_pass or not 1 <= document.page_count <= max_pages:
            raise PdfParseError("Stored PDF cannot be parsed within page limits.")
        for page_index in range(document.page_count):
            page = document[page_index]
            extracted: list[tuple[tuple[float, float, float, float, int], str]] = []
            flags = pymupdf.TEXTFLAGS_BLOCKS & ~pymupdf.TEXT_PRESERVE_IMAGES
            for index, item in enumerate(page.get_text("blocks", flags=flags, sort=False)):
                if len(item) < 7 or item[6] != 0:
                    continue  # Image metadata and non-text blocks are not evidence text.
                raw = item[4]
                if not isinstance(raw, str):
                    raise PdfParseError("Invalid PDF text block.")
                raw_size = len(raw.encode("utf-8"))
                raw_total += raw_size
                if raw_size > MAX_BLOCK_BYTES or raw_total > MAX_TEXT_BYTES:
                    raise PdfParseError("PDF text exceeds extraction limits.")
                text = _normalize_text(raw)
                if not text:
                    continue
                size = len(text.encode("utf-8"))
                normalized_total += size
                if size > MAX_BLOCK_BYTES or normalized_total > MAX_TEXT_BYTES:
                    raise PdfParseError("PDF text exceeds extraction limits.")
                coordinates = tuple(float(value) for value in item[:4])
                if not all(math.isfinite(value) for value in coordinates):
                    raise PdfParseError("Invalid PDF text coordinates.")
                extracted.append(((coordinates[1], coordinates[0], coordinates[3],
                                   coordinates[2], index), text))
                if len(result) + len(extracted) > MAX_BLOCKS:
                    raise PdfParseError("PDF has too many text blocks.")
            extracted.sort(key=lambda block: block[0])
            result.extend(
                ParsedBlock(page_index + 1, number, text)
                for number, (_, text) in enumerate(extracted, start=1)
            )
        if not result:
            raise NoExtractableTextError("PDF has no extractable text; image-only PDFs are unsupported.")
        return document.page_count, result


def _write_bounded(path: Path, payload: dict[str, Any]) -> None:
    size = 0
    with path.open("xb") as output:
        for segment in json.JSONEncoder(ensure_ascii=False, separators=(",", ":")).iterencode(payload):
            encoded = segment.encode("utf-8")
            size += len(encoded)
            if size > MAX_OUTPUT_BYTES:
                raise PdfParseError("PDF parser output exceeds limit.")
            output.write(encoded)


def _child(input_path: Path, output_path: Path, max_pages: int) -> int:
    try:
        page_count, blocks = _extract(input_path, max_pages=max_pages)
        _write_bounded(output_path, {
            "page_count": page_count,
            "blocks": [[block.page_number, block.block_number, block.text] for block in blocks],
        })
        return 0
    except NoExtractableTextError:
        return 3
    except Exception:  # noqa: BLE001 - child errors must become fixed, content-free exit codes
        return 2


def parse_pdf_snapshot(
    path: Path, output_path: Path, *, timeout_seconds: int, max_pages: int,
    expected_pages: int | None,
) -> list[ParsedBlock]:
    """Run PyMuPDF outside the application process and validate its complete result."""
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "sourcepilot.documents.parse_pdf", str(path),
             str(output_path), str(max_pages)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise PdfParseTimeoutError("PDF parsing timed out.") from error
    if completed.returncode == 3:
        raise NoExtractableTextError(
            "PDF has no extractable text; image-only PDFs are unsupported."
        )
    if completed.returncode != 0:
        raise PdfParseError("PDF parsing failed or exceeded extraction limits.")
    try:
        with output_path.open("rb") as source:
            serialized = source.read(MAX_OUTPUT_BYTES + 1)
        if len(serialized) > MAX_OUTPUT_BYTES:
            raise PdfParseError("PDF parser output exceeds limit.")
        payload = json.loads(serialized)
        if not isinstance(payload, dict) or set(payload) != {"page_count", "blocks"}:
            raise ValueError("Invalid result shape")
        page_count = payload["page_count"]
        rows = payload["blocks"]
        if type(page_count) is not int or not 1 <= page_count <= max_pages:
            raise ValueError("Invalid page count")
        if expected_pages is not None and page_count != expected_pages:
            raise ValueError("Stored page count differs")
        if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_BLOCKS:
            raise ValueError("Invalid block count")
        blocks: list[ParsedBlock] = []
        total = 0
        last_page = last_number = 0
        for row in rows:
            if not isinstance(row, list) or len(row) != 3:
                raise ValueError("Invalid block")
            page, number, text = row
            if type(page) is not int or type(number) is not int or not isinstance(text, str):
                raise ValueError("Invalid block types")
            if not 1 <= page <= page_count or page < last_page:
                raise ValueError("Invalid block page")
            if number != (last_number + 1 if page == last_page else 1):
                raise ValueError("Invalid block number")
            if not text or text != _normalize_text(text):
                raise ValueError("Invalid block text")
            size = len(text.encode("utf-8"))
            total += size
            if size > MAX_BLOCK_BYTES or total > MAX_TEXT_BYTES:
                raise ValueError("Block text exceeds limit")
            blocks.append(ParsedBlock(page, number, text))
            last_page, last_number = page, number
        return blocks
    except PdfParseError:
        raise
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise PdfParseError("PDF parser returned invalid output.") from error


if __name__ == "__main__":
    raise SystemExit(_child(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])))
