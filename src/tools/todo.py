"""Todo management tools for AI agents."""

from __future__ import annotations

from typing import List, Optional
from dataclasses import dataclass, field

from .base import Tool, ToolResult


@dataclass
class TodoItem:
    """Individual todo item."""
    number: int
    text: str
    completed: bool = False
    
    def to_markdown(self) -> str:
        """Convert to markdown checkbox format."""
        checkbox = "[x]" if self.completed else "[ ]"
        return f"- {checkbox} {self.number}. {self.text}"


@dataclass
class TodoList:
    """Manages a list of todo items with markdown output."""
    items: List[TodoItem] = field(default_factory=list)
    _next_number: int = field(default=1, init=False)
    
    def add(self, text: str) -> int:
        """Add a new todo item.
        
        Args:
            text: Description of the todo item
            
        Returns:
            The number assigned to the new todo item
        """
        item = TodoItem(self._next_number, text)
        self.items.append(item)
        self._next_number += 1
        return item.number
    
    def edit(self, number: int, status: Optional[bool] = None, text: Optional[str] = None) -> bool:
        """Edit an existing todo item.
        
        Args:
            number: Todo item number to edit
            status: New completion status (True/False) or None to keep current
            text: New text or None to keep current
            
        Returns:
            True if item was found and edited, False otherwise
        """
        item = self._find_item(number)
        if not item:
            return False
        
        if status is not None:
            item.completed = status
        if text is not None:
            item.text = text
        
        return True
    
    def get_item(self, number: int) -> Optional[TodoItem]:
        """Get todo item by number.
        
        Args:
            number: Todo item number
            
        Returns:
            TodoItem if found, None otherwise
        """
        return self._find_item(number)
    
    def _find_item(self, number: int) -> Optional[TodoItem]:
        """Find todo item by number."""
        for item in self.items:
            if item.number == number:
                return item
        return None
    
    def to_markdown(self) -> str:
        """Convert entire todo list to markdown format.
        
        Returns:
            Markdown string with checkboxes and item numbers
        """
        if not self.items:
            return "No todos yet."
        
        return "\n".join(item.to_markdown() for item in self.items)
    
    def get_stats(self) -> dict:
        """Get todo list statistics.
        
        Returns:
            Dictionary with total_items, completed_items, pending_items
        """
        total = len(self.items)
        completed = sum(1 for item in self.items if item.completed)
        pending = total - completed
        
        return {
            "total_items": total,
            "completed_items": completed,
            "pending_items": pending
        }
    
    def clear(self) -> None:
        """Clear all todos and reset numbering."""
        self.items.clear()
        self._next_number = 1


class TodoViewTool(Tool):
    """Tool to view the current todo list."""
    
    def __init__(self, todo_list: TodoList):
        """Initialize TodoViewTool.
        
        Args:
            todo_list: TodoList instance to operate on
        """
        self.todo_list = todo_list
    
    @property
    def name(self) -> str:
        return "todo_view"
    
    @property
    def description(self) -> str:
        return "View the current todo list in markdown format with completion status."
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self) -> ToolResult:
        """Execute todo view command.
        
        Returns:
            ToolResult with todo list markdown and statistics
        """
        markdown = self.todo_list.to_markdown()
        stats = self.todo_list.get_stats()
        
        result_data = {
            "markdown": markdown,
            **stats
        }
        
        return ToolResult(success=True, data=result_data)


class TodoEditTool(Tool):
    """Tool to edit a specific todo item by number."""
    
    def __init__(self, todo_list: TodoList):
        """Initialize TodoEditTool.
        
        Args:
            todo_list: TodoList instance to operate on
        """
        self.todo_list = todo_list
    
    @property  
    def name(self) -> str:
        return "todo_edit"
    
    @property
    def description(self) -> str:
        return ("Edit a todo item by number. Can change completion status (true/false) "
                "and/or update the text description.")
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "number": {
                    "type": "integer",
                    "description": "Todo item number to edit (must be existing number)"
                },
                "completed": {
                    "type": "boolean", 
                    "description": "Mark as completed (true) or incomplete (false)"
                },
                "text": {
                    "type": "string",
                    "description": "New text description for the todo item"
                }
            },
            "required": ["number"]
        }
    
    def execute(self, number: int, completed: Optional[bool] = None, text: Optional[str] = None) -> ToolResult:
        """Execute todo edit command.
        
        Args:
            number: Todo item number to edit
            completed: New completion status or None
            text: New text or None
            
        Returns:
            ToolResult with edit success and updated todo list
        """
        if completed is None and text is None:
            return ToolResult(
                success=False, 
                error="Must provide either 'completed' status or 'text' to edit"
            )
        
        success = self.todo_list.edit(number, completed, text)
        if not success:
            return ToolResult(
                success=False, 
                error=f"Todo item #{number} not found"
            )
        
        # Get the updated item for confirmation
        updated_item = self.todo_list.get_item(number)
        
        result_data = {
            "number": number,
            "updated": True,
            "item": {
                "number": updated_item.number,
                "text": updated_item.text,
                "completed": updated_item.completed
            },
            "new_markdown": self.todo_list.to_markdown()
        }
        
        return ToolResult(success=True, data=result_data)


class TodoAddTool(Tool):
    """Tool to add a new todo item to the list."""
    
    def __init__(self, todo_list: TodoList):
        """Initialize TodoAddTool.
        
        Args:
            todo_list: TodoList instance to operate on
        """
        self.todo_list = todo_list
    
    @property
    def name(self) -> str:
        return "todo_add" 
    
    @property
    def description(self) -> str:
        return "Add a new todo item to the list. Items are automatically numbered."
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text description for the new todo item"
                }
            },
            "required": ["text"]
        }
    
    def execute(self, text: str) -> ToolResult:
        """Execute todo add command.
        
        Args:
            text: Description for new todo item
            
        Returns:
            ToolResult with new todo details and updated list
        """
        if not text.strip():
            return ToolResult(
                success=False, 
                error="Todo text cannot be empty"
            )
        
        number = self.todo_list.add(text.strip())
        
        result_data = {
            "number": number,
            "text": text.strip(),
            "added": True,
            "new_markdown": self.todo_list.to_markdown()
        }
        
        return ToolResult(success=True, data=result_data)
