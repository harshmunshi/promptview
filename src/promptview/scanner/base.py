"""Scanner orchestration - scans a directory tree for prompts."""

import ast
from pathlib import Path
from typing import Optional

from .ast_visitor import PromptASTVisitor
from .result import ScannedPrompt

DEFAULT_EXCLUDES = {
    ".venv", "venv", ".env", "env",
    "node_modules", "__pycache__", ".git", ".promptview",
    "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
}


def _should_exclude(path: Path, excludes: set[str]) -> bool:
    for part in path.parts:
        if part in excludes:
            return True
    return False


def scan_file(file_path: Path, root: Optional[Path] = None) -> list[ScannedPrompt]:
    """Scan a single Python file and return discovered prompts."""
    try:
        source = file_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []
    except Exception:
        return []

    rel_path = str(file_path.relative_to(root)) if root else str(file_path)
    source_lines = source.splitlines(keepends=True)
    visitor = PromptASTVisitor(file_path=rel_path, source_lines=source_lines)
    visitor.visit(tree)
    return visitor.results


def scan_directory(
    root: Path,
    extra_excludes: Optional[list[str]] = None,
    min_confidence: float = 0.0,
) -> list[ScannedPrompt]:
    """
    Recursively scan all Python files under `root` for prompts.
    Returns list of ScannedPrompt sorted by (file_path, line_number).
    """
    excludes = DEFAULT_EXCLUDES.copy()
    if extra_excludes:
        excludes.update(extra_excludes)

    results: list[ScannedPrompt] = []
    seen: set[tuple[str, int]] = set()

    for py_file in root.rglob("*.py"):
        if _should_exclude(py_file.relative_to(root), excludes):
            continue
        file_results = scan_file(py_file, root=root)
        for r in file_results:
            key = (r.file_path, r.line_number)
            if key not in seen and r.confidence >= min_confidence:
                seen.add(key)
                results.append(r)

    results.sort(key=lambda r: (r.file_path, r.line_number))
    return results


def derive_prompt_name(sp: ScannedPrompt, existing_names: set[str]) -> str:
    """Derive a human-readable prompt name from a ScannedPrompt."""
    raw = sp.variable_name

    # Strip line-number suffixes from auto-generated names
    import re
    if re.match(r"(openai|anthropic|langchain|litellm)_\w+_l\d+", raw):
        # Use pattern + file stem + line
        stem = Path(sp.file_path).stem
        base = f"{stem}_{sp.source.value}_l{sp.line_number}"
    else:
        # Convert CamelCase to snake_case
        base = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", raw).lower()
        base = re.sub(r"[^a-z0-9_]", "_", base).strip("_")

    # Ensure uniqueness
    name = base
    counter = 1
    while name in existing_names:
        name = f"{base}_{counter}"
        counter += 1
    return name
