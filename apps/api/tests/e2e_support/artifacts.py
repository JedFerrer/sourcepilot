"""Create the only CI-uploadable E2E bundle, removing captured session credentials."""

from __future__ import annotations

import argparse
import base64
import io
import json
import re
from pathlib import Path
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile, is_zipfile

REDACTED = "[REDACTED]"
# The application generates token_urlsafe(32). Also discover arbitrary cookie/token
# values so shorter dummy tokens and future token formats receive the same treatment.
SESSION_TOKEN = re.compile(r"(?<![\w-])[A-Za-z0-9_-]{43}(?![\w-])")
DATA_URI = re.compile(r"data:([\w.+/-]+);base64,([A-Za-z0-9+/=]+)")
ENCODED_FIELD = re.compile(r'("(?:base64|buffer|body)"\s*:\s*")([A-Za-z0-9+/]{16,}={0,2})(")')
RAW_HEADER = re.compile(r"(?im)^(\s*(?:cookie|set-cookie|authorization)\s*:\s*)([^\r\n]+)")
COOKIE_VALUE = re.compile(r"(?:sourcepilot_demo_session|sourcepilot_session)\s*=\s*([^;\s\"'\\<>]+)", re.IGNORECASE)


def sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z]", "", key.lower())
    return normalized in {"cookie", "setcookie", "authorization", "opaquetoken", "accesstoken"} or (
        "session" in normalized and "token" in normalized
    )


def cookie_record(value: dict) -> bool:
    name = str(value.get("name", ""))
    return sensitive_key(name) or name.lower() in {"sourcepilot_demo_session", "sourcepilot_session"}


def credential_values(value: object, in_cookies: bool = False) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if ((sensitive_key(key) or (key == "value" and (in_cookies or cookie_record(value))))
                    and isinstance(child, str) and child):
                found.add(child)
                if key.lower() in {"cookie", "set-cookie"} or str(value.get("name", "")).lower() in {"cookie", "set-cookie"}:
                    parts = child.split(";")
                    if "set-cookie" in {key.lower(), str(value.get("name", "")).lower()}:
                        parts = parts[:1]
                    found.update(part.split("=", 1)[1].strip() for part in parts if "=" in part)
            found.update(credential_values(child, in_cookies or key.lower() == "cookies"))
    elif isinstance(value, list):
        for child in value:
            found.update(credential_values(child, in_cookies))
    elif isinstance(value, str):
        # Playwright API results/attachments can themselves be JSON-encoded strings.
        try:
            decoded = json.loads(value)
        except (ValueError, TypeError):
            pass
        else:
            if isinstance(decoded, (dict, list)):
                found.update(credential_values(decoded, in_cookies))
    return found


def decode_uri(match: re.Match[str]) -> bytes:
    data = base64.b64decode(match[2], validate=True)
    if match[1] == "application/zip" and not is_zipfile(io.BytesIO(data)):
        raise ValueError("Invalid embedded Playwright report archive.")
    return data


def encoded_fields(text: str) -> list[tuple[re.Match[str], bytes]]:
    fields = []
    for match in ENCODED_FIELD.finditer(text):
        if len(match[2]) % 4 == 0:
            fields.append((match, base64.b64decode(match[2], validate=True)))
    return fields


def standalone_base64(text: str) -> bytes | None:
    value = text.strip()
    if len(value) % 4 == 0 and re.fullmatch(r"[A-Za-z0-9+/]{16,}={0,2}", value):
        return base64.b64decode(value, validate=True)
    return None


def zip_bytes(entries: list[tuple[str, bytes]]) -> bytes:
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return output.getvalue()


def unpack(data: bytes) -> list[tuple[str, bytes]] | None:
    if not is_zipfile(io.BytesIO(data)):
        return None
    with ZipFile(io.BytesIO(data)) as archive:
        return [(item.filename, archive.read(item)) for item in archive.infolist() if not item.is_dir()]


def decoded_texts(data: bytes) -> list[str]:
    entries = unpack(data)
    if entries is not None:
        return [name for name, _ in entries] + [text for _, child in entries for text in decoded_texts(child)]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return []
    standalone = standalone_base64(text)
    if standalone is not None:
        return decoded_texts(standalone)
    fields = encoded_fields(text)
    visible = text
    for match, _ in reversed(fields):
        visible = visible[:match.start()] + match[1] + "[encoded artifact]" + match[3] + visible[match.end():]
    texts = [DATA_URI.sub("[embedded artifact]", visible)]
    for _, decoded in fields:
        texts.extend(decoded_texts(decoded))
    for match in DATA_URI.finditer(text):
        texts.extend(decoded_texts(decode_uri(match)))
    return texts


def discover_tokens(data: bytes) -> set[str]:
    found: set[str] = set()
    for text in decoded_texts(data):
        found.update(SESSION_TOKEN.findall(text))
        found.update(COOKIE_VALUE.findall(text))
        for match in RAW_HEADER.finditer(text):
            found.add(match[2])
            parts = match[2].split(";")
            if "set-cookie" in match[1].lower():
                parts = parts[:1]  # Cookie attributes (Path=/, SameSite=Lax) are not secrets.
            found.update(part.split("=", 1)[1].strip() for part in parts if "=" in part)
        # Both JSON documents (storage state, report data) and JSONL trace events.
        for candidate in [text, *text.splitlines()]:
            try:
                found.update(credential_values(json.loads(candidate)))
            except ValueError:
                continue
    return found - {REDACTED, ""}


def representations(token: str) -> set[str]:
    raw = token.encode()
    return {token, quote(token, safe=""), json.dumps(token)[1:-1], raw.hex(),
            base64.b64encode(raw).decode(), base64.urlsafe_b64encode(raw).decode(),
            base64.b64encode(raw).decode().rstrip("="),
            base64.urlsafe_b64encode(raw).decode().rstrip("="),
            "".join(f"\\u{ord(char):04x}" for char in token),
            "".join(f"%{byte:02X}" for byte in raw),
            "".join(f"%{byte:02x}" for byte in raw)}


def sanitize_bundle(inputs: list[tuple[str, Path]], destination: Path) -> None:
    # Remove a prior upload bundle first: any parse/read/sanitization failure must
    # leave nothing uploadable. Raw inputs are never part of the upload path.
    destination.unlink(missing_ok=True)
    entries: list[tuple[str, bytes]] = []
    for prefix, source in inputs:
        if source.is_dir():
            for item in sorted(source.rglob("*")):
                if item.is_file():
                    if item.is_symlink():
                        raise RuntimeError("E2E artifacts must not contain symlinks.")
                    entries.append((f"{prefix}/{item.relative_to(source).as_posix()}", item.read_bytes()))
        elif source.is_file():
            entries.append((prefix, source.read_bytes()))
    raw_bundle = zip_bytes(entries)
    tokens = discover_tokens(raw_bundle)
    variants = sorted({variant for token in tokens for variant in representations(token)}, key=len, reverse=True)

    def scrub(text: str) -> str:
        for variant in variants:
            text = text.replace(variant, REDACTED)
        text = RAW_HEADER.sub(lambda match: match[1] + REDACTED, text)
        return SESSION_TOKEN.sub(REDACTED, text)

    def sanitize(data: bytes) -> bytes:
        nested = unpack(data)
        if nested is not None:
            return zip_bytes([(scrub(name), sanitize(child)) for name, child in nested])
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Screenshots stay useful. Opaque binary attachments are omitted rather
            # than assuming that an unknown compressed format is credential-free.
            if data.startswith((b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")) and not any(
                variant.encode() in data or variant.encode("utf-16-le") in data for variant in variants
            ):
                return data
            return b"[REDACTED binary attachment; diagnostics retained in trace/report]\n"
        standalone = standalone_base64(text)
        if standalone is not None:
            return base64.b64encode(sanitize(standalone))
        # Playwright's buffer/body fields can encode entire attachments or output
        # strings, so replacing only base64(token) would miss offset encodings.
        # Scrub surrounding HTML/JSON without corrupting the newly encoded ZIP.
        embedded = [(match.start(), match.end(), f"data:{match[1]};base64,", "", decode_uri(match))
                    for match in DATA_URI.finditer(text)]
        embedded.extend((match.start(), match.end(), match[1], match[3], decoded)
                        for match, decoded in encoded_fields(text))
        pieces: list[str] = []
        position = 0
        for start, end, prefix, suffix, decoded in sorted(embedded):
            pieces.append(scrub(text[position:start]))
            pieces.append(prefix + base64.b64encode(sanitize(decoded)).decode() + suffix)
            position = end
        pieces.append(scrub(text[position:]))
        return "".join(pieces).encode()

    sanitized = sanitize(raw_bundle)
    # Verify decompressed entries, including HTML's embedded report ZIP, rather
    # than scanning only the outer compressed bytes.
    for text in decoded_texts(sanitized):
        if any(variant in text for variant in variants):
            raise RuntimeError("Credential survived E2E artifact sanitization.")
    if discover_tokens(sanitized):
        raise RuntimeError("Captured credential representation survived E2E sanitization.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(sanitized)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["golden", "targeted", "regression"])
    parser.add_argument("--web-directory", type=Path)
    arguments = parser.parse_args()
    stage = arguments.stage
    web = arguments.web_directory or Path(__file__).resolve().parents[3] / "web"
    sanitize_bundle([
        ("playwright-report", web / "playwright-report"),
        ("test-results", web / "test-results"),
        (f"e2e-logs/{stage}.log", web / "e2e-logs" / f"{stage}.log"),
    ], web / "e2e-upload" / stage / "diagnostics.zip")
    print(f"Sanitized {stage} E2E diagnostics are ready for upload.")


if __name__ == "__main__":
    main()
