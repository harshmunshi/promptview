"""promptview diff command."""

from typing import Optional
import typer
from ..output import console, error, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def diff_command(
    name: Optional[str] = typer.Argument(None, help="Prompt name to diff"),
    v1: Optional[int] = typer.Argument(None, help="Old version number"),
    v2: Optional[int] = typer.Argument(None, help="New version number"),
    staged: bool = typer.Option(False, "--staged", help="Compare staged vs last commit"),
) -> None:
    """Show changes between prompt versions."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    from ...storage.diff_engine import format_diff

    def _print_diff(diff):
        if diff is None:
            warn("No changes detected.")
            return
        text = format_diff(diff)
        for line in text.splitlines():
            if line.startswith("+"):
                console.print(f"[green]{line}[/green]")
            elif line.startswith("-"):
                console.print(f"[red]{line}[/red]")
            elif line.startswith("@"):
                console.print(f"[cyan]{line}[/cyan]")
            else:
                console.print(line)

    if name is None:
        # Show diff for all staged prompts
        staged_entries = repo.get_staged()
        if not staged_entries:
            warn("No staged changes. Use `promptview add` first or specify a prompt name.")
        for entry in staged_entries:
            console.rule(f"[prompt_name]{entry.prompt_name}[/prompt_name]")
            diff = repo.diff(entry.prompt_id, staged=True)
            _print_diff(diff)
    else:
        prompt = repo.get_prompt_by_name(name)
        if prompt is None:
            error(f"Prompt not found: {name}")
            raise typer.Exit(1)
        diff = repo.diff(prompt.id, old_version_number=v1, new_version_number=v2, staged=staged)
        _print_diff(diff)

    repo.close()
