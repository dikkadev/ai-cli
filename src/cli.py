from __future__ import annotations

import typer
from pathlib import Path
from rich.console import Console

from core.sandbox import SandboxMode, SandboxPolicy, SandboxGuard
from llm.openai_provider import OpenAIProvider
from llm.provider import Provider
from utils.render import Renderer, RunMeta, Stopwatch
from usecases.ask import Ask, AskInput
from usecases.task import Task, TaskInput

app = typer.Typer(add_completion=False, help="ai CLI")


@app.command()
def ask(
    query: str = typer.Argument(..., help="Question to ask"),
    style: str = typer.Option("plain", help="Answer style: plain, summary, bullets"),
    use_context: bool = typer.Option(False, "--context", help="Include local context"),
    context_paths: list[str] = typer.Option([], "--path", help="Specific paths to include"),
) -> None:
    """Ask a question with optional local context."""
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    with Stopwatch() as sw:
        # Render header
        renderer.render_header(
            RunMeta(
                usecase="ask",
                sandbox_badge="FULL SANDBOX",
                model_name="gpt-4o-mini",
            )
        )
        
        # Prepare input
        input_data = AskInput(
            query=query,
            style=style,  # type: ignore
            use_context=use_context,
            context_paths=context_paths,
        )
        
        # Context summary
        total_paths = len(context_paths) if context_paths else (1 if use_context else 0)
        renderer.render_context_summary(
            included_count=total_paths,
            skipped_count=0,
            redaction_on=True,
            top_sources=context_paths[:3] if context_paths else None,
        )
        
        # Execute
        try:
            provider = OpenAIProvider()
            result = Ask.execute(input_data, provider, project_root)
            
            # Render result
            renderer.render_text_block(result.answer)
            
            if result.sources:
                console.print(f"\n[dim]Sources: {len(result.sources)} files[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.command()
def task(
    objective: str = typer.Argument(..., help="Task or objective to plan for"),
    mode: str = typer.Option("plan", help="Planning mode: plan, plan+steps"),
    risk_level: str = typer.Option("moderate", help="Risk tolerance: conservative, moderate, aggressive"),
    use_context: bool = typer.Option(False, "--context", help="Include project context"),
    context_paths: list[str] = typer.Option([], "--path", help="Specific paths to include"),
) -> None:
    """Create a structured plan for a task or objective."""
    console = Console()
    renderer = Renderer(console)
    project_root = Path.cwd()
    
    with Stopwatch() as sw:
        # Render header
        renderer.render_header(
            RunMeta(
                usecase="task",
                sandbox_badge="FULL SANDBOX",
                model_name="gpt-4o-mini",
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
        
        # Context summary
        total_paths = len(context_paths) if context_paths else (1 if use_context else 0)
        renderer.render_context_summary(
            included_count=total_paths,
            skipped_count=0,
            redaction_on=True,
            top_sources=context_paths[:3] if context_paths else None,
        )
        
        # Execute
        try:
            provider = OpenAIProvider()
            result = Task.execute(input_data, provider, project_root)
            
            # Render result
            renderer.render_plan(result.plan, result.risks, result.assumptions, result.next_actions)
            
            if result.sources:
                console.print(f"\n[dim]Sources: {len(result.sources)} files[/dim]")
        
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
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
        console.print("Available commands: ask, task")


if __name__ == "__main__":
    app()