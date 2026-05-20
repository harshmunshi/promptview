# PromptView — Claude Code Build Spec

This file is the single source of truth for reproducing the entire PromptView project from scratch using Claude Code. Follow it top to bottom in a single session.

---

## What PromptView Is

A pip-installable Python library that brings git-like versioning to LLM prompts. It scans any codebase, finds all prompts, versions them, and exposes a web UI where each prompt is broken into structural components (Role, Context, Instructions, Format, Examples…) displayed as a linear node graph. Nodes can be added, deleted, or edited and the prompt is regenerated surgically via LLM — preserving the original style and structure. Built to be the default go-to for prompt management the way DVC is for data.

---

## What Is Already Built (Do Not Rebuild)

Every item below is implemented, tested, and pushed to `feat/dvc-parity`.

---

### Package & Tooling
- `pyproject.toml` — hatchling build, UV package manager, entry points `promptview` and `pv`
- `.gitignore` — covers Python, UV, venv, OS, IDE, `.promptview/`
- `README.md` — full docs with SVG logo, shields.io badges, pip install, CLI reference, build/publish guide
- `assets/logo.svg` — dark-theme SVG logo
- `uv.lock` — locked dependency graph

### Core Dependencies (all in `pyproject.toml`)
```
typer[all], rich, fastapi, uvicorn[standard], pydantic, tomli-w,
httpx, python-dotenv, openai>=1.0, anthropic>=0.20, google-generativeai>=0.5
```
Optional extras:
- `promptview[langfuse]` — `langfuse>=2.0`
- `promptview[langsmith]` — `langsmith>=0.1`
- `promptview[s3]` — `boto3>=1.28`
- `promptview[gcs]` — `google-cloud-storage>=2.10`

---

### Storage Layer (`src/promptview/storage/`)

**`models.py`** — all dataclasses and enums:
- `PromptSource` enum: OPENAI, ANTHROPIC, LANGCHAIN, LITELLM, RAW, MANUAL
- `PromptRole` enum: SYSTEM, USER, ASSISTANT, FULL
- `PromptBlock(role, content)`
- `Prompt` — unique identity record per prompt
- `PromptVersion` — immutable snapshot; fields: id, prompt_id, version_number, raw_content, blocks JSON, content_hash, commit_id, parent_version_id
- `Commit` — id as 8-char SHA256 hash, message, author, timestamp, version_ids JSON
- `PromptComponent` — id, prompt_id, version_id, label, content, position
- `PromptVariable` — id, prompt_id, name, default_value, description, created_at; `.new()` factory

**`db.py`** — plain `sqlite3`, `check_same_thread=False`, 6 tables:
| Table | Key columns |
|---|---|
| `prompts` | id, name, description, source, file_path, line_number, variable_name, tags, timestamps |
| `prompt_versions` | id, prompt_id, version_number, raw_content, blocks, content_hash, commit_id, parent_version_id |
| `commits` | id (8-char hash), message, author, timestamp, version_ids |
| `remotes` | name PK, provider, endpoint, project |
| `prompt_components` | id, prompt_id, version_id, label, content, position |
| `prompt_variables` | id, prompt_id, name, default_value, description — UNIQUE(prompt_id, name) |

Schema runs `CREATE TABLE IF NOT EXISTS` on every `connect()` — no migration scripts ever needed.

Methods on `Database`: full CRUD for all 6 tables including `upsert_variable`, `list_variables`, `get_variable_by_name`, `delete_variable`.

**`repository.py`** — `PromptRepository` facade over db.py:
- Lifecycle: `initialize()`, `open()`, `close()`, `is_initialized()`
- Prompt CRUD: `create_prompt()`, `update_prompt_content()`, `delete_prompt()`, `list_prompts()`
- Staging: `stage()`, `unstage()`, `get_staged()`, `clear_index()`
- Versioning: `commit()`, `list_commits()`, `list_commits_for_prompt()`
- Diff: `diff()` between any two versions
- Status: `status()` — staged / modified / untracked

**`diff_engine.py`** — unified diff between two `PromptVersion` objects

---

### Scanner (`src/promptview/scanner/`)
- **`base.py`** — recursive directory walker; skips `.venv`, `node_modules`, `__pycache__`, `.git`, `.promptview`, `dist`, `build`
- **`ast_visitor.py`** — AST visitor; detects OpenAI, Anthropic, LangChain, LiteLLM call patterns; confidence scoring
- **`resolver.py`** — resolves Python variable names → string content from AST symbol table
- **`result.py`** — `ScannedPrompt` dataclass
- **`patterns/__init__.py`** — SDK-specific pattern definitions

---

### Template Engine (`src/promptview/template.py`)
- `extract_variables(text)` — finds all `{slot}` names; ignores `{{ include: ... }}`
- `extract_includes(text)` — finds all `{{ include: prompt_name }}` directives
- `render(text, variables)` — substitutes `{slot}` values; leaves unknowns intact
- `resolve_includes(text, lookup)` — embeds referenced prompt content inline
- `render_full(text, variables, lookup)` — resolve includes then render variables in one pass

---

### LLM Client (`src/promptview/llm/`)
**`client.py`** — `LLMClient(provider, api_key, model)` with uniform `complete(system, user) → str`:
| Provider | Default model | API key | Notes |
|---|---|---|---|
| `openai` | `gpt-4o-mini` | Yes | Cloud |
| `anthropic` | `claude-haiku-4-5` | Yes | Cloud |
| `gemini` | `gemini-2.0-flash` | Yes | Cloud |
| `ollama` | `llama3` | No | Local; uses `httpx` → `localhost:11434`; friendly error if not running |

No `ImportError` guards — all three cloud SDKs are always installed as core deps.

**`decomposer.py`** — two operations:
1. `decompose(prompt_text)` → list of `{label, content}` dicts
2. `regenerate(original, old_components, new_components)` → surgically updated prompt; only changed sections rewritten; tone/style/whitespace preserved

---

### Evaluation Framework (`src/promptview/eval/`)
- **`dataset.py`** — `EvalDataset`: load/save JSONL test cases with input / expected_output fields
- **`runner.py`** — `EvalRunner`: run a prompt version against a dataset using a real LLM; records actual outputs and latency per test case
- **`scorer.py`** — `EvalScorer`: built-in scorers — `exact_match`, `contains`, `llm_judge` (LLM grades response quality 0–1); extensible with custom scorer functions

---

### Remote Backends (`src/promptview/remotes/`)
Push/pull the entire `.promptview/promptview.db` to shared storage so teams and CI runners share one source of truth:
- **`base.py`** — `RemoteBackend` ABC: `push(db_path)`, `pull(db_path)`, `exists()`, `from_url(url)` factory
- **`s3.py`** — `S3Backend`: lazy `boto3`; parses `s3://bucket/prefix` → key `prefix/promptview.db`
- **`gcs.py`** — `GCSBackend`: lazy `google-cloud-storage`; same URL pattern
- **`http.py`** — `HTTPBackend`: `httpx` PUT/GET/HEAD against `{base_url}/promptview.db`; no extra deps

---

### CLI (`src/promptview/cli/`)
Both `pv` and `promptview` are registered entry points. Always use `pv` in docs and examples.

**`main.py`** — Typer app; registers all commands and sub-apps.

**`commands/`** — one file per command:

| Command | File | Description |
|---|---|---|
| `pv init` | `init.py` | Create `.promptview/` repo; `--author`, `--force`, `--no-scan` |
| `pv scan` | `scan.py` | AST-walk codebase; `--min-confidence`, `--show-all` |
| `pv add` | `add.py` | Stage prompts; `--file`, `--min-confidence` |
| `pv commit` | `commit.py` | Commit staged; `-m "message"` |
| `pv status` | `status.py` | Show staged / modified / untracked |
| `pv diff` | `diff.py` | Unified diff between versions; `--staged` |
| `pv log` | `log.py` | Commit history; `--oneline`, `-n` |
| `pv ui` | `ui.py` | Launch web UI; `--port`, `--host`, `--no-browser` |
| `pv config` | `config.py` | Read/write config; `--show` |
| `pv push` | `push.py` | Push to langfuse / langsmith / remote backend |
| `pv pull` | `pull.py` | Pull from langfuse / langsmith |
| `pv sync` | `sync.py` | Push + pull in one command |
| `pv branch` | `branch.py` | Create / list / delete prompt branches |
| `pv eval` | `eval.py` | Run eval suite against a prompt version |
| `pv metrics` | `metrics.py` | Show eval metrics history (Rich table) |
| `pv hooks` | `hooks.py` | Install / uninstall / status git pre-commit hooks |
| `pv cicd` | `cicd.py` | Generate GitHub Actions workflow YAML |
| `pv remote add/list/remove` | `remote.py` | Manage named remote backends stored in config.toml |
| `pv push-remote` | `push.py` | Push DB to remote backend (S3/GCS/HTTP) |
| `pv pull-remote` | `pull_backend.py` | Pull DB from remote backend; backs up local first |
| `pv vars sync/show/set` | `vars.py` | Manage `{variable}` slot defaults per prompt |
| `pv run` | `run.py` | Render prompt with variable substitution; `--call` to invoke LLM |

---

### FastAPI Server (`src/promptview/server/`)

**`app.py`** — factory; registers all routers under `/api`; mounts static; serves `index.html` at `/`; health at `/health`

**`schemas.py`** — Pydantic request/response models for all endpoints

**`routes/`**:

| Router | Key Endpoints |
|---|---|
| `prompts.py` | `GET/POST /api/prompts`, `GET/PATCH/DELETE /api/prompts/{id}`, `GET /api/prompts/{id}/versions`, `POST /api/scan`, `POST /api/commit`, `GET/POST/PUT /api/prompts/{id}/variables`, `POST /api/prompts/{id}/variables/sync` |
| `components.py` | `GET /api/prompts/{id}/components`, `POST /api/prompts/{id}/decompose`, `POST .../components/add`, `PUT .../components`, `DELETE .../components/{cid}` |
| `diff.py` | `GET /api/diff/{id}?v1=X&v2=Y` |
| `graph.py` | `GET /api/graph` |
| `branches.py` | `GET/POST /api/branches`, `DELETE /api/branches/{name}`, `POST /api/branches/{name}/checkout` |
| `evals.py` | `GET/POST /api/evals`, `GET /api/evals/{id}`, `GET /api/prompts/{id}/metrics` |

---

### Frontend (`src/promptview/server/static/index.html`)

Single-file vanilla JS + D3.js SPA. GitHub Dark theme (`#0d1117`, `#161b22`).

| Feature | Description |
|---|---|
| Sidebar | Searchable prompt list; source badge; version count; click to open |
| Component graph | D3 vertical linear node stack; arrows between nodes; click to edit; `+` to insert; `×` to delete |
| Version switcher | Pill buttons at top; switching reloads components for that version |
| Edit panel | Slides in from right; edit label + content inline; save triggers LLM regeneration |
| Variables panel | Table of `{slot}` names with editable defaults and descriptions; Sync Variables button; auto-syncs after decompose |
| Metrics tab | Eval score history per prompt version |
| Footer | Collapsible reconstructed full prompt text |
| Toolbar | Scan, Commit buttons; LLM config gear icon |
| LLM config modal | Provider dropdown (openai / anthropic / gemini / ollama); API key input; model override; stored in `localStorage` |
| Toast notifications | Success/error feedback for all async actions |

---

### Integrations (`src/promptview/integrations/`)
- **`base.py`** — abstract `RemoteIntegration`: `push_version()`, `pull_versions()`, `list_remote_prompts()`
- **`langfuse.py`** — Langfuse push + pull implementation
- **`langsmith.py`** — LangSmith push + pull implementation

---

### Examples & Assets
- **`examples/prompts_demo.py`** — realistic demo prompts covering OpenAI, Anthropic, raw string patterns
- **`assets/logo.svg`** — dark SVG logo (420×120)
- **`assets/github-actions/promptview.yml`** — CI workflow template generated by `pv cicd generate`

---

## What Is NOT Built Yet (Remaining Work)

### High Priority
- [ ] **Diff view in UI** — side-by-side version diff rendering in the web interface
- [ ] **Export** — export prompt version as `.txt`, `.json`, or clipboard copy from UI
- [ ] **Full-text search** — search across prompt content, not just names

### Medium Priority
- [ ] **Confidence score display** — show scanner confidence score in the sidebar
- [ ] **Pytest plugin** — `pv test` running prompt regression tests against expected outputs
- [ ] **`pv merge`** — merge two prompt branches with conflict resolution

### Low Priority / Polish
- [ ] **Dark/light theme toggle** in UI
- [ ] **Keyboard shortcuts** in component graph (j/k navigate, e edit, d delete)
- [ ] **Undo** for node deletions in UI
- [ ] **Publish to PyPI** — set up PyPI token, `python -m build && twine upload`
- [ ] **GitHub Actions release workflow** — auto-publish on tag push

---

## Directory Structure (Complete)

```
promptview/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── assets/
│   ├── logo.svg
│   └── github-actions/
│       └── promptview.yml
├── examples/
│   └── prompts_demo.py
└── src/promptview/
    ├── __init__.py
    ├── exceptions.py
    ├── template.py                     ← {variable} + {{ include }} engine
    ├── cli/
    │   ├── main.py
    │   ├── output.py
    │   └── commands/
    │       ├── init.py
    │       ├── scan.py
    │       ├── add.py
    │       ├── commit.py
    │       ├── status.py
    │       ├── diff.py
    │       ├── log.py
    │       ├── ui.py
    │       ├── config.py
    │       ├── push.py
    │       ├── pull.py
    │       ├── sync.py
    │       ├── branch.py
    │       ├── eval.py
    │       ├── metrics.py
    │       ├── hooks.py
    │       ├── cicd.py
    │       ├── remote.py
    │       ├── pull_backend.py
    │       ├── vars.py
    │       └── run.py
    ├── scanner/
    │   ├── base.py
    │   ├── ast_visitor.py
    │   ├── resolver.py
    │   ├── result.py
    │   └── patterns/__init__.py
    ├── llm/
    │   ├── client.py                   ← openai / anthropic / gemini / ollama
    │   └── decomposer.py               ← decompose + surgical regenerate
    ├── eval/
    │   ├── __init__.py
    │   ├── dataset.py                  ← JSONL test case loader
    │   ├── runner.py                   ← LLM-driven eval execution
    │   └── scorer.py                   ← exact_match, contains, llm_judge
    ├── storage/
    │   ├── models.py
    │   ├── db.py
    │   ├── repository.py
    │   └── diff_engine.py
    ├── remotes/
    │   ├── __init__.py
    │   ├── base.py                     ← RemoteBackend ABC + from_url() factory
    │   ├── s3.py                       ← boto3
    │   ├── gcs.py                      ← google-cloud-storage
    │   └── http.py                     ← httpx (no extra deps)
    ├── server/
    │   ├── app.py
    │   ├── schemas.py
    │   ├── static/
    │   │   └── index.html              ← D3 SPA: graph + variables + metrics
    │   └── routes/
    │       ├── prompts.py
    │       ├── components.py
    │       ├── diff.py
    │       ├── graph.py
    │       ├── branches.py
    │       └── evals.py
    └── integrations/
        ├── base.py
        ├── langfuse.py
        └── langsmith.py
```

---

## Critical Implementation Details

### 1. SQLite Thread Safety
`db.py` opens with `check_same_thread=False`. FastAPI runs route handlers in a thread pool; the connection is created in the main thread and reused across workers.

### 2. Schema Auto-Migration
`Database.connect()` always runs the full `CREATE TABLE IF NOT EXISTS` block. Adding a new table = add it there. No migration framework needed.

### 3. Prompt Regeneration Strategy
Surgical: the LLM receives the original text, the old component list, and the new component list. Only changed sections are rewritten — tone, whitespace, and unchanged text are preserved exactly.

### 4. Version Switching
`GET /api/prompts/{id}/versions` returns all versions. Frontend pills call `GET /api/prompts/{id}/components?version_id=X`. Components stored per `(prompt_id, version_id)` pair.

### 5. LLM Config — Frontend
`localStorage` stores `{provider, api_key, model}`. Passed in every POST body that needs LLM. Server never persists API keys.

### 6. LLM Config — CLI / `pv run`
Falls back through env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`. Ollama needs no key.

### 7. No ORM
Plain `sqlite3` with hand-written SQL throughout. No SQLAlchemy, no Alembic.

### 8. Remote Backend URL Dispatch
`RemoteBackend.from_url()` dispatches on scheme: `s3://` → S3Backend, `gcs://` → GCSBackend, `http(s)://` → HTTPBackend. Named remotes stored in `[remotes]` section of `.promptview/config.toml`.

### 9. Template Variable Sync
`pv vars sync <name>` (and `POST /api/prompts/{id}/variables/sync`) runs `extract_variables()` on the latest raw content and upserts any new `PromptVariable` rows. Existing defaults are never overwritten.

### 10. Ollama Integration
No extra dependency. Uses `httpx` (always installed) to POST to `http://localhost:11434/api/chat` with `stream: false`. Raises a user-friendly `RuntimeError` if the server isn't running.

### 11. CLI Alias
Both `promptview` and `pv` registered as entry points in `pyproject.toml`. Use `pv` everywhere.

---

## How to Reproduce This Project from Scratch

Bootstrap:
```bash
mkdir promptview && cd promptview
uv init --no-workspace
uv add typer rich fastapi "uvicorn[standard]" pydantic tomli-w httpx \
        python-dotenv openai anthropic google-generativeai
uv add --optional langfuse langfuse
uv add --optional langsmith langsmith
uv add --optional s3 boto3
uv add --optional gcs google-cloud-storage
uv add --dev pytest pytest-anyio
mkdir -p src/promptview/{cli/commands,scanner/patterns,llm,eval,storage,\
remotes,server/{routes,static},integrations}
touch src/promptview/__init__.py src/promptview/exceptions.py
```

Build in this exact order (each step depends on previous):

1. `storage/models.py` — all dataclasses + enums (no deps)
2. `storage/db.py` — SQLite layer; `check_same_thread=False`; 6 tables; full schema on every `connect()`
3. `storage/diff_engine.py` — unified diff between `PromptVersion` objects
4. `storage/repository.py` — facade; init/open/close, staging, commit, diff, status
5. `scanner/result.py` — `ScannedPrompt` dataclass
6. `scanner/resolver.py` — AST variable → string resolver
7. `scanner/patterns/__init__.py` — SDK call patterns
8. `scanner/ast_visitor.py` — AST visitor; returns `ScannedPrompt` list
9. `scanner/base.py` — directory walker calling ast_visitor per file
10. `template.py` — `extract_variables`, `extract_includes`, `render`, `resolve_includes`, `render_full`
11. `llm/client.py` — uniform `complete(system, user)` over openai / anthropic / gemini / ollama
12. `llm/decomposer.py` — decompose → components; surgical regenerate
13. `eval/dataset.py`, `eval/runner.py`, `eval/scorer.py` — eval framework
14. `remotes/base.py`, `remotes/s3.py`, `remotes/gcs.py`, `remotes/http.py` — remote backends
15. `integrations/base.py`, `langfuse.py`, `langsmith.py` — external platform adapters
16. `cli/output.py` — Rich formatting utilities
17. `cli/commands/*.py` — all 22 command files (see table above)
18. `cli/main.py` — registers all commands and sub-apps
19. `server/schemas.py` — Pydantic request/response models
20. `server/routes/prompts.py` — CRUD + scan + commit + variable endpoints
21. `server/routes/components.py` — decompose + add/delete/update + regenerate
22. `server/routes/branches.py` — branch CRUD + checkout
23. `server/routes/evals.py` — eval run + metrics history
24. `server/routes/diff.py` + `graph.py` — diff + graph endpoints
25. `server/app.py` — FastAPI factory; mount all routers
26. `server/static/index.html` — full SPA: D3 graph, sidebar, version switcher, variables panel, metrics tab, LLM config modal
27. `examples/prompts_demo.py` — realistic test prompts
28. `assets/logo.svg` — SVG logo
29. `assets/github-actions/promptview.yml` — CI workflow template
30. `.gitignore` — Python + `.promptview/` + `dist/`
31. `README.md` — full user docs
32. `CLAUDE.md` — this file

---

## Running Locally

```bash
uv sync

# Initialize and capture prompts
pv init
pv scan
pv add .
pv commit -m "initial capture"

# Open visual editor
pv ui                           # http://localhost:8765

# Template variables
pv vars sync my_prompt
pv vars show my_prompt
pv vars set my_prompt user Alice
pv run my_prompt --var user=Bob --call --provider openai

# Team sharing via S3
pv remote add origin s3://my-bucket/my-project/
pv push-remote origin
pv pull-remote origin           # on another machine or in CI

# Eval
pv eval run my_prompt --dataset evals/cases.jsonl --provider openai
pv metrics show my_prompt

# CI/CD hooks
pv hooks install
pv cicd generate --output .github/workflows/promptview.yml

# Two-way sync with Langfuse
pv pull langfuse
pv sync langfuse
```
