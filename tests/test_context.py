"""Tests for context ingestion functionality."""

from pathlib import Path
import pytest

from core.context import collect_paths, ContextCaps, looks_binary, TEXT_EXTENSIONS
from core.blacklist import Blacklist


def test_text_extensions():
    """Test that TEXT_EXTENSIONS contains expected file types."""
    assert ".py" in TEXT_EXTENSIONS
    assert ".js" in TEXT_EXTENSIONS
    assert ".md" in TEXT_EXTENSIONS
    assert ".json" in TEXT_EXTENSIONS
    assert ".toml" in TEXT_EXTENSIONS


def test_looks_binary_detection():
    """Test binary file detection."""
    # Text files (by extension)
    assert not looks_binary(Path("script.py"))
    assert not looks_binary(Path("README.md"))
    assert not looks_binary(Path("config.json"))
    
    # Binary files (by extension)
    assert looks_binary(Path("image.png"))
    assert looks_binary(Path("binary.exe"))
    assert looks_binary(Path("archive.zip"))


def test_looks_binary_with_actual_content(tmp_path: Path):
    """Test binary detection with actual file content."""
    # Create text file
    text_file = tmp_path / "text.py"
    text_file.write_text("print('hello world')")
    assert not looks_binary(text_file)
    
    # Create binary file with null bytes
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"hello\x00world\x00")
    assert looks_binary(binary_file)


def test_collect_paths_basic(tmp_path: Path):
    """Test basic path collection."""
    # Create test files
    file1 = tmp_path / "file1.py"
    file1.write_text("# File 1\nprint('hello')")
    
    file2 = tmp_path / "file2.md"
    file2.write_text("# Documentation\nThis is a test.")
    
    blacklist = Blacklist(patterns=[])  # Empty blacklist
    result = collect_paths([tmp_path], blacklist)
    
    assert len(result.included) == 2
    assert file1 in result.included
    assert file2 in result.included
    assert result.total_bytes > 0


def test_collect_paths_with_blacklist(tmp_path: Path):
    """Test path collection with blacklist filtering."""
    # Create test files
    good_file = tmp_path / "script.py"
    good_file.write_text("print('hello')")
    
    bad_file = tmp_path / "image.png"
    bad_file.write_bytes(b"fake png data")
    
    vcs_dir = tmp_path / ".git"
    vcs_dir.mkdir()
    vcs_file = vcs_dir / "config"
    vcs_file.write_text("git config")
    
    blacklist = Blacklist()  # Default blacklist
    result = collect_paths([tmp_path], blacklist)
    
    assert good_file in result.included
    assert bad_file in result.skipped  # Blocked by blacklist
    assert vcs_file in result.skipped  # Blocked by blacklist


def test_collect_paths_with_caps(tmp_path: Path):
    """Test path collection with size limits."""
    # Create files
    small_file = tmp_path / "small.py"
    small_file.write_text("print('small')")
    
    large_file = tmp_path / "large.py"
    large_file.write_text("x" * 1000)  # 1000 bytes
    
    # Set tight limits
    caps = ContextCaps(max_files=1, max_total_bytes=500, max_file_bytes=100)
    blacklist = Blacklist(patterns=[])  # Empty blacklist
    
    result = collect_paths([tmp_path], blacklist, caps)
    
    # Should only include small file
    assert small_file in result.included
    assert large_file in result.skipped  # Too large
    assert len(result.included) == 1


def test_collect_paths_max_files_limit(tmp_path: Path):
    """Test max files limit."""
    # Create multiple small files
    files = []
    for i in range(5):
        file = tmp_path / f"file{i}.py"
        file.write_text(f"# File {i}")
        files.append(file)
    
    caps = ContextCaps(max_files=3)
    blacklist = Blacklist(patterns=[])
    
    result = collect_paths([tmp_path], blacklist, caps)
    
    assert len(result.included) == 3
    assert len(result.skipped) == 2


def test_collect_paths_total_bytes_limit(tmp_path: Path):
    """Test total bytes limit."""
    # Create files that exceed total limit when combined
    file1 = tmp_path / "file1.py"
    file1.write_text("x" * 300)  # 300 bytes
    
    file2 = tmp_path / "file2.py"
    file2.write_text("y" * 300)  # 300 bytes
    
    file3 = tmp_path / "file3.py"
    file3.write_text("z" * 300)  # 300 bytes
    
    caps = ContextCaps(max_total_bytes=500)  # Can only fit 1-2 files
    blacklist = Blacklist(patterns=[])
    
    result = collect_paths([tmp_path], blacklist, caps)
    
    assert result.total_bytes <= 500
    assert len(result.included) < 3  # Some files should be skipped


def test_collect_paths_single_file(tmp_path: Path):
    """Test collecting a single file directly."""
    target_file = tmp_path / "target.py"
    target_file.write_text("def hello(): return 'world'")
    
    blacklist = Blacklist(patterns=[])
    result = collect_paths([target_file], blacklist)
    
    assert len(result.included) == 1
    assert target_file in result.included


def test_collect_paths_nonexistent(tmp_path: Path):
    """Test collecting nonexistent paths."""
    nonexistent = tmp_path / "does_not_exist.py"
    
    blacklist = Blacklist(patterns=[])
    result = collect_paths([nonexistent], blacklist)
    
    assert len(result.included) == 0
    assert nonexistent in result.skipped


def test_collect_paths_binary_files_skipped(tmp_path: Path):
    """Test that binary files are automatically skipped."""
    # Create text file
    text_file = tmp_path / "text.py"
    text_file.write_text("print('hello')")
    
    # Create binary file with null bytes
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"binary\x00data\x00here")
    
    blacklist = Blacklist(patterns=[])
    result = collect_paths([tmp_path], blacklist)
    
    assert text_file in result.included
    assert binary_file in result.skipped  # Binary files skipped
