# pv push / pull / sync — Integrations

Two-way sync with Langfuse and LangSmith prompt management platforms.

---

## Overview

PromptView can push prompt versions to Langfuse and LangSmith, and pull remote versions back into your local database. This enables:

- Using PromptView as the version control layer with Langfuse/LangSmith as the runtime serving layer
- Sharing prompts with team members who use Langfuse or LangSmith
- Pulling prompts created in those platforms back into PromptView for offline editing

---

## pv push

```bash
pv push langfuse
pv push langsmith
```

Pushes all committed prompt versions to the target platform.

---

## pv pull

```bash
pv pull langfuse
pv pull langsmith
```

Pulls prompt versions from the target platform into the local PromptView database. New prompts that don't exist locally are created; existing prompts get new versions if the content differs.

---

## pv sync

```bash
pv sync langfuse
pv sync langsmith
```

Runs `push` then `pull` in a single command — a full two-way sync.

---

## Langfuse Integration

### Installation

```bash
pip install "promptview[langfuse]"
```

### Configuration

```bash
pv config langfuse.public_key pk-lf-...
pv config langfuse.secret_key sk-lf-...

# Optional: self-hosted Langfuse
pv config langfuse.host https://langfuse.my-company.com
```

Or use environment variables:

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"   # optional
```

### What Gets Synced

**Push (`pv push langfuse`):**
- Each `Prompt` becomes a Langfuse prompt with the same name
- Each `PromptVersion.raw_content` becomes a new version in Langfuse
- Commit messages are included as labels

**Pull (`pv pull langfuse`):**
- Each Langfuse prompt is fetched
- New prompts are created locally with source `MANUAL`
- New versions are created for prompts that already exist locally

### Usage

```bash
# Initial setup
pv config langfuse.public_key pk-lf-abc123
pv config langfuse.secret_key sk-lf-xyz789

# Push your captured prompts to Langfuse
pv push langfuse

# Pull any prompts created in Langfuse UI
pv pull langfuse

# Daily sync
pv sync langfuse
```

---

## LangSmith Integration

### Installation

```bash
pip install "promptview[langsmith]"
```

### Configuration

```bash
pv config langsmith.api_key ls__abc123
pv config langsmith.project my-project-name
```

Or use environment variables:

```bash
export LANGCHAIN_API_KEY="ls__abc123"
export LANGCHAIN_PROJECT="my-project"
```

### What Gets Synced

**Push (`pv push langsmith`):**
- Each `Prompt` becomes a LangSmith prompt hub entry
- Each `PromptVersion.raw_content` is pushed as a prompt version
- Source and version metadata is preserved

**Pull (`pv pull langsmith`):**
- All prompts in the configured project are fetched
- New versions are created for changed content

### Usage

```bash
# Setup
pv config langsmith.api_key ls__abc123
pv config langsmith.project my-project

# Push all local prompts
pv push langsmith

# Pull any remote changes
pv pull langsmith

# Full sync
pv sync langsmith
```

---

## Using Both Simultaneously

You can sync with both platforms in parallel:

```bash
pv sync langfuse
pv sync langsmith
```

PromptView's local DB remains the single source of truth. Pushes to both platforms go out from there.

---

## Configuration Reference

View current configuration:

```bash
pv config --show
```

Set a value:

```bash
pv config KEY VALUE
```

All config keys:

| Key | Description |
|---|---|
| `author` | Default commit author |
| `llm.provider` | Default LLM provider for CLI operations |
| `llm.api_key` | Default API key |
| `llm.model` | Default model override |
| `langfuse.public_key` | Langfuse public key |
| `langfuse.secret_key` | Langfuse secret key |
| `langfuse.host` | Langfuse host (default: `https://cloud.langfuse.com`) |
| `langsmith.api_key` | LangSmith API key |
| `langsmith.project` | LangSmith project name |

Config is stored in `.promptview/config.toml`. API keys stored there are project-local — consider using environment variables for secrets in shared repositories.

---

## See Also

- [Langfuse Integration](../integrations/langfuse.md)
- [LangSmith Integration](../integrations/langsmith.md)
- [pv remote backends](remote-backends.md)
- [Team Workflow](../advanced/team-workflow.md)
