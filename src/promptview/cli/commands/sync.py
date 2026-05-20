"""promptview sync command — bidirectional push + pull for a remote."""

import typer

from ..output import console, success, error, info, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError

app = typer.Typer(
    name="sync",
    help="Bidirectional sync (push then pull) with a remote (langfuse/langsmith).",
    no_args_is_help=True,
)


def _do_push(remote: str, repo: PromptRepository) -> int:
    """Push all committed versions to the remote. Returns count of pushed versions."""
    from .pull import _get_integration

    integration = _get_integration(remote, repo)
    prompts = repo.list_prompts()
    pushed = 0
    for prompt in prompts:
        versions = repo.list_versions(prompt.id)
        committed_versions = [v for v in versions if v.commit_id is not None]
        for version in committed_versions:
            try:
                remote_id = integration.push_version(version, prompt)
                console.print(
                    f"  [green]pushed:[/green] {prompt.name} v{version.version_number} → {remote_id}"
                )
                pushed += 1
            except Exception as exc:
                warn(f"  failed to push {prompt.name} v{version.version_number}: {exc}")
    return pushed


def _do_pull(remote: str, repo: PromptRepository) -> dict:
    """Pull all prompts from the remote. Returns ingestion summary dict."""
    from .pull import _get_integration

    integration = _get_integration(remote, repo)
    try:
        remote_data = integration.pull_prompts()
    except Exception as exc:
        warn(f"Failed to fetch prompts from {remote}: {exc}")
        return {"created": 0, "updated": 0, "skipped": 0}

    if not remote_data:
        warn(f"No prompts found in {remote}.")
        return {"created": 0, "updated": 0, "skipped": 0}

    return repo.ingest_remote_prompts(remote_data, source=remote)


@app.command("langfuse")
def sync_langfuse() -> None:
    """Push all committed prompts to Langfuse, then pull remote prompts back."""
    _sync("langfuse")


@app.command("langsmith")
def sync_langsmith() -> None:
    """Push all committed prompts to LangSmith, then pull remote prompts back."""
    _sync("langsmith")


def _sync(remote: str) -> None:
    """Core bidirectional sync: push then pull."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    # ---- Phase 1: Push ----
    info(f"[1/2] Pushing committed prompts to {remote}...")
    pushed = _do_push(remote, repo)
    if pushed:
        success(f"Pushed {pushed} version(s) to {remote}.")
    else:
        warn("Nothing pushed (no committed versions found).")

    # ---- Phase 2: Pull ----
    info(f"[2/2] Pulling prompts from {remote}...")
    summary = _do_pull(remote, repo)
    success(
        f"Pull complete. created={summary['created']}  "
        f"updated={summary['updated']}  "
        f"skipped={summary['skipped']}"
    )

    repo.close()
