from __future__ import annotations

import typer
from rich.console import Console

from .core.sandbox import SandboxMode, SandboxPolicy, SandboxGuard
from .utils.render import Renderer, RunMeta, Stopwatch

app = typer.Typer(add_completion=False, help="ai CLI (scaffold)")


@app.callback(invoke_without_command=True)
def main() -> None:
    console = Console()
    renderer = Renderer(console)
    with Stopwatch() as sw:
        # Minimal render to demonstrate header composition only
        renderer.render_header(
            RunMeta(
                usecase="ai",
                sandbox_badge=SandboxMode.FULL.value.upper() + " SANDBOX",
                model_name=None,
                elapsed_s=None,
            )
        )
    # Avoid printing elapsed until we have a real run context


if __name__ == "__main__":
    app()
