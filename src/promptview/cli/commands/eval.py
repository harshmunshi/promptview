"""pv eval — run evaluations against test datasets."""
import typer
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Run evaluations against test datasets.")
console = Console()


@app.callback(invoke_without_command=True)
def eval_cmd(
    ctx: typer.Context,
    dataset: Optional[Path] = typer.Argument(None, help="JSONL dataset file path"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Prompt name"),
    version: Optional[int] = typer.Option(None, "--version", "-v", help="Version number"),
    judge: bool = typer.Option(False, "--judge", help="Enable LLM-as-judge scoring"),
    provider: Optional[str] = typer.Option(None, "--provider", help="LLM provider (openai/anthropic/gemini/ollama)"),
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar=["OPENAI_API_KEY", "ANTHROPIC_API_KEY"], help="LLM API key"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name override"),
    fail_on_regression: Optional[float] = typer.Option(None, "--fail-on-regression", help="Exit 1 if pass_rate drops more than this fraction vs previous run"),
    import_from: Optional[str] = typer.Option(None, "--import", help="Import eval scores from: langfuse, langsmith"),
):
    """Run evaluations against a JSONL test dataset."""
    from ...storage.repository import PromptRepository
    from ...eval.dataset import load_jsonl, build_test_cases
    from ...eval.runner import EvalRunner
    from ...llm.client import LLMClient
    from ...exceptions import NotInitializedError

    if ctx.invoked_subcommand is not None:
        return

    repo = PromptRepository(PromptRepository.find_root())
    try:
        repo.open()
    except NotInitializedError:
        console.print("[red]Not initialized. Run: pv init[/red]")
        raise typer.Exit(1)

    try:
        if import_from:
            console.print(f"[yellow]Importing eval scores from {import_from}...[/yellow]")
            console.print("[dim]Pull integration coming in Phase 4[/dim]")
            return

        if not dataset:
            console.print("[red]Please provide a dataset path or use --import[/red]")
            raise typer.Exit(1)

        if not dataset.exists():
            console.print(f"[red]Dataset not found: {dataset}[/red]")
            raise typer.Exit(1)

        # Load dataset
        rows = load_jsonl(str(dataset))
        console.print(f"Loaded [cyan]{len(rows)}[/cyan] test cases from [dim]{dataset}[/dim]")

        # Determine prompts to evaluate
        all_prompts = repo.list_prompts()
        if prompt:
            prompts_to_eval = [p for p in all_prompts if p.name == prompt]
            if not prompts_to_eval:
                console.print(f"[red]Prompt '{prompt}' not found[/red]")
                raise typer.Exit(1)
        else:
            prompts_to_eval = all_prompts

        if not prompts_to_eval:
            console.print("[yellow]No prompts found. Run: pv scan && pv add . && pv commit[/yellow]")
            return

        # Build LLM client
        llm_client = None
        if provider and (api_key or provider == 'ollama'):
            llm_client = LLMClient(provider=provider, api_key=api_key or '', model=model)

        runner = EvalRunner(repo=repo, llm_client=llm_client)

        # Results table
        table = Table(title="Eval Results", show_header=True)
        table.add_column("Prompt", style="cyan")
        table.add_column("Version", justify="right")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Passed/Total", justify="right")
        table.add_column("Avg Latency", justify="right")
        if judge:
            table.add_column("Judge Score", justify="right")

        had_regression = False

        for p in prompts_to_eval:
            cases = build_test_cases(p.id, rows)
            versions = repo.db.list_versions(p.id)
            if not versions:
                continue

            target_version = None
            if version:
                for v in versions:
                    if v.version_number == version:
                        target_version = v
                        break
            else:
                target_version = versions[-1]

            if not target_version:
                continue

            with console.status(f"Evaluating [cyan]{p.name}[/cyan] v{target_version.version_number}..."):
                run = runner.run(
                    prompt_id=p.id,
                    version_id=target_version.id,
                    test_cases=cases,
                    use_judge=judge,
                    dataset_path=str(dataset),
                )

            # Check regression
            if fail_on_regression is not None:
                prev_runs = repo.db.list_eval_runs(p.id)
                if len(prev_runs) >= 2:
                    prev_run = prev_runs[-2]
                    drop = prev_run.pass_rate - run.pass_rate
                    if drop > (fail_on_regression * 100):
                        console.print(f"[red]REGRESSION: {p.name} pass rate dropped {drop:.1f}% (threshold: {fail_on_regression*100:.1f}%)[/red]")
                        had_regression = True

            row_data = [
                p.name,
                str(target_version.version_number),
                f"{run.pass_rate:.1f}%",
                f"{run.passed}/{run.total_cases}",
                f"{run.avg_latency_ms:.0f}ms",
            ]
            if judge:
                score_str = f"{run.avg_judge_score:.2f}" if run.avg_judge_score is not None else "-"
                row_data.append(score_str)
            table.add_row(*row_data)

        console.print(table)

        if had_regression:
            raise typer.Exit(1)

    finally:
        repo.close()
