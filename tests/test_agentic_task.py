"""Tests for the agentic task usecase."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from agent import MockToolCallingProvider, AgentResponse
from usecases.agentic_task import AgenticTask, AgenticTaskInput, AgenticTaskOutput


class TestAgenticTaskInput:
    """Test AgenticTaskInput model."""
    
    def test_default_values(self):
        input_data = AgenticTaskInput(objective="Test objective")
        
        assert input_data.objective == "Test objective"
        assert input_data.mode == "explore+plan"
        assert input_data.risk_level == "moderate"
        assert input_data.exploration_depth == 3
        assert input_data.max_iterations == 15
        assert input_data.context_files == []
    
    def test_custom_values(self):
        input_data = AgenticTaskInput(
            objective="Custom objective",
            mode="plan",
            risk_level="conservative",
            exploration_depth=2,
            max_iterations=10,
            context_files=["test.py"]
        )
        
        assert input_data.mode == "plan"
        assert input_data.risk_level == "conservative"
        assert input_data.exploration_depth == 2
        assert input_data.max_iterations == 10
        assert input_data.context_files == ["test.py"]
    
    def test_validation_ranges(self):
        # Test valid ranges
        input_data = AgenticTaskInput(
            objective="Test",
            exploration_depth=1,
            max_iterations=5
        )
        assert input_data.exploration_depth == 1
        assert input_data.max_iterations == 5
        
        # Test boundary values
        input_data = AgenticTaskInput(
            objective="Test",
            exploration_depth=5,
            max_iterations=50
        )
        assert input_data.exploration_depth == 5
        assert input_data.max_iterations == 50


class TestAgenticTaskOutput:
    """Test AgenticTaskOutput model."""
    
    def test_output_creation(self):
        output = AgenticTaskOutput(
            objective="Test objective",
            plan="- [ ] 1. Test task",
            exploration_summary="Explored 2 files",
            agent_reasoning="Test reasoning",
            iterations_used=5,
            files_explored=["test.py"],
            todo_stats={"total_items": 1, "completed_items": 0, "pending_items": 1},
            success=True
        )
        
        assert output.objective == "Test objective"
        assert output.plan == "- [ ] 1. Test task"
        assert output.success is True
        assert len(output.files_explored) == 1


class TestAgenticTask:
    """Test AgenticTask usecase."""
    
    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("print('hello')")
        (tmp_path / "README.md").write_text("# Test Project")
        return tmp_path
    
    @pytest.fixture
    def mock_responses(self):
        """Create mock agent responses."""
        return [
            AgentResponse(
                message="I'll explore the project structure first.",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "tree",
                        "arguments": '{"depth": 2}'
                    }
                }],
                should_continue=True
            ),
            AgentResponse(
                message="Now I'll read the README to understand the project.",
                tool_calls=[{
                    "id": "call_2",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": '{"path": "README.md"}'
                    }
                }],
                should_continue=True
            ),
            AgentResponse(
                message="I'll create a structured plan for the objective.",
                tool_calls=[
                    {
                        "id": "call_3",
                        "type": "function",
                        "function": {
                            "name": "todo_add",
                            "arguments": '{"text": "Analyze current architecture"}'
                        }
                    },
                    {
                        "id": "call_4",
                        "type": "function",
                        "function": {
                            "name": "todo_add",
                            "arguments": '{"text": "Implement new feature"}'
                        }
                    }
                ],
                should_continue=True
            ),
            AgentResponse(
                message="Let me view the current plan and mark analysis complete.",
                tool_calls=[
                    {
                        "id": "call_5",
                        "type": "function",
                        "function": {
                            "name": "todo_view",
                            "arguments": '{}'
                        }
                    },
                    {
                        "id": "call_6",
                        "type": "function",
                        "function": {
                            "name": "todo_edit",
                            "arguments": '{"number": 1, "completed": true}'
                        }
                    }
                ],
                should_continue=True
            ),
            AgentResponse(
                message="Perfect! I've analyzed the project and created a comprehensive plan.",
                tool_calls=[],
                should_continue=False
            )
        ]
    
    def test_agentic_task_execution_success(self, temp_project, mock_responses):
        """Test successful agentic task execution."""
        # Create input
        input_data = AgenticTaskInput(
            objective="Add new feature to the project",
            mode="explore+plan",
            risk_level="moderate",
            max_iterations=10
        )
        
        # Create mock provider
        provider = MockToolCallingProvider(mock_responses)
        
        # Execute
        result = AgenticTask.execute(input_data, provider, temp_project)
        
        # Verify result
        assert result.success is True
        assert result.objective == "Add new feature to the project"
        assert result.iterations_used == 5
        assert len(result.files_explored) > 0
        assert "Analyze current architecture" in result.plan or "No plan created" in result.plan
        assert result.exploration_summary != "No exploration performed"
    
    def test_agentic_task_plan_mode(self, temp_project):
        """Test agentic task in plan mode (minimal exploration)."""
        input_data = AgenticTaskInput(
            objective="Quick planning task",
            mode="plan",
            max_iterations=5
        )
        
        # Simple responses for plan mode
        responses = [
            AgentResponse(
                message="I'll create a quick plan.",
                tool_calls=[{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "todo_add",
                        "arguments": '{"text": "Quick task 1"}'
                    }
                }],
                should_continue=True
            ),
            AgentResponse(
                message="Plan completed.",
                tool_calls=[],
                should_continue=False
            )
        ]
        
        provider = MockToolCallingProvider(responses)
        result = AgenticTask.execute(input_data, provider, temp_project)
        
        assert result.success is True
        assert result.iterations_used == 2
    
    def test_agentic_task_with_context_files(self, temp_project, mock_responses):
        """Test agentic task with specific context files."""
        input_data = AgenticTaskInput(
            objective="Refactor main.py",
            context_files=["src/main.py", "README.md"],
            exploration_depth=2
        )
        
        provider = MockToolCallingProvider(mock_responses)
        result = AgenticTask.execute(input_data, provider, temp_project)
        
        assert result.success is True
        assert result.objective == "Refactor main.py"
    
    def test_agentic_task_risk_levels(self, temp_project):
        """Test different risk levels."""
        for risk_level in ["conservative", "moderate", "aggressive"]:
            input_data = AgenticTaskInput(
                objective=f"Test {risk_level} approach",
                risk_level=risk_level,
                max_iterations=5
            )
            
            responses = [
                AgentResponse(
                    message=f"Using {risk_level} approach",
                    tool_calls=[],
                    should_continue=False
                )
            ]
            
            provider = MockToolCallingProvider(responses)
            result = AgenticTask.execute(input_data, provider, temp_project)
            
            assert result.success is True
            assert risk_level in result.agent_reasoning or "approach" in result.agent_reasoning.lower()
    
    def test_agentic_task_failure_handling(self, temp_project):
        """Test handling of agent execution failures."""
        input_data = AgenticTaskInput(
            objective="This will fail",
            max_iterations=5
        )
        
        # Create a provider that will cause agent failure
        class FailingProvider(MockToolCallingProvider):
            def generate_with_tools(self, messages, tools, max_tool_calls=5):
                raise ValueError("Provider failure")
        
        provider = FailingProvider()
        result = AgenticTask.execute(input_data, provider, temp_project)
        
        assert result.success is False
        assert "failed" in result.plan.lower()
        assert "Provider failure" in result.agent_reasoning
    
    def test_setup_agent_components(self, temp_project):
        """Test the setup of agent components."""
        input_data = AgenticTaskInput(objective="Test setup")
        
        registry, state = AgenticTask._setup_agent_components(temp_project, input_data)
        
        # Check tool registry
        assert len(registry) > 0
        assert "tree" in registry
        assert "read_file" in registry
        assert "todo_view" in registry
        assert "todo_edit" in registry
        assert "todo_add" in registry
        
        # Check agent state
        assert state.current_focus == "Test setup"
        assert state.todo_state is not None
    
    def test_create_agent_prompt(self):
        """Test agent prompt creation."""
        input_data = AgenticTaskInput(
            objective="Test objective",
            mode="explore+plan",
            risk_level="conservative",
            context_files=["test.py"]
        )
        
        prompt = AgenticTask._create_agent_prompt(input_data)
        
        assert "Test objective" in prompt
        assert "conservative" in prompt
        assert "thoroughly explore and understand" in prompt
        assert "test.py" in prompt
        assert "tree" in prompt
        assert "read_file" in prompt
        assert "todo_add" in prompt
    
    def test_convert_agent_result_success(self):
        """Test conversion of successful agent result."""
        from agent import AgentResult, AgentState
        
        state = AgentState()
        state.add_explored_file(Path("test.py"))
        
        agent_result = AgentResult(
            success=True,
            final_output={
                "todo_list": "- [ ] 1. Test task",
                "todo_stats": {"total_items": 1, "completed_items": 0, "pending_items": 1},
                "agent_summary": "Task completed successfully",
                "exploration_summary": "Explored 1 file",
                "files_explored": ["test.py"]
            },
            state=state,
            iterations_used=3
        )
        
        input_data = AgenticTaskInput(objective="Test")
        result = AgenticTask._convert_agent_result(agent_result, input_data)
        
        assert result.success is True
        assert result.plan == "- [ ] 1. Test task"
        assert result.iterations_used == 3
        assert result.files_explored == ["test.py"]
        # Sources would be created if files existed - test passes without them
    
    def test_convert_agent_result_failure(self):
        """Test conversion of failed agent result."""
        from agent import AgentResult, AgentState
        
        agent_result = AgentResult(
            success=False,
            final_output={},
            state=AgentState(),
            iterations_used=2,
            error="Agent failed"
        )
        
        input_data = AgenticTaskInput(objective="Test")
        result = AgenticTask._convert_agent_result(agent_result, input_data)
        
        assert result.success is False
        assert "Agent failed" in result.plan
        assert result.iterations_used == 2
        assert result.files_explored == []
        assert result.todo_stats["total_items"] == 0
