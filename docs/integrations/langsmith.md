# LangSmith Integration

PromptView integrates with [LangSmith](https://smith.langchain.com/) for two-way prompt synchronization. Use PromptView for local version control and visual editing, and LangSmith for runtime serving, tracing, and evaluation.

---

## Installation

```bash
pip install "promptview[langsmith]"
```

---

## Configuration

### Via CLI

```bash
pv config langsmith.api_key ls__abc123...
pv config langsmith.project my-project-name
```

### Via Environment Variables

```bash
export LANGCHAIN_API_KEY="ls__abc123..."
export LANGCHAIN_PROJECT="my-project"
```

### Where to Find Keys

Log into [smith.langchain.com](https://smith.langchain.com) → Settings → API Keys → Create new key. API keys start with `ls__`.

---

## Commands

### Push to LangSmith

```bash
pv push langsmith
```

Pushes all committed prompt versions to the LangSmith prompt hub under your configured project.

**What gets pushed:**
- Each `Prompt` becomes a LangSmith prompt hub entry
- Each `PromptVersion.raw_content` is pushed as a prompt version
- Version numbers and source metadata are preserved

### Pull from LangSmith

```bash
pv pull langsmith
```

Pulls prompts from LangSmith into the local PromptView database.

**What gets pulled:**
- All prompts in the configured project are fetched
- Prompts not in the local DB are created with `source=MANUAL`
- New versions are created for prompts whose content has changed

### Two-Way Sync

```bash
pv sync langsmith
```

Runs push then pull in a single operation — the recommended daily operation.

---

## Typical Workflow

```bash
# Initial setup — push existing prompts to LangSmith
pv push langsmith

# Development cycle
pv scan
pv add .
pv commit -m "Add chain-of-thought to reviewer"
pv sync langsmith      # keep in sync

# Before deployment
pv sync langsmith
```

---

## What Gets Synced

| PromptView Data | LangSmith Data |
|---|---|
| `Prompt.name` | Prompt name in hub |
| `PromptVersion.raw_content` | Prompt version text |
| `PromptVersion.version_number` | Version number |
| `Commit.author` | Commit attribution |

---

## Using LangSmith in Production

After pushing, use the LangSmith client to fetch and use prompts:

```python
from langsmith import Client

client = Client()

# Pull the latest prompt
prompt = client.pull_prompt("support_agent")

# Use with LangChain
from langchain_core.prompts import ChatPromptTemplate
template = ChatPromptTemplate.from_messages(prompt.messages)
```

PromptView manages version control and editing. LangSmith handles production serving, tracing, and evaluation.

---

## Project Configuration

The `langsmith.project` config determines which LangSmith project your prompts are pushed to:

```bash
pv config langsmith.project production-prompts

# Push to a different project for staging
pv config langsmith.project staging-prompts
pv push langsmith
```

---

## See Also

- [pv push / pull / sync CLI](../cli/integrations.md)
- [Langfuse Integration](langfuse.md)
- [Team Workflow](../advanced/team-workflow.md)
