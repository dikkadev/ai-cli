"""Tests for the agent system."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

from agent import (
    AgentEngine, AgentResult, AgentState, Message, TodoState,
    ToolCallingProvider, MockToolCallingProvider, AgentResponse
)
from tools import ToolRegistry, TodoList
from tools.base import Tool, ToolResult


class MockTestTool(Tool):
    """Simple mock tool for testing."""
    
    @property
    def name(self) -> str:
        return "test_tool"
    
    @property
    def description(self) -> str:
        return "A test tool"
    
    def get_parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action to perform"}
            },
            "required": ["action"]
        }
    
    def execute(self, **kwargs) -> ToolResult:
        action = kwargs.get("action", "default")
        if action == "error":
            return ToolResult(success=False, error="Test error")
        return ToolResult(success=True, data=f"Test result: {action}")


class TestMessage:
    """Test Message class."""
    
    def test_message_creation(self):
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.tool_calls is None
        assert msg.tool_call_id is None
    
    def test_message_with_tool_calls(self):
        tool_calls = [{"id": "call_1", "function": {"name": "test", "arguments": "{}"}}]
        msg = Message(role="assistant", content="I'll use a tool", tool_calls=tool_calls)
        assert msg.tool_calls == tool_calls
    
    def test_message_to_dict(self):
        msg = Message(role="user", content="Test")
        result = msg.to_dict()
        expected = {"role": "user", "content": "Test"}
        assert result == expected
    
    def test_message_to_dict_with_tool_call_id(self):
        msg = Message(role="tool", content="Result", tool_call_id="call_1")
        result = msg.to_dict()
        assert result["tool_call_id"] == "call_1"


class TestTodoState:
    """Test TodoState class."""
    
    def test_todo_state_creation(self):
        state = TodoState()
        assert isinstance(state.todo_list, TodoList)
        assert state.get_current_todos_markdown() == "No todos yet."
    
    def test_todo_state_with_items(self):
        state = TodoState()
        state.todo_list.add("Test task")
        
        markdown = state.get_current_todos_markdown()
        assert "Test task" in markdown
        
        stats = state.get_stats()
        assert stats["total_items"] == 1


class TestAgentState:
    """Test AgentState class."""
    
    def test_agent_state_creation(self):
        state = AgentState()
        assert len(state.messages) == 0
        assert state.iteration_count == 0
        assert state.should_continue is True
        assert state.todo_state is None
    
    def test_add_messages(self):
        state = AgentState()
        
        state.add_user_message("Hello")
        state.add_assistant_message("Hi there")
        state.add_tool_message("Tool result", "call_1")
        
        assert len(state.messages) == 3
        assert state.messages[0].role == "user"
        assert state.messages[1].role == "assistant"
        assert state.messages[2].role == "tool"
    
    def test_get_conversation_for_api(self):
        state = AgentState()
        state.add_user_message("Test")
        
        api_messages = state.get_conversation_for_api()
        assert len(api_messages) == 1
        assert api_messages[0]["role"] == "user"
        assert api_messages[0]["content"] == "Test"
    
    def test_initialize_todo_state(self):
        state = AgentState()
        todo_state = state.initialize_todo_state()
        
        assert state.todo_state is not None
        assert state.todo_state == todo_state
        assert isinstance(todo_state.todo_list, TodoList)
    
    def test_exploration_tracking(self):
        state = AgentState()
        
        file1 = Path("test1.py")
        file2 = Path("test2.py")
        state.add_explored_file(file1)
        state.add_explored_file(file2)
        
        assert file1 in state.files_explored
        assert file2 in state.files_explored
        summary = state.get_exploration_summary()
        assert "2 files" in summary
    
    def test_iteration_management(self):
        state = AgentState()
        
        state.increment_iteration()
        assert state.iteration_count == 1
        
        state.stop_execution("test reason")
        assert state.should_continue is False
        assert state.metadata["stop_reason"] == "test reason"


class TestMockToolCallingProvider:
    """Test MockToolCallingProvider."""
    
    def test_mock_provider_with_predefined_responses(self):
        responses = [
            AgentResponse(message="First", tool_calls=[], should_continue=True),
            AgentResponse(message="Second", tool_calls=[], should_continue=False)
        ]
        provider = MockToolCallingProvider(responses)
        
        result1 = provider.generate_with_tools([], [])
        assert result1.message == "First"
        assert result1.should_continue is True
        
        result2 = provider.generate_with_tools([], [])
        assert result2.message == "Second"
        assert result2.should_continue is False
    
    def test_mock_provider_default_behavior(self):
        provider = MockToolCallingProvider()
        tools = [{"function": {"name": "test_tool"}}]
        
        # First call should use a tool
        result1 = provider.generate_with_tools([], tools)
        assert result1.has_tool_calls()
        assert result1.should_continue is True
        
        # Second call should finish
        result2 = provider.generate_with_tools([], tools)
        assert not result2.has_tool_calls()
        assert result2.should_continue is False


class TestAgentEngine:
    """Test AgentEngine class."""
    
    @pytest.fixture
    def basic_setup(self):
        """Create basic test setup."""
        # Create tool registry
        registry = ToolRegistry()
        registry.register(MockTestTool())
        
        # Create mock provider
        responses = [
            AgentResponse(
                message="I'll use the test tool",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "test_tool", "arguments": '{"action": "hello"}'}
                }],
                should_continue=True
            ),
            AgentResponse(
                message="Task completed",
                tool_calls=[],
                should_continue=False
            )
        ]
        provider = MockToolCallingProvider(responses)
        
        # Create agent state
        state = AgentState()
        
        return registry, provider, state
    
    def test_agent_engine_creation(self, basic_setup):
        registry, provider, state = basic_setup
        
        engine = AgentEngine(provider, registry, state, max_iterations=5)
        
        assert engine.provider == provider
        assert engine.tools == registry
        assert engine.state == state
        assert engine.max_iterations == 5
    
    def test_agent_execution_success(self, basic_setup):
        registry, provider, state = basic_setup
        
        engine = AgentEngine(provider, registry, state, max_iterations=5)
        result = engine.run("Test prompt")
        
        assert result.success is True
        assert result.iterations_used == 2
        assert len(result.state.messages) > 0
        assert "Task completed" in result.final_output["agent_summary"]
    
    def test_agent_execution_with_tool_calls(self, basic_setup):
        registry, provider, state = basic_setup
        
        engine = AgentEngine(provider, registry, state)
        result = engine.run("Use the test tool")
        
        # Check that tool was called
        tool_messages = [m for m in result.state.messages if m.role == "tool"]
        assert len(tool_messages) > 0
        assert "Test result: hello" in tool_messages[0].content
    
    def test_agent_max_iterations_limit(self):
        # Create a provider that never stops
        provider = MockToolCallingProvider([
            AgentResponse(message="Continue", tool_calls=[], should_continue=True)
        ])
        
        registry = ToolRegistry()
        state = AgentState()
        
        engine = AgentEngine(provider, registry, state, max_iterations=3)
        result = engine.run("Never ending task")
        
        assert result.success is True
        assert result.iterations_used == 3
        assert "max_iterations_reached" in result.state.metadata.get("stop_reason", "")
    
    def test_agent_tool_execution_error(self):
        # Create provider that calls non-existent tool
        responses = [
            AgentResponse(
                message="I'll use a non-existent tool",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "nonexistent", "arguments": "{}"}
                }],
                should_continue=True
            ),
            AgentResponse(message="Done", tool_calls=[], should_continue=False)
        ]
        provider = MockToolCallingProvider(responses)
        
        registry = ToolRegistry()
        state = AgentState()
        
        engine = AgentEngine(provider, registry, state)
        result = engine.run("Test error handling")
        
        # Should still succeed but log the error
        assert result.success is True
        tool_messages = [m for m in result.state.messages if m.role == "tool"]
        assert any("not found" in msg.content for msg in tool_messages)
    
    def test_agent_invalid_json_arguments(self, basic_setup):
        registry, _, state = basic_setup
        
        # Provider with invalid JSON in tool arguments
        responses = [
            AgentResponse(
                message="I'll use invalid JSON",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "test_tool", "arguments": "invalid json"}
                }],
                should_continue=True
            ),
            AgentResponse(message="Done", tool_calls=[], should_continue=False)
        ]
        provider = MockToolCallingProvider(responses)
        
        engine = AgentEngine(provider, registry, state)
        result = engine.run("Test invalid JSON")
        
        assert result.success is True
        tool_messages = [m for m in result.state.messages if m.role == "tool"]
        assert any("Invalid JSON" in msg.content for msg in tool_messages)
    
    def test_agent_conversation_summary(self, basic_setup):
        registry, provider, state = basic_setup
        
        engine = AgentEngine(provider, registry, state)
        engine.run("Test conversation")
        
        summary = engine.get_conversation_summary()
        assert "👤 user:" in summary
        assert "🤖 assistant:" in summary
        assert "🔧 tool:" in summary
    
    def test_agent_with_todo_state(self, basic_setup):
        registry, provider, state = basic_setup
        
        # Initialize todo state
        todo_state = state.initialize_todo_state()
        todo_state.todo_list.add("Test task")
        
        engine = AgentEngine(provider, registry, state)
        result = engine.run("Test with todos")
        
        assert "todo_list" in result.final_output
        assert "Test task" in result.final_output["todo_list"]
        assert "todo_stats" in result.final_output
    
    def test_agent_error_handling(self):
        # Create a provider that raises an exception
        class ErrorProvider(ToolCallingProvider):
            def generate_with_tools(self, messages, tools, max_tool_calls=5):
                raise ValueError("Provider error")
        
        provider = ErrorProvider()
        registry = ToolRegistry()
        state = AgentState()
        
        engine = AgentEngine(provider, registry, state)
        result = engine.run("Test error")
        
        assert result.success is False
        assert "Provider error" in result.error


class TestAgentResult:
    """Test AgentResult class."""
    
    def test_successful_result_summary(self):
        state = AgentState()
        state.add_explored_file(Path("test.py"))
        
        result = AgentResult(
            success=True,
            final_output={
                "files_explored": ["test.py"],
                "todo_list": "- [ ] 1. Test task"
            },
            state=state,
            iterations_used=3
        )
        
        summary = result.get_summary()
        assert "Completed successfully in 3 iterations" in summary
        assert "explored 1 files" in summary
        assert "created todo plan" in summary
    
    def test_failed_result_summary(self):
        result = AgentResult(
            success=False,
            final_output={},
            state=AgentState(),
            iterations_used=2,
            error="Something went wrong"
        )
        
        summary = result.get_summary()
        assert "Failed after 2 iterations" in summary
        assert "Something went wrong" in summary
