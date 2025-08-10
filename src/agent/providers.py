"""Enhanced providers with tool calling support for agents."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from dataclasses import dataclass

from .state import Message


@dataclass
class AgentResponse:
    """Response from LLM with potential tool calls."""
    message: str
    tool_calls: List[Dict[str, Any]]
    should_continue: bool = True
    raw_response: Optional[Any] = None
    
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class ToolCallingProvider:
    """Extended provider interface that supports tool/function calling."""
    
    def generate_with_tools(self, 
                          messages: List[Message],
                          tools: List[Dict[str, Any]],
                          max_tool_calls: int = 5) -> AgentResponse:
        """Generate response with potential tool calls.
        
        Args:
            messages: Conversation history
            tools: Available tools as function schemas
            max_tool_calls: Maximum number of tool calls in single response
            
        Returns:
            AgentResponse with message and potential tool calls
        """
        raise NotImplementedError


class OpenAIToolCallingProvider(ToolCallingProvider):
    """OpenAI provider with function calling support."""
    
    def __init__(self, client=None, model: str = "gpt-4o"):
        """Initialize OpenAI tool calling provider.
        
        Args:
            client: OpenAI client instance (created if None)
            model: Model to use for generation
        """
        if client is None:
            from openai import OpenAI
            client = OpenAI()
        
        self.client = client
        self.model = model
    
    def generate_with_tools(self, 
                          messages: List[Message],
                          tools: List[Dict[str, Any]],
                          max_tool_calls: int = 5) -> AgentResponse:
        """Generate response with tool calling support.
        
        Args:
            messages: Conversation history as Message objects
            tools: Available tools as function schemas
            max_tool_calls: Maximum tool calls (used in prompt guidance)
            
        Returns:
            AgentResponse with message content and tool calls
        """
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages_to_openai(messages)
        
        # Prepare API call parameters
        api_params = {
            "model": self.model,
            "messages": openai_messages,
            "max_tokens": 2000,
            "temperature": 0.1,  # Lower temperature for more focused responses
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = "auto"
        
        try:
            # Make API call
            response = self.client.chat.completions.create(**api_params)
            
            message = response.choices[0].message
            
            # Extract message content
            content = message.content or ""
            
            # Extract tool calls if any
            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
            
            # Determine if should continue
            should_continue = self._should_continue_based_on_response(content, tool_calls)
            
            return AgentResponse(
                message=content,
                tool_calls=tool_calls,
                should_continue=should_continue,
                raw_response=response
            )
            
        except Exception as e:
            # Return error response
            return AgentResponse(
                message=f"Error: {str(e)}",
                tool_calls=[],
                should_continue=False
            )
    
    def _convert_messages_to_openai(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Convert Message objects to OpenAI API format.
        
        Args:
            messages: List of Message objects
            
        Returns:
            List of dictionaries in OpenAI message format
        """
        openai_messages = []
        
        for msg in messages:
            openai_msg = {
                "role": msg.role,
                "content": msg.content
            }
            
            # Add tool calls if present
            if msg.tool_calls:
                openai_msg["tool_calls"] = msg.tool_calls
            
            # Add tool call ID if this is a tool response
            if msg.tool_call_id:
                openai_msg["tool_call_id"] = msg.tool_call_id
            
            openai_messages.append(openai_msg)
        
        return openai_messages
    
    def _should_continue_based_on_response(self, content: str, tool_calls: List[Dict]) -> bool:
        """Determine if agent should continue based on response.
        
        Args:
            content: Response content
            tool_calls: List of tool calls
            
        Returns:
            True if agent should continue, False if it should stop
        """
        # Continue if there are tool calls to execute
        if tool_calls:
            return True
        
        # Check for explicit stop signals in content
        stop_signals = [
            "task completed",
            "analysis complete", 
            "plan finished",
            "done",
            "finished",
            "complete"
        ]
        
        content_lower = content.lower()
        for signal in stop_signals:
            if signal in content_lower:
                return False
        
        # Check for explicit continue signals
        continue_signals = [
            "let me",
            "i'll",
            "next",
            "now i",
            "continue"
        ]
        
        for signal in continue_signals:
            if signal in content_lower:
                return True
        
        # Default to stopping if no clear signals
        return False


class MockToolCallingProvider(ToolCallingProvider):
    """Mock provider for testing agent flows."""
    
    def __init__(self, responses: Optional[List[AgentResponse]] = None):
        """Initialize mock provider.
        
        Args:
            responses: Predefined responses to return (cycles through them)
        """
        self.responses = responses or []
        self.call_count = 0
    
    def generate_with_tools(self, 
                          messages: List[Message],
                          tools: List[Dict[str, Any]],
                          max_tool_calls: int = 5) -> AgentResponse:
        """Return predefined response or default response.
        
        Args:
            messages: Conversation history (used for context)
            tools: Available tools (used to generate tool calls)
            max_tool_calls: Maximum tool calls (ignored)
            
        Returns:
            AgentResponse (mock response)
        """
        self.call_count += 1
        
        # Return predefined responses if available
        if self.responses:
            response_index = (self.call_count - 1) % len(self.responses)
            return self.responses[response_index]
        
        # Generate default mock response based on available tools
        if self.call_count == 1 and tools:
            # First call: use a tool
            first_tool = tools[0]["function"]["name"]
            return AgentResponse(
                message=f"I'll use the {first_tool} tool to help with this task.",
                tool_calls=[{
                    "id": f"call_{self.call_count}",
                    "type": "function",
                    "function": {
                        "name": first_tool,
                        "arguments": "{}"
                    }
                }],
                should_continue=True
            )
        else:
            # Subsequent calls: finish
            return AgentResponse(
                message="Task completed successfully.",
                tool_calls=[],
                should_continue=False
            )
