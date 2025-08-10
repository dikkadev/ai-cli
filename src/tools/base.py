"""Core tool system base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from dataclasses import dataclass


@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    data: Any = None
    error: str | None = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error
        }


class Tool(ABC):
    """Abstract base class for all tools.
    
    Tools are functions that AI agents can call to interact with the environment.
    Each tool has a name, description, parameter schema, and execution method.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this tool."""
        pass
    
    @property  
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass
    
    @abstractmethod
    def get_parameters_schema(self) -> dict:
        """Return JSON schema for tool parameters.
        
        This schema is used for function calling APIs like OpenAI's.
        Should follow JSON Schema format.
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters.
        
        Args:
            **kwargs: Parameters as defined by get_parameters_schema()
            
        Returns:
            ToolResult with success status, data, and optional error
        """
        pass
    
    def get_function_schema(self) -> dict:
        """Get OpenAI function calling schema for this tool."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_parameters_schema()
            }
        }


class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool name conflicts with existing tool
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Tool | None:
        """Get tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools.
        
        Returns:
            List of all registered tool instances
        """
        return list(self._tools.values())
    
    def get_tool_names(self) -> List[str]:
        """Get names of all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_function_schemas(self) -> List[dict]:
        """Get all tool schemas for function calling.
        
        Returns:
            List of OpenAI function calling schemas
        """
        return [tool.get_function_schema() for tool in self._tools.values()]
    
    def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name.
        
        Args:
            name: Tool name to execute
            **kwargs: Parameters to pass to tool
            
        Returns:
            ToolResult with execution result
        """
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False, 
                error=f"Tool '{name}' not found. Available tools: {', '.join(self.get_tool_names())}"
            )
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' execution failed: {str(e)}"
            )
    
    def __len__(self) -> int:
        """Return number of registered tools."""
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return tool_name in self._tools
