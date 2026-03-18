"""Rich console helpers."""

from rich.console import Console
from rich.theme import Theme

theme = Theme({
    "info": "cyan",
    "success": "green bold",
    "warning": "yellow",
    "error": "red bold",
    "staged": "green",
    "modified": "yellow",
    "untracked": "dim",
    "prompt_name": "cyan bold",
    "commit_sha": "yellow",
    "version": "magenta",
})

console = Console(theme=theme)


def success(msg: str) -> None:
    console.print(f"[success]{msg}[/success]")


def error(msg: str) -> None:
    console.print(f"[error]Error:[/error] {msg}")


def info(msg: str) -> None:
    console.print(f"[info]{msg}[/info]")


def warn(msg: str) -> None:
    console.print(f"[warning]{msg}[/warning]")
