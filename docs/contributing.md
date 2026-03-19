# Contributing

Thank you for your interest in contributing to PromptView! This guide explains how to set up the development environment and contribute code, documentation, or bug reports.

---

## Development Setup

### Prerequisites

- Python 3.10+
- [UV](https://docs.astral.sh/uv/) (recommended) or pip
- Git

### Clone and Install

```bash
git clone https://github.com/harshmunshi/promptview.git
cd promptview

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev tools)
uv sync

# Verify installation
uv run pv --help
```

### Run the CLI from Source

```bash
uv run pv init
uv run pv scan
uv run pv ui
```

### Run Tests

```bash
uv run pytest

# Run a specific test file
uv run pytest tests/test_scanner.py -v

# Run with output
uv run pytest -s
```

---

## Project Structure

```
promptview/
├── pyproject.toml               # Build config, dependencies, entry points
├── CLAUDE.md                    # Build spec (single source of truth)
├── README.md                    # User documentation
├── docs/                        # MkDocs documentation
├── examples/
│   └── prompts_demo.py          # Demo prompts for testing
└── src/promptview/
    ├── __init__.py
    ├── exceptions.py            # Custom exceptions (NotInitializedError, etc.)
    ├── template.py              # {variable} + {{ include }} engine
    ├── cli/
    │   ├── main.py              # Typer app — registers all commands
    │   ├── output.py            # Rich formatting helpers
    │   └── commands/            # One file per command (22 files)
    ├── scanner/                 # AST-based prompt detector
    │   ├── base.py              # Directory walker
    │   ├── ast_visitor.py       # AST node visitor
    │   ├── resolver.py          # Variable name → string content
    │   ├── result.py            # ScannedPrompt dataclass
    │   └── patterns/__init__.py # SDK call pattern definitions
    ├── llm/
    │   ├── client.py            # Uniform LLM interface
    │   └── decomposer.py        # Decompose + surgical regenerate
    ├── eval/
    │   ├── dataset.py           # JSONL test case loader
    │   ├── runner.py            # LLM-driven eval execution
    │   └── scorer.py            # Scoring functions
    ├── storage/
    │   ├── models.py            # All dataclasses and enums
    │   ├── db.py                # SQLite layer (raw SQL)
    │   ├── repository.py        # PromptRepository facade
    │   └── diff_engine.py       # Unified diff between versions
    ├── remotes/
    │   ├── base.py              # RemoteBackend ABC
    │   ├── s3.py                # S3 backend
    │   ├── gcs.py               # GCS backend
    │   └── http.py              # HTTP backend
    ├── server/
    │   ├── app.py               # FastAPI factory
    │   ├── schemas.py           # Pydantic request/response models
    │   ├── static/index.html    # Full SPA (D3 + vanilla JS)
    │   └── routes/              # 6 router files
    └── integrations/
        ├── base.py              # RemoteIntegration ABC
        ├── langfuse.py
        └── langsmith.py
```

---

## Adding a New LLM Provider

1. Open `src/promptview/llm/client.py`
2. Add a branch in the `complete()` method for your provider
3. Follow the same pattern: receive `(system, user)` strings, return a response string
4. Add your provider to the UI dropdown in `server/static/index.html`
5. Add your provider to the CLI `--provider` option in relevant command files
6. Add a row to the providers table in `docs/llm/providers.md`

```python
# In client.py — adding a hypothetical "mistral-cloud" provider
elif self.provider == "mistral-cloud":
    import mistralai
    client = mistralai.Mistral(api_key=self.api_key)
    response = client.chat.complete(
        model=self.model or "mistral-large-latest",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return response.choices[0].message.content
```

---

## Adding a New Remote Backend

1. Create `src/promptview/remotes/mybackend.py`
2. Subclass `RemoteBackend` and implement `push()`, `pull()`, `exists()`, and `from_url()`
3. Add the URL scheme dispatch in `remotes/base.py`'s `from_url()` method
4. Add an optional extra in `pyproject.toml` if it needs a new dependency
5. Document in `docs/integrations/remote-backends.md`

```python
# remotes/mybackend.py
from pathlib import Path
from .base import RemoteBackend

class MyBackend(RemoteBackend):
    def __init__(self, ...):
        ...

    def push(self, db_path: Path) -> None:
        ...

    def pull(self, db_path: Path) -> None:
        ...

    def exists(self) -> bool:
        ...

    @classmethod
    def from_url(cls, url: str) -> "MyBackend":
        # Parse the URL and return an instance
        ...
```

```python
# In remotes/base.py — add the dispatch
elif url.startswith("myscheme://"):
    from .mybackend import MyBackend
    return MyBackend.from_url(url)
```

---

## Adding a New CLI Command

1. Create `src/promptview/cli/commands/my_command.py`
2. Define a `app = typer.Typer()` with your commands
3. Register it in `src/promptview/cli/main.py`
4. Add to the CLI overview table in `docs/cli/overview.md`
5. Create `docs/cli/my-command.md` with full documentation

```python
# cli/commands/my_command.py
import typer
from rich.console import Console

app = typer.Typer(help="Description of what this command group does.")
console = Console()

@app.command("run")
def run(
    name: str = typer.Argument(..., help="The thing to run"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run something useful."""
    from ...storage.repository import PromptRepository
    repo = PromptRepository(PromptRepository.find_root())
    repo.open()
    try:
        ...
    finally:
        repo.close()
```

```python
# In cli/main.py — register it
from .commands.my_command import app as my_command_app
app.add_typer(my_command_app, name="mycommand")
```

---

## Adding a New Database Table

PromptView uses no ORM and no migration framework. Adding a new table:

1. Add the `CREATE TABLE IF NOT EXISTS` statement to `storage/db.py`'s schema block
2. Add the corresponding dataclass to `storage/models.py`
3. Add CRUD methods to `storage/db.py` and expose them via `storage/repository.py`
4. Add Pydantic schemas to `server/schemas.py`
5. Create a new route in `server/routes/` or add to an existing one

The schema block runs on every `connect()` call, so the table appears automatically.

---

## Code Style

- **Type hints**: use them everywhere. `def foo(x: str) -> list[str]:`
- **Docstrings**: short one-line for simple functions, multi-line for complex ones
- **Error handling**: catch specific exceptions; use `rich.console.Console` for user-facing errors
- **No magic**: explicit is better than implicit. Avoid metaclasses, decorators-that-modify-behaviour, etc.
- **No ORM**: continue using plain `sqlite3` with hand-written SQL

---

## Pull Request Guidelines

- Keep PRs focused — one feature or fix per PR
- Include tests for new functionality where practical
- Update the relevant `docs/` page for any user-facing change
- Run `mkdocs build --strict` before submitting to catch doc errors
- Use descriptive commit messages (see the commit style in `pv log --oneline`)

### PR Checklist

- [ ] Code works locally with `uv run pv <command>`
- [ ] Tests pass: `uv run pytest`
- [ ] Docs updated for user-facing changes
- [ ] `mkdocs build --strict` passes
- [ ] No untracked prompts: `uv run pv scan --fail-on-untracked`

---

## Reporting Bugs

Open a GitHub issue with:
- PromptView version (`pv --version`)
- Python version (`python --version`)
- OS and version
- Steps to reproduce
- Expected vs. actual behavior
- Full error output (run with `--debug` if available)

---

## Feature Requests

Open a GitHub issue labeled "enhancement" with:
- The use case you're trying to solve
- Your proposed solution (if any)
- Any alternatives you've considered

---

## License

PromptView is MIT licensed. By contributing, you agree your contributions will be licensed under the same terms.
