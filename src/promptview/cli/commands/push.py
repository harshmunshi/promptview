"""promptview push command."""

from pathlib import Path
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
        # Try it as a remote backend name or URL
        _push_backend_impl(remote)
        repo.close()
        return

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
                    console.print(f"  [green]pushed:[/green] {prompt.name} v{version.version_number} -> {remote_id}")
                    pushed += 1
                except Exception as exc:
                    warn(f"  failed to push {prompt.name} v{version.version_number}: {exc}")

    if not dry_run:
        success(f"Pushed {pushed} version(s) to {remote}.")

    repo.close()


def _find_pv_paths() -> tuple[Path, Path]:
    """Return (config_path, db_path) for the nearest .promptview/ directory.

    Raises typer.Exit(1) if not found.
    """
    current = Path.cwd()
    for candidate in [current] + list(current.parents):
        pv_dir = candidate / ".promptview"
        config_path = pv_dir / "config.toml"
        db_path = pv_dir / "promptview.db"
        if config_path.exists():
            return config_path, db_path
    error(
        "Not a promptview repository (no .promptview/config.toml found). "
        "Run `pv init` first."
    )
    raise typer.Exit(1)


def _read_config(config_path: Path) -> dict:
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with open(config_path, "rb") as f:
        return tomllib.load(f)


def _push_backend_impl(target: str) -> None:
    """Core logic: resolve target to a URL and push the local DB to it."""
    from ...remotes.base import RemoteBackend

    config_path, db_path = _find_pv_paths()

    # Determine URL
    _VALID_SCHEMES = ("s3://", "gcs://", "http://", "https://")
    if any(target.startswith(s) for s in _VALID_SCHEMES):
        url = target
    else:
        # Look up named remote in config.toml
        cfg = _read_config(config_path)
        remotes = cfg.get("remotes", {})
        if target not in remotes:
            error(
                f"Remote {target!r} not found. "
                "Register it with `pv remote add <name> <url>` or pass a URL directly."
            )
            raise typer.Exit(1)
        url = remotes[target]

    if not db_path.exists():
        error(f"Database not found at {db_path}. Has this repo been initialized and committed?")
        raise typer.Exit(1)

    backend = RemoteBackend.from_url(url)
    try:
        backend.push(db_path)
    except Exception as exc:
        error(f"Push failed: {exc}")
        raise typer.Exit(1)

    success(f"Pushed to {url}")


def push_backend_command(
    target: str = typer.Argument(..., help="Remote name (from `pv remote list`) or direct URL (s3://, gcs://, https://)"),
) -> None:
    """Push the local .promptview DB to a remote backend (S3, GCS, or HTTP)."""
    _push_backend_impl(target)
