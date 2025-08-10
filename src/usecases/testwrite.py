from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from core.blacklist import Blacklist
from core.context import ContextCaps, collect_paths
from core.models import SourceRef, UsecaseInput, UsecaseOutput
from core.sandbox import SandboxMode
from usecases.ask import usecase


class ProposedFile(BaseModel):
    path: str = Field(description="Relative path to the file")
    content: str = Field(description="Proposed file content")
    action: Literal["create", "update", "delete"] = Field(description="What to do with the file")
    rationale: str = Field(description="Why this change is needed")


class TestWriteInput(UsecaseInput):
    target: str = Field(description="Target file or directory to generate tests for")
    framework: Literal["pytest", "unittest"] = Field(default="pytest", description="Testing framework to use")
    placement: Literal["new_file", "inline"] = Field(default="new_file", description="Where to place tests")
    use_context: bool = Field(default=True, description="Include target and related files as context")
    context_paths: list[str] = Field(default_factory=list, description="Additional paths to include as context")


class TestWriteOutput(UsecaseOutput):
    proposed_files: list[ProposedFile] = Field(description="Proposed test files to create/update")
    rationale: str = Field(description="Overall reasoning for the test approach")
    coverage_targets: list[str] = Field(default_factory=list, description="Functions/classes that will be tested")
    sources: list[SourceRef] = Field(default_factory=list, description="Sources used")


@usecase(
    id="testwrite",
    summary="Generate test files for code with proposed changes",
    sandbox=SandboxMode.LIMITED,  # Will allow writes in Phase 4
    allows_writes=True,
    default_context=["*.py", "pyproject.toml", "requirements.txt"],
)
class TestWrite:
    InputModel = TestWriteInput
    OutputModel = TestWriteOutput

    @staticmethod
    def execute(input_data: TestWriteInput, provider, project_root: Path) -> TestWriteOutput:
        context_text = ""
        sources = []
        
        # Always collect context for the target
        blacklist = Blacklist()
        caps = ContextCaps(max_files=20, max_total_bytes=512 * 1024)  # 512KB
        
        paths_to_scan = []
        
        # Add target path
        target_path = project_root / input_data.target
        if target_path.exists():
            paths_to_scan.append(target_path)
        
        # Add additional context paths
        if input_data.context_paths:
            paths_to_scan.extend(Path(p) for p in input_data.context_paths)
        elif input_data.use_context:
            # Use default context patterns
            paths_to_scan.extend(project_root.glob("*.py"))
            for config_file in ["pyproject.toml", "requirements.txt", "setup.py"]:
                config_path = project_root / config_file
                if config_path.exists():
                    paths_to_scan.append(config_path)
        
        # Resolve and collect paths
        result = collect_paths(paths_to_scan, blacklist, caps)
        
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
        prompt_parts = [f"Target for testing: {input_data.target}"]
        prompt_parts.append(f"Testing framework: {input_data.framework}")
        prompt_parts.append(f"Test placement: {input_data.placement}")
        
        prompt_parts.extend([
            "\nGenerate comprehensive tests for the target code.",
            "Focus on:",
            "- Unit tests for individual functions/methods",
            "- Edge cases and error conditions", 
            "- Mock external dependencies appropriately",
            "- Follow testing best practices for the chosen framework",
        ])
        
        if input_data.framework == "pytest":
            prompt_parts.extend([
                "\nUse pytest conventions:",
                "- Test files should be named test_*.py or *_test.py",
                "- Test functions should start with test_",
                "- Use fixtures appropriately",
                "- Use pytest.raises for exception testing",
            ])
        else:
            prompt_parts.extend([
                "\nUse unittest conventions:",
                "- Test classes should inherit from unittest.TestCase",
                "- Test methods should start with test_",
                "- Use setUp/tearDown as needed",
                "- Use self.assertRaises for exception testing",
            ])
        
        if context_text:
            prompt_parts.append(f"\nSource code context:\n{context_text}")
        
        prompt_parts.extend([
            "\nProvide:",
            "1. Proposed test files with complete content",
            "2. Rationale for the testing approach",
            "3. List of functions/classes that will be covered",
            "",
            "Generate comprehensive test coverage:"
        ])
        
        prompt = "\n".join(prompt_parts)

        # Get response from provider
        response = provider.generate_structured(prompt=prompt, response_model=TestWriteOutput)
        
        # Merge sources from context
        response.output.sources = sources
        
        return response.output