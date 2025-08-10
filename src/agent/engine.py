"""Agent execution engine for iterative tool-based problem solving."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .state import AgentState, Message
from .providers import ToolCallingProvider, AgentResponse
from tools.base import ToolRegistry, ToolResult


@dataclass
class AgentResult:
    """Final result from agent execution."""
    success: bool
    final_output: Dict[str, Any]
    state: AgentState
    iterations_used: int
    error: Optional[str] = None
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the result."""
        if not self.success:
            return f"Failed after {self.iterations_used} iterations: {self.error}"
        
        summary_parts = [
            f"Completed successfully in {self.iterations_used} iterations"
        ]
        
        if "files_explored" in self.final_output:
            file_count = len(self.final_output["files_explored"])
            if file_count > 0:
                summary_parts.append(f"explored {file_count} files")
        
        if "todo_list" in self.final_output:
            summary_parts.append("created todo plan")
        
        return ", ".join(summary_parts)


class AgentEngine:
    """Main agent execution engine with tool calling support."""
    
    def __init__(self, 
                 provider: ToolCallingProvider, 
                 tool_registry: ToolRegistry,
                 state: Optional[AgentState] = None,
                 max_iterations: int = 15,
                 verbose: bool = False):
        """Initialize AgentEngine.
        
        Args:
            provider: LLM provider with tool calling support
            tool_registry: Registry of available tools
            state: Agent state (created if None)
            max_iterations: Maximum iterations before stopping
            verbose: Whether to print detailed execution info
        """
        self.provider = provider
        self.tools = tool_registry
        self.state = state or AgentState()
        self.max_iterations = max_iterations
        self.verbose = verbose
    
    def run(self, initial_prompt: str) -> AgentResult:
        """Main agent execution loop.
        
        Args:
            initial_prompt: Initial prompt to start the agent
            
        Returns:
            AgentResult with execution outcome and final state
        """
        try:
            # Add initial user message
            self.state.add_user_message(initial_prompt)
            
            # Get available tools
            tool_schemas = self.tools.get_function_schemas()
            
            if self.verbose:
                print(f"🤖 Starting agent with {len(tool_schemas)} tools available")
                print(f"📊 Max iterations: {self.max_iterations}")
                tool_names = [tool["function"]["name"] for tool in tool_schemas]
                print(f"🔧 Tools: {', '.join(tool_names)}")
                print(f"🎯 Initial prompt: {initial_prompt[:100]}...")
                print()
            
            # Main execution loop
            while (self.state.iteration_count < self.max_iterations and 
                   self.state.should_continue):
                
                self.state.increment_iteration()
                
                if self.verbose:
                    print(f"🔄 Iteration {self.state.iteration_count}")
                
                # Get response from LLM
                response = self.provider.generate_with_tools(
                    messages=self.state.messages,
                    tools=tool_schemas,
                    max_tool_calls=5
                )
                
                if self.verbose:
                    print(f"💭 LLM Response: {response.message[:150]}...")
                    if response.tool_calls:
                        print(f"🔧 Tool calls requested: {len(response.tool_calls)}")
                
                # Add assistant message
                self.state.add_assistant_message(
                    response.message, 
                    response.tool_calls if response.tool_calls else None
                )
                
                # Execute tool calls if any
                if response.has_tool_calls():
                    success = self._execute_tool_calls(response.tool_calls)
                    if not success:
                        if self.verbose:
                            print("❌ Tool execution failed, stopping agent")
                        break
                else:
                    # No tool calls, update continue flag based on response
                    self.state.should_continue = response.should_continue
                    if self.verbose and not response.should_continue:
                        print("✅ Agent indicated completion")
                
                # Safety check for max iterations
                if self.state.iteration_count >= self.max_iterations:
                    if self.verbose:
                        print(f"⏰ Max iterations ({self.max_iterations}) reached")
                    self.state.stop_execution("max_iterations_reached")
                    break
            
            # Extract final output
            final_output = self._extract_final_output()
            
            if self.verbose:
                print(f"🏁 Agent execution complete")
                print(f"📈 Final result: {len(final_output)} output fields")
            
            return AgentResult(
                success=True,
                final_output=final_output,
                state=self.state,
                iterations_used=self.state.iteration_count
            )
            
        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            if self.verbose:
                print(f"💥 {error_msg}")
            
            return AgentResult(
                success=False,
                final_output={},
                state=self.state,
                iterations_used=self.state.iteration_count,
                error=error_msg
            )
    
    def _execute_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> bool:
        """Execute tool calls and add results to conversation.
        
        Args:
            tool_calls: List of tool calls from LLM response
            
        Returns:
            True if all tool calls succeeded, False if any failed critically
        """
        for tool_call in tool_calls:
            try:
                # Parse tool call
                function_name = tool_call["function"]["name"]
                arguments_str = tool_call["function"]["arguments"]
                tool_call_id = tool_call["id"]
                
                # Parse arguments
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON arguments for {function_name}: {str(e)}"
                    self.state.add_tool_message(error_msg, tool_call_id)
                    if self.verbose:
                        print(f"❌ JSON error: {error_msg}")
                    continue
                
                if self.verbose:
                    print(f"🔧 Executing: {function_name}({self._format_args(arguments)})")
                
                # Execute tool
                result = self.tools.execute_tool(function_name, **arguments)
                
                # Track file exploration for read_file tool
                if function_name == "read_file" and result.success:
                    if "path" in arguments:
                        from pathlib import Path
                        self.state.add_explored_file(Path(arguments["path"]))
                
                # Format result for LLM
                result_content = self._format_tool_result(result, function_name)
                
                # Add tool result message
                self.state.add_tool_message(result_content, tool_call_id)
                
                if self.verbose:
                    status = "✅" if result.success else "❌"
                    print(f"{status} Tool result: {result_content[:100]}...")
                
            except Exception as e:
                error_content = f"Tool execution failed: {str(e)}"
                self.state.add_tool_message(error_content, tool_call.get("id", "unknown"))
                
                if self.verbose:
                    print(f"💥 Tool error: {error_content}")
        
        return True  # Continue execution even if some tools fail
    
    def _format_args(self, args: Dict[str, Any]) -> str:
        """Format arguments for display.
        
        Args:
            args: Tool arguments
            
        Returns:
            Formatted string representation
        """
        if not args:
            return ""
        
        formatted_args = []
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 30:
                value = value[:30] + "..."
            formatted_args.append(f"{key}={repr(value)}")
        
        return ", ".join(formatted_args)
    
    def _format_tool_result(self, result: ToolResult, tool_name: str) -> str:
        """Format tool result for LLM consumption.
        
        Args:
            result: Tool execution result
            tool_name: Name of the tool that was executed
            
        Returns:
            Formatted result string
        """
        if result.success:
            if result.data:
                # Handle different data types appropriately
                if isinstance(result.data, dict):
                    return json.dumps(result.data, indent=2)
                elif isinstance(result.data, str):
                    return result.data
                else:
                    return str(result.data)
            else:
                return f"{tool_name} executed successfully"
        else:
            return f"Error: {result.error}"
    
    def _extract_final_output(self) -> Dict[str, Any]:
        """Extract meaningful output from agent execution.
        
        Returns:
            Dictionary with final output data
        """
        # Get last assistant message
        last_message = self.state.get_last_assistant_message()
        
        # Build output
        output = {
            "agent_summary": last_message.content if last_message else "No final message",
            "iterations_used": self.state.iteration_count,
            "conversation_length": len(self.state.messages),
            "exploration_summary": self.state.get_exploration_summary(),
            "files_explored": [str(p) for p in self.state.files_explored]
        }
        
        # Add use-case specific output
        if self.state.todo_state:
            output["todo_list"] = self.state.todo_state.get_current_todos_markdown()
            output["todo_stats"] = self.state.todo_state.get_stats()
        
        # Add any metadata
        output.update(self.state.metadata)
        
        return output
    
    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for debugging.
        
        Returns:
            String summary of the conversation flow
        """
        summary_lines = []
        
        for i, message in enumerate(self.state.messages):
            role_emoji = {"user": "👤", "assistant": "🤖", "tool": "🔧"}
            emoji = role_emoji.get(message.role, "❓")
            
            content_preview = message.content[:80] + "..." if len(message.content) > 80 else message.content
            summary_lines.append(f"{i+1:2d}. {emoji} {message.role}: {content_preview}")
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_name = tc["function"]["name"]
                    summary_lines.append(f"    └─ Tool call: {tool_name}")
        
        return "\n".join(summary_lines)
