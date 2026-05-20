"""pv vars — inspect and set template variable defaults for a prompt."""
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Manage template variables for a prompt.")
console = Console()


def _open_repo():
    from promptview.storage.repository import PromptRepository
    from promptview.exceptions import NotInitializedError
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    return repo


def _get_prompt(repo, name: str):
    prompt = repo.get_prompt_by_name(name)
    if prompt is None:
        console.print(f"[red]Prompt not found: {name!r}[/red]")
        raise typer.Exit(1)
    return prompt


@app.command("show")
def vars_show(
    name: str = typer.Argument(..., help="Prompt name"),
) -> None:
    """Show all template variables for a prompt."""
    repo = _open_repo()
    prompt = _get_prompt(repo, name)
    variables = repo.db.list_variables(prompt.id)

    if not variables:
        console.print(f"[yellow]No variables found for {name!r}. Run: pv vars sync {name}[/yellow]")
        repo.close()
        return

    table = Table(title=f"Variables — {name}", border_style="blue")
    table.add_column("Name", style="cyan bold")
    table.add_column("Default Value", style="green")
    table.add_column("Description", style="dim")
    for v in variables:
        table.add_row(v.name, v.default_value or "[dim]<none>[/dim]", v.description or "")
    console.print(table)
    repo.close()


@app.command("set")
def vars_set(
    name: str = typer.Argument(..., help="Prompt name"),
    var_name: str = typer.Argument(..., help="Variable name"),
    default: str = typer.Argument(..., help="Default value"),
    description: str = typer.Option("", "--desc", "-d", help="Human description"),
) -> None:
    """Set the default value for a template variable."""
    from promptview.storage.models import PromptVariable
    repo = _open_repo()
    prompt = _get_prompt(repo, name)
    v = PromptVariable.new(prompt.id, var_name, default_value=default, description=description)
    repo.db.upsert_variable(v)
    console.print(f"[green]Set {var_name}={default!r} for prompt {name!r}[/green]")
    repo.close()


@app.command("sync")
def vars_sync(
    name: str = typer.Argument(..., help="Prompt name"),
) -> None:
    """Scan the latest prompt version and auto-register detected {variables}."""
    from promptview.template import extract_variables
    from promptview.storage.models import PromptVariable
    repo = _open_repo()
    prompt = _get_prompt(repo, name)
    versions = repo.db.list_versions(prompt.id)
    if not versions:
        console.print(f"[red]No versions for {name!r}[/red]")
        raise typer.Exit(1)

    raw = versions[-1].raw_content
    found = extract_variables(raw)
    if not found:
        console.print(f"[yellow]No {{variable}} slots detected in {name!r}[/yellow]")
        repo.close()
        return

    added = 0
    for var_name in found:
        existing = repo.db.get_variable_by_name(prompt.id, var_name)
        if existing is None:
            v = PromptVariable.new(prompt.id, var_name)
            repo.db.upsert_variable(v)
            added += 1

    console.print(f"[green]Synced {len(found)} variables ({added} new) for {name!r}[/green]")
    repo.close()
