from pathlib import Path
import pytest
from unittest.mock import Mock

from usecases.ask import Ask, AskInput, AskOutput
from llm.provider import ProviderResponse
from core.models import SourceRef


def test_ask_without_context(tmp_path: Path):
    """Test ask use case without any context."""
    # Mock provider
    mock_provider = Mock()
    mock_response = ProviderResponse(
        output=AskOutput(answer="Test answer", sources=[]),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = AskInput(query="What is this?", use_context=False)
    result = Ask.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert result.answer == "Test answer"
    assert len(result.sources) == 0
    mock_provider.generate_structured.assert_called_once()


def test_ask_with_context(tmp_path: Path):
    """Test ask use case with context files."""
    # Create test files
    readme = tmp_path / "README.md"
    readme.write_text("# Test Project\nThis is a test.")
    
    # Mock provider
    mock_provider = Mock()
    mock_response = ProviderResponse(
        output=AskOutput(answer="Based on the context, this is a test project.", sources=[]),
        raw={},
        model="test"
    )
    mock_provider.generate_structured.return_value = mock_response
    
    # Execute
    input_data = AskInput(query="What is this project?", context_paths=["README.md"])
    result = Ask.execute(input_data, mock_provider, tmp_path)
    
    # Verify
    assert result.answer == "Based on the context, this is a test project."
    assert len(result.sources) == 1
    assert result.sources[0].path == "README.md"
    
    # Check that context was included in prompt
    call_args = mock_provider.generate_structured.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Test Project" in prompt
    assert "This is a test." in prompt
