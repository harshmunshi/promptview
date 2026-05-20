"""pv remote — manage named remote backends (S3, GCS, HTTP)."""

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ..output import console, success, error, info, warn

app = typer.Typer(
    name="remote",
    help="Manage named remote backends (S3, GCS, HTTP) for pushing/pulling the prompt DB.",
    no_args_is_help=True,
)

_VALID_SCHEMES = ("s3://", "gcs://", "http://", "https://")


def _url_type(url: str) -> str:
    """Return a human-readable backend type label for the given URL."""
    if url.startswith("s3://"):
        return "S3"
    elif url.startswith("gcs://"):
        return "GCS"
    elif url.startswith("http://") or url.startswith("https://"):
        return "HTTP"
    return "Unknown"


def _find_config() -> Path:
    """Walk up from cwd looking for .promptview/config.toml.

    Raises typer.Exit(1) with an error message if not found.
    """
    current = Path.cwd()
    for candidate in [current] + list(current.parents):
        config_path = candidate / ".promptview" / "config.toml"
        if config_path.exists():
            return config_path
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


def _write_config(config_path: Path, cfg: dict) -> None:
    import tomli_w
    config_path.write_bytes(tomli_w.dumps(cfg).encode())


@app.command("add")
def add_command(
    name: str = typer.Argument(..., help="Name for the remote (e.g. 'origin')"),
    url: str = typer.Argument(..., help="Remote URL (s3://, gcs://, http://, https://)"),
) -> None:
    """Register a named remote backend in config.toml."""
    if not any(url.startswith(scheme) for scheme in _VALID_SCHEMES):
        error(
            f"Invalid URL scheme: {url!r}. "
            "Use s3://, gcs://, http://, or https://"
        )
        raise typer.Exit(1)

    config_path = _find_config()
    cfg = _read_config(config_path)

    if "remotes" not in cfg:
        cfg["remotes"] = {}

    if name in cfg["remotes"]:
        warn(f"Remote {name!r} already exists ({cfg['remotes'][name]}). Overwriting.")

    cfg["remotes"][name] = url
    _write_config(config_path, cfg)
    success(f"Remote {name!r} added: {url}")


@app.command("list")
def list_command() -> None:
    """Show all registered remotes."""
    config_path = _find_config()
    cfg = _read_config(config_path)
    remotes = cfg.get("remotes", {})

    if not remotes:
        info("No remotes configured. Use `pv remote add <name> <url>` to add one.")
        return

    table = Table(title="Registered Remotes", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold white")
    table.add_column("URL", style="white")
    table.add_column("Type", style="dim")

    for remote_name, remote_url in remotes.items():
        table.add_row(remote_name, remote_url, _url_type(remote_url))

    console.print(table)


@app.command("remove")
def remove_command(
    name: str = typer.Argument(..., help="Name of the remote to remove"),
) -> None:
    """Unregister a named remote from config.toml."""
    config_path = _find_config()
    cfg = _read_config(config_path)

    remotes = cfg.get("remotes", {})
    if name not in remotes:
        warn(f"Remote {name!r} not found. Nothing to remove.")
        raise typer.Exit(0)

    removed_url = remotes.pop(name)
    cfg["remotes"] = remotes
    _write_config(config_path, cfg)
    success(f"Remote {name!r} ({removed_url}) removed.")
