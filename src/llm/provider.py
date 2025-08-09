from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

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

    Concrete providers should implement `generate_structured`.
    """

    def generate_structured(self, *, prompt: str, response_model: type[T_Output]) -> ProviderResponse[T_Output]:
        raise NotImplementedError
