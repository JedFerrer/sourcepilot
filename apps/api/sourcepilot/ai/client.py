from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, cast

from openai import OpenAI

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
SOURCEPILOT_AI_MODEL_ENV = "SOURCEPILOT_AI_MODEL"


@dataclass(frozen=True)
class AISettings:
    api_key: str
    model: str


@dataclass(frozen=True)
class ModelInvocation:
    output_text: str
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
        self.model = settings.model
        self._client = OpenAI(api_key=settings.api_key)

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
