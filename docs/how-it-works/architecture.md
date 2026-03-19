# Architecture

PromptView is built as a local-first tool with a clean layered architecture. All data lives in your project directory. Nothing is sent to any remote unless you explicitly run `pv push` or `pv push-remote`.

---

## Layered Architecture

```
┌─────────────────────────────────────────────┐
│                CLI (pv)                      │
│   22 Typer commands · Rich output · stdin   │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│           FastAPI Server (pv ui)             │
│   REST API · Static SPA · D3.js frontend    │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│          PromptRepository (facade)           │
│   Staging · Versioning · Commit · Diff      │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│           Storage (SQLite)                   │
│   6 tables · No ORM · check_same_thread=F   │
└──────────────────────┬──────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌─────────▼───────┐
│ Scanner (AST)  │          │   LLM Client    │
│ OpenAI pattern │          │ openai/anthropic│
│ Anthropic etc. │          │ gemini/ollama   │
└────────────────┘          └─────────────────┘
```

Each layer has a single responsibility and communicates downward only. The CLI and FastAPI server both use `PromptRepository` — they share the same storage layer, so changes made via the UI are immediately visible in CLI commands.

---

## Local-First Philosophy

PromptView stores everything in `.promptview/` inside your project directory:

```
.promptview/
├── promptview.db    # SQLite — the single source of truth
├── config.toml      # author, LLM provider config, named remotes
├── HEAD             # current branch name
├── index.json       # staging area (what will go into the next commit)
├── objects/         # content-addressed blob store
├── refs/            # branch and tag references
└── logs/            # per-prompt commit log files
```

The `promptview.db` file contains all prompts, versions, commits, components, variables, eval runs, and eval results. It is a self-contained SQLite database. You can inspect it directly with any SQLite browser.

**Nothing leaves your machine** until you run one of:
- `pv push-remote <name>` — upload DB to S3/GCS/HTTP
- `pv push langfuse/langsmith` — push prompt versions to external platforms

---

## Data Flow: From Source Code to Visual Editor

```
1. pv scan
   └── Scanner walks .py files recursively
   └── AST visitor finds prompt strings per SDK pattern
   └── Resolver follows variable references to string content
   └── Confidence score assigned to each candidate

2. pv add .
   └── Staged prompts written to .promptview/index.json
   └── Status: untracked → staged

3. pv commit -m "message"
   └── For each staged prompt:
       └── Content is hashed (SHA256)
       └── If hash changed or new: PromptVersion created
       └── PromptComponent rows cleared for new version
   └── Commit record created (8-char hash, message, author, version_ids)
   └── index.json cleared

4. pv ui
   └── FastAPI starts on localhost:8765
   └── GET /api/prompts → sidebar list
   └── Click prompt → POST /api/prompts/{id}/decompose
       └── LLMClient.complete() sends decomposition prompt
       └── Components parsed and stored in DB
       └── D3 renders node graph

5. Edit a node → Save
   └── PUT /api/prompts/{id}/components
   └── LLMClient regenerates full prompt (surgical rewrite)
   └── New PromptVersion created
   └── New Components stored for that version
```

---

## The 5 Layers in Detail

### 1. CLI Layer

The CLI is built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/). All 22 commands live in `src/promptview/cli/commands/` — one file per command. The main entry point in `cli/main.py` registers all commands and sub-apps.

Both `pv` and `promptview` are registered as entry points in `pyproject.toml`. They are identical aliases.

### 2. FastAPI Server Layer

The web server (`src/promptview/server/`) is a FastAPI application with:
- 6 router modules, each mounted at `/api/<resource>`
- A static mount serving the single-file `index.html` SPA
- A health endpoint at `/health`
- The root `/` serves the frontend

The server reuses the same `PromptRepository` instance as the CLI — there is no separate "server database".

### 3. Repository Layer

`PromptRepository` (`src/promptview/storage/repository.py`) is the facade that all higher-level code uses. It hides raw SQL behind a clean Python API:

```python
repo = PromptRepository("/path/to/project")
repo.open()

# All higher-level operations
repo.list_prompts()
repo.stage(scanned_prompt)
repo.commit("Initial capture", author="Alice")
repo.diff(version_id_1, version_id_2)
repo.status()

repo.close()
```

### 4. Storage Layer

The storage layer (`src/promptview/storage/db.py`) is plain `sqlite3` with hand-written SQL. No ORM, no migration framework. The full schema is run as `CREATE TABLE IF NOT EXISTS` on every `connect()` — adding a new table means adding it to that block and reconnecting.

The database opens with `check_same_thread=False` because FastAPI's route handlers run in a thread pool while the connection is created in the main thread.

### 5. Scanner and LLM Layers

These are independent utility layers:

- **Scanner** (`src/promptview/scanner/`) — pure Python, no network. Takes a directory path and returns `ScannedPrompt` objects.
- **LLM Client** (`src/promptview/llm/`) — network only. Wraps OpenAI, Anthropic, Gemini, and Ollama behind a uniform `complete(system, user) → str` interface.

---

## Schema Overview

```sql
prompts          -- identity records (name, source, file_path, ...)
prompt_versions  -- immutable content snapshots (raw_content, hash, ...)
commits          -- grouped changes (id=8char_hash, message, author, ...)
prompt_components-- structural nodes per (prompt_id, version_id)
prompt_variables -- {slot} defaults per prompt_id
remotes          -- named remote backends (name, provider, endpoint)
eval_runs        -- scored test suite results
eval_results     -- per-case actual outputs and scores
test_cases       -- JSONL test case records
```

---

## Remote Backends

For team sharing, PromptView can push and pull the entire `promptview.db` file to and from:
- **S3** (`s3://bucket/path/`) — via `boto3`
- **GCS** (`gcs://bucket/path/`) — via `google-cloud-storage`
- **HTTP/HTTPS** (`https://host/path/`) — via `httpx`, no extra dependency

The `RemoteBackend.from_url()` factory dispatches on URL scheme. Named remotes are stored in `config.toml` and referenced by name.

---

## Next Steps

- [Prompt Scanner](scanner.md) — how AST-based detection works
- [Versioning Model](versioning.md) — git analogy and data model details
- [Component Graph](component-graph.md) — how decompose and regenerate work
