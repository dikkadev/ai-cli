from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Iterable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass
class RunMeta:
    usecase: str
    sandbox_badge: str
    model_name: str | None = None
    elapsed_s: float | None = None


class Renderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def render_header(self, meta: RunMeta) -> None:
        pieces = [
            (meta.usecase, "bold cyan"),
            ("  •  ", "dim"),
            (meta.sandbox_badge, "bold white on grey23"),
        ]
        if meta.model_name:
            pieces += [("  •  ", "dim"), (meta.model_name, "italic dim")]
        if meta.elapsed_s is not None:
            pieces += [
                ("  •  ", "dim"),
                (f"{meta.elapsed_s:.2f}s", "italic dim"),
            ]
        header = Text.assemble(*[(t, s) for t, s in pieces])
        self.console.print(Panel(header, border_style="cyan", expand=False))

    def render_context_summary(
        self,
        included_count: int,
        skipped_count: int,
        redaction_on: bool,
        top_sources: Iterable[str] | None = None,
    ) -> None:
        table = Table.grid(padding=(0, 1))
        table.add_row(
            Text(f"included: {included_count}", style="green"),
            Text(f"skipped: {skipped_count}", style="yellow"),
            Text("redaction: on" if redaction_on else "redaction: off", style="magenta"),
        )
        if top_sources:
            for src in list(top_sources)[:3]:
                table.add_row(Text(src, style="dim"))
        self.console.print(Panel(table, border_style="grey39", expand=False))

    def render_text_block(self, content: str) -> None:
        self.console.print(content)

    def render_plan(self, plan: list, risks: list[str], assumptions: list[str], next_actions: list[str]) -> None:
        """Render a structured task plan with numbered steps."""
        # Steps
        if plan:
            self.console.print("\n[bold cyan]Plan:[/bold cyan]")
            for i, step in enumerate(plan, 1):
                risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(step.risk_level, "white")
                risk_badge = f"[{risk_color}]{step.risk_level.upper()}[/{risk_color}]"
                
                self.console.print(f"\n[bold]{i}. {step.title}[/bold] {risk_badge}")
                self.console.print(f"   {step.description}")
                if hasattr(step, 'rationale') and step.rationale:
                    self.console.print(f"   [dim]→ {step.rationale}[/dim]")
        
        # Risks
        if risks:
            self.console.print("\n[bold yellow]Risks:[/bold yellow]")
            for risk in risks:
                self.console.print(f"  • {risk}")
        
        # Assumptions
        if assumptions:
            self.console.print("\n[bold magenta]Assumptions:[/bold magenta]")
            for assumption in assumptions:
                self.console.print(f"  • {assumption}")
        
        # Next actions
        if next_actions:
            self.console.print("\n[bold green]Next Actions:[/bold green]")
            for action in next_actions:
                self.console.print(f"  • {action}")


class Stopwatch:
    def __enter__(self):
        self._t0 = perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = perf_counter() - self._t0
        return False
