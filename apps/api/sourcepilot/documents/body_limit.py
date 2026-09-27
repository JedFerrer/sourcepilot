"""Bound upload request bytes before Starlette's multipart parser runs."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sourcepilot.api_errors import error_response
from sourcepilot.documents.settings import document_settings_from_environment


class UploadBodyLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]],
                       send: Callable[..., Awaitable[None]]) -> None:
        path = scope.get("path", "")
        if scope["type"] != "http" or scope.get("method") != "POST" or not (
            path.startswith("/projects/") and path.endswith("/quotes/upload")
        ):
            await self.app(scope, receive, send)
            return
        limit = document_settings_from_environment().max_request_bytes
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > limit:
            await error_response(413, code="UPLOAD_TOO_LARGE", message="Upload request is too large.")(
                scope, receive, send
            )
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            body.extend(message.get("body", b""))
            if len(body) > limit:
                await error_response(413, code="UPLOAD_TOO_LARGE", message="Upload request is too large.")(
                    scope, receive, send
                )
                return
            if not message.get("more_body", False):
                break
        delivered = False

        async def replay() -> dict[str, Any]:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return {"type": "http.disconnect"}

        await self.app(scope, replay, send)
