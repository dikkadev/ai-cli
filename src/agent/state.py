"""Agent state management for maintaining context during execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.todo import TodoList


@dataclass
class Message:
    """Represents a message in the agent conversation."""
    role: str  # "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        result = {
            "role": self.role,
            "content": self.content
        }
        
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        
        return result


@dataclass
class TodoState:
    """State related to todo management."""
    todo_list: TodoList = field(default_factory=TodoList)
    
    def get_current_todos_markdown(self) -> str:
        """Get current todos in markdown format."""
        return self.todo_list.to_markdown()
    
    def get_stats(self) -> Dict[str, int]:
        """Get todo statistics."""
        return self.todo_list.get_stats()


@dataclass  
class AgentState:
    """Maintains state during agent execution."""
    
    # Conversation history
    messages: List[Message] = field(default_factory=list)
    
    # Execution tracking
    files_explored: set[Path] = field(default_factory=set)
    current_focus: Optional[str] = None
    iteration_count: int = 0
    should_continue: bool = True
    
    # Use case specific state
    todo_state: Optional[TodoState] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.messages.append(message)
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.add_message(Message(role="user", content=content))
    
    def add_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None) -> None:
        """Add an assistant message to the conversation."""
        self.add_message(Message(role="assistant", content=content, tool_calls=tool_calls))
    
    def add_tool_message(self, content: str, tool_call_id: str) -> None:
        """Add a tool result message to the conversation."""
        self.add_message(Message(role="tool", content=content, tool_call_id=tool_call_id))
    
    def get_conversation_for_api(self) -> List[Dict[str, Any]]:
        """Get conversation in format suitable for API calls."""
        return [msg.to_dict() for msg in self.messages]
    
    def get_last_assistant_message(self) -> Optional[Message]:
        """Get the most recent assistant message."""
        for message in reversed(self.messages):
            if message.role == "assistant":
                return message
        return None
    
    def add_explored_file(self, file_path: Path) -> None:
        """Track a file that was explored."""
        self.files_explored.add(file_path)
    
    def get_exploration_summary(self) -> str:
        """Get summary of exploration activity."""
        file_count = len(self.files_explored)
        if file_count == 0:
            return "No files explored"
        elif file_count == 1:
            return f"Explored 1 file: {list(self.files_explored)[0]}"
        else:
            return f"Explored {file_count} files and directories"
    
    def initialize_todo_state(self) -> TodoState:
        """Initialize todo state if not already present."""
        if self.todo_state is None:
            self.todo_state = TodoState()
        return self.todo_state
    
    def set_focus(self, focus: str) -> None:
        """Set the current focus/objective."""
        self.current_focus = focus
    
    def increment_iteration(self) -> None:
        """Increment iteration counter."""
        self.iteration_count += 1
    
    def should_stop(self) -> bool:
        """Check if agent should stop execution."""
        return not self.should_continue
    
    def stop_execution(self, reason: Optional[str] = None) -> None:
        """Stop agent execution."""
        self.should_continue = False
        if reason:
            self.metadata["stop_reason"] = reason
