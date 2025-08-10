from pathlib import Path
import pytest
from unittest.mock import Mock

from usecases.task import Task, TaskInput, TaskOutput, Step
from llm.provider import ProviderResponse
from core.models import SourceRef


def test_task_without_context(tmp_path: Path):
    """Test task use case without any context."""
    # Mock provider
    mock_provider = Mock()
    mock_steps = [
        Step(title="Step 1", description="Do first thing", rationale="Because needed", risk_level="low"),
        Step(title="Step 2", description="Do second thing", rationale="To continue", risk_level="medium"),
    ]
    mock_response = ProviderResponse(
        output=TaskOutput(
            plan=mock_steps,
            risks=["Some risk"],
            assumptions=["Some assumption"],
            next_actions=["Start with step 1"],
            sources=[]
        ),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = TaskInput(objective="Build a new feature", use_context=False)
    result = Task.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert len(result.plan) == 2
    assert result.plan[0].title == "Step 1"
    assert result.plan[1].risk_level == "medium"
    assert len(result.risks) == 1
    assert len(result.assumptions) == 1
    assert len(result.next_actions) == 1
    assert len(result.sources) == 0
    mock_provider.generate_structured.assert_called_once()


def test_task_with_context(tmp_path: Path):
    """Test task use case with context files."""
    # Create test files
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\nThis is a Python project.")
    
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')
    
    # Mock provider
    mock_provider = Mock()
    mock_steps = [
        Step(title="Update docs", description="Update README", rationale="Documentation needs work", risk_level="low"),
    ]
    mock_response = ProviderResponse(
        output=TaskOutput(
            plan=mock_steps,
            risks=[],
            assumptions=["Project is Python-based"],
            next_actions=["Edit README.md"],
            sources=[]
        ),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = TaskInput(objective="Improve documentation", context_paths=["README.md", "pyproject.toml"])
    result = Task.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert len(result.plan) == 1
    assert result.plan[0].title == "Update docs"
    assert len(result.sources) == 2
    assert any(s.path == "README.md" for s in result.sources)
    assert any(s.path == "pyproject.toml" for s in result.sources)
    
    # Check that context was included in prompt
    call_args = mock_provider.generate_structured.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Test Project" in prompt
    assert "Python project" in prompt
