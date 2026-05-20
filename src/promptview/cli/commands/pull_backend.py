"""pv pull-remote — pull the .promptview DB from a remote backend (S3, GCS, HTTP)."""

from pathlib import Path

import typer
from ..output import success, error, warn


def _find_pv_paths() -> tuple[Path, Path]:
    """Return (config_path, db_path) for the nearest .promptview/ directory.

    Raises typer.Exit(1) if not found.
    """
    current = Path.cwd()
    for candidate in [current] + list(current.parents):
        pv_dir = candidate / ".promptview"
        config_path = pv_dir / "config.toml"
        if config_path.exists():
            db_path = pv_dir / "promptview.db"
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


def pull_backend_command(
    target: str = typer.Argument(
        ...,
        help="Remote name (from `pv remote list`) or direct URL (s3://, gcs://, https://)",
    ),
) -> None:
    """Pull the remote .promptview DB and overwrite the local one (S3, GCS, or HTTP)."""
    from ...remotes.base import RemoteBackend

    config_path, db_path = _find_pv_paths()

    _VALID_SCHEMES = ("s3://", "gcs://", "http://", "https://")
    if any(target.startswith(s) for s in _VALID_SCHEMES):
        url = target
    else:
        cfg = _read_config(config_path)
        remotes = cfg.get("remotes", {})
        if target not in remotes:
            error(
                f"Remote {target!r} not found. "
                "Register it with `pv remote add <name> <url>` or pass a URL directly."
            )
            raise typer.Exit(1)
        url = remotes[target]

    backend = RemoteBackend.from_url(url)

    if not backend.exists():
        warn(f"No remote DB found at {url}. Has anything been pushed yet?")
        raise typer.Exit(1)

    if db_path.exists():
        import shutil
        backup = db_path.with_suffix(".db.bak")
        shutil.copy2(db_path, backup)
        warn(f"Existing DB backed up to {backup}")

    try:
        backend.pull(db_path)
    except Exception as exc:
        error(f"Pull failed: {exc}")
        raise typer.Exit(1)

    success(f"Pulled from {url}")
