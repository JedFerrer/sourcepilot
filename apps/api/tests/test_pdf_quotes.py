"""PDF upload validation, ownership, and storage lifecycle tests."""

from __future__ import annotations

import asyncio
import hashlib
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Lock
from typing import Any, Self
from unittest.mock import Mock
from uuid import UUID

import pymupdf
import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from sourcepilot.documents.body_limit import UploadBodyLimitMiddleware
from sourcepilot.documents.inspect_pdf import PdfInspectionTimeoutError
from sourcepilot.documents.service import (
    PdfCommitUncertainError,
    PdfUploadError,
    stage_pdf_upload,
    store_pdf_quote,
)
from sourcepilot.documents.settings import (
    MULTIPART_OVERHEAD_BYTES,
    document_settings_from_environment,
)
from sourcepilot.documents.storage import (
    LocalDocumentStorage,
    S3DocumentStorage,
    new_storage_key,
)
from sourcepilot.main import app, get_document_storage
from sourcepilot.persistence.database import get_database_session
from sourcepilot.persistence.models import Project, Quote, QuoteDocument
from sourcepilot.quotes.service import QuoteWorkflowError, create_manual_quote
from sourcepilot.suppliers.seed import seed_suppliers
from tests.database_test_support import (
    create_test_engine,
    persistence_test_database_url_from_environment,
    reset_test_database,
)
from tests.test_manual_quotes import setup_shortlist


@pytest.fixture(scope="module")
def database_url() -> str:
    return persistence_test_database_url_from_environment()


@pytest.fixture(scope="module")
def engine(database_url: str) -> Iterator[Engine]:
    test_engine = create_test_engine(database_url)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def client(engine: Engine, database_url: str) -> Iterator[TestClient]:
    reset_test_database(database_url)
    with Session(engine) as session:
        seed_suppliers(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_database_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app, raise_server_exceptions=False) as value:
        assert value.post("/demo-session").status_code == 204
        yield value
    app.dependency_overrides.clear()
    reset_test_database(database_url)


def pdf_bytes(pages: int = 1) -> bytes:
    document = pymupdf.open()
    for _ in range(pages):
        document.new_page()
    result = document.tobytes()
    document.close()
    return result


@pytest.fixture
def storage_client(client: TestClient, tmp_path: Path) -> tuple[TestClient, LocalDocumentStorage]:
    storage = LocalDocumentStorage(tmp_path / "stored")
    app.dependency_overrides[get_document_storage] = lambda: storage
    return client, storage


def upload(client: TestClient, project_id: str, supplier_id: str, data: bytes,
           filename: str = "quote.pdf"):
    return client.post(
        f"/projects/{project_id}/quotes/upload",
        data={"supplier_id": supplier_id},
        files={"file": (filename, data, "application/pdf")},
    )


def test_upload_creates_unconfirmed_pdf_metadata_without_exposing_storage_key(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original = pdf_bytes()
    response = upload(api, project_id, supplier_id, original, "../supplier.pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["quote"]["entry_type"] == "PDF"
    assert body["quote"]["status"] == "PROCESSING"
    assert body["quote"]["revision"] == 0
    assert body["quote"]["confirmed_at"] is None
    assert body["quote"]["values"] == {}
    assert body["document"]["processing_status"] == "PROCESSING"
    assert body["document"]["processing_attempts"] == 0
    assert body["document"]["processing_started_at"] is None
    assert body["document"]["processing_completed_at"] is None
    assert body["document"]["last_error"] is None
    assert body["document"]["page_count"] == 1
    assert body["document"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert "storage_key" not in response.text
    assert str(storage.root) not in response.text
    assert next(iter(storage.root.rglob("*.pdf"))).read_bytes() == original
    quote_id = body["quote"]["id"]
    assert api.post(f"/quotes/{quote_id}/confirm").status_code == 409
    assert api.get(f"/quotes/{quote_id}").json()["status"] == "PROCESSING"
    with Session(engine) as database_session:
        stored = database_session.scalars(select(QuoteDocument)).one()
        assert stored.quote_id == UUID(quote_id)
        assert stored.original_filename == "supplier.pdf"
        assert stored.sha256 == hashlib.sha256(original).hexdigest()
        assert stored.processing_attempts == 0
        assert stored.processing_started_at is None
        assert stored.processing_completed_at is None
        assert stored.last_error is None


def test_pdf_validation_rejects_bad_files_and_page_limit(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    encrypted = pymupdf.open()
    encrypted.new_page()
    encrypted_data = encrypted.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,  # pyright: ignore[reportAttributeAccessIssue]
        owner_pw="owner", user_pw="reader",
    )
    encrypted.close()
    for data, name in ((pdf_bytes(), "quote.txt"), (b"not a pdf", "quote.pdf"),
                       (b"%PDF-broken", "quote.pdf"), (encrypted_data, "quote.pdf"),
                       (pdf_bytes(16), "quote.pdf")):
        response = upload(api, project_id, supplier_id, data, name)
        assert response.status_code == 422, response.text
    if storage.root.exists():
        assert list(storage.root.rglob("*.pdf")) == []
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    accepted = upload(api, project_id, supplier_id, pdf_bytes(15))
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["document"]["page_count"] == 15


def test_duplicate_and_different_existing_quote_conflicts(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, _ = storage_client
    project_id, supplier_id, other = setup_shortlist(api, approve_shortlist=False)
    assert api.patch(f"/projects/{project_id}/suppliers/{other}", json={
        "shortlisted": True,
    }).status_code == 200
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    original = pdf_bytes()
    assert upload(api, project_id, supplier_id, original).status_code == 201
    duplicate = upload(api, project_id, supplier_id, original)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_PDF"
    different = upload(api, project_id, supplier_id, pdf_bytes(2))
    assert different.status_code == 409
    assert different.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"
    assert api.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": other,
    }).status_code == 201
    manual_conflict = upload(api, project_id, other, pdf_bytes())
    assert manual_conflict.status_code == 409
    assert manual_conflict.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"


def test_stage_pdf_exact_byte_boundary_and_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = document_settings_from_environment()
    monkeypatch.setattr("sourcepilot.documents.service.inspect_page_count", lambda *args, **kwargs: 1)
    accepted = b"%PDF-" + b"x" * (10_000_000 - 5)
    staged = stage_pdf_upload(UploadFile(file=BytesIO(accepted), filename="a.pdf"), settings)
    directory, path, _, digest, pages = staged
    assert path.stat().st_size == 10_000_000
    assert digest == hashlib.sha256(accepted).hexdigest()
    assert pages == 1
    directory.cleanup()
    assert not path.exists()
    with pytest.raises(PdfUploadError) as error:
        stage_pdf_upload(
            UploadFile(file=BytesIO(accepted + b"x"), filename="a.pdf"), settings,
        )
    assert error.value.status_code == 413


def test_invalid_stage_removes_private_temporary_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    original_temporary = TemporaryDirectory
    monkeypatch.setattr(
        "sourcepilot.documents.service.TemporaryDirectory",
        lambda prefix: original_temporary(prefix=prefix, dir=tmp_path),
    )
    with pytest.raises(PdfUploadError):
        stage_pdf_upload(
            UploadFile(file=BytesIO(b"%PDF-broken"), filename="a.pdf"),
            document_settings_from_environment(),
        )
    assert list(tmp_path.iterdir()) == []


def test_inspection_timeout_reaps_child_cleans_temporary_file_and_allows_retry(
    storage_client: tuple[TestClient, LocalDocumentStorage],
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    api, _ = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    marker = tmp_path / "child-started"
    staged_root = tmp_path / "staged"
    staged_root.mkdir()
    real_popen = subprocess.Popen
    real_temporary = TemporaryDirectory
    children: list[subprocess.Popen[str]] = []
    child_code = (
        "import os, pathlib, sys, time; "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(60)"
    )

    def spawn_blocking_child(args: list[str], *positional: Any, **options: Any) -> subprocess.Popen[str]:
        assert args[1:3] == ["-m", "sourcepilot.documents.inspect_pdf"]
        child = real_popen(
            [sys.executable, "-c", child_code, str(marker)], *positional, **options,
        )
        children.append(child)
        return child

    with monkeypatch.context() as patch:
        patch.setattr(subprocess, "Popen", spawn_blocking_child)
        patch.setattr(
            "sourcepilot.documents.service.TemporaryDirectory",
            lambda prefix: real_temporary(prefix=prefix, dir=staged_root),
        )
        with pytest.raises(PdfUploadError, match="timed out") as timeout_error:
            stage_pdf_upload(
                UploadFile(file=BytesIO(pdf_bytes()), filename="a.pdf"),
                replace(document_settings_from_environment(), inspection_timeout_seconds=2),
            )
    assert isinstance(timeout_error.value.__cause__, PdfInspectionTimeoutError)
    assert marker.exists(), "The real child must start before the timeout"
    assert len(children) == 1
    assert children[0].returncode is not None
    assert children[0].wait(timeout=0) == children[0].returncode
    assert list(staged_root.iterdir()) == []
    accepted = upload(api, project_id, supplier_id, pdf_bytes())
    assert accepted.status_code == 201, accepted.text


def test_local_and_s3_storage_use_owned_safe_keys(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-original")
    key = new_storage_key()
    local = LocalDocumentStorage(tmp_path / "local")
    local.put(key, source)
    assert (local.root / key).read_bytes() == source.read_bytes()
    with pytest.raises(ValueError):
        local.delete("../other.pdf")
    local.delete(key)
    assert not (local.root / key).exists()
    mock_client = Mock()
    s3 = S3DocumentStorage("bucket", client=mock_client)
    s3.put(key, source)
    assert mock_client.put_object.call_args.kwargs["Key"] == key
    assert mock_client.put_object.call_args.kwargs["ContentType"] == "application/pdf"
    s3.delete(key)
    mock_client.delete_object.assert_called_once_with(Bucket="bucket", Key=key)


def test_request_limit_rejects_stream_without_content_length_before_parser() -> None:
    calls = 0
    async def inner(*args: object) -> None:
        nonlocal calls
        calls += 1
    middleware = UploadBodyLimitMiddleware(inner)
    settings = document_settings_from_environment()
    assert settings.max_request_bytes == 10_000_000 + MULTIPART_OVERHEAD_BYTES
    messages = iter([
        {"type": "http.request", "body": b"x" * settings.max_request_bytes, "more_body": True},
        {"type": "http.request", "body": b"x", "more_body": False},
    ])
    sent: list[dict[str, object]] = []
    async def receive() -> dict[str, object]:
        return next(messages)
    async def send(message: dict[str, object]) -> None:
        sent.append(message)
    asyncio.run(middleware(
        {"type": "http", "method": "POST", "path": "/projects/x/quotes/upload", "headers": []},
        receive, send,
    ))
    assert calls == 0
    assert sent[0]["status"] == 413


def test_upload_scope_and_existing_manual_quote(
    storage_client: tuple[TestClient, LocalDocumentStorage],
) -> None:
    api, _ = storage_client
    project_id, supplier_id, other = setup_shortlist(api, approve_shortlist=False)
    assert upload(api, project_id, supplier_id, pdf_bytes()).status_code == 409
    assert api.post(f"/projects/{project_id}/shortlist/approve").status_code == 200
    assert upload(api, project_id, other, pdf_bytes()).status_code == 409
    with TestClient(app, raise_server_exceptions=False) as stranger:
        assert stranger.post("/demo-session").status_code == 204
        assert upload(stranger, project_id, supplier_id, pdf_bytes()).status_code == 404
    assert api.post(f"/projects/{project_id}/quotes/manual", json={
        "supplier_id": supplier_id,
    }).status_code == 201
    conflict = upload(api, project_id, supplier_id, pdf_bytes())
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "QUOTE_ALREADY_EXISTS"


def test_storage_partial_write_is_cleaned_after_failure(
    storage_client: tuple[TestClient, LocalDocumentStorage], monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original_put = storage.put
    def failing_put(key: str, source: Path) -> None:
        original_put(key, source)
        raise OSError("simulated uncertain write")
    monkeypatch.setattr(storage, "put", failing_put)
    response = upload(api, project_id, supplier_id, pdf_bytes())
    assert response.status_code == 503
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    assert list(storage.root.rglob("*.pdf")) == []


def test_partial_write_and_unlink_failure_records_safe_identifiers(
    storage_client: tuple[TestClient, LocalDocumentStorage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    original_open = Path.open
    original_unlink = Path.unlink
    secret = "sensitive PDF bytes and connection secret"
    content_marker = "PRIVATE PDF CONTENT MARKER"
    document = pymupdf.open()
    document.new_page().insert_text((50, 50), content_marker)
    sensitive_pdf = document.tobytes()
    document.close()
    log = Mock()
    original_put = storage.put
    write_errors: list[Exception] = []
    monkeypatch.setattr("sourcepilot.documents.storage.logger", log)

    def observed_put(key: str, source: Path) -> None:
        try:
            original_put(key, source)
        except Exception as error:
            write_errors.append(error)
            raise

    monkeypatch.setattr(storage, "put", observed_put)

    class FailingOutput:
        def __init__(self, path: Path) -> None:
            self.file = original_open(path, "xb")

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            self.file.close()

        def write(self, data: bytes) -> None:
            self.file.write(data[:16])
            raise OSError("original partial write failure")

    def failing_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any) -> Any:
        if path.suffix == ".part" and mode == "xb":
            return FailingOutput(path)
        return original_open(path, mode, *args, **kwargs)

    def failing_unlink(path: Path, *args: Any, **kwargs: Any) -> None:
        if path.suffix == ".part":
            raise OSError(secret)
        original_unlink(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", failing_open)
        patch.setattr(Path, "unlink", failing_unlink)
        response = upload(api, project_id, supplier_id, sensitive_pdf)
    assert response.status_code == 503
    assert len(write_errors) == 1
    assert str(write_errors[0]) == "original partial write failure"
    assert response.json()["error"]["code"] == "UPLOAD_UNAVAILABLE"
    assert "original partial write failure" not in response.text
    assert secret not in response.text
    assert content_marker not in response.text
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    partials = list(storage.root.rglob("*.part"))
    assert len(partials) == 1
    message = log.error.call_args.args[0] % log.error.call_args.args[1:]
    assert "PDF partial cleanup failed" in message
    assert "quote-pdfs/" in message
    assert partials[0].name in message
    assert secret not in message
    assert content_marker not in message
    assert "original partial write failure" not in message
    original_unlink(partials[0])


def test_cleanup_failure_is_recorded_without_erasing_original_error(
    storage_client: tuple[TestClient, LocalDocumentStorage], monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    log = Mock()
    monkeypatch.setattr("sourcepilot.documents.service.logger", log)
    def failing_put(key: str, source: Path) -> None:
        raise OSError("write failed")
    def failing_delete(key: str) -> None:
        raise OSError("cleanup failed")
    monkeypatch.setattr(storage, "put", failing_put)
    monkeypatch.setattr(storage, "delete", failing_delete)
    response = upload(api, project_id, supplier_id, pdf_bytes())
    assert response.status_code == 503
    assert api.get(f"/projects/{project_id}/quotes").json() == []
    assert "PDF upload cleanup failed" in log.exception.call_args.args[0]


def test_confirmed_database_rollback_removes_owned_object(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    with Session(engine) as database_session:
        project = database_session.get(Project, UUID(project_id))
        assert project is not None
        def failing_commit() -> None:
            raise IntegrityError("commit", {}, Exception("constraint"))
        monkeypatch.setattr(database_session, "commit", failing_commit)
        with pytest.raises(IntegrityError):
            store_pdf_quote(
                database_session, project, UUID(supplier_id), path=source,
                filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                page_count=1, storage=storage,
            )
    assert list(storage.root.rglob("*.pdf")) == []
    with Session(engine) as database_session:
        assert database_session.scalars(select(Quote).where(Quote.project_id == UUID(project_id))).all() == []


def test_uncertain_commit_preserves_object_and_reports_it(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    log = Mock()
    monkeypatch.setattr("sourcepilot.documents.service.logger", log)
    with Session(engine) as database_session:
        project = database_session.get(Project, UUID(project_id))
        assert project is not None
        def uncertain_commit() -> None:
            raise ConnectionError("connection dropped")
        monkeypatch.setattr(database_session, "commit", uncertain_commit)
        with pytest.raises(PdfCommitUncertainError):
            store_pdf_quote(
                database_session, project, UUID(supplier_id), path=source,
                filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                page_count=1, storage=storage,
            )
    assert len(list(storage.root.rglob("*.pdf"))) == 1
    assert "commit outcome uncertain" in log.exception.call_args.args[0]


@pytest.mark.parametrize("same_pdf", [True, False], ids=["identical", "different"])
def test_concurrent_pdf_uploads_serialize_with_independent_postgres_transactions(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine,
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, same_pdf: bool,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    winner_bytes = pdf_bytes()
    loser_bytes = winner_bytes if same_pdf else pdf_bytes(2)
    first_stored = Event()
    release_first = Event()
    second_transaction_attempt = Event()
    guard = Lock()
    transaction_connections: list[object] = []
    original_put = storage.put
    real_temporary = TemporaryDirectory
    staged_root = tmp_path / "staged"
    staged_root.mkdir()

    def held_first_put(key: str, source: Path) -> None:
        original_put(key, source)
        first_stored.set()
        assert release_first.wait(timeout=15), "Second request did not reach PostgreSQL"

    def observe_transaction(connection: object, _cursor: object, statement: str,
                            _parameters: object, _context: object, _executemany: bool) -> None:
        # The session activity update can block before the second project FOR UPDATE.
        if "update demo_sessions" in statement.lower():
            with guard:
                transaction_connections.append(connection)
                if len(transaction_connections) == 2:
                    second_transaction_attempt.set()

    monkeypatch.setattr(storage, "put", held_first_put)
    monkeypatch.setattr(
        "sourcepilot.documents.service.TemporaryDirectory",
        lambda prefix: real_temporary(prefix=prefix, dir=staged_root),
    )
    event.listen(engine, "before_cursor_execute", observe_transaction)
    try:
        with TestClient(app, raise_server_exceptions=False) as second_api, ThreadPoolExecutor(
            max_workers=2,
        ) as executor:
            second_api.cookies.update(api.cookies)
            first = executor.submit(upload, api, project_id, supplier_id, winner_bytes)
            assert first_stored.wait(timeout=15), "First request did not hold the transaction"
            second = executor.submit(upload, second_api, project_id, supplier_id, loser_bytes)
            try:
                assert second_transaction_attempt.wait(timeout=15), (
                    f"Second request did not overlap: observed={len(transaction_connections)}, "
                    f"second_done={second.done()}, "
                    f"second_result={second.result() if second.done() else None}"
                )
                assert not first.done()
                assert not second.done()
            finally:
                release_first.set()
            winning_response = first.result(timeout=15)
            losing_response = second.result(timeout=15)
    finally:
        release_first.set()
        event.remove(engine, "before_cursor_execute", observe_transaction)

    assert transaction_connections[0] is not transaction_connections[1]
    assert winning_response.status_code == 201, winning_response.text
    assert losing_response.status_code == 409, losing_response.text
    assert losing_response.json()["error"]["code"] == (
        "DUPLICATE_PDF" if same_pdf else "QUOTE_ALREADY_EXISTS"
    )
    with Session(engine) as database_session:
        quotes = database_session.scalars(select(Quote)).all()
        documents = database_session.scalars(select(QuoteDocument)).all()
        assert len(quotes) == len(documents) == 1
        assert documents[0].quote_id == quotes[0].id
        assert documents[0].sha256 == hashlib.sha256(winner_bytes).hexdigest()
        stored_file = storage.root / documents[0].storage_key
        assert stored_file.read_bytes() == winner_bytes
    assert list(storage.root.rglob("*.pdf")) == [stored_file]
    assert list(storage.root.rglob("*.part")) == []
    assert list(staged_root.iterdir()) == []


def test_concurrent_manual_and_pdf_creation_keeps_one_quote(
    storage_client: tuple[TestClient, LocalDocumentStorage], engine: Engine, tmp_path: Path,
) -> None:
    api, storage = storage_client
    project_id, supplier_id, _ = setup_shortlist(api)
    source = tmp_path / "quote.pdf"
    source.write_bytes(pdf_bytes())
    def create_pdf() -> str:
        with Session(engine) as database_session:
            project = database_session.get(Project, UUID(project_id))
            assert project is not None
            try:
                store_pdf_quote(
                    database_session, project, UUID(supplier_id), path=source,
                    filename="quote.pdf", sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    page_count=1, storage=storage,
                )
                return "created"
            except PdfUploadError:
                database_session.rollback()
                return "conflict"
    def create_manual() -> str:
        with Session(engine) as database_session:
            project = database_session.get(Project, UUID(project_id))
            assert project is not None
            try:
                create_manual_quote(database_session, project, UUID(supplier_id), {}, None)
                database_session.commit()
                return "created"
            except QuoteWorkflowError:
                database_session.rollback()
                return "conflict"
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [executor.submit(create_pdf), executor.submit(create_manual)]
        assert sorted(future.result() for future in outcomes) == ["conflict", "created"]
    with Session(engine) as database_session:
        quotes = database_session.scalars(select(Quote).where(Quote.project_id == UUID(project_id))).all()
        assert len(quotes) == 1
        documents = database_session.scalars(select(QuoteDocument)).all()
        assert len(documents) == (1 if quotes[0].entry_type == "PDF" else 0)
