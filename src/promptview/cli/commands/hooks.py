"""pv hooks — manage git pre-commit hooks for PromptView."""

import os
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ..output import console

app = typer.Typer(
    name="hooks",
    help="Manage git pre-commit hooks for PromptView.",
    no_args_is_help=True,
)

_HOOK_COMMENT = "# PromptView pre-commit hook"

_HOOK_CONTENT = """\
#!/bin/sh
# PromptView pre-commit hook
# Fails if any prompts in the codebase are untracked (not yet versioned)
pv scan --fail-on-untracked
"""


def _find_git_hooks_dir(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start until a .git/ directory is found; return .git/hooks/."""
    current = start or Path.cwd()
    for candidate in [current] + list(current.parents):
        git_dir = candidate / ".git"
        if git_dir.is_dir():
            hooks_dir = git_dir / "hooks"
            hooks_dir.mkdir(exist_ok=True)
            return hooks_dir
    return None


@app.command("install")
def install_command() -> None:
    """Install a PromptView pre-commit hook in the nearest git repository."""
    hooks_dir = _find_git_hooks_dir()
    if hooks_dir is None:
        console.print(
            "[red]✗ Could not find a .git/ directory. "
            "Are you inside a git repository?[/red]"
        )
        raise typer.Exit(1)

    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists():
        existing = hook_path.read_text()
        if _HOOK_COMMENT in existing:
            console.print(
                f"[yellow]Already installed at {hook_path}[/yellow]"
            )
            return
        # Hook exists but was not written by PromptView — ask to overwrite
        overwrite = typer.confirm(
            f"A pre-commit hook already exists at {hook_path}. Overwrite?",
            default=False,
        )
        if not overwrite:
            console.print("[yellow]Aborted — existing hook was not modified.[/yellow]")
            raise typer.Exit(0)

    hook_path.write_text(_HOOK_CONTENT)
    os.chmod(hook_path, 0o755)
    console.print(f"[green]✓ Pre-commit hook installed at {hook_path}[/green]")


@app.command("uninstall")
def uninstall_command() -> None:
    """Remove the PromptView pre-commit hook from the nearest git repository."""
    hooks_dir = _find_git_hooks_dir()
    if hooks_dir is None:
        console.print(
            "[red]✗ Could not find a .git/ directory. "
            "Are you inside a git repository?[/red]"
        )
        raise typer.Exit(1)

    hook_path = hooks_dir / "pre-commit"

    if not hook_path.exists():
        console.print("[yellow]No pre-commit hook found — nothing to remove.[/yellow]")
        return

    content = hook_path.read_text()
    if _HOOK_COMMENT not in content:
        console.print(
            "[yellow]⚠ Hook was not installed by PromptView, skipping.[/yellow]"
        )
        return

    hook_path.unlink()
    console.print(f"[green]✓ Pre-commit hook removed from {hook_path}[/green]")


@app.command("status")
def status_command() -> None:
    """Show the current status of the PromptView pre-commit hook."""
    hooks_dir = _find_git_hooks_dir()

    table = Table(title="PromptView Hook Status")
    table.add_column("Hook", style="cyan")
    table.add_column("Status")
    table.add_column("Path", style="dim")

    if hooks_dir is None:
        table.add_row(
            "pre-commit",
            "[red]✗ No git repository found[/red]",
            "—",
        )
        console.print(table)
        return

    hook_path = hooks_dir / "pre-commit"

    if not hook_path.exists():
        table.add_row(
            "pre-commit",
            "[red]✗ Not installed[/red]",
            str(hook_path),
        )
    else:
        content = hook_path.read_text()
        if _HOOK_COMMENT in content:
            table.add_row(
                "pre-commit",
                "[green]✓ Installed (PromptView)[/green]",
                str(hook_path),
            )
        else:
            table.add_row(
                "pre-commit",
                "[yellow]⚠ Installed (other)[/yellow]",
                str(hook_path),
            )

    console.print(table)
