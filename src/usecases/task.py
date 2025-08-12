from __future__ import annotations

from pathlib import Path
from typing import Literal, Callable

from pydantic import BaseModel, Field

from core.blacklist import Blacklist
from core.context import ContextCaps, collect_paths
from core.models import SourceRef, UsecaseInput, UsecaseOutput
from core.sandbox import SandboxMode
from usecases.ask import usecase


class Step(BaseModel):
    title: str = Field(description="Brief title for this step")
    description: str = Field(description="Detailed description of what to do")
    rationale: str = Field(description="Why this step is necessary")
    risk_level: Literal["low", "medium", "high"] = Field(default="low", description="Risk assessment")


class TaskInput(UsecaseInput):
    objective: str = Field(description="The task or objective to plan for")
    mode: Literal["plan", "plan+steps"] = Field(default="plan", description="Planning depth")
    risk_level: Literal["conservative", "moderate", "aggressive"] = Field(default="moderate", description="Risk tolerance")
    use_context: bool = Field(default=False, description="Include project context")
    context_paths: list[str] = Field(default_factory=list, description="Paths to include as context")


class TaskOutput(UsecaseOutput):
    plan: list[Step] = Field(description="Structured plan with numbered steps")
    risks: list[str] = Field(default_factory=list, description="Identified risks")
    assumptions: list[str] = Field(default_factory=list, description="Key assumptions made")
    next_actions: list[str] = Field(default_factory=list, description="Immediate next actions")
    sources: list[SourceRef] = Field(default_factory=list, description="Sources used")


@usecase(
    id="task",
    summary="Create a structured plan for a task or objective",
    sandbox=SandboxMode.FULL,
    allows_writes=False,
    default_context=["README.md", "*.md", "pyproject.toml", "package.json"],
)
class Task:
    InputModel = TaskInput
    OutputModel = TaskOutput

    @staticmethod
    def execute(input_data: TaskInput, provider, project_root: Path, progress_callback: Callable[[str], None] | None = None) -> TaskOutput:
        context_text = ""
        sources = []
        
        if input_data.use_context or input_data.context_paths:
            # Collect context
            blacklist = Blacklist()
            caps = ContextCaps(max_files=30, max_total_bytes=1 * 1024 * 1024)  # 1MB
            
            paths_to_scan = []
            if input_data.context_paths:
                paths_to_scan.extend(Path(p) for p in input_data.context_paths)
            elif input_data.use_context:
                # Use default context patterns
                paths_to_scan.extend(Path(p) for p in ["README.md", "*.md", "pyproject.toml", "package.json"])
            
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
        prompt_parts = [f"Objective: {input_data.objective}"]
        
        if input_data.mode == "plan+steps":
            prompt_parts.append("Please create a detailed plan with specific implementation steps.")
        else:
            prompt_parts.append("Please create a high-level plan.")
        
        if input_data.risk_level == "conservative":
            prompt_parts.append("Use a conservative approach with minimal risk.")
        elif input_data.risk_level == "aggressive":
            prompt_parts.append("Use an aggressive approach, accepting higher risk for faster results.")
        
        if context_text:
            prompt_parts.append(f"\nProject context:\n{context_text}")
        
        prompt_parts.extend([
            "\nCreate a structured plan with:",
            "1. A list of numbered steps, each with title, description, and rationale",
            "2. Risk assessment for each step",
            "3. Overall risks and assumptions",
            "4. Immediate next actions to get started",
            "",
            "Format your response as a structured plan:"
        ])
        
        prompt = "\n".join(prompt_parts)

        # Get response from provider
        if hasattr(provider, 'generate_structured_streaming'):
            response = provider.generate_structured_streaming(
                prompt=prompt, 
                response_model=TaskOutput, 
                progress_callback=progress_callback
            )
        else:
            response = provider.generate_structured(prompt=prompt, response_model=TaskOutput)
        
        # Merge sources from context
        response.output.sources = sources
        
        return response.output