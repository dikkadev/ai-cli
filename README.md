# AI CLI

A modern command-line tool that provides AI-powered assistance for common development tasks.

## Features

- **`ai ask`**: Question answering with optional project context
- **`ai task`**: Structured planning and task breakdown with risk assessment  
- **`ai testwrite`**: Test code generation with safe file writing capabilities

## Quick Start

### Development Mode

```bash
# Clone and enter directory
cd /path/to/ai-cli

# Install dependencies  
uv sync

# Run from project directory
uv run ai

# Examples
uv run ai ask "What does this project do?" --context
uv run ai task "Add error handling" --risk-level conservative
uv run ai testwrite src/utils.py --write --framework pytest
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
   ```

## Usage Examples

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

## Safety Features

- **Sandboxed execution**: All operations restricted to project directory
- **Write permissions**: File modifications require explicit `--write` consent
- **Interactive confirmations**: Prompts before making changes (override with `--force`)
- **Context limits**: Automatic file size and count restrictions

## Development

See `DEVELOPER_HANDOFF.md` for comprehensive development documentation including:
- Architecture overview and design patterns
- Security model and sandbox system
- Adding new use cases and providers
- Testing strategy and troubleshooting

## License

[Add your license here]
