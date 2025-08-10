"""Tests for blacklist functionality."""

from pathlib import Path
import pytest

from core.blacklist import Blacklist, DEFAULT_BLACKLIST


def test_default_blacklist_patterns():
    """Test that default blacklist contains expected patterns."""
    assert ".git/" in DEFAULT_BLACKLIST
    assert ".jj/" in DEFAULT_BLACKLIST
    assert ".venv/" in DEFAULT_BLACKLIST
    assert "node_modules/" in DEFAULT_BLACKLIST
    assert ".env" in DEFAULT_BLACKLIST
    assert "*.png" in DEFAULT_BLACKLIST


def test_blacklist_blocks_common_patterns():
    """Test that blacklist blocks common unwanted files."""
    blacklist = Blacklist()
    
    # VCS directories
    assert blacklist.is_blocked(Path(".git/config"))
    assert blacklist.is_blocked(Path(".jj/repo/store"))
    
    # Dependencies
    assert blacklist.is_blocked(Path("node_modules/package/index.js"))
    assert blacklist.is_blocked(Path(".venv/lib/python3.11/site-packages"))
    
    # Secrets
    assert blacklist.is_blocked(Path(".env"))
    assert blacklist.is_blocked(Path(".env.local"))
    assert blacklist.is_blocked(Path("private.key"))
    
    # Binary/media files
    assert blacklist.is_blocked(Path("image.png"))
    assert blacklist.is_blocked(Path("video.mp4"))
    assert blacklist.is_blocked(Path("archive.zip"))


def test_blacklist_allows_source_files():
    """Test that blacklist allows common source files."""
    blacklist = Blacklist()
    
    # Source code files
    assert not blacklist.is_blocked(Path("main.py"))
    assert not blacklist.is_blocked(Path("src/app.js"))
    assert not blacklist.is_blocked(Path("lib/utils.ts"))
    
    # Documentation
    assert not blacklist.is_blocked(Path("README.md"))
    assert not blacklist.is_blocked(Path("docs/guide.md"))
    
    # Config files
    assert not blacklist.is_blocked(Path("pyproject.toml"))
    assert not blacklist.is_blocked(Path("package.json"))


def test_blacklist_with_extra_ignores():
    """Test blacklist with extra ignore patterns."""
    blacklist = Blacklist(extra_ignores=["production.env"])
    
    # Should normally be blocked
    assert blacklist.is_blocked(Path(".env"))
    
    # But ignored due to extra_ignores
    assert not blacklist.is_blocked(Path("production.env"))


def test_blacklist_filter_paths():
    """Test filtering a list of paths."""
    blacklist = Blacklist()
    
    paths = [
        Path("main.py"),
        Path(".git/config"),
        Path("README.md"),
        Path("node_modules/lib.js"),
        Path("src/utils.py"),
        Path("image.png"),
    ]
    
    filtered = blacklist.filter_paths(paths)
    
    assert Path("main.py") in filtered
    assert Path("README.md") in filtered
    assert Path("src/utils.py") in filtered
    
    assert Path(".git/config") not in filtered
    assert Path("node_modules/lib.js") not in filtered
    assert Path("image.png") not in filtered


def test_directory_suffix_matching():
    """Test directory suffix matching with trailing slashes."""
    blacklist = Blacklist()
    
    # Should match directories even without trailing slash in path
    assert blacklist.is_blocked(Path(".git"))
    assert blacklist.is_blocked(Path(".git/config"))  # Files inside directories
    assert blacklist.is_blocked(Path("node_modules"))
    assert blacklist.is_blocked(Path("node_modules/lib.js"))  # Files inside directories


def test_custom_patterns():
    """Test blacklist with custom patterns."""
    custom_patterns = ["*.tmp", "build/", "*.log"]
    blacklist = Blacklist(patterns=custom_patterns)
    
    assert blacklist.is_blocked(Path("temp.tmp"))
    assert blacklist.is_blocked(Path("build/output"))
    assert blacklist.is_blocked(Path("app.log"))
    
    # Default patterns should not be active
    assert not blacklist.is_blocked(Path(".git/config"))
    assert not blacklist.is_blocked(Path("image.png"))
