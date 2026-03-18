"""promptview commit command."""

import typer
from ..output import console, success, error, info
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError, NothingToCommitError


def commit_command(
    message: str = typer.Option(..., "--message", "-m", help="Commit message"),
) -> None:
    """Commit staged prompts."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    try:
        commit = repo.commit(message)
        count = len(commit.version_ids)
        success(f"[commit_sha]{commit.id}[/commit_sha] {message}")
        info(f"  {count} prompt version(s) committed.")
    except NothingToCommitError as e:
        error(str(e))
        raise typer.Exit(1)
    finally:
        repo.close()
