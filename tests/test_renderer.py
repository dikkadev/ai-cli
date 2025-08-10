"""Tests for Rich-based rendering functionality."""

from io import StringIO
from unittest.mock import Mock

from rich.console import Console

from utils.render import Renderer, RunMeta, Stopwatch
from usecases.task import Step


def capture_render_output(render_func, *args, **kwargs) -> str:
    """Capture Rich console output as string."""
    output = StringIO()
    console = Console(file=output, width=80, legacy_windows=False)
    renderer = Renderer(console)
    render_func(renderer, *args, **kwargs)
    return output.getvalue()


def test_render_header():
    """Test header rendering with different metadata."""
    meta = RunMeta(
        usecase="ask",
        sandbox_badge="FULL SANDBOX",
        model_name="gpt-4o-mini",
        elapsed_s=1.23
    )
    
    output = capture_render_output(lambda r: r.render_header(meta))
    
    assert "ask" in output
    assert "FULL SANDBOX" in output
    assert "gpt-4o-mini" in output
    assert "1.23s" in output


def test_render_header_minimal():
    """Test header rendering with minimal metadata."""
    meta = RunMeta(usecase="task", sandbox_badge="LIMITED")
    
    output = capture_render_output(lambda r: r.render_header(meta))
    
    assert "task" in output
    assert "LIMITED" in output


def test_render_context_summary():
    """Test context summary rendering."""
    output = capture_render_output(
        lambda r: r.render_context_summary(
            included_count=5,
            skipped_count=2,
            redaction_on=True,
            top_sources=["README.md", "src/main.py"]
        )
    )
    
    assert "included: 5" in output
    assert "skipped: 2" in output
    assert "redaction: on" in output
    assert "README.md" in output
    assert "src/main.py" in output


def test_render_context_summary_no_sources():
    """Test context summary without sources."""
    output = capture_render_output(
        lambda r: r.render_context_summary(
            included_count=0,
            skipped_count=0,
            redaction_on=False
        )
    )
    
    assert "included: 0" in output
    assert "redaction: off" in output


def test_render_text_block():
    """Test simple text block rendering."""
    content = "This is a test answer with some content."
    
    output = capture_render_output(lambda r: r.render_text_block(content))
    
    assert content in output


def test_render_plan():
    """Test structured plan rendering."""
    steps = [
        Step(
            title="Setup environment",
            description="Install dependencies and configure settings",
            rationale="Need clean environment for development",
            risk_level="low"
        ),
        Step(
            title="Implement feature",
            description="Write the core functionality",
            rationale="This is the main deliverable",
            risk_level="medium"
        ),
        Step(
            title="Deploy to production",
            description="Release the changes",
            rationale="Make feature available to users",
            risk_level="high"
        )
    ]
    
    risks = ["Deployment might fail", "Dependencies could conflict"]
    assumptions = ["Users want this feature", "Current infrastructure can handle load"]
    next_actions = ["Review requirements", "Setup development environment"]
    
    output = capture_render_output(
        lambda r: r.render_plan(steps, risks, assumptions, next_actions)
    )
    
    # Check plan structure
    assert "Plan:" in output
    assert "1. Setup environment" in output
    assert "2. Implement feature" in output  
    assert "3. Deploy to production" in output
    
    # Check risk levels
    assert "LOW" in output
    assert "MEDIUM" in output
    assert "HIGH" in output
    
    # Check descriptions and rationales
    assert "Install dependencies" in output
    assert "Need clean environment" in output
    
    # Check other sections
    assert "Risks:" in output
    assert "Deployment might fail" in output
    assert "Assumptions:" in output
    assert "Users want this feature" in output
    assert "Next Actions:" in output
    assert "Review requirements" in output


def test_render_plan_empty_sections():
    """Test plan rendering with empty sections."""
    steps = [
        Step(
            title="Only step",
            description="Do something",
            rationale="Because we need to",
            risk_level="low"
        )
    ]
    
    output = capture_render_output(
        lambda r: r.render_plan(steps, [], [], [])
    )
    
    assert "1. Only step" in output
    assert "Risks:" not in output  # Empty sections shouldn't appear
    assert "Assumptions:" not in output
    assert "Next Actions:" not in output


def test_render_proposed_files():
    """Test proposed files rendering."""
    from usecases.testwrite import ProposedFile
    
    proposed_files = [
        ProposedFile(
            path="test_utils.py",
            content="import pytest\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_multiply():\n    assert multiply(2, 3) == 6",
            action="create",
            rationale="Add comprehensive tests for utility functions"
        ),
        ProposedFile(
            path="old_tests.py",
            content="",
            action="delete",
            rationale="Remove outdated test file"
        )
    ]
    
    rationale = "Improve test coverage and remove dead code"
    coverage_targets = ["add", "multiply", "divide"]
    
    output = capture_render_output(
        lambda r: r.render_proposed_files(proposed_files, rationale, coverage_targets)
    )
    
    # Check overall structure
    assert "Approach:" in output
    assert rationale in output
    assert "Coverage Targets:" in output
    assert "Proposed Changes:" in output
    
    # Check coverage targets
    assert "add" in output
    assert "multiply" in output
    assert "divide" in output
    
    # Check proposed files
    assert "1. test_utils.py" in output
    assert "CREATE" in output
    assert "2. old_tests.py" in output
    assert "DELETE" in output
    
    # Check content preview
    assert "import pytest" in output
    assert "Preview" in output


def test_stopwatch():
    """Test stopwatch context manager."""
    import time
    
    with Stopwatch() as sw:
        time.sleep(0.01)  # Sleep for 10ms
    
    assert hasattr(sw, 'elapsed')
    assert sw.elapsed > 0.005  # Should be at least 5ms
    assert sw.elapsed < 1.0    # Should be much less than 1 second
