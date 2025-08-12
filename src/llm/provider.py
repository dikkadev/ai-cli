from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, Iterator, Callable
from collections.abc import Iterable

from pydantic import BaseModel

T_Output = TypeVar("T_Output", bound=BaseModel)


@dataclass(slots=True)
class ProviderResponse(Generic[T_Output]):
    output: T_Output
    raw: Any | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None


class Provider:
    """Abstract interface for LLM providers that produce structured outputs.

    Concrete providers should implement `generate_structured` and optionally `generate_structured_streaming`.
    """

    def generate_structured(self, *, prompt: str, response_model: type[T_Output]) -> ProviderResponse[T_Output]:
        raise NotImplementedError
    
    def generate_structured_streaming(
        self, 
        *, 
        prompt: str, 
        response_model: type[T_Output],
        progress_callback: Callable[[str], None] | None = None
    ) -> ProviderResponse[T_Output]:
        """Generate structured output with streaming support and progress updates."""
        # Default implementation falls back to non-streaming
        return self.generate_structured(prompt=prompt, response_model=response_model)
