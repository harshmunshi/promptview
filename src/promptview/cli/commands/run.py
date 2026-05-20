"""pv run — render a prompt with variable substitution and optionally call an LLM."""
import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

app = typer.Typer(help="Render a prompt with variable values.")
console = Console()


@app.callback(invoke_without_command=True)
def run_command(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Prompt name to run"),
    var: list[str] = typer.Option([], "--var", "-v", help="Variable values: key=value"),
    call: bool = typer.Option(False, "--call", help="Send rendered prompt to LLM"),
    provider: str = typer.Option("openai", "--provider", "-p"),
    api_key: str = typer.Option("", "--api-key", envvar=["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]),
    model: str = typer.Option("", "--model", "-m"),
    output: bool = typer.Option(True, "--output/--no-output", help="Print rendered prompt"),
) -> None:
    """Render prompt NAME with variable substitution.

    Example:
        pv run my_prompt --var user=Alice --var lang=Python
    """
    from promptview.storage.repository import PromptRepository
    from promptview.template import render_full, extract_variables
    from promptview.exceptions import NotInitializedError

    # Parse --var key=value pairs
    overrides: dict[str, str] = {}
    for v in var:
        if "=" not in v:
            console.print(f"[red]Invalid --var format: {v!r}. Use key=value[/red]")
            raise typer.Exit(1)
        k, val = v.split("=", 1)
        overrides[k.strip()] = val.strip()

    # Open repo
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Find prompt
    prompt = repo.get_prompt_by_name(name)
    if prompt is None:
        console.print(f"[red]Prompt not found: {name!r}[/red]")
        raise typer.Exit(1)

    # Get latest version content
    versions = repo.db.list_versions(prompt.id)
    if not versions:
        console.print(f"[red]No versions found for prompt: {name!r}[/red]")
        raise typer.Exit(1)

    latest = versions[-1]
    raw = latest.raw_content

    # Build variable map: stored defaults -> overrides
    stored_vars = repo.db.list_variables(prompt.id)
    var_map = {v.name: v.default_value for v in stored_vars}
    var_map.update(overrides)

    # Build include lookup
    all_prompts = repo.list_prompts()
    lookup: dict[str, str] = {}
    for p in all_prompts:
        vs = repo.db.list_versions(p.id)
        if vs:
            lookup[p.name] = vs[-1].raw_content

    # Render
    rendered = render_full(raw, var_map, lookup)

    # Show unresolved variables
    unresolved = extract_variables(rendered)
    if unresolved:
        console.print(f"[yellow]Unresolved variables: {', '.join(unresolved)}[/yellow]")

    if output:
        console.print(Panel(
            Syntax(rendered, "markdown", theme="monokai", word_wrap=True),
            title=f"[bold]{name}[/bold]",
            border_style="blue",
        ))

    # Optionally call LLM
    if call:
        from promptview.llm.client import LLMClient
        if not api_key:
            api_key = (
                os.getenv("OPENAI_API_KEY") or
                os.getenv("ANTHROPIC_API_KEY") or
                os.getenv("GOOGLE_API_KEY") or ""
            )
        client = LLMClient(provider=provider, api_key=api_key, model=model or None)
        console.print("\n[dim]Calling LLM...[/dim]")
        result = client.complete(system=rendered, user="")
        console.print(Panel(result, title="[bold green]LLM Response[/bold green]", border_style="green"))

    repo.close()
