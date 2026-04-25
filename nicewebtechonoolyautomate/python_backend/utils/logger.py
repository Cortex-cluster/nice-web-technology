from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme


_console = Console(
    theme=Theme(
        {
            "info": "bold cyan",
            "success": "bold green",
            "warning": "bold yellow",
            "error": "bold red",
        }
    )
)


def get_console() -> Console:
    return _console


def log_info(message: str) -> None:
    _console.print(Panel.fit(message, title="INFO", border_style="cyan"))


def log_success(message: str) -> None:
    _console.print(Panel.fit(message, title="SUCCESS", border_style="green"))


def log_error(message: str) -> None:
    _console.print(Panel.fit(message, title="ERROR", border_style="red"))


def build_status_table(rows: list[tuple[str, str]]) -> Table:
    table = Table(title="Automation Status", show_header=True, header_style="bold magenta")
    table.add_column("Item", style="cyan")
    table.add_column("Value", style="green")
    for key, value in rows:
        table.add_row(key, value)
    return table
