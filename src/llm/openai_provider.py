"""OpenAI provider scaffolding (to be implemented in Phase 2)."""

from __future__ import annotations

import json
import time
from typing import Any, TypeVar, Callable

from openai import OpenAI
from pydantic import BaseModel

from .provider import Provider, ProviderResponse

T = TypeVar("T", bound=BaseModel)


class OpenAIProvider(Provider):
    def __init__(self, client: OpenAI | None = None, *, model: str = "gpt-5-mini") -> None:
        self._client = client or OpenAI()
        self._model = model

    def generate_structured(self, *, prompt: str, response_model: type[T]) -> ProviderResponse[T]:
        schema = response_model.model_json_schema()
        # Using chat completions with structured outputs
        result = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": {"name": "Output", "schema": schema}},
        )
        # Extract the response data
        raw = result.model_dump() if hasattr(result, "model_dump") else result
        message = result.choices[0].message
        
        # Parse the structured response
        data: Any
        if hasattr(message, 'parsed') and message.parsed:
            data = response_model.model_validate(message.parsed)
        elif message.content:
            data = response_model.model_validate_json(message.content)
        else:
            raise RuntimeError("Unable to parse structured response from OpenAI result")
            
        return ProviderResponse(output=data, raw=raw, model=self._model, usage=result.usage)
    
    def generate_structured_streaming(
        self, 
        *, 
        prompt: str, 
        response_model: type[T],
        progress_callback: Callable[[str], None] | None = None
    ) -> ProviderResponse[T]:
        """Generate structured output with streaming and progress updates."""
        schema = response_model.model_json_schema()
        
        if progress_callback:
            progress_callback("🤖 Contacting OpenAI...")
        
        try:
            # First try with structured outputs (non-streaming for structured responses)
            if progress_callback:
                progress_callback(f"🧠 Processing with {self._model}...")
            
            result = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_schema", "json_schema": {"name": "Output", "schema": schema}},
            )
            
            if progress_callback:
                progress_callback("✨ Parsing response...")
            
            # Extract the response data (same as non-streaming)
            raw = result.model_dump() if hasattr(result, "model_dump") else result
            message = result.choices[0].message
            
            # Parse the structured response
            data: Any
            if hasattr(message, 'parsed') and message.parsed:
                data = response_model.model_validate(message.parsed)
            elif message.content:
                data = response_model.model_validate_json(message.content)
            else:
                raise RuntimeError("Unable to parse structured response from OpenAI result")
                
            if progress_callback:
                progress_callback("✅ Complete!")
                
            return ProviderResponse(output=data, raw=raw, model=self._model, usage=result.usage)
            
        except Exception as e:
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}")
            raise
