"""promptview scan command."""

import typer
from pathlib import Path

from ..output import console, info, warn
from ...storage.repository import PromptRepository


def scan_command(
    path: str = typer.Argument(".", help="Directory to scan"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-c"),
    show_all: bool = typer.Option(False, "--show-all", help="Show low-confidence hits too"),
    fail_on_untracked: bool = typer.Option(
        False,
        "--fail-on-untracked",
        help="Exit with code 1 if any discovered prompts are not yet staged/committed",
    ),
) -> None:
    """Scan the codebase for LLM prompts."""
    root = Path(path).resolve()
    repo = PromptRepository(root)

    # Load exclude patterns from config if repo is initialized
    extra_excludes = []
    if repo.is_initialized():
        cfg = repo.get_config()
        extra_excludes = cfg.get("scan", {}).get("exclude", [])
        if min_confidence == 0.5:
            min_confidence = cfg.get("scan", {}).get("confidence_threshold", 0.5)

    from ...scanner import scan_directory
    threshold = 0.0 if show_all else min_confidence

    with console.status("[cyan]Scanning...[/cyan]"):
        results = scan_directory(root, extra_excludes=extra_excludes, min_confidence=threshold)

    if not results:
        warn("No prompts found.")
        if fail_on_untracked:
            console.print("[green]✓ No prompts found — nothing untracked.[/green]")
        return

    from rich.table import Table
    table = Table(title=f"Found {len(results)} prompt(s)")
    table.add_column("File", style="dim", no_wrap=True)
    table.add_column("Line", justify="right", style="dim")
    table.add_column("Variable / Name", style="cyan")
    table.add_column("Source")
    table.add_column("Preview", overflow="fold")
    table.add_column("Conf.", justify="right")

    for r in results:
        preview = r.raw_content[:60].replace("\n", " ")
        if len(r.raw_content) > 60:
            preview += "..."
        confidence_style = "green" if r.confidence >= 0.8 else ("yellow" if r.confidence >= 0.5 else "dim")
        table.add_row(
            r.file_path,
            str(r.line_number),
            r.variable_name,
            r.source.value,
            preview,
            f"[{confidence_style}]{r.confidence:.0%}[/{confidence_style}]",
        )
    console.print(table)
    info(f"\nRun [cyan]promptview add .[/cyan] to stage all discovered prompts.")

    if fail_on_untracked:
        # Determine which discovered prompts are untracked (not staged or committed)
        untracked = []
        if repo.is_initialized():
            repo.open()
            try:
                status = repo.status(scanned_prompts=results)
                untracked = status.get("untracked", [])
            finally:
                repo.close()
        else:
            # Repo not initialized — every discovered prompt is untracked
            untracked = list(results)

        if untracked:
            console.print(
                "\n[red]✗ The following prompts are untracked (not staged or committed):[/red]"
            )
            for sp in untracked:
                console.print(
                    f"  [red]•[/red] [cyan]{sp.variable_name}[/cyan]"
                    f"  ({sp.file_path}:{sp.line_number})"
                )
            console.print(
                "\n[red]Run [cyan]pv add .[/cyan][red] then [cyan]pv commit[/cyan]"
                "[red] to version these prompts.[/red]"
            )
            raise typer.Exit(1)
        else:
            console.print(
                "\n[green]✓ All discovered prompts are tracked.[/green]"
            )
