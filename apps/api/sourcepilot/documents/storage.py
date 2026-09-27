"""Private storage of original PDF bytes."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

import boto3

from sourcepilot.documents.settings import DocumentSettings

logger = logging.getLogger(__name__)


class DocumentStorage(Protocol):
    def put(self, key: str, source: Path) -> None: ...
    def delete(self, key: str) -> None: ...


def new_storage_key() -> str:
    return f"quote-pdfs/{uuid4().hex}.pdf"


def _valid_key(key: str) -> bool:
    prefix = "quote-pdfs/"
    suffix = key.removeprefix(prefix)
    return key.startswith(prefix) and len(suffix) == 36 and suffix.endswith(".pdf") and all(
        character in "0123456789abcdef" for character in suffix[:-4]
    )


class LocalDocumentStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        if not _valid_key(key):
            raise ValueError("Invalid document storage key.")
        return self.root / key

    def put(self, key: str, source: Path) -> None:
        destination = self._path(key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(f"{destination.name}.{uuid4().hex}.part")
        try:
            with source.open("rb") as original, partial.open("xb") as output:
                while chunk := original.read(1024 * 1024):
                    output.write(chunk)
            os.replace(partial, destination)
        finally:
            try:
                partial.unlink(missing_ok=True)
            except OSError as error:
                logger.error(
                    "PDF partial cleanup failed for owned key %s, partial file %s (%s)",
                    key, partial.name, type(error).__name__,
                )

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3DocumentStorage:
    def __init__(self, bucket: str, *, endpoint_url: str | None = None,
                 region: str | None = None, client: Any = None) -> None:
        self.bucket = bucket
        self.client = client or boto3.client("s3", endpoint_url=endpoint_url, region_name=region)

    def put(self, key: str, source: Path) -> None:
        if not _valid_key(key):
            raise ValueError("Invalid document storage key.")
        with source.open("rb") as original:
            self.client.put_object(
                Bucket=self.bucket, Key=key, Body=original, ContentType="application/pdf"
            )

    def delete(self, key: str) -> None:
        if not _valid_key(key):
            raise ValueError("Invalid document storage key.")
        self.client.delete_object(Bucket=self.bucket, Key=key)


def storage_from_settings(settings: DocumentSettings) -> DocumentStorage:
    if settings.backend == "local":
        return LocalDocumentStorage(settings.local_directory)
    assert settings.s3_bucket is not None
    return S3DocumentStorage(
        settings.s3_bucket, endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
    )
