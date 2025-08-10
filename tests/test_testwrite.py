from pathlib import Path
import pytest
from unittest.mock import Mock

from usecases.testwrite import TestWrite, TestWriteInput, TestWriteOutput, ProposedFile
from llm.provider import ProviderResponse
from core.models import SourceRef


def test_testwrite_without_context(tmp_path: Path):
    """Test testwrite use case without additional context."""
    # Create a target file
    target_file = tmp_path / "calculator.py"
    target_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")
    
    # Mock provider
    mock_provider = Mock()
    mock_files = [
        ProposedFile(
            path="test_calculator.py",
            content="import pytest\nfrom calculator import add, multiply\n\ndef test_add():\n    assert add(2, 3) == 5",
            action="create",
            rationale="Create comprehensive tests for calculator functions"
        )
    ]
    mock_response = ProviderResponse(
        output=TestWriteOutput(
            proposed_files=mock_files,
            rationale="Generate unit tests for basic math functions",
            coverage_targets=["add", "multiply"],
            sources=[]
        ),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = TestWriteInput(target="calculator.py", use_context=False)
    result = TestWrite.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert len(result.proposed_files) == 1
    assert result.proposed_files[0].path == "test_calculator.py"
    assert result.proposed_files[0].action == "create"
    assert len(result.coverage_targets) == 2
    assert "add" in result.coverage_targets
    assert "multiply" in result.coverage_targets
    mock_provider.generate_structured.assert_called_once()


def test_testwrite_with_context(tmp_path: Path):
    """Test testwrite use case with additional context."""
    # Create target and related files
    target_file = tmp_path / "math_utils.py"
    target_file.write_text("""
class Calculator:
    def add(self, a, b):
        return a + b
    
    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
""")
    
    config_file = tmp_path / "pyproject.toml"
    config_file.write_text('[project]\nname = "math-utils"')
    
    # Mock provider
    mock_provider = Mock()
    mock_files = [
        ProposedFile(
            path="tests/test_math_utils.py",
            content="import pytest\nfrom math_utils import Calculator\n\nclass TestCalculator:",
            action="create",
            rationale="Create pytest-based tests for Calculator class"
        )
    ]
    mock_response = ProviderResponse(
        output=TestWriteOutput(
            proposed_files=mock_files,
            rationale="Use pytest with class-based tests to match the Calculator structure",
            coverage_targets=["Calculator.add", "Calculator.divide"],
            sources=[]
        ),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = TestWriteInput(
        target="math_utils.py",
        framework="pytest",
        context_paths=["pyproject.toml"]
    )
    result = TestWrite.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert len(result.proposed_files) == 1
    assert result.proposed_files[0].path == "tests/test_math_utils.py"
    assert len(result.coverage_targets) == 2
    assert len(result.sources) >= 1  # At least target file (pyproject.toml may be filtered by blacklist)
    
    # Check that context was included in prompt
    call_args = mock_provider.generate_structured.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Calculator" in prompt
    assert "divide by zero" in prompt
