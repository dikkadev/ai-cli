# AI CLI

A modern command-line tool that provides AI-powered assistance for development tasks, featuring both traditional AI commands and an advanced **agentic AI system** that can explore projects and create comprehensive action plans.

## 🚀 Features

### Traditional AI Commands
- **`ai ask`**: Question answering with optional project context
- **`ai task`**: Structured planning and task breakdown with risk assessment  
- **`ai testwrite`**: Test code generation with safe file writing capabilities

### 🤖 Agentic AI System (NEW!)
- **`ai agentic-task`**: Deploy an AI agent that iteratively explores your project, understands the codebase, and creates detailed, context-aware action plans

## ⚡ Quick Start

### Development Mode

```bash
# Clone and enter directory
cd /path/to/ai-cli

# Install dependencies  
uv sync

# Run from project directory
uv run ai

# Examples - Traditional Commands
uv run ai ask "What does this project do?" --context
uv run ai task "Add error handling" --risk-level conservative
uv run ai testwrite src/utils.py --write --framework pytest

# Examples - Agentic AI Agent
uv run ai agentic-task "Add user authentication"
uv run ai agentic-task "Optimize database performance" --mode explore+plan --risk-level conservative
```

### Global Installation

To install globally so you can use `ai` from anywhere:

#### Option 1: Install from Local Directory (Recommended)

```bash
# From the project directory
uv tool install .

# Or with explicit path
uv tool install /path/to/ai-cli/main

# Now use from anywhere
ai ask "What is this codebase about?" --context
ai agentic-task "Add monitoring to this service" --mode explore+plan
```

#### Option 2: Install in Development Mode (for active development)

```bash
# Install in editable mode (changes to code take effect immediately)
uv tool install --editable .

# Uninstall when done
uv tool uninstall ai-cli
```

#### Option 3: Manual Install via pip (if uv tool isn't available)

```bash
# Build and install
uv build
pip install dist/ai_cli-*.whl

# Or install directly
pip install .
```

### Setup

1. **Set OpenAI API Key**:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   # Add to ~/.bashrc or ~/.zshrc for persistence
   ```

2. **Test Installation**:
   ```bash
   ai --help
   ai ask "Hello world"
   ai agentic-task "Create a simple todo app" --mode plan --max-iterations 5
   ```

## 🎯 Usage Examples

### Traditional Commands

```bash
# Question answering with project context
ai ask "How does authentication work in this codebase?" --context

# Structured planning 
ai task "Implement user registration" --mode plan+steps --risk-level moderate

# Generate tests with file writing
ai testwrite src/auth.py --framework pytest --write

# Preview test generation without writing
ai testwrite src/utils.py --framework unittest
```

### 🤖 Agentic AI Agent

The agentic AI agent can explore your project, understand the architecture, and create comprehensive action plans:

```bash
# Basic agentic planning
ai agentic-task "Add user authentication"
ai agentic-task "Implement real-time notifications"
ai agentic-task "Optimize database queries" --risk-level conservative

# Advanced configuration
ai agentic-task "Refactor API architecture" \
  --mode explore+plan \
  --risk-level moderate \
  --max-iterations 20 \
  --exploration-depth 3 \
  --file "src/api/main.py" \
  --file "docs/architecture.md" \
  --verbose

# Quick planning mode (faster, less exploration)
ai agentic-task "Fix login bug" --mode plan --max-iterations 5

# Focused exploration for specific components
ai agentic-task "Add monitoring to payment service" \
  --file "src/payments/" \
  --exploration-depth 2
```

## 🤖 How Agentic AI Works

Unlike traditional AI commands that provide one-shot responses, the agentic AI agent works iteratively:

### Agent Capabilities
- **🌳 Project Exploration**: Uses `tree` tool to understand directory structure
- **📄 File Analysis**: Reads and analyzes key files (respects security blacklist)
- **📋 Todo Management**: Creates, edits, and organizes structured action items
- **🧠 Iterative Planning**: Refines plans based on discoveries
- **🎯 Context-Aware**: Tailors recommendations to your specific project

### Agent Workflow
1. **Explore** project structure using configurable depth
2. **Analyze** key files to understand current architecture and dependencies
3. **Plan** by creating numbered, actionable todo items
4. **Organize** tasks by priority and dependencies
5. **Reason** about implementation strategies and potential risks
6. **Refine** the plan iteratively until comprehensive

### Agent Modes
- **`plan`**: Quick planning with minimal exploration (faster)
- **`explore+plan`**: Thorough exploration followed by detailed planning (comprehensive)

### Risk Levels
- **`conservative`**: Emphasizes safety, testing, gradual implementation
- **`moderate`**: Balanced approach with reasonable safeguards  
- **`aggressive`**: Fast execution, accepting higher risks for speed

### Example Agent Output

When you run `ai agentic-task "Add user authentication"`, the agent will:

1. 🌳 Explore your project structure to understand the current setup
2. 📄 Read key files like `main.py`, `models.py`, `requirements.txt`
3. 🧠 Analyze the architecture and identify integration points
4. 📋 Create a structured plan like:

```markdown
Generated Action Plan:
- [x] 1. ✓ ANALYSIS: Explored FastAPI project structure
- [ ] 2. Install authentication dependencies (passlib, python-jose)
- [ ] 3. Extend User model with password_hash and email fields
- [ ] 4. Create authentication utilities (password hashing, JWT)
- [ ] 5. Add login/register endpoints to API router
- [ ] 6. Add authentication middleware for route protection
- [ ] 7. Update existing routes to require authentication
- [ ] 8. Add comprehensive tests for auth endpoints
```

5. 💭 Provide detailed reasoning about the implementation approach
6. 📊 Show statistics about the plan (8 tasks, 1 completed, 7 pending)

## 🛡️ Safety Features

### Sandbox Protection
- **Restricted Operations**: All operations limited to current project directory
- **Read-Only by Default**: File modifications require explicit `--write` consent
- **Blacklist Filtering**: Automatic exclusion of sensitive files (.env, keys, credentials)
- **Interactive Confirmations**: Prompts before making changes (override with `--force`)

### Agent-Specific Safety
- **Tool Restrictions**: Agents can only use approved, sandboxed tools
- **Iteration Limits**: Configurable maximum iterations (5-50) prevent runaway execution
- **Content Filtering**: Automatic redaction of sensitive information
- **Audit Trail**: All agent actions and tool usage are logged

### Context Controls
- **File Size Limits**: Automatic restrictions on large files and binary content
- **File Count Limits**: Prevents excessive context collection
- **Selective Inclusion**: Fine-grained control over which files to analyze

## 🔧 Development

### Architecture Overview

The AI CLI features a dual architecture:

1. **Traditional System**: Direct LLM calls for quick responses (`ask`, `task`, `testwrite`)
2. **Agentic System**: Iterative AI agents with tool access (`agentic-task`)

### Agentic Architecture Components

- **Tool System** (`src/tools/`): Pluggable tools for file exploration, todo management
- **Agent Engine** (`src/agent/`): Execution loop with OpenAI function calling
- **Agent State**: Conversation history, file tracking, todo lists
- **Provider System**: LLM abstraction with tool calling support

### Adding New Tools

```python
from tools.base import Tool, ToolResult

class CustomTool(Tool):
    @property
    def name(self) -> str:
        return "custom_tool"
    
    @property
    def description(self) -> str:
        return "Description for AI agent"
    
    def get_parameters_schema(self) -> dict:
        return {"type": "object", "properties": {...}}
    
    def execute(self, **kwargs) -> ToolResult:
        # Tool implementation
        return ToolResult(success=True, data=result)
```

### Testing

```bash
# Run all tests
uv run python -m pytest

# Run specific test categories
uv run python -m pytest tests/test_tools.py      # Tool system tests
uv run python -m pytest tests/test_agent.py      # Agent engine tests  
uv run python -m pytest tests/test_agentic_task.py  # Agentic usecase tests

# Run with coverage
uv run python -m pytest --cov=src tests/
```

### Documentation

See `DEVELOPER_HANDOFF.md` for comprehensive development documentation including:
- Detailed architecture overview and design patterns
- Security model and sandbox system
- Adding new use cases and providers
- Testing strategy and troubleshooting guides

## 📈 Performance & Scaling

### Traditional Commands
- **Speed**: Near-instant responses (< 2 seconds)
- **Cost**: Single LLM call per request
- **Use Case**: Quick questions, simple planning, code generation

### Agentic Commands  
- **Speed**: Moderate (30 seconds - 3 minutes depending on complexity)
- **Cost**: Multiple LLM calls (typically 3-15 calls per task)
- **Use Case**: Complex planning, project exploration, comprehensive analysis

### Optimization Tips
- Use `--mode plan` for faster agentic responses
- Set `--max-iterations 5-10` for quicker results
- Use `--exploration-depth 1-2` for simpler projects
- Traditional commands for simple questions, agentic for complex planning

## 🆚 When to Use Which Command

| Use Case | Command | Why |
|----------|---------|-----|
| Quick questions about code | `ai ask` | Fast, contextual answers |
| Simple task planning | `ai task` | Structured plans without exploration |
| Generate tests | `ai testwrite` | Specialized for test generation |
| **Complex project planning** | `ai agentic-task` | **Explores and understands before planning** |
| **Architecture decisions** | `ai agentic-task` | **Context-aware recommendations** |
| **Large feature implementation** | `ai agentic-task` | **Comprehensive, ordered action plans** |

## 🤝 Contributing

Contributions are welcome! Please see our contributing guidelines and feel free to:

- Add new tools for the agentic system
- Improve existing use cases
- Enhance safety and security features
- Add support for new LLM providers
- Improve documentation and examples

## 📄 License

See the LICENSE file for license information.