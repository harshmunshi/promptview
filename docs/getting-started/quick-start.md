# Quick Start

This guide walks you through capturing your first prompts with PromptView in under 5 minutes.

---

## Prerequisites

- PromptView installed — see [Installation](installation.md)
- A Python project containing LLM calls (OpenAI, Anthropic, LangChain, or raw string prompts)
- Optionally: an API key for OpenAI, Anthropic, or Gemini (or a local Ollama install) for the visual editor

---

## Step 1: Initialize the Repository

Navigate to your project root and run:

```bash
cd my-ai-project
pv init
```

This creates a `.promptview/` directory in your project:

```
.promptview/
├── promptview.db    # SQLite database — all prompts, versions, commits
├── config.toml      # project configuration
├── HEAD             # current branch pointer
├── index.json       # staging area
├── objects/         # content-addressed storage
├── refs/            # branch references
└── logs/            # commit log
```

Output:

```
Initialized PromptView repository in /my-ai-project/.promptview/
```

!!! tip "Author Configuration"
    Set your name once to tag all commits:
    ```bash
    pv init --author "Alice Smith"
    ```
    Or update it any time: `pv config author "Alice Smith"`

---

## Step 2: Scan for Prompts

PromptView uses AST analysis to find prompts in your Python source:

```bash
pv scan
```

Example output:

```
Scanning /my-ai-project ...

  src/agent.py:42       system_prompt          openai    confidence=0.95
  src/agent.py:67       user_template          openai    confidence=0.88
  src/summarizer.py:15  summarize_prompt       anthropic confidence=0.92
  src/utils.py:8        BASE_INSTRUCTIONS      raw       confidence=0.72

Found 4 prompts across 3 files.
```

The scanner detects:
- OpenAI `client.chat.completions.create(...)` calls
- Anthropic `client.messages.create(...)` calls
- LangChain `ChatPromptTemplate.from_messages(...)` patterns
- Raw Python string variables assigned near LLM call sites

---

## Step 3: Stage Prompts

Stage all discovered prompts (like `git add .`):

```bash
pv add .
```

To stage prompts from a specific file only:

```bash
pv add --file src/agent.py
```

Check what is staged:

```bash
pv status
```

Output:

```
Staged (ready to commit):
  + system_prompt           src/agent.py:42
  + user_template           src/agent.py:67
  + summarize_prompt        src/summarizer.py:15
  + BASE_INSTRUCTIONS       src/utils.py:8
```

---

## Step 4: Commit

Create your first prompt commit:

```bash
pv commit -m "Initial prompt capture"
```

Output:

```
[a3f2c891] Initial prompt capture
  4 prompts committed
```

The commit ID is an 8-character SHA256 hash — identical to git's short hashes.

---

## Step 5: Open the Visual Editor

```bash
pv ui
```

Output:

```
Starting PromptView UI on http://localhost:8765
Press Ctrl+C to stop.
```

Your browser opens automatically. You will see:

- **Left sidebar** — all 4 prompts listed with source badges and version counts
- **Click any prompt** — opens the component graph view
- **Decompose button** — breaks the prompt into labeled nodes (requires LLM config)
- **Version pill** — shows "v1" — the version you just committed

---

## Step 6: Configure an LLM (for the Visual Editor)

Click the gear icon (⚙) in the top-right of the UI:

1. Select **Provider**: `openai`, `anthropic`, `gemini`, or `ollama`
2. Enter your **API Key** (not needed for Ollama)
3. Optionally set a **Model** (defaults are: `gpt-4o-mini`, `claude-haiku-4-5`, `gemini-2.0-flash`, `llama3`)
4. Click **Save**

Settings are stored in your browser's `localStorage`. They are never sent to any server.

!!! tip "Using Ollama (Free, Local)"
    If you have Ollama running, select "ollama" in the provider dropdown. No API key needed.
    ```bash
    ollama pull llama3
    # Ollama starts automatically on http://localhost:11434
    ```

---

## Step 7: Decompose and Edit

1. Click a prompt in the sidebar
2. Click **Decompose** — the LLM parses the prompt into components (Role, Instructions, Format, etc.)
3. Click any node to expand and edit its content
4. Click **Save** — the prompt is surgically updated and a new version is committed automatically

---

## What Happens as You Work

Every time you modify prompts in your codebase, repeat the git-like cycle:

```bash
pv scan              # find new/changed prompts
pv add .             # stage changes
pv commit -m "..."   # create a new version
```

Or use the git pre-commit hook to automate detection:

```bash
pv hooks install     # blocks git commits if prompts are untracked
```

---

## Next Steps

- [Core Concepts](concepts.md) — understand Prompts, Versions, Commits, and Components in depth
- [CLI Reference](../cli/overview.md) — all commands and flags
- [Template Variables](../template-system/variables.md) — add `{slots}` to your prompts
- [Evaluations](../eval/overview.md) — run test suites against your prompt versions
- [Team Sharing](../integrations/remote-backends.md) — share the DB via S3, GCS, or HTTP
