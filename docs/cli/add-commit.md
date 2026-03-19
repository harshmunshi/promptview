# pv add & pv commit

Stage prompts and create version commits — the heart of the PromptView workflow.

---

## pv add

### Synopsis

```bash
pv add [NAME|.] [OPTIONS]
```

### Description

`pv add` moves scanned prompts into the staging area (`.promptview/index.json`). Only staged prompts are included in the next `pv commit`.

This is directly analogous to `git add` — you explicitly choose what to include rather than committing everything automatically.

### Arguments

| Argument | Description |
|---|---|
| `NAME` | Stage a specific prompt by name |
| `.` | Stage all found prompts |

### Options

| Option | Description |
|---|---|
| `--file PATH` | Stage all prompts found in a specific file |
| `--min-confidence FLOAT` | Only stage prompts above this confidence (default: 0.60) |
| `--unstage NAME` | Remove a prompt from the staging area |

### Examples

```bash
# Stage everything
pv add .

# Stage a specific prompt by name
pv add system_prompt
pv add summarize_prompt

# Stage all prompts in a specific file
pv add --file src/agent.py

# Stage only high-confidence detections
pv add . --min-confidence 0.85

# Unstage a prompt
pv add --unstage user_template
```

### What "Staging" Means

When you `pv add` a prompt:
1. The `ScannedPrompt` record (name, content, source, file_path, line_number, confidence) is written to `.promptview/index.json`
2. `pv status` shows it as "staged"
3. The next `pv commit` will create a `PromptVersion` record for it

If the prompt's content hasn't changed since the last commit, staging it and committing creates no new version (the content hash matches). This is identical to git's behaviour with unchanged files.

---

## pv commit

### Synopsis

```bash
pv commit -m "MESSAGE" [OPTIONS]
```

### Description

`pv commit` reads the staging area, creates a new `PromptVersion` for each staged prompt whose content has changed, and bundles them into a `Commit` record with your message.

### Options

| Option | Description |
|---|---|
| `-m, --message TEXT` | Commit message (required) |
| `--author TEXT` | Override the author for this commit only |

### Examples

```bash
pv commit -m "Initial prompt capture"
pv commit -m "Improve tone in summarizer"
pv commit -m "Add output format constraints to code reviewer"
pv commit -m "Parameterise company name as {company}" --author "Bob"
```

### What a Commit Does

1. Reads `.promptview/index.json` (the staging area)
2. For each staged prompt:
   - Computes SHA256 of content
   - If hash differs from last known version: creates a new `PromptVersion` record
   - If hash is unchanged: skips (no redundant versions)
3. Creates a `Commit` record:
   - `id` = first 8 chars of SHA256(`message + author + timestamp`)
   - Stores list of all new version IDs
4. Clears `index.json`

### Output

```
[a3f2c891] Improve tone in summarizer
  2 prompts committed (1 new version, 1 unchanged)
```

---

## The Full Workflow

```bash
# 1. Discover
pv scan

# 2. Review
pv status

# 3. Stage
pv add .
# or selectively:
pv add system_prompt
pv add summarize_prompt

# 4. Verify staging
pv status
# Staged:
#   + system_prompt    src/agent.py:42    (new)
#   ~ summarize_prompt src/summarizer.py  (modified)

# 5. Commit
pv commit -m "Update prompts for v2 launch"

# 6. Verify
pv log --oneline
# a3f2c891  Update prompts for v2 launch   2024-03-16
# b7e1d234  Initial capture                2024-03-15
```

---

## Best Practices for Commit Messages

Write commit messages that explain *why* the prompt changed, not just *what* changed:

```bash
# Good — explains the reasoning
pv commit -m "Add chain-of-thought instructions to improve accuracy"
pv commit -m "Constrain output to JSON to fix downstream parsing failures"
pv commit -m "Remove filler text to reduce token usage"

# Less useful — just describes the action
pv commit -m "Updated prompt"
pv commit -m "Changes"
```

Use the git commit message convention:
- Short summary line (under 72 chars)
- For longer messages, use multiple `-m` flags (if supported) or keep it concise

---

## What a Commit Contains

```json
{
  "id": "a3f2c891",
  "message": "Add chain-of-thought instructions",
  "author": "Alice Smith",
  "timestamp": "2024-03-16T14:22:07Z",
  "version_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
  ]
}
```

Each version ID points to a `PromptVersion` record that holds:
- The full raw content
- The content hash
- The parent version ID (for lineage)
- The version number

---

## Handling Unchanged Prompts

If you stage and commit a prompt whose content is identical to the last version, PromptView detects this via the content hash and does not create a redundant version:

```bash
pv add .
pv commit -m "Routine check"
# [d9c4f211] Routine check
#   3 prompts staged, 0 new versions created (all content unchanged)
```

---

## See Also

- [pv status, diff & log](status-diff-log.md)
- [Versioning Model](../how-it-works/versioning.md)
- [pv scan](scan.md)
