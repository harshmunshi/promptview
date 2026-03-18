"""promptview log command."""

from typing import Optional
import typer
from ..output import console, error, info
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def log_command(
    name: Optional[str] = typer.Argument(None, help="Filter by prompt name"),
    oneline: bool = typer.Option(False, "--oneline", help="Compact one-line format"),
    limit: int = typer.Option(20, "--limit", "-n", help="Max commits to show"),
) -> None:
    """Show commit history."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    if name:
        prompt = repo.get_prompt_by_name(name)
        if prompt is None:
            error(f"Prompt not found: {name}")
            raise typer.Exit(1)
        commits = repo.list_commits_for_prompt(prompt.id)[:limit]
    else:
        commits = repo.list_commits()[:limit]

    if not commits:
        info("No commits yet.")
        repo.close()
        return

    # Build a map of commit_id -> prompt names for annotation
    all_prompts = repo.list_prompts()
    commit_prompt_map: dict[str, list[str]] = {}
    for p in all_prompts:
        for v in repo.list_versions(p.id):
            if v.commit_id:
                commit_prompt_map.setdefault(v.commit_id, [])
                if p.name not in commit_prompt_map[v.commit_id]:
                    commit_prompt_map[v.commit_id].append(p.name)

    for commit in commits:
        affected = commit_prompt_map.get(commit.id, [])
        if oneline:
            prompt_str = f" ({', '.join(affected[:3])})" if affected else ""
            console.print(f"[yellow]{commit.id}[/yellow] {commit.message}{prompt_str}")
        else:
            console.print(f"[yellow]commit {commit.id}[/yellow]")
            console.print(f"Author: {commit.author}")
            console.print(f"Date:   {commit.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            if affected:
                console.print(f"Prompts: {', '.join(affected)}")
            console.print(f"\n    {commit.message}\n")

    repo.close()
