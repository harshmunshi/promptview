"""promptview config command."""

from typing import Optional
import typer
from ..output import console, error, info
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def config_command(
    key: Optional[str] = typer.Argument(None, help="Config key (e.g. project.author)"),
    value: Optional[str] = typer.Argument(None, help="Value to set"),
    show: bool = typer.Option(False, "--show", help="Show all config"),
) -> None:
    """Get or set configuration values."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    cfg = repo.get_config()

    if show or (key is None and value is None):
        import tomli_w
        console.print(tomli_w.dumps(cfg))
        repo.close()
        return

    if key and value is not None:
        # Set value: navigate nested dict by "." separator
        parts = key.split(".")
        d = cfg
        for part in parts[:-1]:
            d = d.setdefault(part, {})
        d[parts[-1]] = value

        import tomli_w
        repo.config_path.write_bytes(tomli_w.dumps(cfg).encode())
        info(f"Set {key} = {value}")
    elif key:
        # Get value
        parts = key.split(".")
        d = cfg
        for part in parts:
            if not isinstance(d, dict) or part not in d:
                error(f"Key not found: {key}")
                raise typer.Exit(1)
            d = d[part]
        console.print(str(d))

    repo.close()
