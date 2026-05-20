"""Branch management CLI commands for PromptView."""

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError

console = Console()

# ── Sub-app for `pv branch *` ─────────────────────────────────────────────────
app = typer.Typer(
    name="branch",
    help="Manage prompt branches (list, create, delete).",
    no_args_is_help=True,
)


def _get_repo() -> PromptRepository:
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)
    return repo


def _resolve_prompt(repo: PromptRepository, name: str):
    prompt = repo.get_prompt_by_name(name)
    if prompt is None:
        rprint(f"[red]Error:[/red] Prompt '{name}' not found. Run `pv scan` first.")
        raise typer.Exit(1)
    return prompt


# ── pv branch list ─────────────────────────────────────────────────────────────

@app.command("list")
def list_branches(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
) -> None:
    """List all branches for a prompt."""
    repo = _get_repo()
    p = _resolve_prompt(repo, prompt)
    branches = repo.list_branches(p.id)
    current = repo.get_current_branch(p.id)

    if not branches:
        rprint(f"[yellow]No branches found for '{prompt}'. Run [bold]pv branch create main --prompt {prompt}[/bold] to initialise.[/yellow]")
        repo.close()
        return

    table = Table(title=f"Branches for '{prompt}'", show_header=True, header_style="bold #58a6ff")
    table.add_column("Name", style="bold")
    table.add_column("Head Version", justify="center")
    table.add_column("Default", justify="center")
    table.add_column("Created At")
    table.add_column("Merged At")

    all_versions = {v.id: v for v in repo.list_versions(p.id)}

    for b in branches:
        is_active = b.name == current
        name_cell = f"[bold green]{b.name} (active)[/bold green]" if is_active else b.name
        head_v = all_versions.get(b.head_version_id or "") if b.head_version_id else None
        head_label = f"v{head_v.version_number}" if head_v else "-"
        default_mark = "[green]✓[/green]" if b.is_default else ""
        merged = b.merged_at[:19] if b.merged_at else "-"
        table.add_row(name_cell, head_label, default_mark, b.created_at[:19], merged)

    console.print(table)
    repo.close()


# ── pv branch create ──────────────────────────────────────────────────────────

@app.command("create")
def create_branch(
    name: str = typer.Argument(..., help="Branch name"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
    from_version: Optional[int] = typer.Option(
        None, "--from-version", help="Version number to branch from (default: latest)"
    ),
) -> None:
    """Create a new branch for a prompt."""
    repo = _get_repo()
    p = _resolve_prompt(repo, prompt)

    from_version_id: Optional[str] = None
    if from_version is not None:
        v = repo.get_version_by_number(p.id, from_version)
        if v is None:
            rprint(f"[red]Error:[/red] Version {from_version} not found for prompt '{prompt}'.")
            repo.close()
            raise typer.Exit(1)
        from_version_id = v.id

    try:
        branch = repo.create_branch(p.id, name, from_version_id=from_version_id)
    except Exception as exc:
        rprint(f"[red]Error:[/red] {exc}")
        repo.close()
        raise typer.Exit(1)

    all_versions = {v.id: v for v in repo.list_versions(p.id)}
    head_v = all_versions.get(branch.head_version_id or "") if branch.head_version_id else None
    head_label = f"v{head_v.version_number}" if head_v else "(no versions)"
    rprint(f"[green]✓[/green] Created branch '[bold]{name}[/bold]' on prompt '[bold]{prompt}[/bold]' at {head_label}")
    repo.close()


# ── pv branch delete ──────────────────────────────────────────────────────────

@app.command("delete")
def delete_branch(
    name: str = typer.Argument(..., help="Branch name to delete"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation for unmerged branches"),
) -> None:
    """Delete a branch. Cannot delete 'main'."""
    if name == "main":
        rprint("[red]Error:[/red] Cannot delete the 'main' branch.")
        raise typer.Exit(1)

    repo = _get_repo()
    p = _resolve_prompt(repo, prompt)
    branch = repo.db.get_branch(p.id, name)
    if branch is None:
        rprint(f"[red]Error:[/red] Branch '{name}' not found.")
        repo.close()
        raise typer.Exit(1)

    if branch.merged_at is None and not force:
        confirmed = typer.confirm(
            f"Branch '{name}' has not been merged yet. Delete anyway?"
        )
        if not confirmed:
            rprint("[yellow]Aborted.[/yellow]")
            repo.close()
            return

    repo.delete_branch(p.id, name)
    rprint(f"[green]✓[/green] Deleted branch '[bold]{name}[/bold]' from prompt '[bold]{prompt}[/bold]'")
    repo.close()


# ── pv checkout ───────────────────────────────────────────────────────────────
# Defined as a standalone function so it can be registered as a top-level command.

def checkout_command(
    branch_name: str = typer.Argument(..., help="Branch name to switch to"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
) -> None:
    """Switch the active branch for a prompt."""
    repo = _get_repo()
    p = _resolve_prompt(repo, prompt)
    branch = repo.db.get_branch(p.id, branch_name)
    if branch is None:
        rprint(f"[red]Error:[/red] Branch '{branch_name}' not found for prompt '{prompt}'.")
        repo.close()
        raise typer.Exit(1)

    repo.set_current_branch(p.id, branch_name)
    rprint(f"[green]✓[/green] Switched to branch '[bold]{branch_name}[/bold]' on prompt '[bold]{prompt}[/bold]'")
    repo.close()


# ── pv merge ──────────────────────────────────────────────────────────────────

def merge_command(
    source: str = typer.Argument(..., help="Source branch name"),
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
    into: str = typer.Option("main", "--into", help="Target branch (default: main)"),
) -> None:
    """Merge a source branch into a target branch."""
    repo = _get_repo()
    p = _resolve_prompt(repo, prompt)

    try:
        new_version = repo.merge_branch(p.id, source, target_branch=into)
    except ValueError as exc:
        rprint(f"[red]Error:[/red] {exc}")
        repo.close()
        raise typer.Exit(1)

    rprint(
        f"[green]✓[/green] Merged '[bold]{source}[/bold]' into '[bold]{into}[/bold]' "
        f"→ new version [bold]v{new_version.version_number}[/bold]"
    )
    repo.close()
