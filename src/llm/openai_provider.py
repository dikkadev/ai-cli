"""OpenAI provider scaffolding (to be implemented in Phase 2)."""

from __future__ import annotations

from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from .provider import Provider, ProviderResponse

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(Provider):
    def __init__(self, client: OpenAI | None = None, *, model: str = "gpt-4o-mini") -> None:
        self._client = client or OpenAI()
        self._model = model

    def generate_structured(self, *, prompt: str, response_model: type[T]) -> ProviderResponse[T]:
        schema = response_model.model_json_schema()
        # Using responses.create with structured outputs; adapt as needed when updating SDKs
        result = self._client.responses.create(
            model=self._model,
            input=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": {"name": "Output", "schema": schema}},
        )
        # The shape of result.output_text or result.parsed may vary; keep robust parsing
        raw = result.dict() if hasattr(result, "dict") else result
        text = None
        try:
            # Fallback to first text output if present
            text = result.output_text  # type: ignore[attr-defined]
        except Exception:
            pass
        data: Any
        if text:
            data = response_model.model_validate_json(text)
        else:
            # If a parsed field exists, try it
            parsed = getattr(result, "parsed", None)
            if parsed is not None:
                data = response_model.model_validate(parsed)
            else:
                # Last resort: find a candidate in generic fields
                raise RuntimeError("Unable to parse structured response from OpenAI result")
        return ProviderResponse(output=data, raw=raw, model=self._model, usage=getattr(result, "usage", None))
