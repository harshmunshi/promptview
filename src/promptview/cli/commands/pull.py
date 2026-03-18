"""promptview pull command — pull prompts and evals from a remote."""

from typing import Optional

import typer
from rich.table import Table

from ..output import console, success, error, info, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError

app = typer.Typer(
    name="pull",
    help="Pull prompts and eval scores from a remote (langfuse/langsmith).",
    no_args_is_help=True,
)


def _get_integration(remote: str, repo: PromptRepository):
    """Instantiate the correct integration, reading credentials from config.toml."""
    cfg = repo.get_config()

    if remote == "langfuse":
        import os
        langfuse_cfg = cfg.get("langfuse", {})
        public_key = langfuse_cfg.get("public_key", os.environ.get("LANGFUSE_PUBLIC_KEY", ""))
        secret_key = langfuse_cfg.get("secret_key", os.environ.get("LANGFUSE_SECRET_KEY", ""))
        host = langfuse_cfg.get("host", os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"))

        if not public_key or not secret_key:
            error(
                "Langfuse credentials not configured.\n"
                "Run: pv config langfuse.public_key <key> && pv config langfuse.secret_key <key>"
            )
            raise typer.Exit(1)

        # Override env so LangfuseIntegration picks them up
        os.environ["LANGFUSE_PUBLIC_KEY"] = public_key
        os.environ["LANGFUSE_SECRET_KEY"] = secret_key
        os.environ["LANGFUSE_HOST"] = host

        try:
            from ...integrations.langfuse import LangfuseIntegration
            return LangfuseIntegration()
        except ImportError:
            error("Langfuse not installed. Run: pip install promptview[langfuse]")
            raise typer.Exit(1)
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1)

    elif remote == "langsmith":
        import os
        langsmith_cfg = cfg.get("langsmith", {})
        api_key = langsmith_cfg.get("api_key", os.environ.get("LANGSMITH_API_KEY", ""))
        project = langsmith_cfg.get("project", os.environ.get("LANGCHAIN_PROJECT", ""))

        if not api_key:
            error(
                "LangSmith credentials not configured.\n"
                "Run: pv config langsmith.api_key <key>"
            )
            raise typer.Exit(1)

        os.environ["LANGSMITH_API_KEY"] = api_key
        if project:
            os.environ["LANGCHAIN_PROJECT"] = project

        try:
            from ...integrations.langsmith import LangSmithIntegration
            return LangSmithIntegration()
        except ImportError:
            error("LangSmith not installed. Run: pip install promptview[langsmith]")
            raise typer.Exit(1)
        except ValueError as e:
            error(str(e))
            raise typer.Exit(1)

    else:
        error(f"Unknown remote: {remote!r}. Use 'langfuse' or 'langsmith'.")
        raise typer.Exit(1)


@app.command("langfuse")
def pull_langfuse(
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Pull only this prompt by name"),
    evals: bool = typer.Option(False, "--evals", help="Also pull eval scores for local versions"),
) -> None:
    """Pull prompts (and optionally eval scores) from Langfuse."""
    _pull("langfuse", prompt_filter=prompt, pull_evals=evals)


@app.command("langsmith")
def pull_langsmith(
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Pull only this prompt by name"),
    evals: bool = typer.Option(False, "--evals", help="Also pull eval scores for local versions"),
) -> None:
    """Pull prompts (and optionally eval scores) from LangSmith."""
    _pull("langsmith", prompt_filter=prompt, pull_evals=evals)


def _pull(remote: str, prompt_filter: Optional[str], pull_evals: bool) -> None:
    """Core pull logic shared by langfuse and langsmith sub-commands."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    integration = _get_integration(remote, repo)

    # ---- Pull prompts ----
    if not pull_evals:
        info(f"Fetching prompts from {remote}...")
        try:
            remote_data = integration.pull_prompts()
        except Exception as exc:
            error(f"Failed to fetch prompts from {remote}: {exc}")
            raise typer.Exit(1)

        if not remote_data:
            warn(f"No prompts found in {remote}.")
        else:
            # Filter to a single prompt if requested
            if prompt_filter:
                remote_data = [d for d in remote_data if d.get("name") == prompt_filter]
                if not remote_data:
                    warn(f"Prompt {prompt_filter!r} not found in {remote}.")
                    repo.close()
                    return

            summary = repo.ingest_remote_prompts(remote_data, source=remote)

            # Pretty table output
            table = Table(title=f"Pull from {remote}", show_header=True, header_style="bold cyan")
            table.add_column("Prompt", style="white")
            table.add_column("Status", style="green")
            for item in remote_data:
                name = item.get("name", "?")
                table.add_row(name, "ingested")
            console.print(table)

            success(
                f"Done. created={summary['created']}  "
                f"updated={summary['updated']}  "
                f"skipped={summary['skipped']}"
            )

    # ---- Pull evals ----
    if pull_evals:
        info(f"Fetching eval scores from {remote}...")
        local_prompts = repo.list_prompts()
        if prompt_filter:
            local_prompts = [p for p in local_prompts if p.name == prompt_filter]

        total_evals = 0
        for prompt_obj in local_prompts:
            versions = repo.list_versions(prompt_obj.id)
            for version in versions:
                try:
                    scores = integration.pull_evals(prompt_obj.name, version.content_hash)
                except Exception:
                    scores = []

                if not scores:
                    continue

                # Store each score batch as an EvalRun
                from ...storage.models import EvalRun
                run = EvalRun.new(
                    prompt_id=prompt_obj.id,
                    version_id=version.id,
                    source=remote,
                    provider=remote,
                    model=None,
                )
                # Summarise scores into the run's custom_metrics
                avg_score = sum(s.get("score", 0) for s in scores) / len(scores)
                run.total_cases = len(scores)
                run.avg_judge_score = avg_score
                run.custom_metrics = {
                    "scores": [
                        {
                            "name": s.get("name", ""),
                            "score": s.get("score", 0),
                            "comment": s.get("comment", ""),
                            "created_at": s.get("created_at", ""),
                        }
                        for s in scores
                    ]
                }
                repo.db.create_eval_run(run)
                total_evals += len(scores)
                info(f"  {prompt_obj.name} v{version.version_number}: {len(scores)} score(s)")

        if total_evals:
            success(f"Imported {total_evals} eval score(s) from {remote}.")
        else:
            warn(f"No eval scores found in {remote}.")

    repo.close()
