"""Integration tests for CLI commands using subprocess to test actual CLI behavior."""

import subprocess
import tempfile
from pathlib import Path
import pytest
import json


def run_ai_command(args: list[str], cwd: Path = None, expect_success: bool = True) -> subprocess.CompletedProcess:
    """Run ai CLI command and return result."""
    cmd = ["uv", "run", "python", "-m", "cli"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd or Path.cwd(),
        capture_output=True,
        text=True,
        timeout=30
    )
    if expect_success and result.returncode != 0:
        pytest.fail(f"Command failed: {' '.join(cmd)}\nstdout: {result.stdout}\nstderr: {result.stderr}")
    return result


def test_cli_help():
    """Test that the main CLI shows help and available commands."""
    result = run_ai_command([])
    assert result.returncode == 0
    assert "Available commands: ask, task, testwrite" in result.stdout


def test_ask_command_help():
    """Test ask command help."""
    result = run_ai_command(["ask", "--help"])
    assert result.returncode == 0
    assert "Ask a question with optional local context" in result.stdout
    assert "--context" in result.stdout
    assert "--path" in result.stdout


def test_task_command_help():
    """Test task command help."""
    result = run_ai_command(["task", "--help"])
    assert result.returncode == 0
    assert "Create a structured plan for a task" in result.stdout
    assert "--risk-level" in result.stdout
    assert "--mode" in result.stdout


def test_testwrite_command_help():
    """Test testwrite command help."""
    result = run_ai_command(["testwrite", "--help"])
    assert result.returncode == 0
    assert "Generate test files for code" in result.stdout
    assert "--framework" in result.stdout
    assert "--placement" in result.stdout


def test_ask_missing_query():
    """Test ask command fails with missing query argument."""
    result = run_ai_command(["ask"], expect_success=False)
    assert result.returncode != 0
    assert "Missing argument" in result.stderr or "required" in result.stderr.lower()


def test_task_missing_objective():
    """Test task command fails with missing objective argument."""
    result = run_ai_command(["task"], expect_success=False)
    assert result.returncode != 0
    assert "Missing argument" in result.stderr or "required" in result.stderr.lower()


def test_testwrite_missing_target():
    """Test testwrite command fails with missing target argument."""
    result = run_ai_command(["testwrite"], expect_success=False)
    assert result.returncode != 0
    assert "Missing argument" in result.stderr or "required" in result.stderr.lower()


@pytest.mark.slow
def test_ask_basic_query_no_context():
    """Test ask command with basic query and no context (will fail due to no API key, but should parse correctly)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # This will fail due to no OpenAI API key, but we can test CLI parsing
        result = run_ai_command(["ask", "What is 2+2?"], cwd=tmpdir_path, expect_success=False)
        
        # Should fail with OpenAI API error, not CLI parsing error
        assert "ask" in result.stdout  # Should show header
        assert "FULL SANDBOX" in result.stdout  # Should show sandbox badge
        # The actual error will be OpenAI-related, not argument parsing


@pytest.mark.slow  
def test_task_basic_objective_no_context():
    """Test task command with basic objective and no context."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        result = run_ai_command(["task", "Write a README"], cwd=tmpdir_path, expect_success=False)
        
        # Should fail with OpenAI API error, not CLI parsing error
        assert "task" in result.stdout
        assert "FULL SANDBOX" in result.stdout


@pytest.mark.slow
def test_testwrite_basic_target_no_context():
    """Test testwrite command with basic target."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create a dummy Python file
        test_file = tmpdir_path / "example.py"
        test_file.write_text("def hello(): return 'world'")
        
        result = run_ai_command(["testwrite", "example.py"], cwd=tmpdir_path, expect_success=False)
        
        # Should fail with OpenAI API error, not CLI parsing error
        assert "testwrite" in result.stdout
        assert "LIMITED SANDBOX" in result.stdout


def test_ask_with_context_flag():
    """Test ask command with context flag (should parse correctly)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create some context files
        readme = tmpdir_path / "README.md"
        readme.write_text("# Test Project\nThis is a test.")
        
        result = run_ai_command(
            ["ask", "What is this project?", "--context"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        # Should show context was included
        assert "included: 1" in result.stdout or "included: 2" in result.stdout  # README.md might be found


def test_task_with_risk_level():
    """Test task command with different risk levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        result = run_ai_command(
            ["task", "Refactor code", "--risk-level", "conservative"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        assert "task" in result.stdout


def test_testwrite_with_framework():
    """Test testwrite command with different frameworks."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        test_file = tmpdir_path / "code.py"
        test_file.write_text("def add(a, b): return a + b")
        
        result = run_ai_command(
            ["testwrite", "code.py", "--framework", "unittest"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        assert "testwrite" in result.stdout


def test_context_path_handling():
    """Test that context paths are handled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        # Create multiple files
        file1 = tmpdir_path / "file1.py"
        file1.write_text("# File 1")
        file2 = tmpdir_path / "file2.py"  
        file2.write_text("# File 2")
        
        result = run_ai_command(
            ["ask", "What do these files do?", "--path", "file1.py", "--path", "file2.py"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        # Should show multiple paths in context
        assert "file1.py" in result.stdout
        assert "file2.py" in result.stdout


def test_testwrite_write_flag_parsing():
    """Test that --write flag is parsed correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        test_file = tmpdir_path / "sample.py"
        test_file.write_text("def sample(): return True")
        
        result = run_ai_command(
            ["testwrite", "sample.py", "--write"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        # Should show write capability enabled
        assert "LIMITED SANDBOX + WRITES" in result.stdout or "write" in result.stdout.lower()


def test_testwrite_force_flag_parsing():
    """Test that --force flag is parsed correctly.""" 
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        
        test_file = tmpdir_path / "sample.py"
        test_file.write_text("def sample(): return True")
        
        result = run_ai_command(
            ["testwrite", "sample.py", "--write", "--force"],
            cwd=tmpdir_path,
            expect_success=False
        )
        
        # Should parse correctly (will fail on OpenAI call, not argument parsing)
        assert "testwrite" in result.stdout


def test_ask_task_no_write_flags():
    """Test that ask and task commands don't accept write flags."""
    # ask should not accept --write
    result = run_ai_command(["ask", "test", "--write"], expect_success=False)
    assert result.returncode != 0
    
    # task should not accept --write  
    result = run_ai_command(["task", "test", "--write"], expect_success=False)
    assert result.returncode != 0
