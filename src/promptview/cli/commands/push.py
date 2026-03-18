"""promptview push command."""

from typing import Optional
import typer
from ..output import console, success, error, info, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def push_command(
    remote: str = typer.Argument(..., help="Remote name: langfuse or langsmith"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be pushed"),
) -> None:
    """Push committed prompts to a remote (langfuse/langsmith)."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    if remote == "langfuse":
        try:
            from ...integrations.langfuse import LangfuseIntegration
            integration = LangfuseIntegration()
        except ImportError:
            error("Langfuse not installed. Run: pip install promptview[langfuse]")
            raise typer.Exit(1)
    elif remote == "langsmith":
        try:
            from ...integrations.langsmith import LangSmithIntegration
            integration = LangSmithIntegration()
        except ImportError:
            error("LangSmith not installed. Run: pip install promptview[langsmith]")
            raise typer.Exit(1)
    else:
        error(f"Unknown remote: {remote}. Use 'langfuse' or 'langsmith'.")
        raise typer.Exit(1)

    prompts = repo.list_prompts()
    pushed = 0
    for prompt in prompts:
        versions = repo.list_versions(prompt.id)
        committed_versions = [v for v in versions if v.commit_id is not None]
        for version in committed_versions:
            if dry_run:
                info(f"  would push: {prompt.name} v{version.version_number}")
            else:
                try:
                    remote_id = integration.push_version(version, prompt)
                    console.print(f"  [green]pushed:[/green] {prompt.name} v{version.version_number} → {remote_id}")
                    pushed += 1
                except Exception as exc:
                    warn(f"  failed to push {prompt.name} v{version.version_number}: {exc}")

    if not dry_run:
        success(f"Pushed {pushed} version(s) to {remote}.")

    repo.close()
