"""promptview status command."""

import typer
from ..output import console, info, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def status_command() -> None:
    """Show working tree status."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        from ..output import error
        error(str(e))
        raise typer.Exit(1)

    from ...scanner import scan_directory
    cfg = repo.get_config()
    extra_excludes = cfg.get("scan", {}).get("exclude", [])
    threshold = cfg.get("scan", {}).get("confidence_threshold", 0.5)

    with console.status("[cyan]Checking status...[/cyan]"):
        scanned = scan_directory(root, extra_excludes=extra_excludes, min_confidence=threshold)
        status = repo.status(scanned_prompts=scanned)

    head = repo.get_head()
    console.print(f"HEAD: [yellow]{head}[/yellow]\n")

    staged = status["staged"]
    if staged:
        console.print("[green]Changes staged for commit:[/green]")
        for entry in staged:
            style = {"added": "green", "modified": "yellow", "deleted": "red"}.get(entry.change_type, "white")
            console.print(f"  [{style}]{entry.change_type:12}[/{style}]  {entry.prompt_name}")
        console.print()

    modified = status["modified"]
    if modified:
        console.print("[yellow]Changes not staged (run `promptview add <name>` to stage):[/yellow]")
        for p in modified:
            console.print(f"  [yellow]modified:  [/yellow]  {p.name}")
        console.print()

    untracked = status["untracked"]
    if untracked:
        console.print("[dim]Untracked prompts (run `promptview add .` to track all):[/dim]")
        for sp in untracked:
            console.print(f"  [dim]{sp.variable_name}[/dim] ({sp.file_path}:{sp.line_number})")
        console.print()

    if not staged and not modified and not untracked:
        info("Nothing to commit, working tree clean.")

    repo.close()
