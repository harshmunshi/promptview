<p align="center">
  <img src="assets/logo.svg" alt="PromptView" width="420"/>
</p>

<p align="center">
  <a href="https://pypi.org/project/promptview/">
    <img src="https://img.shields.io/pypi/v/promptview?color=6366f1&label=pypi&logo=pypi&logoColor=white" alt="PyPI version"/>
  </a>
  <a href="https://pypi.org/project/promptview/">
    <img src="https://img.shields.io/pypi/dm/promptview?color=8b5cf6&logo=pypi&logoColor=white&label=downloads" alt="PyPI downloads"/>
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-3b82f6?logo=python&logoColor=white" alt="Python 3.10+"/>
  </a>
  <a href="https://pypi.org/project/promptview/">
    <img src="https://img.shields.io/pypi/pyversions/promptview?color=3b82f6&logo=python&logoColor=white" alt="Python versions"/>
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-22c55e?logo=opensourceinitiative&logoColor=white" alt="MIT License"/>
  </a>
  <img src="https://img.shields.io/badge/built%20with-uv-ec4899?logo=astral&logoColor=white" alt="Built with uv"/>
</p>

<p align="center">
  <b>Git-like versioning and visual management for LLM prompts.</b><br/>
  The DVC of prompt engineering.
</p>

Prompts in AI applications grow large and hard to manage. PromptView scans your codebase, versions every prompt like git commits, and gives you a visual editor where each prompt is broken into its structural components — which you can add, remove, or edit, with changes reflected back into the original prompt automatically via LLM.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Web UI](#web-ui)
- [LLM Integration](#llm-integration)
- [Template Variables](#template-variables)
- [Evaluations](#evaluations)
- [Team Sharing (Remote Backends)](#team-sharing-remote-backends)
- [External Integrations](#external-integrations)
- [CI/CD Integration](#cicd-integration)
- [How It Works](#how-it-works)
- [Development Setup](#development-setup)
- [pip-installable Package](#pip-installable-package)

---

## Features

- **Auto-discovery** — AST-based scanner finds prompts across OpenAI, Anthropic, LangChain, LiteLLM, and raw string patterns — zero config
- **Git-like workflow** — `pv scan → pv add → pv commit → pv log → pv diff`
- **Component graph** — every prompt is decomposed into labeled nodes (Role, Context, Instructions, Format, Examples…); edit nodes and the prompt updates surgically, preserving your original style
- **Version history** — toggle between any past version of a prompt in the UI
- **Template variables** — `{slot}` detection, default management, and `pv run` for parameterised rendering
- **Prompt composition** — embed one prompt inside another with `{{ include: prompt_name }}`
- **Provider-agnostic LLM** — OpenAI, Anthropic, Gemini, or **Ollama** (local, free, no API key)
- **Eval framework** — run test suites against prompt versions; score with `exact_match`, `contains`, or LLM-as-judge
- **Team sharing** — push/pull the prompt DB to S3, GCS, or any HTTP endpoint
- **Two-way sync** — push to and pull from Langfuse and LangSmith
- **Git hooks + GitHub Actions** — block commits with untracked prompts; auto-generate CI workflow

---

## Installation

### From PyPI (recommended)

```bash
pip install promptview

# or with UV (faster)
uv add promptview
```

### With optional extras

```bash
pip install "promptview[langfuse]"     # Langfuse integration
pip install "promptview[langsmith]"    # LangSmith integration
pip install "promptview[s3]"           # S3 remote backend (adds boto3)
pip install "promptview[gcs]"          # GCS remote backend (adds google-cloud-storage)
pip install "promptview[all]"          # langfuse + langsmith
```

### Requirements

- Python 3.10+
- An API key for OpenAI, Anthropic, or Google **or** a locally running [Ollama](https://ollama.com) instance — only needed for the component editor (decompose / regenerate). Everything else works without any LLM.

---

## Quick Start

```bash
cd my-ai-project

# 1. Initialize a local prompt repository
pv init

# 2. Scan the codebase for prompts
pv scan

# 3. Stage everything found
pv add .

# 4. Commit the snapshot
pv commit -m "Initial prompt capture"

# 5. Open the visual editor
pv ui
```

`pv ui` opens `http://localhost:8765`. Click any prompt to decompose it into nodes, then edit, add, or delete nodes — the original prompt updates automatically.

> **Note:** `pv` and `promptview` are identical aliases. Use whichever you prefer.

---

## CLI Reference

### Core git-like commands

| Command | Description |
|---|---|
| `pv init [PATH]` | Initialise `.promptview/` repo; `--author`, `--force`, `--no-scan` |
| `pv scan [PATH]` | AST-scan for prompts; `--min-confidence`, `--show-all` |
| `pv add [NAME\|.]` | Stage prompts; `--file src/agent.py` stages one file |
| `pv commit -m "MSG"` | Commit all staged prompts |
| `pv status` | Show staged / modified / untracked (like `git status`) |
| `pv diff [NAME] [V1] [V2]` | Unified diff between versions; `--staged` |
| `pv log [NAME]` | Commit history; `--oneline`, `-n 10` |

### UI

```bash
pv ui                      # http://localhost:8765 (default)
pv ui --port 9000
pv ui --host 0.0.0.0       # bind to all interfaces
pv ui --no-browser
```

### Config

```bash
pv config                          # show all settings
pv config author "Alice"
pv config llm.provider openai
pv config llm.api_key sk-...
```

### Branching

```bash
pv branch create feature/new-tone
pv branch list
pv branch delete feature/new-tone
```

### Remote backends

```bash
pv remote add origin s3://my-bucket/my-project/
pv remote add staging gcs://staging-bucket/prompts/
pv remote list
pv remote remove staging

pv push-remote origin                  # upload .promptview.db
pv pull-remote origin                  # download (backs up local first)
pv push-remote s3://bucket/path/       # direct URL also works
```

### External integrations (Langfuse / LangSmith)

```bash
pv push langfuse
pv push langsmith
pv pull langfuse
pv pull langsmith
pv sync langfuse                       # push + pull in one step
pv sync langsmith
```

### Template variables

```bash
pv vars sync my_prompt                 # auto-detect {slots} from latest version
pv vars show my_prompt                 # list with defaults
pv vars set my_prompt lang Python      # set default value
pv vars set my_prompt lang Python --desc "Target language"
```

### Render and run

```bash
pv run my_prompt                       # render using stored defaults
pv run my_prompt --var user=Alice      # override inline
pv run my_prompt -v user=Alice -v lang=Python --call    # render + call LLM
pv run my_prompt --call --provider anthropic --api-key $KEY
```

### Evaluations

```bash
pv eval run my_prompt --dataset evals/cases.jsonl --provider openai
pv eval run my_prompt --dataset evals/cases.jsonl --scorer llm_judge
pv metrics show my_prompt
pv metrics show my_prompt --version 3
```

### CI/CD hooks

```bash
pv hooks install        # add .git/hooks/pre-commit (blocks untracked prompts)
pv hooks status
pv hooks uninstall

pv cicd generate --output .github/workflows/promptview.yml
```

### Misc

```bash
pv version              # installed version
```

---

## Web UI

Open with `pv ui`. The interface has two main areas:

### Left sidebar — Prompt list

All prompts discovered in the project are listed with their source file, version count, and last-committed date. A search bar filters by name.

### Right area — Component graph

The selected prompt is decomposed into its structural components as a **linear node graph**:

```
[Role] → [Context] → [Instructions] → [Output Format] → [Examples]
```

- **Click a node** — expand and edit its full text inline
- **Press `+`** between nodes — insert a new component; LLM suggests appropriate content
- **Press `×`** — delete a node; LLM regenerates the prompt around the deletion
- **Version pills** — switch between any committed version; the graph updates instantly
- **Variables panel** — shows all `{slot}` names with editable defaults; "Sync Variables" detects them automatically
- **Metrics tab** — eval score history per version
- **Footer** — collapsible full reconstructed prompt text

### LLM settings

Gear icon → Settings modal:

| Provider | Default Model | API Key | Notes |
|---|---|---|---|
| OpenAI | `gpt-4o-mini` | Yes | Cloud |
| Anthropic | `claude-haiku-4-5` | Yes | Cloud |
| Google Gemini | `gemini-2.0-flash` | Yes | Cloud |
| **Ollama** | `llama3` | **No** | Local — free, private, offline |

Settings are stored in `localStorage` and never sent to any server.

---

## LLM Integration

PromptView uses LLMs for two operations:

1. **Decompose** — break a raw prompt string into labeled structural components
2. **Regenerate** — after a node edit/add/delete, rewrite only the changed portion back into the original prompt, keeping everything else identical

### Cloud providers

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."

# Or persist per-project
pv config llm.provider anthropic
pv config llm.api_key sk-ant-...
```

### Ollama — local, free, no API key

```bash
# Install
curl -fsSL https://ollama.com/install.sh | sh

# Pull any model
ollama pull llama3       # Meta Llama 3
ollama pull mistral      # Mistral 7B
ollama pull gemma3       # Google Gemma 3
ollama pull phi3         # Microsoft Phi-3 mini
ollama pull codellama    # Code-focused Llama

# Ollama serves on http://localhost:11434 automatically
# In pv ui → gear icon → select "Ollama (local)" → Save
# For CLI: --provider ollama (no --api-key needed)
```

All inference stays on your machine. No data leaves.

---

## Template Variables

PromptView automatically detects `{variable}` slots and lets you manage defaults, making prompts reusable across environments and use cases.

### Detect and manage

```bash
pv vars sync my_prompt                              # scan and register all {slots}
pv vars show my_prompt                              # list with defaults
pv vars set my_prompt language Python               # set a default
pv vars set my_prompt language Python --desc "Target programming language"
```

### Render

```bash
pv run my_prompt                                    # uses stored defaults
pv run my_prompt --var language=TypeScript          # override
pv run my_prompt -v user=Alice -v language=Go       # multiple overrides
pv run my_prompt --var user=Alice --call            # render + send to LLM
```

### Prompt composition

Embed one prompt inside another:

```
You are a helpful assistant.

{{ include: base_instructions }}

Now help {user_name} with: {task}
```

`{{ include: prompt_name }}` is resolved at render time by `pv run` and the variables API. Nested includes are supported.

### Variables API

```
GET    /api/prompts/{id}/variables          List variables + defaults
POST   /api/prompts/{id}/variables/sync     Auto-detect from latest version
PUT    /api/prompts/{id}/variables/{vid}    Update default value / description
```

---

## Evaluations

Run structured test suites against any prompt version and track quality scores over time.

### Dataset format (JSONL)

```jsonl
{"input": "Translate 'hello' to French", "expected_output": "Bonjour"}
{"input": "Translate 'goodbye' to French", "expected_output": "Au revoir"}
```

### Run an eval

```bash
pv eval run my_prompt --dataset evals/cases.jsonl --provider openai
pv eval run my_prompt --dataset evals/cases.jsonl --scorer llm_judge
pv eval run my_prompt --dataset evals/cases.jsonl --scorer contains
```

### View metrics

```bash
pv metrics show my_prompt           # all versions
pv metrics show my_prompt --version 3
```

Scores are also visible in the web UI Metrics tab per version.

### Scorers

| Scorer | Description |
|---|---|
| `exact_match` | Output must exactly equal expected (after strip) |
| `contains` | Output must contain the expected string |
| `llm_judge` | LLM grades response quality 0–1 against expected |

---

## Team Sharing (Remote Backends)

Share the `.promptview/` database across machines, team members, and CI using a remote backend. Think of it as `git push/pull` but for your prompt DB.

### Setup

```bash
# Register a named remote
pv remote add origin s3://my-bucket/my-project/
pv remote add origin gcs://my-bucket/my-project/
pv remote add origin https://my-server.com/promptview/

pv remote list

# Push / pull
pv push-remote origin
pv pull-remote origin          # backs up local DB before overwriting
```

### Backends

| Backend | URL Scheme | Extra Install |
|---|---|---|
| Amazon S3 | `s3://bucket/path` | `pip install "promptview[s3]"` |
| Google Cloud Storage | `gcs://bucket/path` | `pip install "promptview[gcs]"` |
| HTTP/HTTPS | `https://host/path` | None (uses built-in `httpx`) |

### CI example

```yaml
- name: Restore prompt DB
  run: |
    pip install "promptview[s3]"
    pv pull-remote origin
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

- name: Scan for untracked prompts
  run: pv scan --fail-on-untracked
```

---

## External Integrations

### Langfuse

```bash
pip install "promptview[langfuse]"

pv config langfuse.public_key pk-lf-...
pv config langfuse.secret_key sk-lf-...
pv config langfuse.host https://cloud.langfuse.com   # optional

pv push langfuse          # push all committed versions
pv pull langfuse          # pull remote versions into local DB
pv sync langfuse          # push + pull in one command
```

### LangSmith

```bash
pip install "promptview[langsmith]"

pv config langsmith.api_key ls__...
pv config langsmith.project my-project

pv push langsmith
pv pull langsmith
pv sync langsmith
```

---

## CI/CD Integration

### Git pre-commit hook

Automatically block commits when prompts in the codebase are untracked:

```bash
pv hooks install      # installs .git/hooks/pre-commit
pv hooks status
pv hooks uninstall
```

### GitHub Actions

Generate a ready-to-use workflow:

```bash
pv cicd generate --output .github/workflows/promptview.yml
```

The generated workflow:
1. Pulls the prompt DB from the configured remote backend
2. Scans for untracked prompts (`--fail-on-untracked`)
3. Optionally runs eval regression checks (uncomment the eval step + add your API key as a secret)

---

## How It Works

```
your codebase
     │
     ▼
 pv scan         ← AST visitor walks .py files; detects prompt strings
     │               across OpenAI / Anthropic / LangChain / raw patterns
     ▼
 pv add          ← stages detected prompts into .promptview/index.json
     │
     ▼
 pv commit       ← hashes content, stores in .promptview/promptview.db
     │               creates a commit record with full version lineage
     ▼
 pv ui           ← FastAPI server + D3.js browser UI
                    • LLM decomposes prompt into component nodes
                    • edits applied surgically — only changed parts rewritten
                    • all changes create new committed versions
                    • variables panel shows {slot} defaults
                    • metrics tab shows eval scores per version
```

**Local-first.** Everything lives in `.promptview/` inside your project. Nothing is sent anywhere unless you explicitly run `pv push` or `pv push-remote`.

### `.promptview/` layout

```
.promptview/
├── promptview.db    # SQLite — prompts, versions, commits, components, variables, evals
├── config.toml      # author, LLM provider, remote URLs
├── HEAD             # current branch
├── index.json       # staging area
├── objects/         # content-addressed object store
├── refs/            # branch and tag references
└── logs/            # commit log files
```

---

## Development Setup

```bash
git clone https://github.com/harshmunshi/promptview.git
cd promptview

# Install UV if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies
uv sync

# Run CLI directly
uv run pv --help

# Run tests
uv run pytest
```

### Project layout

```
src/promptview/
├── cli/
│   ├── main.py              # Typer app — all commands registered
│   ├── output.py            # Rich formatting helpers
│   └── commands/            # 22 command files — one per command
│       ├── init.py, scan.py, add.py, commit.py, status.py
│       ├── diff.py, log.py, ui.py, config.py
│       ├── push.py, pull.py, sync.py, branch.py
│       ├── eval.py, metrics.py, hooks.py, cicd.py
│       ├── remote.py, pull_backend.py
│       └── vars.py, run.py
├── scanner/                 # AST-based prompt detector
│   ├── base.py, ast_visitor.py, resolver.py, result.py
│   └── patterns/__init__.py
├── llm/
│   ├── client.py            # openai / anthropic / gemini / ollama
│   └── decomposer.py        # decompose + surgical regenerate
├── eval/
│   ├── dataset.py           # JSONL test case loader
│   ├── runner.py            # LLM-driven eval execution
│   └── scorer.py            # exact_match, contains, llm_judge
├── storage/
│   ├── models.py            # all dataclasses + enums
│   ├── db.py                # SQLite, check_same_thread=False, 6 tables
│   ├── repository.py        # PromptRepository facade
│   └── diff_engine.py
├── remotes/
│   ├── base.py              # RemoteBackend ABC + from_url() factory
│   ├── s3.py, gcs.py, http.py
├── server/
│   ├── app.py               # FastAPI factory
│   ├── schemas.py           # Pydantic models
│   ├── static/index.html    # D3 SPA — graph + variables + metrics
│   └── routes/
│       ├── prompts.py       # CRUD + scan + commit + variables
│       ├── components.py    # decompose + add/delete/edit + regenerate
│       ├── diff.py, graph.py
│       ├── branches.py      # branch CRUD + checkout
│       └── evals.py         # eval run + metrics history
├── integrations/
│   ├── base.py, langfuse.py, langsmith.py
├── template.py              # {variable} + {{ include }} engine
└── exceptions.py
```

---

## pip-installable Package

PromptView is packaged with [Hatchling](https://hatch.pypa.io) and ready to publish to PyPI.

### Build

```bash
uv add --dev build twine
uv run python -m build
# Produces:
#   dist/promptview-0.1.0-py3-none-any.whl
#   dist/promptview-0.1.0.tar.gz
```

### Publish

```bash
# Test PyPI first (recommended)
uv run twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ promptview

# Real PyPI
uv run twine upload dist/*
```

Set credentials via `~/.pypirc` or environment variables:

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-AgEIcHlwaS5vcmcA...
```

### Local install without publishing

```bash
pip install dist/promptview-0.1.0-py3-none-any.whl

# Editable (for development)
pip install -e .
uv pip install -e .
```

### Bump version

Edit `pyproject.toml`:
```toml
[project]
version = "0.2.0"
```
Then rebuild and upload.

---

## License

MIT
