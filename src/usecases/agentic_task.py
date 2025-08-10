"""Agentic version of the task planning usecase.

This usecase uses the agent system to iteratively explore the project,
understand the requirements, and create comprehensive action plans.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from agent import AgentEngine, AgentState, OpenAIToolCallingProvider
from core.blacklist import Blacklist
from core.models import SourceRef, UsecaseInput, UsecaseOutput
from core.sandbox import SandboxMode
from tools import ToolRegistry, TreeTool, ReadFileTool, TodoViewTool, TodoEditTool, TodoAddTool
from usecases.ask import usecase


class AgenticTaskInput(UsecaseInput):
    """Input for agentic task usecase."""
    objective: str = Field(description="The task or objective to plan and analyze")
    mode: Literal["plan", "explore+plan"] = Field(
        default="explore+plan", 
        description="Mode: 'plan' (quick planning), 'explore+plan' (thorough exploration + planning)"
    )
    risk_level: Literal["conservative", "moderate", "aggressive"] = Field(
        default="moderate", 
        description="Risk tolerance for the plan"
    )
    exploration_depth: int = Field(
        default=3, 
        description="Directory exploration depth (1-5)",
        ge=1, 
        le=5
    )
    max_iterations: int = Field(
        default=15, 
        description="Maximum agent iterations (5-50)",
        ge=5, 
        le=50
    )
    context_files: list[str] = Field(
        default_factory=list, 
        description="Specific files to prioritize during exploration"
    )


class AgenticTaskOutput(UsecaseOutput):
    """Output from agentic task usecase."""
    objective: str = Field(description="Original objective")
    plan: str = Field(description="Final todo list/plan in markdown format")
    exploration_summary: str = Field(description="Summary of project exploration")
    agent_reasoning: str = Field(description="Final reasoning and recommendations from agent")
    iterations_used: int = Field(description="Number of agent iterations used")
    files_explored: list[str] = Field(description="List of files that were analyzed")
    todo_stats: dict = Field(description="Statistics about the generated plan")
    sources: list[SourceRef] = Field(default_factory=list, description="Sources used")
    success: bool = Field(description="Whether the agent completed successfully")


@usecase(
    id="agentic_task",
    summary="AI agent that explores projects and creates comprehensive action plans",
    sandbox=SandboxMode.FULL,
    allows_writes=False,
    default_context=[]  # Agent will explore dynamically
)
class AgenticTask:
    """Agentic task planning usecase that uses AI agent with tools."""
    
    InputModel = AgenticTaskInput
    OutputModel = AgenticTaskOutput
    
    @staticmethod
    def execute(input_data: AgenticTaskInput, provider, project_root: Path) -> AgenticTaskOutput:
        """Execute the agentic task planning.
        
        Args:
            input_data: Input parameters for the task
            provider: LLM provider (will be wrapped for tool calling)
            project_root: Root directory of the project
            
        Returns:
            AgenticTaskOutput with comprehensive plan and analysis
        """
        # Create tool calling provider
        if hasattr(provider, 'generate_with_tools'):
            # Already a tool calling provider
            tool_provider = provider
        else:
            # Wrap regular provider - for now we'll use OpenAI directly
            tool_provider = OpenAIToolCallingProvider(model="gpt-4o")
        
        # Set up tools and agent state
        tool_registry, agent_state = AgenticTask._setup_agent_components(
            project_root, input_data
        )
        
        # Create agent
        agent = AgentEngine(
            provider=tool_provider,
            tool_registry=tool_registry,
            state=agent_state,
            max_iterations=input_data.max_iterations,
            verbose=False  # Will be controlled by CLI verbose flag
        )
        
        # Create initial prompt
        initial_prompt = AgenticTask._create_agent_prompt(input_data)
        
        # Run agent
        result = agent.run(initial_prompt)
        
        # Convert result to output format
        return AgenticTask._convert_agent_result(result, input_data)
    
    @staticmethod
    def _setup_agent_components(project_root: Path, input_data: AgenticTaskInput) -> tuple:
        """Set up tool registry and agent state.
        
        Args:
            project_root: Project root directory
            input_data: Input parameters
            
        Returns:
            Tuple of (ToolRegistry, AgentState)
        """
        # Create blacklist for security
        blacklist = Blacklist()
        
        # Create tool registry
        registry = ToolRegistry()
        
        # Register filesystem tools
        registry.register(TreeTool(project_root, blacklist))
        registry.register(ReadFileTool(project_root, blacklist))
        
        # Create agent state with todo management
        state = AgentState()
        todo_state = state.initialize_todo_state()
        
        # Register todo tools (linked to the state)
        registry.register(TodoViewTool(todo_state.todo_list))
        registry.register(TodoEditTool(todo_state.todo_list))
        registry.register(TodoAddTool(todo_state.todo_list))
        
        # Set initial focus
        state.set_focus(input_data.objective)
        
        return registry, state
    
    @staticmethod
    def _create_agent_prompt(input_data: AgenticTaskInput) -> str:
        """Create the initial prompt for the agent.
        
        Args:
            input_data: Input parameters
            
        Returns:
            Formatted prompt string
        """
        # Risk level guidance
        risk_guidance = {
            "conservative": (
                "Take a conservative approach prioritizing safety and stability. "
                "Focus on thorough testing, gradual implementation, and minimal risk. "
                "Prefer well-established patterns and avoid experimental approaches."
            ),
            "moderate": (
                "Balance speed with safety. Consider both quick wins and long-term stability. "
                "Take reasonable risks where benefits are clear, but maintain good practices."
            ),
            "aggressive": (
                "Move fast and prioritize rapid implementation. Accept higher risks for speed. "
                "Focus on minimum viable solutions and iterate quickly. "
                "Use cutting-edge approaches where they provide clear advantages."
            )
        }
        
        # Mode guidance
        mode_guidance = {
            "plan": (
                "Focus primarily on creating a comprehensive plan. "
                "Do minimal exploration, just enough to understand the context."
            ),
            "explore+plan": (
                "First thoroughly explore and understand the project structure, "
                "then create a detailed, context-aware plan."
            )
        }
        
        # Build prompt
        prompt_parts = [
            f"You are an expert technical planning agent helping with software development tasks.",
            f"",
            f"OBJECTIVE: {input_data.objective}",
            f"",
            f"MODE: {mode_guidance.get(input_data.mode, 'Create comprehensive plan')}",
            f"",
            f"RISK APPROACH: {risk_guidance.get(input_data.risk_level, 'Use balanced approach')}",
            f"",
            f"AVAILABLE TOOLS:",
            f"- tree(depth, path): Explore project directory structure",
            f"- read_file(path): Read and analyze file contents (respects security blacklist)", 
            f"- todo_add(text): Add new todo items to create structured plan",
            f"- todo_edit(number, completed, text): Edit existing todo items",
            f"- todo_view(): View current todo list in markdown format",
            f"",
            f"PROCESS:",
        ]
        
        if input_data.mode == "explore+plan":
            prompt_parts.extend([
                f"1. Start by exploring the project structure with tree tool (depth {input_data.exploration_depth})",
                f"2. Read key files to understand architecture, dependencies, and current state",
                f"3. If specific files were mentioned, prioritize reading: {', '.join(input_data.context_files) if input_data.context_files else 'none specified'}",
                f"4. Create comprehensive todo list breaking down the objective into specific, actionable steps",
                f"5. Organize todos by priority and dependencies",
                f"6. Mark any completed analysis/exploration todos as done",
                f"7. Provide final summary with recommendations",
            ])
        else:
            prompt_parts.extend([
                f"1. Quickly understand the context (minimal exploration)",
                f"2. Create a structured todo list for the objective",
                f"3. Focus on actionable, prioritized steps",
                f"4. Provide concise recommendations",
            ])
        
        prompt_parts.extend([
            f"",
            f"IMPORTANT:",
            f"- Each todo should be specific and actionable",
            f"- Consider dependencies between todos",
            f"- Include testing and validation steps",
            f"- Think about edge cases and potential issues",
            f"- Provide rationale for your planning decisions",
            f"",
            f"Begin by exploring the project to understand what you're working with, then create a comprehensive plan."
        ])
        
        return "\n".join(prompt_parts)
    
    @staticmethod
    def _convert_agent_result(agent_result, input_data: AgenticTaskInput) -> AgenticTaskOutput:
        """Convert agent execution result to usecase output format.
        
        Args:
            agent_result: Result from agent execution
            input_data: Original input data
            
        Returns:
            AgenticTaskOutput with formatted results
        """
        if agent_result.success:
            # Extract data from agent result
            final_output = agent_result.final_output
            
            # Get todo list and stats
            todo_list = final_output.get("todo_list", "No plan created")
            todo_stats = final_output.get("todo_stats", {"total_items": 0, "completed_items": 0, "pending_items": 0})
            
            # Get agent's reasoning (last assistant message)
            agent_reasoning = final_output.get("agent_summary", "No reasoning provided")
            
            # Get exploration summary
            exploration_summary = final_output.get("exploration_summary", "No exploration performed")
            files_explored = final_output.get("files_explored", [])
            
            # Create source references for explored files
            sources = []
            for file_path in files_explored:
                try:
                    full_path = Path(file_path)
                    if full_path.exists():
                        size = full_path.stat().st_size
                        sources.append(SourceRef(path=file_path, bytes=size))
                except Exception:
                    # Skip files that can't be accessed
                    pass
            
            return AgenticTaskOutput(
                objective=input_data.objective,
                plan=todo_list,
                exploration_summary=exploration_summary,
                agent_reasoning=agent_reasoning,
                iterations_used=agent_result.iterations_used,
                files_explored=files_explored,
                todo_stats=todo_stats,
                sources=sources,
                success=True
            )
        else:
            # Handle failure case
            return AgenticTaskOutput(
                objective=input_data.objective,
                plan=f"Planning failed: {agent_result.error}",
                exploration_summary="Exploration failed due to agent error",
                agent_reasoning=f"Agent execution failed: {agent_result.error}",
                iterations_used=agent_result.iterations_used,
                files_explored=[],
                todo_stats={"total_items": 0, "completed_items": 0, "pending_items": 0},
                sources=[],
                success=False
            )
