"""promptview ui command - starts the web server."""

import typer
from ..output import info, error
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def ui_command(
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
) -> None:
    """Start the PromptView web UI."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    import uvicorn
    from ...server.app import create_app

    app = create_app(repo)
    url = f"http://{host}:{port}"
    info(f"Starting PromptView UI at [cyan]{url}[/cyan]")

    if not no_browser:
        import webbrowser, threading
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=host, port=port, log_level="error")
