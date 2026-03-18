# PromptView — Claude Code Build Spec

This file is the single source of truth for reproducing the entire PromptView project from scratch using Claude Code. Follow it top to bottom.

---

## What PromptView Is

A pip-installable Python library that brings git-like versioning to LLM prompts. It scans any codebase, finds all prompts, versions them, and exposes a web UI where each prompt is broken into structural components (Role, Context, Instructions, Format, Examples…) displayed as a linear node graph. Nodes can be added or deleted and the prompt is regenerated surgically via LLM — preserving the original style and structure.

---

## What Is Already Built (Do Not Rebuild)

Every item below is implemented and working.

### Package & Tooling
- `pyproject.toml` — hatchling build, UV package manager, entry points `promptview` and `pv`
- `.gitignore` — covers Python, UV, venv, OS, IDE, `.promptview/`
- `README.md` — full docs with SVG logo, shields.io badges, pip install instructions, CLI reference, build/publish guide
- `assets/logo.svg` — dark-theme SVG logo (node graph + wordmark)
- `uv.lock` — locked dependency graph

### Core Dependencies (all in `pyproject.toml`)
```
typer[all], rich, fastapi, uvicorn[standard], pydantic, tomli-w,
httpx, python-dotenv, openai>=1.0, anthropic>=0.20, google-generativeai>=0.5
```
Optional: `langfuse`, `langsmith` (via extras `promptview[langfuse]` / `promptview[langsmith]`)

### Storage Layer (`src/promptview/storage/`)
- **`models.py`** — dataclasses: `Prompt`, `PromptVersion`, `PromptBlock`, `Commit`, `PromptComponent`, `PromptVariable`; enums: `PromptSource` (OPENAI, ANTHROPIC, LANGCHAIN, LITELLM, RAW, MANUAL), `PromptRole` (SYSTEM, USER, ASSISTANT, FULL)
- **`db.py`** — SQLite layer with `check_same_thread=False`, tables:
  - `prompts` (id, name, description, source, file_path, line_number, variable_name, tags, timestamps)
  - `prompt_versions` (id, prompt_id, version_number, raw_content, blocks JSON, content_hash, commit_id, parent_version_id)
  - `commits` (id as 8-char hash, message, author, timestamp, version_ids JSON)
  - `remotes` (name PK, provider, endpoint, project)
  - `prompt_components` (id, prompt_id, version_id, label, content, position, created_at)
  - `prompt_variables` (id, prompt_id, name, default_value, description, created_at) — template variable slots
  - Schema runs `CREATE TABLE IF NOT EXISTS` on every `connect()` so new tables auto-migrate
- **`repository.py`** — `PromptRepository` facade: `initialize()`, `open()`, `close()`, staging (`stage/unstage/get_staged/clear_index`), commits, diffs, status, CRUD for prompts and components
- **`diff_engine.py`** — unified diff between two prompt versions

### Scanner (`src/promptview/scanner/`)
- **`base.py`** — walks directory tree, skips `.venv`, `node_modules`, `__pycache__`, `.git`, `.promptview`, `dist`, `build`
- **`ast_visitor.py`** — AST-based prompt detection; matches OpenAI, Anthropic, LangChain, LiteLLM call patterns; confidence scoring
- **`resolver.py`** — resolves variable names to string content from AST
- **`result.py`** — `ScannedPrompt` dataclass
- **`patterns/`** — pattern definitions per SDK

### LLM Client (`src/promptview/llm/`)
- **`client.py`** — `LLMClient(provider, api_key, model)` with uniform `complete(system, user) → str`. Providers: `openai` (gpt-4o-mini), `anthropic` (claude-haiku-4-5), `gemini` (gemini-2.0-flash), `ollama` (llama3, local, no API key). Ollama uses `httpx` to call `http://localhost:11434/api/chat` — no extra deps. Raises a friendly `RuntimeError` if Ollama isn't running.
- **`decomposer.py`** — two operations:
  1. `decompose(prompt_text)` → list of `{label, content}` components
  2. `regenerate(original, old_components, new_components)` → updated prompt text that preserves original formatting/style, only reflecting diffs between old and new components

### Template Engine (`src/promptview/template.py`)
- `extract_variables(text)` — finds all `{slot}` names in prompt text
- `extract_includes(text)` — finds all `{{ include: name }}` directives
- `render(text, variables)` — substitutes `{slot}` with values, leaves unknowns intact
- `resolve_includes(text, lookup)` — replaces `{{ include: name }}` with referenced prompt content
- `render_full(text, variables, lookup)` — includes then variables in one pass

### CLI (`src/promptview/cli/`)
- **`main.py`** — Typer app, registers all commands; both `promptview` and `pv` aliases work
- **`output.py`** — Rich formatting helpers
- **`commands/`** — one file per command:
  - `init.py` — `pv init [path] [--author] [--force] [--no-scan]`
  - `scan.py` — `pv scan [path] [--min-confidence] [--show-all]`
  - `add.py` — `pv add [name|.] [--file] [--min-confidence]`
  - `commit.py` — `pv commit -m "message"`
  - `status.py` — `pv status`
  - `diff.py` — `pv diff [name] [v1] [v2] [--staged]`
  - `log.py` — `pv log [name] [--oneline] [-n]`
  - `ui.py` — `pv ui [--port] [--host] [--no-browser]`
  - `config.py` — `pv config [key] [value] [--show]`
  - `push.py` — `pv push langfuse|langsmith [--dry-run]`
  - `vars.py` — `pv vars sync|show|set` — manage template variable defaults per prompt
  - `run.py` — `pv run NAME [--var key=value] [--call]` — render a prompt with variable substitution and optionally call an LLM

### FastAPI Server (`src/promptview/server/`)
- **`app.py`** — factory: registers 4 routers under `/api`, mounts static, serves `index.html` at `/`, health at `/health`
- **`schemas.py`** — Pydantic request/response models
- **`routes/prompts.py`**:
  - `GET /api/prompts` — list all
  - `GET /api/prompts/{id}` — single prompt
  - `POST /api/prompts` — create
  - `PATCH /api/prompts/{id}` — update metadata/content
  - `DELETE /api/prompts/{id}` — delete
  - `GET /api/prompts/{id}/versions` — all versions (used by version switcher)
  - `POST /api/scan` — trigger scan
  - `POST /api/commit` — commit staged
- **`routes/components.py`**:
  - `GET /api/prompts/{id}/components` — fetch stored components for a version
  - `POST /api/prompts/{id}/decompose` — LLM decompose (body: `{provider, api_key, model, version_id?}`)
  - `POST /api/prompts/{id}/components/add` — insert component + regenerate
  - `PUT /api/prompts/{id}/components` — replace all components + regenerate
  - `DELETE /api/prompts/{id}/components/{cid}` — remove + regenerate
- **`routes/diff.py`** — `GET /api/diff/{id}?v1=X&v2=Y`
- **`routes/graph.py`** — `GET /api/graph` (unused by current UI but available)

### Frontend (`src/promptview/server/static/index.html`)
Single ~850-line vanilla JS + D3.js SPA. GitHub Dark color scheme (`#0d1117`, `#161b22`). Features:
- **Left sidebar**: searchable prompt list, source badge, version count
- **Main area**: D3-rendered vertical linear node stack (component graph per prompt); nodes connected by arrows; click to expand/edit; `+` between nodes to add; `×` to delete
- **Version selector**: pill buttons at top; switching versions reloads components for that version
- **Edit panel**: slides in from right; edit label and content inline
- **Footer**: collapsible reconstructed prompt text
- **Toolbar**: Scan, Commit buttons; LLM config indicator (gear icon opens modal)
- **LLM config modal**: provider dropdown (openai/anthropic/gemini), API key input, model override; stored in `localStorage`
- **Toast notifications**: success/error feedback

### Integrations (`src/promptview/integrations/`)
- **`base.py`** — abstract `RemoteIntegration` with `push_version()`, `pull_versions()`, `list_remote_prompts()`
- **`langfuse.py`** — Langfuse implementation
- **`langsmith.py`** — LangSmith implementation

### Examples
- **`examples/prompts_demo.py`** — demo prompts for testing the scanner and UI

---

## What Is NOT Built Yet (Remaining Work)

### High Priority
- [ ] **Git-style branching** — `pv branch`, `pv checkout`, `pv merge` for prompt branches
- [ ] **`pv pull`** — pull versions from langfuse/langsmith into local repo
- [x] **Prompt templates / variables** — `{variable}` slot detection, `pv vars sync/show/set`, `pv run --var key=value`, UI variables panel, `{{ include: other_prompt }}` composition
- [ ] **Diff view in UI** — side-by-side version diff rendering in the web interface
- [ ] **Export** — export a prompt version as `.txt`, `.json`, or copy to clipboard from UI
- [ ] **Search** — full-text search across prompt content (not just name)

### Medium Priority
- [ ] **Confidence score display** — show scanner confidence in the sidebar
- [ ] **Multi-file prompt assembly** — prompts that reference other prompts (composition)
- [ ] **Pytest plugin** — `pv test` to run prompt regression tests against expected outputs
- [ ] **CI/CD integration** — GitHub Action to run `pv scan` and fail if new untracked prompts found
- [ ] **Langfuse/LangSmith two-way sync** — pull remote changes back into local versions

### Low Priority / Polish
- [ ] **Dark/light theme toggle** in UI
- [ ] **Keyboard shortcuts** in component graph (j/k navigation, e to edit, d to delete)
- [ ] **Undo** for node deletions in UI
- [ ] **Publish to PyPI** — set up PyPI token, run `python -m build && twine upload`
- [ ] **GitHub Actions** — automated test + publish workflow on tag push

---

## Directory Structure (Complete)

```
promptview/
├── CLAUDE.md                          ← this file
├── README.md                          ← user-facing docs with logo + badges
├── pyproject.toml                     ← package config (UV + hatchling)
├── uv.lock                            ← locked deps
├── .gitignore                         ← excludes __pycache__, .venv, .promptview/, dist/
├── assets/
│   └── logo.svg                       ← dark SVG logo (420×120)
├── examples/
│   └── prompts_demo.py                ← test prompts for the scanner
└── src/promptview/
    ├── __init__.py
    ├── exceptions.py                  ← NotInitializedError, PromptNotFoundError, etc.
    ├── cli/
    │   ├── main.py                    ← Typer app, `pv` + `promptview` entry points
    │   ├── output.py                  ← Rich helpers
    │   └── commands/                  ← init, scan, add, commit, status, diff, log, ui, config, push
    ├── scanner/
    │   ├── base.py                    ← directory walker
    │   ├── ast_visitor.py             ← AST-based prompt detector
    │   ├── resolver.py                ← variable → string resolver
    │   ├── result.py                  ← ScannedPrompt model
    │   └── patterns/                  ← SDK-specific patterns
    ├── llm/
    │   ├── client.py                  ← OpenAI / Anthropic / Gemini abstraction
    │   └── decomposer.py              ← decompose + surgical regenerate
    ├── storage/
    │   ├── models.py                  ← Prompt, PromptVersion, Commit, PromptComponent
    │   ├── db.py                      ← SQLite layer (check_same_thread=False, auto-migrate)
    │   ├── repository.py              ← PromptRepository facade
    │   └── diff_engine.py             ← unified diff engine
    ├── server/
    │   ├── app.py                     ← FastAPI factory
    │   ├── schemas.py                 ← Pydantic schemas
    │   ├── static/
    │   │   └── index.html             ← SPA: D3 component graph, version switcher, LLM config
    │   └── routes/
    │       ├── prompts.py             ← CRUD + scan + commit
    │       ├── components.py          ← decompose / add / delete / regenerate
    │       ├── diff.py                ← version diff
    │       └── graph.py              ← graph data
    └── integrations/
        ├── base.py                    ← RemoteIntegration protocol
        ├── langfuse.py
        └── langsmith.py
```

---

## Critical Implementation Details

These are the non-obvious decisions that must be preserved when modifying or extending the code.

### 1. SQLite Thread Safety
`db.py` opens the connection with `check_same_thread=False` because FastAPI runs route handlers in a thread pool. The connection is opened in one thread (at startup) and used across worker threads.

### 2. Schema Auto-Migration
`Database.connect()` always runs the full `CREATE TABLE IF NOT EXISTS` schema. Adding a new table = add it to the schema block in `db.py`. No migration scripts needed.

### 3. Prompt Regeneration Strategy
`decomposer.py` uses a **surgical regeneration** approach: the LLM receives the original prompt text, the old component list, and the new component list. It is instructed to output only the modified sections inline — not rewrite the whole prompt — so tone, style, whitespace, and unchanged sections are preserved exactly.

### 4. Version Switching
`GET /api/prompts/{id}/versions` returns all versions. The frontend version pills call `GET /api/prompts/{id}/components?version_id=X` to load components for a specific historical version. Components are stored per `(prompt_id, version_id)` pair.

### 5. LLM Config Storage
The frontend stores `{provider, api_key, model}` in `localStorage`. Every API call that needs LLM passes these in the POST body. The server never persists API keys — they flow through per-request.

### 6. No ORM
The storage layer is plain `sqlite3` with hand-written SQL. No SQLAlchemy, no migrations framework. Keep it simple.

### 7. CLI Alias
Both `promptview` and `pv` are registered as entry points in `pyproject.toml`. Use `pv` in all docs and examples.

---

## How to Reproduce This Project from Scratch

Run these steps in order with Claude Code. Each step maps to a module.

```bash
# 0. Bootstrap
mkdir promptview && cd promptview
uv init --no-workspace
uv add typer rich fastapi "uvicorn[standard]" pydantic tomli-w httpx python-dotenv openai anthropic google-generativeai
uv add --optional langfuse langfuse
uv add --optional langsmith langsmith
uv add --dev pytest pytest-anyio
mkdir -p src/promptview/{cli/commands,scanner/patterns,llm,storage,server/{routes,static},integrations}
touch src/promptview/__init__.py src/promptview/exceptions.py
```

Then build in this order (each depends on the previous):

1. **`storage/models.py`** — dataclasses and enums, no deps
2. **`storage/db.py`** — SQLite CRUD against models; `check_same_thread=False`; 5 tables; schema runs on every `connect()`
3. **`storage/diff_engine.py`** — unified diff between two `PromptVersion` objects
4. **`storage/repository.py`** — facade over db.py; init/open/close, staging, commit, diff, status
5. **`scanner/result.py`** — `ScannedPrompt` dataclass
6. **`scanner/resolver.py`** — AST string resolver
7. **`scanner/patterns/__init__.py`** — SDK-specific call patterns
8. **`scanner/ast_visitor.py`** — AST visitor using patterns; returns `ScannedPrompt` list
9. **`scanner/base.py`** — directory walker calling ast_visitor per file
10. **`llm/client.py`** — uniform `complete(system, user)` over openai/anthropic/gemini
11. **`llm/decomposer.py`** — decompose prompt → components; regenerate with surgical strategy
12. **`integrations/base.py`** — abstract remote interface
13. **`integrations/langfuse.py`** and **`langsmith.py`** — concrete implementations
14. **`cli/output.py`** — Rich formatting utilities
15. **`cli/commands/*.py`** — one Typer command per file (init, scan, add, commit, status, diff, log, config, push, ui)
16. **`cli/main.py`** — Typer app that imports and registers all commands
17. **`server/schemas.py`** — Pydantic request/response models
18. **`server/routes/prompts.py`** — CRUD + scan + commit routes
19. **`server/routes/components.py`** — decompose + add/delete/update + regenerate routes
20. **`server/routes/diff.py`** and **`graph.py`** — diff and graph routes
21. **`server/app.py`** — FastAPI factory mounting all routers
22. **`server/static/index.html`** — full SPA: D3 node graph, sidebar, version switcher, edit panel, LLM config modal
23. **`examples/prompts_demo.py`** — a few realistic prompts to test scanner detection
24. **`assets/logo.svg`** — SVG logo
25. **`.gitignore`** — standard Python ignores + `.promptview/`
26. **`README.md`** — full docs (see existing file for structure)
27. **`CLAUDE.md`** — this file

---

## Running Locally

```bash
# Install
uv sync

# Initialize on a project
pv init

# Scan, stage, commit
pv scan
pv add .
pv commit -m "initial"

# Launch UI (default port 8765)
pv ui
```

To test the LLM decomposition, open the UI, click a prompt, click "Decompose", and enter an API key when prompted. The component graph will render and nodes become editable.
