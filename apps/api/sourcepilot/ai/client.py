from __future__ import annotations

import asyncio
import os
import ssl
import sys
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol, cast

import httpx
from httpx import ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout
from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, OpenAI
from openai.resources.responses import AsyncResponses
from openai.types.responses import ResponseInputParam, ToolParam
from sqlalchemy.util import await_only

from sourcepilot.comparison.deadline import (
    ComparisonDeadline,
    ComparisonDeadlineError,
    TimeoutDiagnostics,
    current_deadline,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
SOURCEPILOT_AI_MODEL_ENV = "SOURCEPILOT_AI_MODEL"

PROVIDER_CATEGORIES = frozenset({
    "AUTHENTICATION", "PERMISSION", "NOT_FOUND", "INVALID_REQUEST", "RATE_LIMIT",
    "SERVER_ERROR", "TIMEOUT", "CONNECTION", "LOCAL_CLIENT_ERROR", "UNKNOWN",
})
PROVIDER_STATUSES = frozenset({
    "400", "401", "403", "404", "408", "409", "422", "429", "OTHER_HTTP", "NO_HTTP_STATUS",
}) | frozenset(str(status) for status in range(500, 600))
PROVIDER_CODES = frozenset({
    "invalid_api_key", "permission_denied", "model_not_found", "invalid_json_schema",
    "unsupported_parameter", "invalid_value", "missing_required_parameter",
    "rate_limit_exceeded", "insufficient_quota", "server_error", "internal_server_error", "UNKNOWN",
})


@dataclass(frozen=True)
class ProviderDiagnostics:
    """Only finite labels can cross the provider diagnostic boundary."""

    category: str = "UNKNOWN"
    status: str = "NO_HTTP_STATUS"
    code: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for name, allowed, fallback in (
            ("category", PROVIDER_CATEGORIES, "UNKNOWN"),
            ("status", PROVIDER_STATUSES, "NO_HTTP_STATUS"),
            ("code", PROVIDER_CODES, "UNKNOWN"),
        ):
            value = getattr(self, name)
            if type(value) is not str or value not in allowed:
                object.__setattr__(self, name, fallback)


def comparison_provider_diagnostics(error: Exception) -> ProviderDiagnostics:
    # Inspect only SDK-owned parsed attributes, never messages, responses or causes.
    if isinstance(error, APIStatusError):
        status = vars(error).get("status_code")
        code = vars(error).get("code")
        label = "NO_HTTP_STATUS"
        category = "UNKNOWN"
        if type(status) is int and 100 <= status <= 599:
            label = str(status) if str(status) in PROVIDER_STATUSES else "OTHER_HTTP"
            category = {
                400: "INVALID_REQUEST", 401: "AUTHENTICATION", 403: "PERMISSION",
                404: "NOT_FOUND", 408: "TIMEOUT", 422: "INVALID_REQUEST", 429: "RATE_LIMIT",
            }.get(status, "SERVER_ERROR" if status >= 500 else "UNKNOWN")
        return ProviderDiagnostics(category, label, code if type(code) is str else "UNKNOWN")
    if isinstance(error, (APITimeoutError, TimeoutError)):
        return ProviderDiagnostics(category="TIMEOUT")
    if isinstance(error, APIConnectionError):
        return ProviderDiagnostics(category="CONNECTION")
    if isinstance(error, (TypeError, ValueError)):
        return ProviderDiagnostics(category="LOCAL_CLIENT_ERROR")
    return ProviderDiagnostics()


class AttemptObservation:
    """Bounded state owned by one invocation; callback payloads are never inspected."""

    def __init__(self) -> None:
        self.phase = "UNKNOWN"
        self.state = "UNKNOWN"
        self.frozen: TimeoutDiagnostics | None = None

    async def request(self, request: httpx.Request) -> None:
        try:
            self.phase = self.state = "UNKNOWN"
            request.extensions["trace"] = self.trace
        except Exception:  # noqa: BLE001 - optional observation must not affect transport
            self.phase = self.state = "UNKNOWN"

    def install(self, client: httpx.AsyncClient) -> None:
        try:
            client.event_hooks["request"].append(self.request)
        except Exception:  # noqa: BLE001 - optional observation must not affect transport
            self.phase = self.state = "UNKNOWN"

    def observe(self, event: str) -> None:
        if self.frozen is not None:
            return
        if type(event) is not str:
            self.phase = self.state = "UNKNOWN"
            return
        operation, separator, state = event.rpartition(".")
        phases = {
            "connection.connect_tcp": "CONNECT_TCP", "connection.start_tls": "START_TLS",
            **{f"{protocol}.{name}": name.upper()
               for protocol in ("http11", "http2") for name in (
                   "send_request_headers", "send_request_body",
                   "receive_response_headers", "receive_response_body",
               )},
        }
        # Closing a response is bookkeeping, not the last request I/O operation.
        if operation in {"http11.response_closed", "http2.response_closed"}:
            return
        if separator and operation in phases and state in {"started", "complete", "failed"}:
            self.phase, self.state = phases[operation], state.upper()
        else:
            self.phase = self.state = "UNKNOWN"

    async def trace(self, event: str, info: dict[str, Any]) -> None:
        try:
            self.observe(event)
        except Exception:  # noqa: BLE001 - never replace an I/O result with observation failure
            if self.frozen is None:
                self.phase = self.state = "UNKNOWN"

    def freeze(self, error: BaseException, deadline: ComparisonDeadline,
               attempt: asyncio.Timeout | None = None) -> TimeoutDiagnostics:
        if self.frozen is not None:
            return self.frozen
        try:
            origin = "UNKNOWN"
            if isinstance(error, APITimeoutError):
                # Exactly one trusted SDK cause type; never inspect its attributes/text.
                origin = next((label for kind, label in (
                    (ConnectTimeout, "SDK_CONNECT"), (ReadTimeout, "SDK_READ"),
                    (WriteTimeout, "SDK_WRITE"), (PoolTimeout, "SDK_POOL"),
                ) if isinstance(error.__cause__, kind)), "SDK_UNKNOWN")
            elif isinstance(error, (ComparisonDeadlineError, asyncio.CancelledError)):
                origin = deadline.timeout_origin()
            elif isinstance(error, TimeoutError):
                if attempt is not None and attempt.expired():
                    origin = deadline.timeout_origin()
                    if origin == "UNKNOWN":
                        origin = "APP_ATTEMPT"
            else:
                origin = "NOT_APPLICABLE"
            self.frozen = TimeoutDiagnostics(origin, self.phase, self.state)
        except Exception:  # noqa: BLE001 - preserve the original exception
            self.frozen = TimeoutDiagnostics()
        return self.frozen

    def cleanup_expired(self, deadline: ComparisonDeadline) -> None:
        if self.frozen is None:
            origin = deadline.timeout_origin()
            self.frozen = TimeoutDiagnostics(
                "APP_TOTAL_BUDGET" if origin == "APP_TOTAL_BUDGET" else "APP_CLEANUP_BUDGET",
                self.phase, self.state,
            )


@cache
def prepare_comparison_transport() -> tuple[ssl.SSLContext, str]:
    """Credential-free startup work; no connection or provider request is made."""
    from openai import __version__, _base_client
    from openai.resources.responses.responses import AsyncResponses as ResponsesResource
    from psycopg import pq
    from sqlalchemy.dialects.postgresql.psycopg import PGDialectAsync_psycopg

    if pq.version() < 170000:
        raise RuntimeError("Comparison requires libpq 17+ nonblocking cancellation support.")
    # Materialize SDK resource imports/headers and TLS roots before admitting work.
    assert ResponsesResource and PGDialectAsync_psycopg
    platform = _base_client.get_platform()
    _base_client.platform_headers(__version__, platform=platform)
    return httpx.create_ssl_context(), str(platform)


@dataclass(frozen=True)
class AISettings:
    api_key: str
    model: str


@dataclass(frozen=True)
class ModelInvocation:
    output_text: str
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class AnalystModelInvocation:
    """One Responses turn, including opaque output items for the next turn."""

    output_text: str
    output_items: tuple[dict[str, Any], ...]
    input_tokens: int | None
    output_tokens: int | None


class ModelProviderError(RuntimeError):
    """A normalized model-provider failure with retryability information."""

    def __init__(
        self, message: str, *, retryable: bool, diagnostics: ProviderDiagnostics | None = None,
        timeout_diagnostics: TimeoutDiagnostics | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.diagnostics = diagnostics or ProviderDiagnostics()
        self.timeout_diagnostics = timeout_diagnostics or TimeoutDiagnostics()


class StructuredModelClient(Protocol):
    model: str

    def invoke(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> ModelInvocation: ...

    def invoke_with_tools(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> AnalystModelInvocation: ...


def ai_settings_from_environment() -> AISettings:
    """Read AI configuration only immediately before a provider invocation."""
    api_key = os.environ.get(OPENAI_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(f"{OPENAI_API_KEY_ENV} must be set for AI operations.")
    model = os.environ.get(SOURCEPILOT_AI_MODEL_ENV)
    if not model:
        raise RuntimeError(f"{SOURCEPILOT_AI_MODEL_ENV} must be set for AI operations.")
    return AISettings(api_key=api_key, model=model)


class OpenAIResponsesClient:
    """Official Responses API wrapper kept narrow enough to replace in tests."""

    def __init__(self, settings: AISettings) -> None:
        self._settings = settings
        self.model = settings.model
        self._client = None if current_deadline.get() is not None else OpenAI(api_key=settings.api_key)

    @classmethod
    def from_environment(cls) -> OpenAIResponsesClient:
        return cls(ai_settings_from_environment())

    def invoke(
        self,
        *,
        instructions: str,
        input_text: str,
        schema_name: str,
        schema: dict[str, Any],
    ) -> ModelInvocation:
        assert self._client is not None
        try:
            response = cast(Any, self._client.responses.create(
                model=self.model,
                instructions=instructions,
                input=input_text,
                store=False,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                },
            ))
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            retryable = status_code is None or status_code == 408 or status_code == 409 or status_code == 429
            if isinstance(status_code, int) and status_code >= 500:
                retryable = True
            raise ModelProviderError(str(error), retryable=retryable) from error

        usage = getattr(response, "usage", None)
        return ModelInvocation(
            output_text=response.output_text,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )

    def invoke_with_tools(
        self,
        *,
        instructions: str,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        schema_name: str,
        schema: dict[str, Any],
    ) -> AnalystModelInvocation:
        deadline = current_deadline.get()
        if deadline is not None:
            return await_only(self._invoke_comparison(
                instructions=instructions, input_items=input_items, tools=tools,
                schema_name=schema_name, schema=schema,
            ))
        assert self._client is not None
        try:
            response = cast(Any, cast(Any, self._client.responses).create(
                model=self.model,
                instructions=instructions,
                input=input_items,
                tools=tools,
                store=False,
                text={"format": {
                    "type": "json_schema", "name": schema_name,
                    "strict": True, "schema": schema,
                }},
            ))
        except Exception as error:
            status_code = getattr(error, "status_code", None)
            retryable = status_code is None or status_code in {408, 409, 429}
            if isinstance(status_code, int) and status_code >= 500:
                retryable = True
            raise ModelProviderError(str(error), retryable=retryable) from error

        usage = getattr(response, "usage", None)
        return AnalystModelInvocation(
            output_text=response.output_text or "",
            output_items=tuple(item.model_dump(exclude_none=True) for item in response.output),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )

    async def _invoke_comparison(
        self, *, instructions: str, input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]], schema_name: str, schema: dict[str, Any],
    ) -> AnalystModelInvocation:
        deadline = current_deadline.get()
        assert deadline is not None
        seconds = deadline.attempt_seconds()
        observation = AttemptObservation()
        attempt: asyncio.Timeout | None = None
        try:
            # Outer request cancellation covers response body consumption and
            # SDK cleanup too. Per-attempt timeout cannot reset the total budget.
            tls, platform = prepare_comparison_transport()
            from sourcepilot.comparison.execution import cleanup_attempt

            http = httpx.AsyncClient(verify=tls)
            observation.install(http)
            client = AsyncOpenAI(api_key=self._settings.api_key, max_retries=0,
                                 timeout=seconds, http_client=http)
            # Installed SDK otherwise probes the OS in an executor on each new client.
            # This comparison-only cache is primed at startup, never with user data.
            client._platform = platform  # type: ignore[assignment]
            try:
                deadline.check()
                async with asyncio.timeout(seconds) as attempt:
                    response = await AsyncResponses(client).create(
                        model=self.model, instructions=instructions,
                        input=cast(ResponseInputParam, input_items),
                        tools=cast(list[ToolParam], tools), store=False, text={"format": {
                            "type": "json_schema", "name": schema_name,
                            "strict": True, "schema": schema,
                        }},
                    )
            except BaseException as error:
                # Freeze while the request context is still attributable, before close.
                snapshot = observation.freeze(error, deadline, attempt)
                if isinstance(error, (asyncio.CancelledError, ComparisonDeadlineError)):
                    setattr(error, "timeout_diagnostics", snapshot)  # noqa: B010 - cancellation metadata
                raise
            finally:
                interrupted = isinstance(sys.exception(), asyncio.CancelledError)
                if not await cleanup_attempt(
                    "provider", client, client.close, deadline,
                    on_timeout=lambda: observation.cleanup_expired(deadline),
                ) and not interrupted:
                    raise ComparisonDeadlineError("Comparison provider cleanup incomplete.")
            deadline.check()
        except asyncio.CancelledError:
            raise
        except ComparisonDeadlineError as error:
            error.timeout_diagnostics = observation.freeze(error, deadline, attempt)
            raise
        except Exception as error:
            snapshot = observation.freeze(error, deadline, attempt)
            try:
                deadline.check()
            except ComparisonDeadlineError as expired:
                # Terminal budget expiry does not erase the earlier attempt's evidence.
                expired.timeout_diagnostics = snapshot
                raise
            status_code = getattr(error, "status_code", None)
            retryable = status_code is None or status_code in {408, 409, 429}
            if isinstance(status_code, int) and status_code >= 500:
                retryable = True
            raise ModelProviderError(
                "Comparison model request failed.", retryable=retryable,
                diagnostics=comparison_provider_diagnostics(error),
                timeout_diagnostics=snapshot,
            ) from error
        usage = getattr(response, "usage", None)
        return AnalystModelInvocation(
            output_text=response.output_text or "",
            output_items=tuple(item.model_dump(exclude_none=True) for item in response.output),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
