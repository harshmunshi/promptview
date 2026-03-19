# Core Concepts

Understanding PromptView's data model makes the CLI and UI much more intuitive. This page explains each concept and how they relate.

---

## Prompt

A **Prompt** is the fundamental unit PromptView tracks. It represents a named, uniquely identified string in your codebase — a system message, a user template, or any text passed to an LLM.

Each prompt has:

| Field | Description |
|---|---|
| `id` | UUID — stable forever, never changes |
| `name` | Human-readable identifier (e.g. `system_prompt`, `summarize_prompt`) |
| `source` | Where it was detected: `openai`, `anthropic`, `langchain`, `litellm`, `raw`, `manual` |
| `file_path` | The Python file containing it |
| `line_number` | The line where the string was found |
| `variable_name` | The Python variable name (e.g. `SYSTEM_PROMPT`) |
| `tags` | Optional labels for filtering |

!!! note "Identity vs. Content"
    The prompt's `id` and `name` are its *identity*. The actual text is stored as a **Version**. This separation means you can change the prompt's content many times while keeping a single identity to track history against.

---

## Version

A **Version** is an immutable snapshot of a prompt's content at a point in time. Every time you `pv commit`, a new version is created for each staged prompt.

| Field | Description |
|---|---|
| `id` | UUID — unique per snapshot |
| `prompt_id` | The prompt this version belongs to |
| `version_number` | Monotonically increasing integer (1, 2, 3, …) |
| `raw_content` | The full prompt text at this snapshot |
| `content_hash` | SHA256 of the content — used to detect changes |
| `commit_id` | Which commit created this version |
| `parent_version_id` | The previous version (null for v1) — forms a linked list |

Versions are **write-once**. PromptView never modifies an existing version. Editing in the UI always creates a new version.

---

## Commit

A **Commit** groups one or more version changes together under a message and timestamp, exactly like a git commit.

| Field | Description |
|---|---|
| `id` | 8-character SHA256 hash (e.g. `a3f2c891`) |
| `message` | The commit message (`-m "..."`) |
| `author` | From config or `--author` flag |
| `timestamp` | ISO 8601 UTC datetime |
| `version_ids` | JSON list of version IDs included in this commit |

```bash
pv log
# a3f2c891  Initial prompt capture        2024-03-15 10:32:11  Alice Smith
# b7e1d234  Improve summarizer tone       2024-03-16 14:05:33  Alice Smith
```

---

## Component

A **Component** is a labeled structural node within a prompt — the result of decomposing it with an LLM. Components are the atoms of the visual editor.

Common component labels:
- **Role** — what persona the LLM should adopt (`You are a senior software engineer…`)
- **Context** — background information the model needs
- **Instructions** — the main task (`Summarize the following article…`)
- **Output Format** — how the response should be structured (`Respond in JSON…`)
- **Examples** — few-shot examples
- **Constraints** — things to avoid or limits to follow

| Field | Description |
|---|---|
| `id` | UUID |
| `prompt_id` | Which prompt |
| `version_id` | Which version of that prompt |
| `label` | The component type (e.g. "Instructions") |
| `content` | The text of this component |
| `position` | Ordering index — determines display order in the graph |

Components are stored per `(prompt_id, version_id)` pair. Switching version in the UI reloads the components for that specific version.

---

## Variable

A **Variable** is a `{slot}` placeholder found in a prompt's raw content. Variables let you reuse the same prompt template with different inputs.

```
You are a helpful assistant for {company_name}.
Help {user_name} with: {task}
```

This prompt has three variables: `company_name`, `user_name`, and `task`.

| Field | Description |
|---|---|
| `id` | UUID |
| `prompt_id` | Which prompt this variable belongs to |
| `name` | The slot name (e.g. `user_name`) |
| `default_value` | Value used when none is supplied |
| `description` | Human-readable description of what goes here |

Variables are synced with `pv vars sync <prompt_name>` — which scans the latest version's content and upserts any new `{slot}` names. Existing defaults are **never overwritten**.

---

## Remote

A **Remote** is a storage location (S3, GCS, or HTTP) where the entire `.promptview/promptview.db` file can be pushed to or pulled from. This is how teams share prompts.

Named remotes are stored in `.promptview/config.toml`:

```toml
[remotes]
origin = "s3://my-bucket/my-project/"
staging = "gcs://staging-bucket/prompts/"
```

Think of remotes as the equivalent of `git remote add origin` — but instead of pushing code, you push the prompt database.

---

## Eval Run

An **Eval Run** is a scored test of a prompt version against a dataset. It records:

| Field | Description |
|---|---|
| `id` | UUID |
| `prompt_id` | Which prompt was tested |
| `version_id` | Which version was tested |
| `total_cases` | Number of test cases in the dataset |
| `passed` | Number that passed scoring |
| `pass_rate` | `passed / total_cases * 100` |
| `avg_judge_score` | Average LLM judge score (0–1), if used |
| `avg_latency_ms` | Average response time per case |
| `dataset_path` | Path to the JSONL file used |

Each eval run also stores per-case **EvalResults** with the actual LLM output, pass/fail status, similarity score, judge score, judge reasoning, and latency.

---

## How They All Relate

```
Prompt (identity)
  └── Version 1 (snapshot)
  │     └── Component: Role
  │     └── Component: Instructions
  │     └── Component: Output Format
  │     └── Variable: {user_name}
  │     └── Variable: {task}
  └── Version 2 (snapshot — after edit)
  │     └── Component: Role
  │     └── Component: Context       ← new component added
  │     └── Component: Instructions  ← edited
  │     └── Component: Output Format
  │
  └── EvalRun A (on Version 1)
        └── EvalResult: case 1 — passed
        └── EvalResult: case 2 — failed

Commit abc12345
  └── version_ids: [Version 1 of system_prompt, Version 1 of summarize_prompt]

Remote: origin = s3://bucket/project/
  └── contains the full promptview.db (all prompts, versions, commits, evals)
```

---

## The Staging Area

Like git, PromptView has a **staging area** (also called the index). After `pv scan` finds prompts, you explicitly choose which ones to include in the next commit using `pv add`.

```bash
pv scan                    # discover prompts → stored in memory
pv add system_prompt       # stage one specific prompt
pv add .                   # stage all found prompts
pv status                  # see what is staged vs. modified vs. untracked
pv commit -m "message"     # create versions for everything staged
```

Prompts in the staging area are stored in `.promptview/index.json`. Running `pv commit` reads the index, creates version records for each staged prompt, bundles them into a commit record, and clears the index.

---

## Next Steps

- [Architecture](../how-it-works/architecture.md) — how the layers fit together
- [CLI Reference](../cli/overview.md) — put these concepts into practice
