"""Tests for filesystem utilities and file writing."""

from pathlib import Path
import pytest
from unittest.mock import Mock

from core.sandbox import SandboxMode, SandboxPolicy, SandboxGuard, SandboxViolation
from utils.fs import FileWriter, FileOperation, create_file_writer


def test_file_operation_str():
    """Test FileOperation string representation."""
    op = FileOperation(Path("test.py"), "content", "create")
    assert str(op) == "CREATE test.py"


def test_file_writer_sandbox_validation(tmp_path: Path):
    """Test that FileWriter validates sandbox permissions."""
    # Create restrictive sandbox (FULL mode)
    policy = SandboxPolicy(
        mode=SandboxMode.FULL,
        project_root=tmp_path,
        allows_writes=False,
        user_write_consent=False,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Should reject write operations
    with pytest.raises(SandboxViolation):
        writer.add_operation(tmp_path / "test.py", "content", "create")


def test_file_writer_sandbox_permissions(tmp_path: Path):
    """Test FileWriter with proper write permissions."""
    # Create permissive sandbox
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Should allow write operations
    writer.add_operation(tmp_path / "test.py", "print('hello')", "create")
    assert len(writer.preview_operations()) == 1


def test_file_writer_create_operation(tmp_path: Path):
    """Test file creation operation."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    test_file = tmp_path / "new_file.py"
    content = "def hello():\n    return 'world'"
    
    writer.add_operation(test_file, content, "create")
    changes = writer.execute_operations(dry_run=False)
    
    assert test_file.exists()
    assert test_file.read_text() == content
    assert f"Created {test_file}" in changes


def test_file_writer_update_operation(tmp_path: Path):
    """Test file update operation."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Create initial file
    test_file = tmp_path / "existing.py"
    test_file.write_text("original content")
    
    new_content = "updated content"
    writer.add_operation(test_file, new_content, "update")
    changes = writer.execute_operations(dry_run=False)
    
    assert test_file.read_text() == new_content
    assert f"Updated {test_file}" in changes


def test_file_writer_delete_operation(tmp_path: Path):
    """Test file deletion operation."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Create file to delete
    test_file = tmp_path / "to_delete.py"
    test_file.write_text("delete me")
    
    writer.add_operation(test_file, "", "delete")
    changes = writer.execute_operations(dry_run=False)
    
    assert not test_file.exists()
    assert f"Deleted {test_file}" in changes


def test_file_writer_dry_run(tmp_path: Path):
    """Test dry run mode."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    test_file = tmp_path / "dry_run_test.py"
    writer.add_operation(test_file, "content", "create")
    changes = writer.execute_operations(dry_run=True)
    
    # File should not be created in dry run
    assert not test_file.exists()
    assert "[DRY RUN]" in changes[0]


def test_file_writer_multiple_operations(tmp_path: Path):
    """Test multiple operations in sequence."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Add multiple operations
    file1 = tmp_path / "file1.py"
    file2 = tmp_path / "file2.py"
    
    writer.add_operation(file1, "content1", "create")
    writer.add_operation(file2, "content2", "create")
    
    changes = writer.execute_operations(dry_run=False)
    
    assert len(changes) == 2
    assert file1.exists() and file2.exists()
    assert file1.read_text() == "content1"
    assert file2.read_text() == "content2"


def test_file_writer_nested_directory_creation(tmp_path: Path):
    """Test creating files in nested directories."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    # Create file in nested directory that doesn't exist
    nested_file = tmp_path / "tests" / "unit" / "test_example.py"
    
    writer.add_operation(nested_file, "test content", "create")
    changes = writer.execute_operations(dry_run=False)
    
    assert nested_file.exists()
    assert nested_file.read_text() == "test content"
    assert f"Created {nested_file}" in changes


def test_file_writer_update_nonexistent_file(tmp_path: Path):
    """Test updating a file that doesn't exist."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    nonexistent_file = tmp_path / "does_not_exist.py"
    
    writer.add_operation(nonexistent_file, "content", "update")
    changes = writer.execute_operations(dry_run=False)
    
    assert "Failed" in changes[0]
    assert "Cannot update non-existent file" in changes[0]


def test_file_writer_clear_operations(tmp_path: Path):
    """Test clearing pending operations."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    writer = FileWriter(guard)
    
    writer.add_operation(tmp_path / "test.py", "content", "create")
    assert len(writer.preview_operations()) == 1
    
    writer.clear_operations()
    assert len(writer.preview_operations()) == 0


def test_create_file_writer_factory(tmp_path: Path):
    """Test the factory function."""
    policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=tmp_path,
        allows_writes=True,
        user_write_consent=True,
    )
    guard = SandboxGuard(policy)
    
    writer = create_file_writer(guard)
    assert isinstance(writer, FileWriter)
    assert writer._guard is guard
