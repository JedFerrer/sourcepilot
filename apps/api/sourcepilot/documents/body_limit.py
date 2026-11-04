"""Bound HTTP request bytes before JSON or multipart parsing."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from sourcepilot.api_errors import error_response
from sourcepilot.documents.settings import document_settings_from_environment
from sourcepilot.session.settings import positive_integer_from_environment


class UploadBodyLimitMiddleware:
    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Callable[..., Awaitable[Any]],
                       send: Callable[..., Awaitable[None]]) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "").rstrip("/")
        is_upload = scope.get("method") == "POST" and (
            path.startswith("/projects/") and path.endswith("/quotes/upload")
        )
        limit = (document_settings_from_environment().max_request_bytes if is_upload else
                 positive_integer_from_environment("API_MAX_REQUEST_BYTES", 1_000_000))
        code = "UPLOAD_TOO_LARGE" if is_upload else "REQUEST_TOO_LARGE"
        message_text = "Upload request is too large." if is_upload else "Request body is too large."
        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > limit:
            await error_response(413, code=code, message=message_text)(
                scope, receive, send
            )
            return
        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                await error_response(413, code=code, message=message_text)(
                    scope, receive, send
                )
                return
            body.extend(chunk)
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
