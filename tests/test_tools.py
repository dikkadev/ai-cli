"""Tests for the new tool system."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from tools import (
    Tool, ToolResult, ToolRegistry,
    TreeTool, ReadFileTool,
    TodoList, TodoViewTool, TodoEditTool, TodoAddTool
)
from core.blacklist import Blacklist


class TestToolResult:
    """Test ToolResult class."""
    
    def test_success_result(self):
        result = ToolResult(success=True, data={"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_error_result(self):
        result = ToolResult(success=False, error="Something went wrong")
        assert result.success is False
        assert result.data is None
        assert result.error == "Something went wrong"
    
    def test_to_dict(self):
        result = ToolResult(success=True, data="test")
        result_dict = result.to_dict()
        assert result_dict == {
            "success": True,
            "data": "test", 
            "error": None
        }


class MockTool(Tool):
    """Mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "mock_tool"
    
    @property
    def description(self) -> str:
        return "A mock tool for testing"
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "string", "description": "Test input"}
            },
            "required": ["input"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        if "error" in kwargs.get("input", ""):
            return ToolResult(success=False, error="Mock error")
        return ToolResult(success=True, data=f"Mock result: {kwargs}")


class TestToolRegistry:
    """Test ToolRegistry class."""
    
    def test_register_tool(self):
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register(tool)
        
        assert len(registry) == 1
        assert "mock_tool" in registry
        assert registry.get_tool("mock_tool") == tool
    
    def test_register_duplicate_tool_fails(self):
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()
        
        registry.register(tool1)
        
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)
    
    def test_get_nonexistent_tool(self):
        registry = ToolRegistry()
        assert registry.get_tool("nonexistent") is None
    
    def test_execute_tool_success(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        
        result = registry.execute_tool("mock_tool", input="test")
        
        assert result.success is True
        assert "Mock result" in result.data
    
    def test_execute_tool_error(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        
        result = registry.execute_tool("mock_tool", input="error")
        
        assert result.success is False
        assert result.error == "Mock error"
    
    def test_execute_nonexistent_tool(self):
        registry = ToolRegistry()
        
        result = registry.execute_tool("nonexistent")
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_get_function_schemas(self):
        registry = ToolRegistry()
        registry.register(MockTool())
        
        schemas = registry.get_function_schemas()
        
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert "parameters" in schema["function"]


class TestTreeTool:
    """Test TreeTool."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        # Create test directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "src" / "utils").mkdir()
        (tmp_path / "src" / "utils" / "helpers.py").write_text("def helper(): pass")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("def test_main(): pass")
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / ".env").write_text("SECRET=value")  # Should be blacklisted
        
        return tmp_path
    
    def test_tree_basic(self, temp_project):
        tool = TreeTool(temp_project, Blacklist())
        
        result = tool.execute(depth=2)
        
        assert result.success is True
        tree_output = result.data["tree"]
        assert "src/" in tree_output
        assert "tests/" in tree_output
        assert "README.md" in tree_output
        assert ".env" not in tree_output  # Should be blacklisted
    
    def test_tree_with_path(self, temp_project):
        tool = TreeTool(temp_project, Blacklist())
        
        result = tool.execute(depth=1, path="src")
        
        assert result.success is True
        tree_output = result.data["tree"]
        assert "main.py" in tree_output
        assert "utils/" in tree_output
        assert "tests/" not in tree_output  # Outside specified path
    
    def test_tree_nonexistent_path(self, temp_project):
        tool = TreeTool(temp_project, Blacklist())
        
        result = tool.execute(depth=1, path="nonexistent")
        
        assert result.success is False
        assert "does not exist" in result.error
    
    def test_tree_outside_project_root(self, temp_project):
        tool = TreeTool(temp_project, Blacklist())
        
        result = tool.execute(depth=1, path="../")
        
        assert result.success is False
        assert "outside project root" in result.error


class TestReadFileTool:
    """Test ReadFileTool."""
    
    @pytest.fixture 
    def temp_project(self, tmp_path):
        """Create temporary files for testing."""
        (tmp_path / "test.py").write_text("print('hello world')")
        (tmp_path / "large.txt").write_text("x" * (2 * 1024 * 1024))  # 2MB file
        (tmp_path / ".env").write_text("SECRET=value")
        (tmp_path / "binary.bin").write_bytes(b'\x00\x01\x02\x03')
        return tmp_path
    
    def test_read_file_success(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path="test.py")
        
        assert result.success is True
        assert result.data["content"] == "print('hello world')"
        assert result.data["path"] == "test.py"
        assert result.data["size_bytes"] > 0
        assert result.data["lines"] == 1
    
    def test_read_blacklisted_file(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path=".env")
        
        assert result.success is False
        assert "blacklisted" in result.error
        assert "security reasons" in result.error
    
    def test_read_nonexistent_file(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path="nonexistent.txt")
        
        assert result.success is False
        assert "does not exist" in result.error
    
    def test_read_large_file(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path="large.txt")
        
        assert result.success is False
        assert "too large" in result.error
    
    def test_read_binary_file(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path="binary.bin")
        
        assert result.success is False
        assert "binary" in result.error
    
    def test_read_outside_project_root(self, temp_project):
        tool = ReadFileTool(temp_project, Blacklist())
        
        result = tool.execute(path="../outside.txt")
        
        assert result.success is False
        assert "outside project root" in result.error


class TestTodoList:
    """Test TodoList functionality."""
    
    def test_empty_todo_list(self):
        todo_list = TodoList()
        
        assert len(todo_list.items) == 0
        assert todo_list.to_markdown() == "No todos yet."
        assert todo_list.get_stats() == {
            "total_items": 0,
            "completed_items": 0,
            "pending_items": 0
        }
    
    def test_add_todo(self):
        todo_list = TodoList()
        
        number = todo_list.add("First task")
        
        assert number == 1
        assert len(todo_list.items) == 1
        assert todo_list.items[0].text == "First task"
        assert todo_list.items[0].completed is False
    
    def test_add_multiple_todos(self):
        todo_list = TodoList()
        
        num1 = todo_list.add("First task")
        num2 = todo_list.add("Second task")
        
        assert num1 == 1
        assert num2 == 2
        assert len(todo_list.items) == 2
    
    def test_edit_todo_status(self):
        todo_list = TodoList()
        todo_list.add("Test task")
        
        success = todo_list.edit(1, status=True)
        
        assert success is True
        assert todo_list.items[0].completed is True
    
    def test_edit_todo_text(self):
        todo_list = TodoList()
        todo_list.add("Original text")
        
        success = todo_list.edit(1, text="Updated text")
        
        assert success is True
        assert todo_list.items[0].text == "Updated text"
    
    def test_edit_nonexistent_todo(self):
        todo_list = TodoList()
        
        success = todo_list.edit(999, status=True)
        
        assert success is False
    
    def test_to_markdown(self):
        todo_list = TodoList()
        todo_list.add("First task")
        todo_list.add("Second task")
        todo_list.edit(1, status=True)
        
        markdown = todo_list.to_markdown()
        
        assert "- [x] 1. First task" in markdown
        assert "- [ ] 2. Second task" in markdown
    
    def test_get_stats(self):
        todo_list = TodoList()
        todo_list.add("Task 1")
        todo_list.add("Task 2") 
        todo_list.add("Task 3")
        todo_list.edit(1, status=True)
        todo_list.edit(2, status=True)
        
        stats = todo_list.get_stats()
        
        assert stats == {
            "total_items": 3,
            "completed_items": 2,
            "pending_items": 1
        }


class TestTodoTools:
    """Test todo management tools."""
    
    @pytest.fixture
    def todo_list(self):
        """Create a todo list with some items."""
        todo_list = TodoList()
        todo_list.add("First task")
        todo_list.add("Second task")
        todo_list.edit(1, status=True)
        return todo_list
    
    def test_todo_view_tool(self, todo_list):
        tool = TodoViewTool(todo_list)
        
        result = tool.execute()
        
        assert result.success is True
        assert "First task" in result.data["markdown"]
        assert result.data["total_items"] == 2
        assert result.data["completed_items"] == 1
    
    def test_todo_add_tool(self, todo_list):
        tool = TodoAddTool(todo_list)
        
        result = tool.execute(text="New task")
        
        assert result.success is True
        assert result.data["number"] == 3
        assert result.data["text"] == "New task"
        assert "New task" in result.data["new_markdown"]
    
    def test_todo_add_empty_text(self, todo_list):
        tool = TodoAddTool(todo_list)
        
        result = tool.execute(text="   ")
        
        assert result.success is False
        assert "cannot be empty" in result.error
    
    def test_todo_edit_tool_status(self, todo_list):
        tool = TodoEditTool(todo_list)
        
        result = tool.execute(number=2, completed=True)
        
        assert result.success is True
        assert result.data["number"] == 2
        assert result.data["item"]["completed"] is True
    
    def test_todo_edit_tool_text(self, todo_list):
        tool = TodoEditTool(todo_list)
        
        result = tool.execute(number=1, text="Updated task")
        
        assert result.success is True
        assert result.data["item"]["text"] == "Updated task"
    
    def test_todo_edit_nonexistent(self, todo_list):
        tool = TodoEditTool(todo_list)
        
        result = tool.execute(number=999, completed=True)
        
        assert result.success is False
        assert "not found" in result.error
    
    def test_todo_edit_no_changes(self, todo_list):
        tool = TodoEditTool(todo_list)
        
        result = tool.execute(number=1)
        
        assert result.success is False
        assert "Must provide either" in result.error

