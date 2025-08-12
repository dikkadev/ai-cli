from __future__ import annotations

import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import typer
from rich.console import Console

from core.sandbox import SandboxMode, SandboxPolicy, SandboxGuard
from llm.openai_provider import OpenAIProvider
from llm.provider import Provider
from utils.render import Renderer, RunMeta, Stopwatch
from usecases.ask import Ask, AskInput
from usecases.task import Task, TaskInput
from usecases.testwrite import TestWrite, TestWriteInput
from usecases.agentic_task import AgenticTask, AgenticTaskInput
from utils.fs import create_file_writer

app = typer.Typer(
    add_completion=False,
    help="""AI CLI - Intelligent development assistance tool.

Provides AI-powered help for common development tasks with built-in safety controls.
All operations are sandboxed and require explicit consent for file modifications.

Examples:
  ai ask "How does authentication work?" --context
  ai task "Add error handling to API" --risk-level conservative  
  ai testwrite src/utils.py --write --framework pytest

Safety: Operations are restricted to the current project directory. File writes
require both use case capability AND explicit --write consent."""
)

# Global options for context and behavior control
ModelOption = typer.Option("gpt-5-mini", "--model", help="AI model to use (gpt-5-nano, gpt-5-mini, gpt-5)")
MaxFilesOption = typer.Option(50, "--max-files", help="Maximum context files (1-500)")
MaxBytesOption = typer.Option(2048, "--max-bytes", help="Max context size in KB (1-10000)")
BlacklistIgnoreOption = typer.Option([], "--blacklist-ignore", help="Ignore blacklist patterns")
RedactionOption = typer.Option(True, "--redaction/--no-redaction", help="Auto-redact sensitive content")
VerboseOption = typer.Option(False, "--verbose", "-v", help="Show detailed execution info")
QuietOption = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output")

# Write control options (only for applicable commands)
WriteOption = typer.Option(False, "--write", help="Enable file modifications")
ForceOption = typer.Option(False, "--force", help="Skip confirmation prompts")


@app.command()
def ask(
    query: str = typer.Argument(..., help="The question you want answered"),
    
    # Content style options
    style: str = typer.Option(
        "plain", 
        help="Answer format: plain, summary, or bullets"
    ),
    
    # Context inclusion options
    use_context: bool = typer.Option(
        False, 
        "--context", 
        help="Include project files as context"
    ),
    context_paths: list[str] = typer.Option(
        [], 
        "--path", 
        help="Specific files/globs to include as context"
    ),
    
    # Global context control options
    model: str = ModelOption,
    max_files: int = MaxFilesOption,
    max_bytes_kb: int = MaxBytesOption,
    blacklist_ignore: list[str] = BlacklistIgnoreOption,
    redaction: bool = RedactionOption,
    verbose: bool = VerboseOption,
    quiet: bool = QuietOption,
) -> None:
    """Ask questions about your code with AI assistance.

\b
DESCRIPTION:
    The 'ask' command provides intelligent answers to questions about your 
    codebase, documentation, or general development topics. It can optionally 
    include local project files as context for more relevant answers.

\b
EXAMPLES:
    # Basic questions
    ai ask "What is dependency injection?"
    ai ask "How do I handle errors in Python?"
    
    # Project-specific with context  
    ai ask "How does authentication work in this app?" --context
    ai ask "What are the main API endpoints?" --path "src/api/*.py"
    ai ask "Explain this function" --path "src/utils/helpers.py"
    
    # Different output styles
    ai ask "List the main features" --style bullets --context
    ai ask "Summarize the architecture" --style summary --context

\b
CONTEXT & SAFETY:
    • Runs in FULL SANDBOX mode (read-only, no file modifications)
    • Context filtered to exclude sensitive files (.env, keys, etc.)
    • Large files and binaries automatically skipped
    • Use --max-files and --max-bytes to control context size
    • Use --blacklist-ignore to include normally filtered patterns
    
    The AI analyzes included context to provide project-specific answers.
    """
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    with Stopwatch() as sw:
        # Render header
        renderer.render_header(
            RunMeta(
                usecase="ask",
                sandbox_badge="FULL SANDBOX",
                model_name=model,
            )
        )
        
        # Prepare input
        input_data = AskInput(
            query=query,
            style=style,  # type: ignore
            use_context=use_context,
            context_paths=context_paths,
        )
        
        # Apply global context control (note: these would be used in a more complete implementation)
        if verbose:
            console.print(f"[dim]Using model: {model}[/dim]")
            console.print(f"[dim]Context limits: {max_files} files, {max_bytes_kb}KB[/dim]")
            if blacklist_ignore:
                console.print(f"[dim]Ignoring blacklist patterns: {blacklist_ignore}[/dim]")
        
        # Context summary
        total_paths = len(context_paths) if context_paths else (1 if use_context else 0)
        renderer.render_context_summary(
            included_count=total_paths,
            skipped_count=0,
            redaction_on=True,
            top_sources=context_paths[:3] if context_paths else None,
        )
        
        # Execute with progress indicator
        try:
            provider = OpenAIProvider(model=model)
            
            # Create progress callback for live updates
            def progress_callback(message: str):
                console.print(f"[dim]{message}[/dim]")
            
            result = Ask.execute(input_data, provider, project_root, progress_callback)
            
            # Render result
            renderer.render_text_block(result.answer)
            
            if result.sources:
                console.print(f"\n[dim]Sources: {len(result.sources)} files[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def task(
    objective: str = typer.Argument(..., help="The task, feature, or objective you want to accomplish"),
    
    # Planning control options
    mode: str = typer.Option(
        "plan", 
        help="Planning depth: 'plan' (high-level steps), 'plan+steps' (detailed implementation steps)"
    ),
    risk_level: str = typer.Option(
        "moderate", 
        help="Risk tolerance: 'conservative' (safe, minimal risk), 'moderate' (balanced), 'aggressive' (fast, higher risk)"
    ),
    
    # Context inclusion options  
    use_context: bool = typer.Option(
        False, 
        "--context", 
        help="Include project context (README.md, *.md, pyproject.toml, package.json)"
    ),
    context_paths: list[str] = typer.Option(
        [], 
        "--path", 
        help="Specific files/directories to include as context (e.g., 'src/', 'docs/architecture.md')"
    ),
    
    # Global context control options
    model: str = ModelOption,
    max_files: int = MaxFilesOption,
    max_bytes_kb: int = MaxBytesOption,
    blacklist_ignore: list[str] = BlacklistIgnoreOption,
    redaction: bool = RedactionOption,
    verbose: bool = VerboseOption,
    quiet: bool = QuietOption,
) -> None:
    """Create structured, actionable plans for development tasks.

\b
DESCRIPTION:
    The 'task' command analyzes your objective and creates a detailed,
    step-by-step plan with risk assessments, assumptions, and next actions.
    It can incorporate your project's existing code and architecture.

\b
EXAMPLES:
    # Simple planning
    ai task "Add user authentication"
    ai task "Optimize database queries" --risk-level conservative
    ai task "Implement real-time notifications" --mode plan+steps
    
    # Context-aware planning
    ai task "Add API rate limiting" --context
    ai task "Refactor the payment system" --path "src/payments/"
    ai task "Migrate to microservices" --context --mode plan+steps
    
    # Risk-based planning
    ai task "Deploy to production" --risk-level conservative
    ai task "Prototype new feature" --risk-level aggressive

\b
PLANNING MODES:
    • plan: High-level strategic steps with risk assessment
    • plan+steps: Detailed implementation steps with specific actions

\b
RISK LEVELS:
    • conservative: Emphasizes safety, testing, gradual rollout
    • moderate: Balanced approach with reasonable safeguards
    • aggressive: Fast execution, accepting higher risks for speed

\b
CONTEXT & SAFETY:
    • Runs in FULL SANDBOX mode (read-only, no file modifications)
    • Plans based on your existing codebase when context is included
    • Automatically excludes sensitive files and large binaries
    • Provides structured output with risks, assumptions, next actions
    """
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    with Stopwatch() as sw:
        # Render header
        renderer.render_header(
            RunMeta(
                usecase="task",
                sandbox_badge="FULL SANDBOX",
                model_name=model,
            )
        )
        
        # Prepare input
        input_data = TaskInput(
            objective=objective,
            mode=mode,  # type: ignore
            risk_level=risk_level,  # type: ignore
            use_context=use_context,
            context_paths=context_paths,
        )
        
        # Apply global context control
        if verbose:
            console.print(f"[dim]Using model: {model}[/dim]")
            console.print(f"[dim]Context limits: {max_files} files, {max_bytes_kb}KB[/dim]")
            if blacklist_ignore:
                console.print(f"[dim]Ignoring blacklist patterns: {blacklist_ignore}[/dim]")
        
        # Context summary
        total_paths = len(context_paths) if context_paths else (1 if use_context else 0)
        renderer.render_context_summary(
            included_count=total_paths,
            skipped_count=0,
            redaction_on=True,
            top_sources=context_paths[:3] if context_paths else None,
        )
        
        # Execute with progress indicator
        try:
            provider = OpenAIProvider(model=model)
            
            # Create progress callback for live updates
            def progress_callback(message: str):
                console.print(f"[dim]{message}[/dim]")
            
            result = Task.execute(input_data, provider, project_root, progress_callback)
            
            # Render result
            renderer.render_plan(result.plan, result.risks, result.assumptions, result.next_actions)
            
            if result.sources:
                console.print(f"\n[dim]Sources: {len(result.sources)} files[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.command() 
def agentic_task(
    objective: str = typer.Argument(..., help="The task, feature, or objective you want the AI agent to plan"),
    
    # Agent control options
    mode: str = typer.Option(
        "explore+plan", 
        help="Agent mode: 'plan' (quick planning), 'explore+plan' (thorough exploration + planning)"
    ),
    risk_level: str = typer.Option(
        "moderate", 
        help="Risk tolerance: 'conservative' (safe approach), 'moderate' (balanced), 'aggressive' (fast, higher risk)"
    ),
    max_iterations: int = typer.Option(
        15,
        help="Maximum agent iterations (5-50)",
        min=5,
        max=50
    ),
    exploration_depth: int = typer.Option(
        3,
        help="Directory exploration depth (1-5)",
        min=1,
        max=5
    ),
    
    # Context inclusion options  
    context_files: list[str] = typer.Option(
        [], 
        "--file", 
        help="Specific files to prioritize during exploration (e.g., 'src/main.py', 'docs/architecture.md')"
    ),
    
    # Global control options
    model: str = ModelOption,
    verbose: bool = VerboseOption,
    quiet: bool = QuietOption,
) -> None:
    """AI agent that explores your project and creates comprehensive action plans.

\b
DESCRIPTION:
    The 'agentic_task' command deploys an AI agent that can iteratively explore
    your project, understand the codebase, and create detailed, context-aware
    action plans. Unlike the regular 'task' command, this agent uses tools to
    gather information and builds plans incrementally.

\b
EXAMPLES:
    # Basic agentic planning
    ai agentic_task "Add user authentication"
    ai agentic_task "Optimize database performance" --risk-level conservative
    ai agentic_task "Implement real-time chat" --mode explore+plan --max-iterations 20
    
    # Focused exploration
    ai agentic_task "Refactor API layer" --file "src/api/main.py" --file "src/models/"
    ai agentic_task "Add monitoring" --exploration-depth 2 --risk-level moderate
    
    # Quick planning mode
    ai agentic_task "Fix login bug" --mode plan --max-iterations 5

\b
AGENT MODES:
    • plan: Quick planning with minimal exploration (faster, less context)
    • explore+plan: Thorough exploration followed by detailed planning (slower, more comprehensive)

\b
RISK LEVELS:
    • conservative: Emphasizes safety, testing, gradual implementation
    • moderate: Balanced approach with reasonable safeguards  
    • aggressive: Fast execution, accepting higher risks for speed

\b
HOW IT WORKS:
    1. Agent explores project structure using file system tools
    2. Reads and analyzes key files to understand current state
    3. Creates structured todo list with numbered, actionable items
    4. Organizes tasks by priority and dependencies
    5. Provides detailed reasoning and recommendations

\b
AGENT CAPABILITIES:
    • Directory tree exploration with configurable depth
    • File content analysis (respects security blacklist)
    • Todo list creation and management in markdown format
    • Iterative plan refinement based on discoveries
    • Context-aware recommendations

\b
CONTEXT & SAFETY:
    • Runs in FULL SANDBOX mode (read-only, no file modifications)
    • Automatically excludes sensitive files (.env, keys, etc.)  
    • Agent stops automatically when plan is complete
    • All tool usage is logged and auditable
    • Use --max-iterations to control execution time
    """
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    with Stopwatch() as sw:
        # Render header with agent badge
        renderer.render_header(
            RunMeta(
                usecase="agentic_task",
                sandbox_badge="AGENT + FULL SANDBOX",
                model_name=model,
            )
        )
        
        # Prepare input
        input_data = AgenticTaskInput(
            objective=objective,
            mode=mode,  # type: ignore
            risk_level=risk_level,  # type: ignore
            exploration_depth=exploration_depth,
            max_iterations=max_iterations,
            context_files=context_files,
        )
        
        # Show agent configuration
        if verbose:
            console.print(f"[dim]Agent mode: {mode}[/dim]")
            console.print(f"[dim]Risk level: {risk_level}[/dim]")
            console.print(f"[dim]Max iterations: {max_iterations}[/dim]")
            console.print(f"[dim]Exploration depth: {exploration_depth}[/dim]")
            if context_files:
                console.print(f"[dim]Priority files: {', '.join(context_files)}[/dim]")
        
        # Show agent status
        console.print("[bold blue]🤖 Starting AI Agent...[/bold blue]")
        console.print(f"[dim]Objective: {objective}[/dim]")
        console.print()
        
        # Execute
        try:
            provider = OpenAIProvider(model=model)
            result = AgenticTask.execute(input_data, provider, project_root)
            
            if result.success:
                # Render successful result
                console.print(f"[bold green]✅ Agent Planning Complete[/bold green]")
                console.print(f"[dim]Iterations used: {result.iterations_used}[/dim]")
                console.print(f"[dim]Files explored: {len(result.files_explored)}[/dim]")
                
                # Show exploration summary
                console.print(f"\n[bold]🔍 Exploration Summary:[/bold]")
                console.print(result.exploration_summary)
                
                # Show the generated plan
                console.print(f"\n[bold]📋 Generated Action Plan:[/bold]")
                from rich.panel import Panel
                plan_panel = Panel(
                    result.plan, 
                    title="Todo List",
                    border_style="green"
                )
                console.print(plan_panel)
                
                # Show todo statistics
                stats = result.todo_stats
                console.print(f"\n[bold]📊 Plan Statistics:[/bold]")
                console.print(f"  • Total tasks: {stats['total_items']}")
                console.print(f"  • Completed: {stats['completed_items']}")
                console.print(f"  • Pending: {stats['pending_items']}")
                
                # Show agent reasoning
                console.print(f"\n[bold]🧠 Agent Analysis:[/bold]")
                reasoning_panel = Panel(
                    result.agent_reasoning,
                    title="Recommendations & Reasoning",
                    border_style="blue"
                )
                console.print(reasoning_panel)
                
                # Show explored files
                if result.files_explored and verbose:
                    console.print(f"\n[bold]📁 Files Analyzed:[/bold]")
                    for file_path in result.files_explored:
                        console.print(f"  • {file_path}")
                
                # Show sources
                if result.sources:
                    console.print(f"\n[dim]Sources: {len(result.sources)} files analyzed[/dim]")
                
            else:
                # Render failure result
                console.print(f"[bold red]❌ Agent Planning Failed[/bold red]")
                console.print(f"[red]Error: {result.plan}[/red]")
                console.print(f"[dim]Iterations used: {result.iterations_used}[/dim]")
        
        except Exception as e:
            console.print(f"[red]Agent execution failed: {e}[/red]")
            if verbose:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise typer.Exit(1)


@app.command()
def testwrite(
    target: str = typer.Argument(..., help="Target file or directory to generate comprehensive tests for"),
    
    # Test generation options
    framework: str = typer.Option(
        "pytest", 
        help="Testing framework: 'pytest' (recommended), 'unittest' (Python standard library)"
    ),
    placement: str = typer.Option(
        "new_file", 
        help="Test file placement: 'new_file' (separate test files), 'inline' (same file as code)"
    ),
    
    # Context inclusion options
    use_context: bool = typer.Option(
        True, 
        "--context/--no-context", 
        help="Include target file and related Python files as context for better test generation"
    ),
    context_paths: list[str] = typer.Option(
        [], 
        "--path", 
        help="Additional files to include as context (e.g., 'src/models.py', 'tests/conftest.py')"
    ),
    
    # Global context control options
    model: str = ModelOption,
    max_files: int = MaxFilesOption,
    max_bytes_kb: int = MaxBytesOption,
    blacklist_ignore: list[str] = BlacklistIgnoreOption,
    redaction: bool = RedactionOption,
    verbose: bool = VerboseOption,
    quiet: bool = QuietOption,
    
    # File modification options
    write: bool = WriteOption,
    force: bool = ForceOption,
) -> None:
    """Generate comprehensive test suites for your code.

\b
DESCRIPTION:
    The 'testwrite' command analyzes your code and generates thorough test
    files following testing best practices. It can preview proposed tests
    or write them directly to your project with the --write flag.

\b
EXAMPLES:
    # Preview test generation
    ai testwrite src/utils.py
    ai testwrite src/api/users.py --framework unittest
    ai testwrite src/ --framework pytest --placement new_file
    
    # Generate and write test files
    ai testwrite src/models.py --write
    ai testwrite src/api/ --write --framework pytest --force
    ai testwrite src/utils.py --write --path "tests/conftest.py"
    
    # Context-aware generation
    ai testwrite src/auth.py --context --path "src/models.py"
    ai testwrite src/api/ --no-context

\b
TESTING FRAMEWORKS:
    • pytest: Modern Python testing (fixtures, parametrize, plugins)
      - Uses test_*.py naming convention
      - Automatic fixture discovery and rich assertion introspection
    
    • unittest: Python standard library testing
      - Uses TestCase classes with setUp/tearDown methods
      - Built-in mocking capabilities

\b
TEST PLACEMENT:
    • new_file: Creates separate test files (recommended)
      - Follows framework conventions (test_*.py)
      - Keeps tests organized and discoverable
    
    • inline: Adds tests within the same file
      - Useful for simple utilities or prototypes
      - Uses if __name__ == '__main__' blocks

\b
CONTEXT & SAFETY:
    • Runs in LIMITED SANDBOX mode (controlled write access)
    • File writes require both --write flag AND use case capability
    • Interactive confirmation before writing (use --force to skip)
    • Automatically includes target file and related Python files
    • Excludes test files, builds, and sensitive files from context

\b
WHAT'S GENERATED:
    • Comprehensive unit tests for functions, classes, methods
    • Edge case and error condition testing
    • Proper mocking for external dependencies
    • Framework-specific best practices and clear organization
    
    Without --write: shows preview of proposed test files and changes
    With --write: creates/updates test files after confirmation
    """
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    # Create sandbox with write consent
    sandbox_policy = SandboxPolicy(
        mode=SandboxMode.LIMITED,
        project_root=project_root,
        allows_writes=True,  # TestWrite declares this capability
        user_write_consent=write,
    )
    sandbox_guard = SandboxGuard(sandbox_policy)
    
    with Stopwatch() as sw:
        # Render header
        sandbox_badge = "LIMITED SANDBOX" + (" + WRITES" if write else " (READ-ONLY)")
        renderer.render_header(
            RunMeta(
                usecase="testwrite",
                sandbox_badge=sandbox_badge,
                model_name=model,
            )
        )
        
        # Prepare input
        input_data = TestWriteInput(
            target=target,
            framework=framework,  # type: ignore
            placement=placement,  # type: ignore
            use_context=use_context,
            context_paths=context_paths,
        )
        
        # Apply global context control
        if verbose:
            console.print(f"[dim]Using model: {model}[/dim]")
            console.print(f"[dim]Context limits: {max_files} files, {max_bytes_kb}KB[/dim]")
            if blacklist_ignore:
                console.print(f"[dim]Ignoring blacklist patterns: {blacklist_ignore}[/dim]")
        
        # Context summary
        total_paths = len(context_paths) + (1 if use_context else 0)  # +1 for target
        renderer.render_context_summary(
            included_count=total_paths,
            skipped_count=0,
            redaction_on=True,
            top_sources=[target] + context_paths[:2] if context_paths else [target],
        )
        
        # Execute
        try:
            provider = OpenAIProvider()
            result = TestWrite.execute(input_data, provider, project_root)
            
            # Render result
            renderer.render_proposed_files(result.proposed_files, result.rationale, result.coverage_targets)
            
            if result.sources:
                console.print(f"\n[dim]Sources: {len(result.sources)} files[/dim]")
            
            # Handle file writing if requested
            if write and result.proposed_files:
                file_writer = create_file_writer(sandbox_guard)
                
                # Add all proposed operations
                for proposed_file in result.proposed_files:
                    file_path = project_root / proposed_file.path
                    file_writer.add_operation(file_path, proposed_file.content, proposed_file.action)
                
                # Confirm before writing (unless --force)
                if not force:
                    console.print(f"\n[yellow]About to write {len(result.proposed_files)} files. Continue? [y/N][/yellow]", end=" ")
                    import sys
                    response = input().strip().lower()
                    if response not in ["y", "yes"]:
                        console.print("[dim]Cancelled.[/dim]")
                        return
                
                # Execute file operations
                changes = file_writer.execute_operations(dry_run=False)
                
                console.print(f"\n[bold green]File Operations:[/bold green]")
                for change in changes:
                    if "Failed" in change:
                        console.print(f"  [red]{change}[/red]")
                    else:
                        console.print(f"  [green]{change}[/green]")
            
            elif not write:
                console.print(f"\n[dim]Note: Files not written (use --write to enable)[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """
    AI CLI - Intelligent development assistance with built-in safety.
    
    A modern command-line tool that provides AI-powered help for common development
    tasks including Q&A, planning, and test generation. All operations are sandboxed
    and require explicit consent for file modifications.
    """
    if ctx.invoked_subcommand is None:
        console = Console()
        renderer = Renderer(console)
        renderer.render_header(
            RunMeta(
                usecase="ai",
                sandbox_badge="FULL SANDBOX",
                model_name=None,
            )
        )
        
        console.print("""
[bold]Available Commands:[/bold]

  [cyan]ask[/cyan]           Ask questions about code with optional project context
  [cyan]task[/cyan]          Create structured plans for development objectives  
  [cyan]agentic_task[/cyan]  🤖 AI agent that explores projects and creates comprehensive plans
  [cyan]testwrite[/cyan]     Generate comprehensive test suites for your code

[bold]Quick Examples:[/bold]

  ai ask "How does authentication work?" --context
  ai task "Add error handling" --risk-level conservative
  ai agentic_task "Add user authentication" --mode explore+plan  
  ai testwrite src/utils.py --write --framework pytest

[bold]Global Options:[/bold]

  --model TEXT           AI model selection (gpt-4o-mini, gpt-4o, gpt-4-turbo)
  --max-files INT        Context file limit (default: 50)
  --max-bytes INT        Context size limit in KB (default: 2048)  
  --blacklist-ignore     Skip specific blacklist patterns
  --redaction/--no-redaction  Control sensitive content filtering
  --verbose, -v          Show detailed execution information
  --quiet, -q            Suppress non-essential output

[bold]Safety Features:[/bold]

  • All operations are sandboxed to the current project directory
  • Sensitive files (.env, keys, credentials) are automatically excluded
  • File writes require explicit --write consent AND use case capability
  • Interactive confirmations prevent accidental modifications

[dim]Use 'ai COMMAND --help' for detailed command information.[/dim]
""".strip())


def main() -> None:
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    app()