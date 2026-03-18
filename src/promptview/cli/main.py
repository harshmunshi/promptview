"""Main CLI entry point for PromptView."""

import typer
from rich import print as rprint

from .commands.init import init_command
from .commands.scan import scan_command
from .commands.add import add_command
from .commands.commit import commit_command
from .commands.status import status_command
from .commands.diff import diff_command
from .commands.log import log_command
from .commands.ui import ui_command
from .commands.config import config_command
from .commands.push import push_command
from .commands.eval import app as eval_app
from .commands.metrics import app as metrics_app
from .commands.branch import app as branch_app, checkout_command, merge_command

app = typer.Typer(
    name="promptview",
    help="Git-like versioning and visualization for LLM prompts.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)

app.command("init", help="Initialize a PromptView repository")(init_command)
app.command("scan", help="Scan codebase for LLM prompts")(scan_command)
app.command("add", help="Stage prompt changes")(add_command)
app.command("commit", help="Commit staged prompts")(commit_command)
app.command("status", help="Show working tree status")(status_command)
app.command("diff", help="Show changes between prompt versions")(diff_command)
app.command("log", help="Show commit history")(log_command)
app.command("ui", help="Start the web UI")(ui_command)
app.command("config", help="Get or set configuration")(config_command)
app.command("push", help="Push prompts to remote (langfuse/langsmith)")(push_command)
app.add_typer(eval_app, name="eval")
app.add_typer(metrics_app, name="metrics")
app.add_typer(branch_app, name="branch")
app.command("checkout", help="Switch active branch for a prompt")(checkout_command)
app.command("merge", help="Merge a branch into another")(merge_command)


@app.command("version")
def version_command() -> None:
    """Show PromptView version."""
    from .. import __version__
    rprint(f"promptview {__version__}")


if __name__ == "__main__":
    app()
