"""Regression checks of decompressed contents of the actual uploadable bundle."""

import base64
import io
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from tests.e2e_support.artifacts import (
    REDACTED,
    decoded_texts,
    representations,
    sanitize_bundle,
    zip_bytes,
)

DUMMY_TOKEN = "M5U3_DUMMY_" + "x" * 32


def assert_token_absent(bundle: Path) -> list[str]:
    texts = decoded_texts(bundle.read_bytes())
    for variant in representations(DUMMY_TOKEN):
        assert all(variant not in text for text in texts), "Credential present in uploadable artifact"
    return texts


def test_upload_bundle_sanitizes_headers_storage_reports_and_encoded_attachments(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    trace = zip_bytes([("trace.network", (json.dumps({
        "request": {"headers": [{"name": "Cookie", "value": f"sourcepilot_demo_session={DUMMY_TOKEN}"}]},
        "response": {"status": 503, "headers": [{"name": "Set-Cookie", "value": f"sourcepilot_demo_session={DUMMY_TOKEN}; Path=/; HttpOnly"}]},
    }) + "\n").encode()), ("trace.trace", json.dumps({
        "type": "after", "error": "Comparison stage probe failure", "duration": 15,
        "storageState": {"cookies": [{"name": "sourcepilot_demo_session", "value": DUMMY_TOKEN}]},
        "sessionToken": DUMMY_TOKEN,
    }).encode())])
    (raw / "trace.zip").write_bytes(trace)
    # Playwright embeds a compressed report ZIP in its HTML in addition to copies
    # of traces/attachments under report/data and test-results.
    report = zip_bytes([("report.json", json.dumps({
        "errors": ["Comparison stage probe failure"], "opaque_token": DUMMY_TOKEN,
    }).encode()), ("data/trace.zip", trace)])
    (raw / "index.html").write_text('<script>window.playwrightReportBase64="data:application/zip;base64,'
        + base64.b64encode(report).decode() + '"</script>')
    (raw / "attachment.txt").write_text(
        f"Cookie: sourcepilot_demo_session={DUMMY_TOKEN}\n"
        f"Set-Cookie: sourcepilot_demo_session={DUMMY_TOKEN}; Path=/; HttpOnly\n"
        + "\n".join(representations(DUMMY_TOKEN))
    )
    (raw / "encoded.json").write_text(json.dumps({"content": "data:application/json;base64,"
        + base64.b64encode(json.dumps({"session_token": DUMMY_TOKEN}).encode()).decode()}))
    (raw / "encoded-buffers.json").write_text(json.dumps({
        "attachments": [{"body": base64.b64encode(json.dumps({"cookies": [
            {"name": "sourcepilot_demo_session", "value": DUMMY_TOKEN}
        ]}).encode()).decode()}],
        "stdout": {"buffer": base64.b64encode(("prefixed log: " + DUMMY_TOKEN).encode()).decode()},
    }))
    (raw / "base64-attachment.txt").write_text(base64.b64encode(
        json.dumps({"opaque_token": DUMMY_TOKEN}).encode()).decode())
    (raw / "opaque.gz").write_bytes(b"\x1f\x8b" + DUMMY_TOKEN.encode())
    screenshot = b"\x89PNG\r\n\x1a\n\x80diagnostic screenshot"
    (raw / "failure.png").write_bytes(screenshot)
    destination = tmp_path / "upload" / "diagnostics.zip"
    sanitize_bundle([("test-results", raw)], destination)
    texts = assert_token_absent(destination)
    assert any("Comparison stage probe failure" in text for text in texts)
    assert any('"status": 503' in text for text in texts)
    assert any('"duration": 15' in text for text in texts)
    assert any(REDACTED in text for text in texts)
    with ZipFile(destination) as archive:
        assert archive.read("test-results/failure.png") == screenshot


def test_unreadable_archive_fails_without_uploadable_output(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "index.html").write_text('data:application/zip;base64,notvalid=')
    destination = tmp_path / "diagnostics.zip"
    destination.write_bytes(b"stale upload must not survive")
    with pytest.raises(ValueError):
        sanitize_bundle([("playwright-report", raw)], destination)
    assert not destination.exists()


def verify_playwright_probe(web: Path) -> None:
    raw = [(name.as_posix(), name.read_bytes()) for directory in ("test-results", "playwright-report")
           for name in (web / directory).rglob("*") if name.is_file()]
    raw_texts = decoded_texts(zip_bytes(raw))
    assert any(DUMMY_TOKEN in text for text in raw_texts), "Probe did not actually capture a token"
    assert any('"name":"Set-Cookie"' in text or '"name":"set-cookie"' in text for text in raw_texts)
    assert any('"name":"Cookie"' in text or '"name":"cookie"' in text for text in raw_texts)
    destination = web / "e2e-upload" / "regression" / "diagnostics.zip"
    texts = assert_token_absent(destination)
    assert any("Artifact security probe failure" in text for text in texts)
    assert any('"type":"before"' in text for text in texts)
    assert any('"status":200' in text for text in texts)
    with ZipFile(destination) as archive:
        assert any(name.endswith("trace.zip") for name in archive.namelist())
        assert any(name.endswith(".png") for name in archive.namelist())
        assert any(name.endswith("index.html") for name in archive.namelist())
        # The sanitized trace remains valid JSONL, not merely a credential-free blob.
        traces = [archive.read(name) for name in archive.namelist() if name.endswith("trace.zip")]
        for trace in traces:
            with ZipFile(io.BytesIO(trace)) as trace_archive:
                for name in trace_archive.namelist():
                    if name.endswith((".trace", ".network")):
                        for line in trace_archive.read(name).decode().splitlines():
                            json.loads(line)
        archive.extractall(web / "sanitized-preview")
    print("Actual Playwright failure upload bundle contains no dummy credential; diagnostics retained.")


if __name__ == "__main__":
    verify_playwright_probe(Path(sys.argv[1]))
