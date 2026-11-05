from __future__ import annotations

import asyncio
import os
import ssl
import sys
from dataclasses import dataclass
from functools import cache
from typing import Any, Protocol, cast

import httpx
from openai import AsyncOpenAI, OpenAI
from openai.resources.responses import AsyncResponses
from openai.types.responses import ResponseInputParam, ToolParam
from sqlalchemy.util import await_only

from sourcepilot.comparison.deadline import ComparisonDeadlineError, current_deadline

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
SOURCEPILOT_AI_MODEL_ENV = "SOURCEPILOT_AI_MODEL"


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

    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


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
        try:
            # Outer request cancellation covers response body consumption and
            # SDK cleanup too. Per-attempt timeout cannot reset the total budget.
            tls, platform = prepare_comparison_transport()
            from sourcepilot.comparison.execution import cleanup_attempt

            client = AsyncOpenAI(api_key=self._settings.api_key, max_retries=0,
                                 timeout=seconds, http_client=httpx.AsyncClient(verify=tls))
            # Installed SDK otherwise probes the OS in an executor on each new client.
            # This comparison-only cache is primed at startup, never with user data.
            client._platform = platform  # type: ignore[assignment]
            try:
                deadline.check()
                async with asyncio.timeout(seconds):
                    response = await AsyncResponses(client).create(
                        model=self.model, instructions=instructions,
                        input=cast(ResponseInputParam, input_items),
                        tools=cast(list[ToolParam], tools), store=False, text={"format": {
                            "type": "json_schema", "name": schema_name,
                            "strict": True, "schema": schema,
                        }},
                    )
            finally:
                interrupted = isinstance(sys.exception(), asyncio.CancelledError)
                if not await cleanup_attempt("provider", client, client.close, deadline) and not interrupted:
                    raise ComparisonDeadlineError("Comparison provider cleanup incomplete.")
            deadline.check()
        except asyncio.CancelledError:
            raise
        except ComparisonDeadlineError:
            raise
        except Exception as error:
            deadline.check()
            status_code = getattr(error, "status_code", None)
            retryable = status_code is None or status_code in {408, 409, 429}
            if isinstance(status_code, int) and status_code >= 500:
                retryable = True
            raise ModelProviderError("Comparison model request failed.", retryable=retryable) from error
        usage = getattr(response, "usage", None)
        return AnalystModelInvocation(
            output_text=response.output_text or "",
            output_items=tuple(item.model_dump(exclude_none=True) for item in response.output),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
