"""promptview add command."""

import hashlib
import typer
from pathlib import Path

from ..output import console, success, error, info, warn
from ...storage.repository import PromptRepository
from ...exceptions import NotInitializedError


def add_command(
    name: str = typer.Argument(".", help="Prompt name, '.' for all, or --file for a specific file"),
    file: str = typer.Option("", "--file", "-f", help="Add all prompts from a specific file"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-c"),
) -> None:
    """Stage prompt changes for commit."""
    root = PromptRepository.find_root()
    repo = PromptRepository(root)
    try:
        repo.open()
    except NotInitializedError as e:
        error(str(e))
        raise typer.Exit(1)

    from ...scanner import scan_directory, scan_file, derive_prompt_name
    cfg = repo.get_config()
    extra_excludes = cfg.get("scan", {}).get("exclude", [])
    threshold = cfg.get("scan", {}).get("confidence_threshold", min_confidence)

    with console.status("[cyan]Scanning for prompts...[/cyan]"):
        if file:
            fp = Path(file)
            if not fp.exists():
                error(f"File not found: {file}")
                raise typer.Exit(1)
            scanned = scan_file(fp, root=root)
        else:
            scanned = scan_directory(root, extra_excludes=extra_excludes, min_confidence=threshold)

    # Filter to specific name if not "."
    if name != "." and not file:
        scanned = [s for s in scanned if s.variable_name == name or s.variable_name.startswith(name)]

    if not scanned:
        warn("No prompts found to stage.")
        return

    existing_names = {p.name for p in repo.list_prompts()}
    staged_count = 0
    modified_count = 0

    for sp in scanned:
        if sp.confidence < threshold and name == ".":
            continue

        # Find existing prompt by variable name or derived name
        existing = repo.get_prompt_by_name(sp.variable_name)
        if existing is None:
            # Try derived name
            derived = derive_prompt_name(sp, existing_names)
            existing = repo.get_prompt_by_name(derived)

        content_hash = hashlib.sha256(sp.raw_content.encode()).hexdigest()

        if existing is None:
            # New prompt
            prompt_name = derive_prompt_name(sp, existing_names)
            existing_names.add(prompt_name)
            prompt, version = repo.create_prompt(
                name=prompt_name,
                content=sp.raw_content,
                source=sp.source,
                file_path=sp.file_path,
                line_number=sp.line_number,
                variable_name=sp.variable_name,
                blocks=sp.blocks,
            )
            repo.stage(prompt.id, prompt.name, version.id, "added")
            staged_count += 1
            console.print(f"  [green]new file:[/green]   {prompt.name}")
        else:
            # Check if content changed
            committed = repo.db.get_committed_version(existing.id)
            if committed and committed.content_hash == content_hash:
                # No change
                continue
            version = repo.update_prompt_content(
                existing.id, sp.raw_content, blocks=sp.blocks
            )
            if version:
                change_type = "added" if committed is None else "modified"
                repo.stage(existing.id, existing.name, version.id, change_type)
                modified_count += 1
                console.print(f"  [yellow]modified:[/yellow]   {existing.name}")

    total = staged_count + modified_count
    if total == 0:
        info("Nothing new to stage. All prompts are up to date.")
    else:
        success(f"\n{total} prompt(s) staged. Run [cyan]promptview commit -m 'message'[/cyan] to commit.")

    repo.close()
