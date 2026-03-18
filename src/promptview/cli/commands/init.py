"""promptview init command."""

import typer
from pathlib import Path

from ..output import console, success, error, info
from ...storage.repository import PromptRepository
from ...exceptions import AlreadyInitializedError


def init_command(
    path: str = typer.Argument(".", help="Directory to initialize"),
    author: str = typer.Option("", "--author", "-a", help="Author name"),
    force: bool = typer.Option(False, "--force", "-f", help="Reinitialize if already exists"),
    no_scan: bool = typer.Option(False, "--no-scan", help="Skip initial scan"),
) -> None:
    """Initialize a PromptView repository in the current directory."""
    root = Path(path).resolve()
    repo = PromptRepository(root)

    if repo.is_initialized() and not force:
        error(f"Already a promptview repository: {root / '.promptview'}")
        error("Use --force to reinitialize.")
        raise typer.Exit(1)

    repo.initialize(author=author)
    success(f"Initialized PromptView repository in {root / '.promptview'}")

    if not no_scan:
        from ...scanner import scan_directory
        info("Scanning for prompts...")
        results = scan_directory(root)
        if results:
            from rich.table import Table
            table = Table(title=f"Found {len(results)} prompt(s)")
            table.add_column("File", style="dim")
            table.add_column("Line", justify="right")
            table.add_column("Name / Variable")
            table.add_column("Source", style="cyan")
            table.add_column("Confidence", justify="right")
            for r in results:
                table.add_row(
                    r.file_path,
                    str(r.line_number),
                    r.variable_name,
                    r.source.value,
                    f"{r.confidence:.0%}",
                )
            console.print(table)
            info(f"\nRun [cyan]promptview add .[/cyan] to stage all prompts.")
        else:
            info("No prompts found. Add Python files with LLM calls and run `promptview scan`.")
