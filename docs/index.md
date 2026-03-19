# PromptView

**Git-like versioning and visual management for LLM prompts. The DVC of prompt engineering.**

Prompts in AI applications grow large, complex, and hard to manage. They live buried in source code as strings, change silently across deployments, and have no history, no diffs, and no structure. PromptView fixes that: it scans your codebase automatically, versions every prompt like git commits, and gives you a visual editor where each prompt is broken into its structural components — Role, Context, Instructions, Format, Examples — displayed as an interactive node graph. Edit any node and the change is reflected back into your original prompt surgically via LLM, preserving your style and whitespace exactly.

---

## :material-lightning-bolt: What PromptView Solves

Modern AI applications contain dozens of prompts scattered across files, often modified without any record of what changed or why. When a model's behaviour degrades, there is no way to bisect the prompt history. When you want to experiment with a new tone or instruction set, you overwrite the original. When a team member modifies a shared prompt, you only find out in production.

PromptView brings the same discipline to prompts that git brings to source code and DVC brings to datasets.

---

## :material-star: Features

| Feature | Description |
|---|---|
| :material-magnify: **Auto-discovery** | AST-based scanner finds prompts across OpenAI, Anthropic, LangChain, LiteLLM, and raw string patterns — zero config |
| :material-git: **Git-like workflow** | `pv scan → pv add → pv commit → pv log → pv diff` — familiar and scriptable |
| :material-graph: **Component graph** | Every prompt decomposed into labeled nodes; edit any node and the prompt updates surgically |
| :material-history: **Version history** | Toggle between any past version instantly in the UI |
| :material-variable: **Template variables** | `{slot}` detection, default management, and `pv run` for parameterised rendering |
| :material-link: **Prompt composition** | Embed one prompt inside another with `{{ include: prompt_name }}` |
| :material-robot: **Provider-agnostic LLM** | OpenAI, Anthropic, Gemini, or Ollama (local, free, no API key) |
| :material-test-tube: **Eval framework** | Run test suites against prompt versions; score with exact_match, contains, or LLM-as-judge |
| :material-cloud-upload: **Team sharing** | Push/pull the prompt DB to S3, GCS, or any HTTP endpoint |
| :material-sync: **Two-way sync** | Push to and pull from Langfuse and LangSmith |
| :material-github: **Git hooks + GitHub Actions** | Block commits with untracked prompts; auto-generate CI workflow |

---

## :material-download: Quick Install

=== "pip"

    ```bash
    pip install promptview
    ```

=== "uv"

    ```bash
    uv add promptview
    ```

=== "With extras"

    ```bash
    pip install "promptview[langfuse,langsmith,s3]"
    ```

---

## :material-rocket-launch: 5-Line Quick Start

```bash
cd my-ai-project
pv init                           # create .promptview/ repo
pv scan                           # find all prompts in codebase
pv add .                          # stage everything
pv commit -m "Initial capture"   # version them
pv ui                             # open http://localhost:8765
```

That's it. Your prompts are now versioned, browsable, and editable.

---

## Why PromptView?

| Capability | Manual Management | Langfuse / LangSmith | **PromptView** |
|---|---|---|---|
| Auto-discover prompts from source code | No | No | **Yes** |
| Works offline / local-first | Yes | No | **Yes** |
| Git-style commit history | No | Partial | **Yes** |
| Visual component graph editor | No | No | **Yes** |
| Surgical LLM regeneration | No | No | **Yes** |
| Template variables with defaults | No | Partial | **Yes** |
| Prompt composition (`{{ include }}`) | No | No | **Yes** |
| Eval framework built-in | No | Yes | **Yes** |
| Push/pull to Langfuse/LangSmith | No | Native | **Yes** |
| Self-hosted, zero cloud dependency | Yes | No | **Yes** |
| Free to use | Yes | Partial | **Yes** |

---

## :material-book-open: Next Steps

- [Installation](getting-started/installation.md) — all install methods and optional extras
- [Quick Start](getting-started/quick-start.md) — step-by-step walkthrough
- [Core Concepts](getting-started/concepts.md) — understand prompts, versions, commits, and components
- [CLI Reference](cli/overview.md) — all 22 commands documented
- [Web UI](ui/overview.md) — the visual editor explained
