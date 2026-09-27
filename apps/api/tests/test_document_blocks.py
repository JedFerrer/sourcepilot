"""Focused M3-U4 parser, storage-read, and PostgreSQL persistence regressions."""

from __future__ import annotations

import hashlib
import socket
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from typing import Any, Self
from unittest.mock import Mock
from uuid import UUID, uuid4, uuid5

import pymupdf
import pytest
from sqlalchemy import Engine, delete, event, select
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.documents.parse_pdf import (
    MAX_BLOCK_BYTES,
    MAX_BLOCKS,
    MAX_OUTPUT_BYTES,
    MAX_TEXT_BYTES,
    NoExtractableTextError,
    ParsedBlock,
    PdfParseError,
    PdfParseTimeoutError,
    _extract,
    _normalize_text,
    _write_bounded,
    parse_pdf_snapshot,
)
from sourcepilot.documents.parse_service import (
    StoredDocumentError,
    _persist,
    parse_and_persist_document,
)
from sourcepilot.documents.settings import document_settings_from_environment
from sourcepilot.documents.storage import LocalDocumentStorage, S3DocumentStorage, new_storage_key
from sourcepilot.persistence.models import (
    DemoSession,
    DocumentBlock,
    Project,
    Quote,
    QuoteDocument,
    Supplier,
)
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)


def pdf_with_pages(*pages: str) -> bytes:
    document = pymupdf.open()
    for content in pages:
        page = document.new_page()
        if content:
            page.insert_text((50, 50), content)
    result = document.tobytes()
    document.close()
    return result


def pdf_with_positioned_blocks() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 180), "Lower block")
    page.insert_text((300, 110), "Middle right")
    page.insert_text((50, 70), "Upper left")
    result = document.tobytes()
    document.close()
    return result


def parse_bytes(tmp_path: Path, data: bytes) -> list[ParsedBlock]:
    source = tmp_path / "source.pdf"
    source.write_bytes(data)
    return parse_pdf_snapshot(
        source, tmp_path / "result.json", timeout_seconds=10, max_pages=15,
        expected_pages=None,
    )


@pytest.fixture
def engine() -> Iterator[Engine]:
    url = persistence_test_database_url_from_environment()
    reset_test_database(url)
    engine = create_test_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()
        reset_test_database(url)


def stored_document(engine: Engine, tmp_path: Path, data: bytes) -> tuple[UUID, LocalDocumentStorage]:
    storage = LocalDocumentStorage(tmp_path / "storage")
    source = tmp_path / "upload.pdf"
    source.write_bytes(data)
    key = new_storage_key()
    storage.put(key, source)
    now = datetime.now(UTC)
    with Session(engine) as session, session.begin():
        owner = DemoSession(
            opaque_token=f"token-{uuid4()}", last_seen_at=now,
            expires_at=now + timedelta(hours=24),
        )
        project = Project(demo_session=owner, name="Parser test", original_request="Source bags")
        supplier = Supplier(
            id=uuid4(), name=f"Parser supplier {uuid4()}", country="Testland",
            description="Synthetic parser fixture supplier",
        )
        session.add_all([project, supplier])
        session.flush()
        quote = Quote(
            project_id=project.id, supplier_id=supplier.id,
            entry_type="PDF", status="PROCESSING", revision=0,
        )
        session.add(quote)
        session.flush()
        with pymupdf.open(stream=data, filetype="pdf") as pdf:
            page_count = pdf.page_count
        document = QuoteDocument(
            quote_id=quote.id, storage_key=key, original_filename="source.pdf",
            sha256=hashlib.sha256(data).hexdigest(), page_count=page_count,
            processing_status="PROCESSING", processing_attempts=0,
        )
        session.add(document)
        session.flush()
        document_id = document.id
    return document_id, storage


def rows(engine: Engine, document_id: UUID) -> list[DocumentBlock]:
    with Session(engine) as session:
        return list(session.scalars(
            select(DocumentBlock).where(DocumentBlock.quote_document_id == document_id)
            .order_by(DocumentBlock.page_number, DocumentBlock.block_number)
        ).all())


def test_multiline_text_blank_pages_and_repeatable_references(tmp_path: Path) -> None:
    data = pdf_with_pages("", "First line\n  Second  line", "", "Final")
    first = parse_bytes(tmp_path, data)
    assert [(block.reference, block.text) for block in first] == [
        ("p2-b1", "First line\n  Second  line"), ("p4-b1", "Final"),
    ]
    (tmp_path / "result.json").unlink()
    assert parse_bytes(tmp_path, data) == first
    assert _normalize_text(" \r\nCafe\u0301  \r Next\n ") == "Café  \n Next"


def test_multiple_text_blocks_have_coordinate_order_references_and_stable_ids(
    engine: Engine, tmp_path: Path,
) -> None:
    data = pdf_with_positioned_blocks()
    first = parse_bytes(tmp_path, data)
    assert [(block.reference, block.text) for block in first] == [
        ("p1-b1", "Upper left"),
        ("p1-b2", "Middle right"),
        ("p1-b3", "Lower block"),
    ]
    (tmp_path / "result.json").unlink()
    assert parse_bytes(tmp_path, data) == first

    document_id, storage = stored_document(engine, tmp_path, data)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = document_settings_from_environment()
    parse_and_persist_document(factory, document_id, storage=storage, settings=settings)
    assert [(row.id, row.text) for row in rows(engine, document_id)] == [
        (uuid5(document_id, block.reference), block.text) for block in first
    ]
    parse_and_persist_document(factory, document_id, storage=storage, settings=settings)
    assert [(row.id, row.text) for row in rows(engine, document_id)] == [
        (uuid5(document_id, block.reference), block.text) for block in first
    ]


def test_blank_image_and_whitespace_only_pdf_has_truthful_failure(tmp_path: Path) -> None:
    scanned = pymupdf.open()
    pixels = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10))
    pixels.clear_with(255)
    scanned.new_page().insert_image(pymupdf.Rect(10, 10, 30, 30), pixmap=pixels)
    image_only = scanned.tobytes()
    scanned.close()
    for data in (pdf_with_pages(""), pdf_with_pages("   "), image_only):
        (tmp_path / "result.json").unlink(missing_ok=True)
        with pytest.raises(NoExtractableTextError, match="no extractable text"):
            parse_bytes(tmp_path, data)


def test_page_bounds_and_malformed_pdf(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "result.json"
    source.write_bytes(pdf_with_pages("Text", "Second"))
    with pytest.raises(PdfParseError, match="extraction limits"):
        parse_pdf_snapshot(source, output, timeout_seconds=10, max_pages=1, expected_pages=2)
    output.unlink(missing_ok=True)
    with pytest.raises(PdfParseError, match="invalid output"):
        parse_pdf_snapshot(source, output, timeout_seconds=10, max_pages=15, expected_pages=1)
    output.unlink(missing_ok=True)
    source.write_bytes(b"%PDF-malformed")
    with pytest.raises(PdfParseError, match="failed"):
        parse_pdf_snapshot(source, output, timeout_seconds=10, max_pages=15, expected_pages=1)


def test_pdf_hyperlink_and_embedded_javascript_are_never_executed(tmp_path: Path) -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    listener.settimeout(0.2)
    url = f"http://127.0.0.1:{listener.getsockname()[1]}/must-not-fetch"
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((50, 50), f"Quoted offer {url}")
    page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(50, 35, 150, 55),
                      "uri": url})
    action = pdf.get_new_xref()
    pdf.update_object(action, f'<< /S /JavaScript /JS (app.launchURL("{url}")) >>')
    pdf.xref_set_key(pdf.pdf_catalog(), "OpenAction", f"{action} 0 R")
    data = pdf.tobytes()
    pdf.close()
    try:
        assert parse_bytes(tmp_path, data)[0].text.startswith("Quoted offer")
        with pytest.raises(TimeoutError):
            listener.accept()
    finally:
        listener.close()


def test_child_output_validation_and_page_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(pdf_with_pages("text"))
    output = tmp_path / "result.json"

    def invalid_child(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        output.write_text('{"page_count":1,"blocks":[[1,2,"bad numbering"]]}')
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", invalid_child)
    with pytest.raises(PdfParseError, match="invalid output"):
        parse_pdf_snapshot(source, output, timeout_seconds=10, max_pages=15, expected_pages=1)

    def oversized_child(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        output.write_bytes(b"x" * (MAX_OUTPUT_BYTES + 1))
        return subprocess.CompletedProcess(args[0], 0)

    monkeypatch.setattr(subprocess, "run", oversized_child)
    with pytest.raises(PdfParseError, match="output exceeds"):
        parse_pdf_snapshot(source, output, timeout_seconds=10, max_pages=15, expected_pages=1)


def test_malformed_child_json_prevents_persistence_and_cleans_up(
    engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, storage = stored_document(engine, tmp_path, pdf_with_pages("Original"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    temporary_paths: list[Path] = []

    def tracked_temporary(*args: Any, **kwargs: Any) -> TemporaryDirectory[str]:
        temporary = TemporaryDirectory(*args, **kwargs)
        temporary_paths.append(Path(temporary.name))
        return temporary

    def malformed_child(args: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        Path(args[4]).write_bytes(b'{"page_count":1,"blocks":[')
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr("sourcepilot.documents.parse_service.TemporaryDirectory", tracked_temporary)
    monkeypatch.setattr(subprocess, "run", malformed_child)
    with pytest.raises(PdfParseError, match="invalid output"):
        parse_and_persist_document(
            factory, document_id, storage=storage,
            settings=document_settings_from_environment(),
        )
    assert rows(engine, document_id) == []
    assert len(temporary_paths) == 1
    assert not temporary_paths[0].exists()


def test_collection_limits_and_bounded_writer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    class Page:
        def __init__(self, blocks: list[tuple[Any, ...]]) -> None:
            self.blocks = blocks

        def get_text(self, *_args: Any, **_kwargs: Any) -> list[tuple[Any, ...]]:
            return self.blocks

    class Pdf:
        is_pdf = True
        needs_pass = False
        page_count = 1

        def __init__(self, blocks: list[tuple[Any, ...]]) -> None:
            self.page = Page(blocks)

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def __getitem__(self, _index: int) -> Page:
            return self.page

    block = lambda text: (0, 0, 10, 10, text, 0, 0)
    for blocks in (
        [block("x" * (MAX_BLOCK_BYTES + 1))],
        [block("x" * 1_000)] * (MAX_BLOCKS + 1),
        [block("x" * 1_000)] * ((MAX_TEXT_BYTES // 1_000) + 1),
    ):
        monkeypatch.setattr(pymupdf, "open", lambda _path, blocks=blocks: Pdf(blocks))
        with pytest.raises(PdfParseError, match="limit|too many"):
            _extract(tmp_path / "ignored.pdf", max_pages=15)
    with pytest.raises(PdfParseError, match="output exceeds"):
        _write_bounded(tmp_path / "too-big.json", {"x": "x" * MAX_OUTPUT_BYTES})


def test_storage_reads_are_bounded_private_and_s3_stream_closes(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-safe")
    key = new_storage_key()
    local = LocalDocumentStorage(tmp_path / "stored")
    local.put(key, source)
    snapshot = tmp_path / "snapshot.pdf"
    assert local.read_to(key, snapshot, max_bytes=source.stat().st_size) == hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    assert snapshot.read_bytes() == source.read_bytes()
    with pytest.raises(ValueError, match="file limit"):
        local.read_to(key, tmp_path / "too-small.pdf", max_bytes=source.stat().st_size - 1)
    with pytest.raises(ValueError, match="key"):
        local.read_to("../unsafe.pdf", tmp_path / "unsafe.pdf", max_bytes=100)

    stream = BytesIO(source.read_bytes())
    client = Mock()
    client.get_object.return_value = {"Body": stream}
    s3 = S3DocumentStorage("test-bucket", client=client)
    assert s3.read_to(key, tmp_path / "s3.pdf", max_bytes=100) == hashlib.sha256(
        source.read_bytes()
    ).hexdigest()
    assert stream.closed
    assert client.get_object.call_args.kwargs == {"Bucket": "test-bucket", "Key": key}

    too_large_stream = BytesIO(b"x" * 101)
    client.get_object.return_value = {"Body": too_large_stream}
    with pytest.raises(ValueError, match="file limit"):
        s3.read_to(key, tmp_path / "s3-too-large.pdf", max_bytes=100)
    assert too_large_stream.closed


def test_s3_read_and_close_failures_preserve_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingStream(BytesIO):
        def read(self, _size: int | None = -1) -> bytes:
            raise OSError("private-read-marker")

        def close(self) -> None:
            super().close()
            raise OSError("private-close-marker")

    stream = FailingStream()
    client = Mock()
    client.get_object.return_value = {"Body": stream}
    storage = S3DocumentStorage("test-bucket", client=client)
    log_error = Mock()
    monkeypatch.setattr("sourcepilot.documents.storage.logger.error", log_error)
    with pytest.raises(OSError, match="private-read-marker"):
        storage.read_to(new_storage_key(), tmp_path / "failed.pdf", max_bytes=100)
    assert stream.closed
    log_error.assert_called_once_with("PDF S3 read stream cleanup failed (%s)", "OSError")
    assert "private-read-marker" not in str(log_error.call_args)
    assert "private-close-marker" not in str(log_error.call_args)


def test_s3_close_only_failure_surfaces(tmp_path: Path) -> None:
    class CloseFails(BytesIO):
        def close(self) -> None:
            super().close()
            raise OSError("close failed")

    client = Mock()
    client.get_object.return_value = {"Body": CloseFails(b"safe")}
    storage = S3DocumentStorage("test-bucket", client=client)
    with pytest.raises(OSError, match="close failed"):
        storage.read_to(new_storage_key(), tmp_path / "closed.pdf", max_bytes=100)


def test_verified_snapshot_persists_stable_blocks_and_status(engine: Engine, tmp_path: Path) -> None:
    document_id, storage = stored_document(engine, tmp_path, pdf_with_pages("Alpha\n  Beta", "Gamma"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = document_settings_from_environment()
    parse_and_persist_document(factory, document_id, storage=storage, settings=settings)
    first = rows(engine, document_id)
    assert [(row.page_number, row.block_number, row.text) for row in first] == [
        (1, 1, "Alpha\n  Beta"), (2, 1, "Gamma"),
    ]
    assert [row.id for row in first] == [uuid5(document_id, "p1-b1"), uuid5(document_id, "p2-b1")]
    parse_and_persist_document(factory, document_id, storage=storage, settings=settings)
    assert [row.id for row in rows(engine, document_id)] == [row.id for row in first]
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        assert document.processing_status == document.quote.status == "PROCESSING"
        assert document.processing_attempts == 0
        assert document.processing_started_at is document.processing_completed_at is None


def test_deleting_document_cascades_to_blocks(engine: Engine, tmp_path: Path) -> None:
    document_id, storage = stored_document(engine, tmp_path, pdf_with_pages("Text"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    parse_and_persist_document(
        factory, document_id, storage=storage, settings=document_settings_from_environment()
    )
    assert len(rows(engine, document_id)) == 1
    with Session(engine) as session, session.begin():
        session.execute(delete(QuoteDocument).where(QuoteDocument.id == document_id))
    assert rows(engine, document_id) == []


def test_hash_and_input_limits_fail_before_child(engine: Engine, tmp_path: Path,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    document_id, storage = stored_document(engine, tmp_path, pdf_with_pages("Original"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    settings = document_settings_from_environment()
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        stored_path = storage.root / document.storage_key
    stored_path.write_bytes(pdf_with_pages("Tampered"))
    monkeypatch.setattr("sourcepilot.documents.parse_service.parse_pdf_snapshot",
                        lambda *args, **kwargs: pytest.fail("child must not run"))
    with pytest.raises(StoredDocumentError, match="checksum"):
        parse_and_persist_document(factory, document_id, storage=storage, settings=settings)
    assert rows(engine, document_id) == []
    stored_path.write_bytes(b"x" * 101)
    with pytest.raises(ValueError, match="file limit"):
        parse_and_persist_document(
            factory, document_id, storage=storage,
            settings=replace(settings, max_file_bytes=100),
        )
    assert rows(engine, document_id) == []


@pytest.mark.parametrize("prior", [False, True])
def test_actual_write_failure_rolls_back_whole_set(engine: Engine, tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch,
                                                    prior: bool) -> None:
    document_id, _ = stored_document(engine, tmp_path, pdf_with_pages("Original"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    if prior:
        _persist(factory, document_id, _document_key(engine, document_id)[0],
                 _document_key(engine, document_id)[1], [ParsedBlock(1, 1, "Old")])
    before = [(row.id, row.text) for row in rows(engine, document_id)]
    key, sha = _document_key(engine, document_id)

    def fail_after_insert(_mapper: Any, _connection: Any, _target: Any) -> None:
        raise RuntimeError("injected after INSERT")

    event.listen(DocumentBlock, "after_insert", fail_after_insert)
    try:
        with pytest.raises(RuntimeError, match="injected"):
            _persist(factory, document_id, key, sha, [ParsedBlock(1, 1, "New")])
    finally:
        event.remove(DocumentBlock, "after_insert", fail_after_insert)
    assert [(row.id, row.text) for row in rows(engine, document_id)] == before


def _document_key(engine: Engine, document_id: UUID) -> tuple[str, str]:
    with Session(engine) as session:
        document = session.get(QuoteDocument, document_id)
        assert document is not None
        return document.storage_key, document.sha256


def test_overlapping_postgres_writes_leave_one_complete_set(engine: Engine, tmp_path: Path) -> None:
    document_id, _ = stored_document(engine, tmp_path, pdf_with_pages("Original"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    key, sha = _document_key(engine, document_id)
    first_written = Event()
    release_first = Event()
    second_statement = Event()
    first_connection: Any = None

    def hold_first(_mapper: Any, connection: Any, _target: Any) -> None:
        nonlocal first_connection
        if first_connection is None:
            first_connection = connection
            first_written.set()
            assert release_first.wait(15)

    def observe_second(connection: Any, _cursor: Any, statement: str, *_args: Any) -> None:
        if first_written.is_set() and connection is not first_connection and "quote_documents" in statement:
            second_statement.set()

    event.listen(DocumentBlock, "after_insert", hold_first)
    event.listen(engine, "before_cursor_execute", observe_second)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(_persist, factory, document_id, key, sha,
                                    [ParsedBlock(1, 1, "First"), ParsedBlock(1, 2, "Set")])
            assert first_written.wait(15)
            second = executor.submit(_persist, factory, document_id, key, sha,
                                     [ParsedBlock(1, 1, "Second"), ParsedBlock(1, 2, "Set")])
            try:
                assert second_statement.wait(15)
                assert not second.done()
            finally:
                release_first.set()
            first.result(timeout=15)
            second.result(timeout=15)
    finally:
        event.remove(DocumentBlock, "after_insert", hold_first)
        event.remove(engine, "before_cursor_execute", observe_second)
        release_first.set()
    assert [(row.block_number, row.text) for row in rows(engine, document_id)] == [
        (1, "Second"), (2, "Set"),
    ]


def test_timeout_reaps_child_and_cleanup_preserves_original_error(
    engine: Engine, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_id, storage = stored_document(engine, tmp_path, pdf_with_pages("Original"))
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    real_popen = subprocess.Popen
    children: list[subprocess.Popen[str]] = []
    marker = tmp_path / "started"
    code = "import pathlib,sys,time; pathlib.Path(sys.argv[1]).touch(); time.sleep(60)"

    def blocking_child(args: list[str], *positional: Any, **options: Any) -> subprocess.Popen[str]:
        assert args[1:3] == ["-m", "sourcepilot.documents.parse_pdf"]
        child = real_popen([sys.executable, "-c", code, str(marker)], *positional, **options)
        children.append(child)
        return child

    real_temporary = TemporaryDirectory
    staged = tmp_path / "staged"
    staged.mkdir()

    class CleanupFails:
        def __init__(self, prefix: str) -> None:
            self.inner = real_temporary(prefix=prefix, dir=staged)
            self.name = self.inner.name

        def cleanup(self) -> None:
            self.inner.cleanup()
            raise OSError("cleanup failed")

    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", blocking_child)
        patch.setattr("sourcepilot.documents.parse_service.TemporaryDirectory", CleanupFails)
        with pytest.raises(PdfParseTimeoutError, match="timed out"):
            parse_and_persist_document(
                factory, document_id, storage=storage,
                settings=replace(document_settings_from_environment(), inspection_timeout_seconds=1),
            )
    assert marker.exists()
    assert len(children) == 1 and children[0].returncode is not None
    assert children[0].wait(timeout=0) == children[0].returncode
    assert list(staged.iterdir()) == []
    assert rows(engine, document_id) == []
