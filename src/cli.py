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
from usecases.testwrite import TestWrite, TestWriteInput
from utils.fs import create_file_writer

app = typer.Typer(add_completion=False, help="ai CLI")

# Global options
WriteOption = typer.Option(False, "--write", help="Allow file writes (requires use case capability)")
ForceOption = typer.Option(False, "--force", help="Skip confirmation prompts")


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


@app.command()
def testwrite(
    target: str = typer.Argument(..., help="Target file or directory to generate tests for"),
    framework: str = typer.Option("pytest", help="Testing framework: pytest, unittest"),
    placement: str = typer.Option("new_file", help="Test placement: new_file, inline"),
    use_context: bool = typer.Option(True, "--context/--no-context", help="Include target and related files as context"),
    context_paths: list[str] = typer.Option([], "--path", help="Additional paths to include as context"),
    write: bool = WriteOption,
    force: bool = ForceOption,
) -> None:
    """Generate test files for code (optionally write them with --write flag)."""
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
                model_name="gpt-4o-mini",
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
        console.print("Available commands: ask, task, testwrite")


def main() -> None:
    """Entry point for console script."""
    app()


if __name__ == "__main__":
    app()