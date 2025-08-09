"""Core models scaffolding (to be implemented in Phase 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    path: str = Field(description="Relative or absolute path of the source file")
    bytes: int = Field(ge=0, description="Size of the included snippet or file")
    score: float | None = Field(default=None, ge=0.0, le=1.0, description="Optional selection score")


class UsecaseInput(BaseModel):
    """Base class for use case inputs."""

    class Config:
        arbitrary_types_allowed = True


class UsecaseOutput(BaseModel):
    """Base class for use case outputs."""

    class Config:
        arbitrary_types_allowed = True


JsonFormat = Literal["pretty", "json", "yaml"]  # placeholder for later use
