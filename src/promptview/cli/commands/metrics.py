"""pv metrics — view eval metrics across prompt versions."""
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="View evaluation metrics across versions.")
console = Console()


@app.command("show")
def show(
    prompt_name: str = typer.Argument(..., help="Prompt name"),
    last: int = typer.Option(10, "--last", "-n", help="Show last N eval runs"),
    plot: bool = typer.Option(False, "--plot", help="Show ASCII sparkline"),
):
    """Show eval metrics for a prompt across versions."""
    from ...storage.repository import PromptRepository
    from ...exceptions import NotInitializedError

    repo = PromptRepository(PromptRepository.find_root())
    try:
        repo.open()
    except NotInitializedError:
        console.print("[red]Not initialized. Run: pv init[/red]")
        raise typer.Exit(1)

    try:
        prompts = repo.list_prompts()
        p = next((x for x in prompts if x.name == prompt_name), None)
        if not p:
            console.print(f"[red]Prompt '{prompt_name}' not found[/red]")
            raise typer.Exit(1)

        runs = repo.db.list_eval_runs(p.id)[-last:]
        if not runs:
            console.print(f"[yellow]No eval runs found for '{prompt_name}'. Run: pv eval <dataset.jsonl> --prompt {prompt_name}[/yellow]")
            return

        table = Table(title=f"Metrics: {prompt_name}", show_header=True)
        table.add_column("Run ID", style="dim", max_width=8)
        table.add_column("Version")
        table.add_column("Source", style="dim")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Passed/Total", justify="right")
        table.add_column("Judge Score", justify="right")
        table.add_column("Avg Latency", justify="right")
        table.add_column("Run At", style="dim")

        versions = {v.id: v for v in repo.db.list_versions(p.id)}

        for run in runs:
            v = versions.get(run.version_id)
            v_num = str(v.version_number) if v else "?"
            judge = f"{run.avg_judge_score:.2f}" if run.avg_judge_score is not None else "-"
            table.add_row(
                run.id[:8],
                f"v{v_num}",
                run.source,
                f"{run.pass_rate:.1f}%",
                f"{run.passed}/{run.total_cases}",
                judge,
                f"{run.avg_latency_ms:.0f}ms",
                run.run_at[:19],
            )

        console.print(table)

        if plot and runs:
            rates = [run.pass_rate for run in runs]
            _print_sparkline(rates, "Pass Rate %")

    finally:
        repo.close()


@app.command("compare")
def compare(
    v1: str = typer.Argument(..., help="First run ID or version number"),
    v2: str = typer.Argument(..., help="Second run ID or version number"),
    prompt_name: Optional[str] = typer.Option(None, "--prompt", "-p"),
):
    """Compare two eval runs side-by-side."""
    from ...storage.repository import PromptRepository
    from ...exceptions import NotInitializedError

    repo = PromptRepository(PromptRepository.find_root())
    try:
        repo.open()
    except NotInitializedError:
        console.print("[red]Not initialized.[/red]")
        raise typer.Exit(1)

    try:
        if prompt_name:
            prompts = repo.list_prompts()
            p = next((x for x in prompts if x.name == prompt_name), None)
            if not p:
                console.print(f"[red]Prompt '{prompt_name}' not found[/red]")
                raise typer.Exit(1)
            runs = repo.db.list_eval_runs(p.id)
        else:
            console.print("[red]Provide --prompt name[/red]")
            raise typer.Exit(1)

        def find_run(key):
            # Try as run ID prefix
            matches = [r for r in runs if r.id.startswith(key)]
            if matches:
                return matches[0]
            # Try as version number
            versions = {v.version_number: v for v in repo.db.list_versions(p.id)}
            try:
                vnum = int(key)
                v = versions.get(vnum)
                if v:
                    vmatches = [r for r in runs if r.version_id == v.id]
                    if vmatches:
                        return vmatches[-1]
            except ValueError:
                pass
            return None

        run1 = find_run(v1)
        run2 = find_run(v2)

        if not run1 or not run2:
            console.print("[red]Could not find one or both runs. Use 'pv metrics show' to list run IDs.[/red]")
            raise typer.Exit(1)

        table = Table(title="Comparison", show_header=True)
        table.add_column("Metric")
        table.add_column(f"Run {run1.id[:8]} (v{v1})", justify="right")
        table.add_column(f"Run {run2.id[:8]} (v{v2})", justify="right")
        table.add_column("Delta", justify="right")

        def delta_str(a, b, fmt=".1f", suffix=""):
            if a is None or b is None:
                return "-"
            d = b - a
            color = "green" if d >= 0 else "red"
            return f"[{color}]{d:+{fmt}}{suffix}[/{color}]"

        table.add_row("Pass Rate", f"{run1.pass_rate:.1f}%", f"{run2.pass_rate:.1f}%", delta_str(run1.pass_rate, run2.pass_rate, suffix="%"))
        table.add_row("Passed", str(run1.passed), str(run2.passed), delta_str(run1.passed, run2.passed, fmt="d"))
        table.add_row("Total Cases", str(run1.total_cases), str(run2.total_cases), "-")
        judge1 = f"{run1.avg_judge_score:.2f}" if run1.avg_judge_score is not None else "-"
        judge2 = f"{run2.avg_judge_score:.2f}" if run2.avg_judge_score is not None else "-"
        table.add_row("Judge Score", judge1, judge2, delta_str(run1.avg_judge_score, run2.avg_judge_score))
        table.add_row("Avg Latency", f"{run1.avg_latency_ms:.0f}ms", f"{run2.avg_latency_ms:.0f}ms", delta_str(run1.avg_latency_ms, run2.avg_latency_ms, suffix="ms"))
        table.add_row("Source", run1.source, run2.source, "-")

        console.print(table)
    finally:
        repo.close()


@app.command("results")
def results(
    run_id: str = typer.Argument(..., help="Eval run ID (or prefix) from 'pv metrics show'"),
    prompt_name: str = typer.Option(..., "--prompt", "-p", help="Prompt name"),
    failed_only: bool = typer.Option(False, "--failed", "-f", help="Show only failed cases"),
):
    """Show per-case inputs, actual responses, and scores for an eval run."""
    from ...storage.repository import PromptRepository
    from ...exceptions import NotInitializedError

    repo = PromptRepository(PromptRepository.find_root())
    try:
        repo.open()
    except NotInitializedError:
        console.print("[red]Not initialized. Run: pv init[/red]")
        raise typer.Exit(1)

    try:
        prompts = repo.list_prompts()
        p = next((x for x in prompts if x.name == prompt_name), None)
        if not p:
            console.print(f"[red]Prompt '{prompt_name}' not found[/red]")
            raise typer.Exit(1)

        # Resolve run ID (full or prefix)
        runs = repo.db.list_eval_runs(p.id)
        run = next((r for r in runs if r.id.startswith(run_id)), None)
        if not run:
            console.print(f"[red]No eval run starting with '{run_id}' for prompt '{prompt_name}'[/red]")
            console.print("[dim]Use 'pv metrics show <prompt>' to list run IDs[/dim]")
            raise typer.Exit(1)

        eval_results = repo.db.list_eval_results(run.id)
        if not eval_results:
            console.print("[yellow]No individual results stored for this run.[/yellow]")
            return

        # Build test case lookup
        test_cases = {tc.id: tc for tc in repo.db.list_test_cases(p.id)}

        if failed_only:
            eval_results = [r for r in eval_results if not r.passed]

        console.print(f"\n[bold]Eval run [cyan]{run.id[:8]}[/cyan] — {len(eval_results)} case(s)[/bold]\n")

        for i, r in enumerate(eval_results, 1):
            tc = test_cases.get(r.test_case_id)
            status = "[green]✓ PASS[/green]" if r.passed else "[red]✗ FAIL[/red]"
            console.print(f"[bold dim]─── Case {i} {status} ───────────────────────────[/bold dim]")

            # Input
            console.print(f"[dim]Input:[/dim]")
            console.print(f"  {tc.input if tc else '[unknown]'}\n")

            # Actual response
            console.print(f"[dim]Actual response:[/dim]")
            if r.actual_output and r.actual_output.startswith("[ERROR"):
                console.print(f"  [red]{r.actual_output}[/red]\n")
            else:
                console.print(f"  [cyan]{r.actual_output or '(empty)'}[/cyan]\n")

            # Expected (if any)
            expected = (tc.expected_output if tc else None)
            if expected:
                console.print(f"[dim]Expected:[/dim]")
                console.print(f"  {expected}\n")

            # Scores row
            scores = []
            if r.similarity_score is not None:
                scores.append(f"similarity={r.similarity_score:.2f}")
            if r.judge_score is not None:
                scores.append(f"judge={r.judge_score:.2f}")
            if r.latency_ms:
                scores.append(f"latency={r.latency_ms:.0f}ms")
            if scores:
                console.print(f"[dim]{' · '.join(scores)}[/dim]")

            # Judge reasoning
            if r.judge_reasoning:
                console.print(f"[dim]Judge reasoning:[/dim] [italic]{r.judge_reasoning}[/italic]")

            console.print()

        passed = sum(1 for r in eval_results if r.passed)
        total = len(eval_results)
        color = "green" if passed == total else "yellow" if passed > 0 else "red"
        console.print(f"[bold]Summary:[/bold] [{color}]{passed}/{total} passed[/{color}]")

    finally:
        repo.close()


def _print_sparkline(values: list, label: str):
    """Print a simple ASCII sparkline."""
    if not values:
        return
    chars = "▁▂▃▄▅▆▇█"
    min_v, max_v = min(values), max(values)
    rng = max_v - min_v or 1
    bars = "".join(chars[int((v - min_v) / rng * 7)] for v in values)
    console.print(f"\n[dim]{label}[/dim]")
    console.print(f"[cyan]{bars}[/cyan]  min={min_v:.1f}% max={max_v:.1f}%")
