from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from core.blacklist import Blacklist
from core.context import ContextCaps, collect_paths
from core.models import SourceRef, UsecaseInput, UsecaseOutput
from core.sandbox import SandboxMode


@dataclass
class UsecaseMetadata:
    id: str
    summary: str
    sandbox: SandboxMode
    allows_writes: bool
    default_context: list[str] = field(default_factory=list)


def usecase(**kwargs):
    """Decorator to register use case metadata."""
    def decorator(cls):
        cls._metadata = UsecaseMetadata(**kwargs)
        return cls
    return decorator


class AskInput(UsecaseInput):
    query: str = Field(description="Question to ask")
    style: Literal["plain", "summary", "bullets"] = Field(default="plain", description="Answer style")
    use_context: bool = Field(default=False, description="Include local context in the prompt")
    context_paths: list[str] = Field(default_factory=list, description="Paths to include as context")


class AskOutput(UsecaseOutput):
    answer: str = Field(description="The answer to the question")
    sources: list[SourceRef] = Field(default_factory=list, description="Sources used")


@usecase(
    id="ask",
    summary="Answer a question with optional local context",
    sandbox=SandboxMode.FULL,
    allows_writes=False,
    default_context=["README.md", "*.md"],
)
class Ask:
    InputModel = AskInput
    OutputModel = AskOutput

    @staticmethod
    def execute(input_data: AskInput, provider, project_root: Path) -> AskOutput:
        context_text = ""
        sources = []
        
        if input_data.use_context or input_data.context_paths:
            # Collect context
            blacklist = Blacklist()
            caps = ContextCaps(max_files=50, max_total_bytes=2 * 1024 * 1024)  # 2MB
            
            paths_to_scan = []
            if input_data.context_paths:
                paths_to_scan.extend(Path(p) for p in input_data.context_paths)
            elif input_data.use_context:
                # Use default context patterns
                paths_to_scan.extend(Path(p) for p in ["README.md", "*.md"])
            
            # Resolve glob patterns to actual paths
            resolved_paths = []
            for path_pattern in paths_to_scan:
                if "*" in str(path_pattern):
                    resolved_paths.extend(project_root.glob(str(path_pattern)))
                else:
                    resolved_paths.append(project_root / path_pattern)
            
            result = collect_paths(resolved_paths, blacklist, caps)
            
            # Build context text and sources
            context_parts = []
            for path in result.included:
                try:
                    content = path.read_text(encoding="utf-8")
                    rel_path = path.relative_to(project_root)
                    context_parts.append(f"=== {rel_path} ===\n{content}\n")
                    sources.append(SourceRef(path=str(rel_path), bytes=len(content.encode())))
                except Exception:
                    continue
            
            if context_parts:
                context_text = "\n".join(context_parts)

        # Build prompt
        prompt_parts = [f"Question: {input_data.query}"]
        
        if input_data.style == "summary":
            prompt_parts.append("Please provide a concise summary-style answer.")
        elif input_data.style == "bullets":
            prompt_parts.append("Please format your answer as bullet points.")
        
        if context_text:
            prompt_parts.append(f"\nContext from project files:\n{context_text}")
        
        prompt_parts.append("\nProvide a helpful answer:")
        prompt = "\n".join(prompt_parts)

        # Get response from provider
        response = provider.generate_structured(prompt=prompt, response_model=AskOutput)
        
        # Merge sources from context
        response.output.sources = sources
        
        return response.output