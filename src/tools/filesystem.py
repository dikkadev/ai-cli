"""File system tools for AI agents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import Tool, ToolResult
from core.blacklist import Blacklist


class TreeTool(Tool):
    """Tool to show directory tree structure with configurable depth."""
    
    def __init__(self, project_root: Path, blacklist: Blacklist | None = None):
        """Initialize TreeTool.
        
        Args:
            project_root: Root directory for all operations
            blacklist: Blacklist instance for filtering files
        """
        self.project_root = project_root
        self.blacklist = blacklist or Blacklist()
    
    @property
    def name(self) -> str:
        return "tree"
    
    @property
    def description(self) -> str:
        return "Show directory tree structure with configurable depth. Helps explore project layout."
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string", 
                    "description": "Path to show tree for (relative to project root)",
                    "default": "."
                },
                "depth": {
                    "type": "integer",
                    "description": "Maximum depth to show (1-10)",
                    "minimum": 1,
                    "maximum": 10,
                    "default": 3
                }
            },
            "required": ["depth"]
        }
    
    def execute(self, depth: int = 3, path: str = ".") -> ToolResult:
        """Execute tree command.
        
        Args:
            depth: Maximum depth to explore
            path: Starting path relative to project root
            
        Returns:
            ToolResult with tree structure as string
        """
        try:
            target_path = self.project_root / path
            
            # Security check - ensure path is within project root
            try:
                target_path.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                return ToolResult(
                    success=False, 
                    error=f"Path '{path}' is outside project root"
                )
            
            if not target_path.exists():
                return ToolResult(
                    success=False, 
                    error=f"Path '{path}' does not exist"
                )
            
            if not target_path.is_dir():
                return ToolResult(
                    success=False, 
                    error=f"Path '{path}' is not a directory"
                )
            
            tree_output = self._build_tree(target_path, depth, 0, "")
            
            # Prepare result with metadata
            result_data = {
                "tree": tree_output,
                "path": path,
                "depth": depth,
                "root": str(target_path.relative_to(self.project_root))
            }
            
            return ToolResult(success=True, data=result_data)
            
        except Exception as e:
            return ToolResult(
                success=False, 
                error=f"Failed to build tree: {str(e)}"
            )
    
    def _build_tree(self, path: Path, max_depth: int, current_depth: int, prefix: str) -> str:
        """Recursively build tree structure.
        
        Args:
            path: Current directory path
            max_depth: Maximum depth to recurse
            current_depth: Current recursion depth
            prefix: Current line prefix for formatting
            
        Returns:
            Tree structure as formatted string
        """
        if current_depth >= max_depth:
            return ""
        
        items = []
        try:
            for item in sorted(path.iterdir()):
                # Skip hidden files except important ones
                if (item.name.startswith('.') and 
                    item.name not in {'.gitignore', '.env.example', '.github'}):
                    continue
                
                # Check blacklist
                relative_path = item.relative_to(self.project_root)
                if self.blacklist.is_blocked(relative_path):
                    continue
                
                items.append(item)
                
        except PermissionError:
            return f"{prefix}[Permission Denied]\n"
        
        if not items:
            return ""
        
        result = ""
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "
            
            # Add special indicators
            display_name = item.name
            if item.is_dir():
                display_name += "/"
            elif item.suffix in {'.py', '.js', '.ts', '.go', '.rs'}:
                display_name += "*"  # Executable/source indicator
            
            result += f"{prefix}{current_prefix}{display_name}\n"
            
            # Recurse into directories
            if item.is_dir() and current_depth + 1 < max_depth:
                subtree = self._build_tree(item, max_depth, current_depth + 1, prefix + next_prefix)
                result += subtree
        
        return result


class ReadFileTool(Tool):
    """Tool to read file contents with blacklist and security checks."""
    
    def __init__(self, project_root: Path, blacklist: Blacklist | None = None):
        """Initialize ReadFileTool.
        
        Args:
            project_root: Root directory for all operations
            blacklist: Blacklist instance for filtering files
        """
        self.project_root = project_root
        self.blacklist = blacklist or Blacklist()
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return ("Read contents of a file. Some files may be blacklisted for security reasons. "
                "Binary files and very large files will be rejected.")
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object", 
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to file to read (relative to project root)"
                }
            },
            "required": ["path"]
        }
    
    def execute(self, path: str) -> ToolResult:
        """Execute read file command.
        
        Args:
            path: File path relative to project root
            
        Returns:
            ToolResult with file contents or error
        """
        try:
            file_path = self.project_root / path
            
            # Security check - ensure path is within project root
            try:
                file_path.resolve().relative_to(self.project_root.resolve())
            except ValueError:
                return ToolResult(
                    success=False, 
                    error=f"Path '{path}' is outside project root"
                )
            
            # Check if file exists
            if not file_path.exists():
                return ToolResult(
                    success=False, 
                    error=f"File '{path}' does not exist"
                )
            
            if not file_path.is_file():
                return ToolResult(
                    success=False, 
                    error=f"'{path}' is not a file"
                )
            
            # Check blacklist
            relative_path = file_path.relative_to(self.project_root)
            if self.blacklist.is_blocked(relative_path):
                return ToolResult(
                    success=False, 
                    error=f"File '{path}' is blacklisted and cannot be read for security reasons. "
                           f"This may contain sensitive information like API keys, passwords, or private data."
                )
            
            # Check file size (limit to 1MB for safety)
            file_size = file_path.stat().st_size
            if file_size > 1024 * 1024:  # 1MB
                return ToolResult(
                    success=False, 
                    error=f"File '{path}' is too large ({file_size} bytes). Maximum size is 1MB."
                )
            
            # Check if binary
            if self._is_binary_file(file_path):
                return ToolResult(
                    success=False, 
                    error=f"File '{path}' appears to be binary and cannot be read as text"
                )
            
            # Read file content
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with different encoding
                try:
                    content = file_path.read_text(encoding='latin-1')
                except UnicodeDecodeError:
                    return ToolResult(
                        success=False, 
                        error=f"File '{path}' contains non-UTF-8 content and cannot be decoded"
                    )
            
            # Prepare result data
            result_data = {
                "path": path,
                "size_bytes": len(content.encode('utf-8')),
                "lines": content.count('\n') + 1,
                "content": content
            }
            
            return ToolResult(success=True, data=result_data)
            
        except Exception as e:
            return ToolResult(
                success=False, 
                error=f"Failed to read file '{path}': {str(e)}"
            )
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if file is binary by reading first chunk.
        
        Args:
            file_path: Path to file to check
            
        Returns:
            True if file appears to be binary
        """
        try:
            with file_path.open('rb') as f:
                chunk = f.read(1024)
                # Check for null bytes which indicate binary
                return b'\0' in chunk
        except Exception:
            return True
