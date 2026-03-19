# Installation

PromptView is a standard Python package installable from PyPI. It requires Python 3.10 or later.

---

## Requirements

- **Python 3.10+** — PromptView uses `match` statements, union types (`X | Y`), and other modern Python features.
- **An LLM provider** — required only for the component decompose/regenerate feature. Everything else (scanning, versioning, diff, status) works without any LLM. Supported providers:
    - [OpenAI](https://platform.openai.com/) — API key required
    - [Anthropic](https://console.anthropic.com/) — API key required
    - [Google Gemini](https://aistudio.google.com/) — API key required
    - [Ollama](https://ollama.com/) — **free, local, no API key** — runs entirely on your machine

---

## From PyPI (Recommended)

=== "pip"

    ```bash
    pip install promptview
    ```

=== "uv (faster)"

    ```bash
    uv add promptview
    ```

=== "pipx (isolated)"

    ```bash
    pipx install promptview
    ```

After installation, both `pv` and `promptview` are registered as CLI entry points:

```bash
pv --help
promptview --help  # identical alias
```

---

## With Optional Extras

Some integrations require additional dependencies. Install them as extras:

| Extra | Install Command | What It Adds |
|---|---|---|
| `langfuse` | `pip install "promptview[langfuse]"` | Langfuse push/pull integration |
| `langsmith` | `pip install "promptview[langsmith]"` | LangSmith push/pull integration |
| `s3` | `pip install "promptview[s3]"` | S3 remote backend (adds `boto3`) |
| `gcs` | `pip install "promptview[gcs]"` | GCS remote backend (adds `google-cloud-storage`) |
| `all` | `pip install "promptview[all]"` | Langfuse + LangSmith |
| `docs` | `pip install "promptview[docs]"` | MkDocs for building this documentation |

Combining extras:

```bash
pip install "promptview[langfuse,langsmith,s3]"
```

---

## Install from Source

To get the latest development version:

```bash
git clone https://github.com/harshmunshi/promptview.git
cd promptview

# Install UV if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (including dev tools)
uv sync

# Run the CLI from source
uv run pv --help
```

For an editable install with pip:

```bash
git clone https://github.com/harshmunshi/promptview.git
cd promptview
pip install -e .
pv --help
```

---

## Verify the Installation

```bash
pv --version
```

Expected output:

```
promptview 0.1.0
```

Run a quick sanity check:

```bash
pv --help
```

You should see all available commands listed.

---

## Upgrading

=== "pip"

    ```bash
    pip install --upgrade promptview
    ```

=== "uv"

    ```bash
    uv add --upgrade promptview
    ```

---

## Core Dependencies

The following packages are installed automatically with PromptView (no extras needed):

| Package | Purpose |
|---|---|
| `typer[all]` | CLI framework with rich help output |
| `rich` | Terminal formatting, tables, progress bars |
| `fastapi` | Web server for the UI backend |
| `uvicorn[standard]` | ASGI server for FastAPI |
| `pydantic` | Request/response validation |
| `httpx` | HTTP client (used for Ollama and HTTP remote backend) |
| `python-dotenv` | Load `.env` files for API keys |
| `openai>=1.0` | OpenAI API client |
| `anthropic>=0.20` | Anthropic API client |
| `google-generativeai>=0.5` | Google Gemini API client |
| `tomli-w` | Write TOML config files |

All LLM SDK dependencies (`openai`, `anthropic`, `google-generativeai`) are core dependencies — no optional extra needed. Ollama uses `httpx` which is also a core dependency.

---

## Next Steps

- [Quick Start](quick-start.md) — run your first `pv init` and `pv scan`
- [Core Concepts](concepts.md) — understand what PromptView tracks and why
