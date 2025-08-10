"""Filesystem utilities for safe file operations with sandbox integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from core.sandbox import SandboxGuard


class FileOperation:
    """Represents a single file operation to be performed."""
    
    def __init__(self, path: Path, content: str, action: str):
        self.path = path
        self.content = content
        self.action = action  # "create", "update", "delete"
    
    def __str__(self) -> str:
        return f"{self.action.upper()} {self.path}"


class FileWriter:
    """Safe file writer that respects sandbox restrictions."""
    
    def __init__(self, sandbox_guard: SandboxGuard):
        self._guard = sandbox_guard
        self._operations: list[FileOperation] = []
    
    def add_operation(self, path: Path, content: str, action: str) -> None:
        """Add a file operation to the batch."""
        # Validate sandbox permissions before adding
        if action in ("create", "update"):
            self._guard.assert_write_allowed(path)
        elif action == "delete":
            self._guard.assert_write_allowed(path)
        
        self._operations.append(FileOperation(path, content, action))
    
    def preview_operations(self) -> list[FileOperation]:
        """Get list of operations without executing them."""
        return self._operations.copy()
    
    def execute_operations(self, dry_run: bool = False) -> list[str]:
        """Execute all operations, returning list of changes made."""
        changes = []
        
        for op in self._operations:
            if dry_run:
                changes.append(f"[DRY RUN] {op}")
                continue
            
            try:
                if op.action == "create":
                    # Ensure parent directory exists
                    op.path.parent.mkdir(parents=True, exist_ok=True)
                    op.path.write_text(op.content, encoding="utf-8")
                    changes.append(f"Created {op.path}")
                
                elif op.action == "update":
                    if not op.path.exists():
                        raise FileNotFoundError(f"Cannot update non-existent file: {op.path}")
                    op.path.write_text(op.content, encoding="utf-8")
                    changes.append(f"Updated {op.path}")
                
                elif op.action == "delete":
                    if op.path.exists():
                        op.path.unlink()
                        changes.append(f"Deleted {op.path}")
                    else:
                        changes.append(f"Skipped delete (not found): {op.path}")
                
            except Exception as e:
                changes.append(f"Failed {op.action} {op.path}: {e}")
        
        return changes
    
    def clear_operations(self) -> None:
        """Clear all pending operations."""
        self._operations.clear()


def create_file_writer(sandbox_guard: SandboxGuard) -> FileWriter:
    """Factory function to create a FileWriter with proper sandbox integration."""
    return FileWriter(sandbox_guard)