# Versioning Model

PromptView's versioning system is directly inspired by git. If you understand git's commit model, you already understand PromptView's versioning.

---

## Git Analogy

| Git Concept | PromptView Equivalent | Notes |
|---|---|---|
| Repository (`.git/`) | `.promptview/` | Local directory in project root |
| Tracked file | Tracked prompt | A named string with an ID |
| `git add <file>` | `pv add <prompt>` | Moves to staging area |
| Staging area (index) | `index.json` | What goes into the next commit |
| `git commit -m "msg"` | `pv commit -m "msg"` | Creates a commit record |
| Commit hash | 8-char SHA256 | Short hash for display |
| `git diff` | `pv diff` | Unified diff between versions |
| `git log` | `pv log` | Commit history |
| `git status` | `pv status` | Staged / modified / untracked |
| Branch | Prompt branch | Supported — WIP |
| Remote (`origin`) | Named remote (S3/GCS/HTTP) | Push/pull the DB file |
| Content-addressable object | `content_hash` | SHA256 of prompt content |

---

## Content Hashing

Every time a prompt is committed, PromptView computes a SHA256 hash of its raw content. This hash is stored as `content_hash` on the `PromptVersion` record.

Consequences:
- **Deduplication**: if you commit the same prompt twice without changes, no new version is created (the hash matches the existing one).
- **Tamper detection**: you can verify that a version's content hasn't been modified in the database.
- **Change detection**: `pv status` detects modified prompts by comparing the current content hash against the last committed hash.

---

## The Staging Area

The staging area lives in `.promptview/index.json`. It is a simple JSON list of `ScannedPrompt` objects that have been `pv add`ed but not yet committed.

```bash
pv scan               # find prompts → candidates in memory
pv add system_prompt  # copy to index.json
pv add summarizer     # add another
pv status             # shows what is staged
pv commit -m "msg"    # read index.json → create versions → create commit → clear index
```

You can unstage a prompt:
```bash
pv add --unstage system_prompt
```

---

## Commit Object

A commit is a lightweight record that bundles version changes:

```json
{
  "id": "a3f2c891",
  "message": "Improve tone for summarizer",
  "author": "Alice Smith",
  "timestamp": "2024-03-15T10:32:11Z",
  "version_ids": ["uuid-of-version-v2", "uuid-of-version-v3"]
}
```

The `id` is the first 8 characters of a SHA256 hash of `(message + author + timestamp)`. This gives unique, short, human-readable identifiers — identical to git's short hashes.

---

## Version Lineage

Versions form a linked list via `parent_version_id`:

```
Version 1 (v1)
  parent_version_id: null
  content: "You are a helpful assistant."
  content_hash: abc123...

Version 2 (v2)
  parent_version_id: version-1-uuid
  content: "You are a helpful assistant. Be concise."
  content_hash: def456...

Version 3 (v3)
  parent_version_id: version-2-uuid
  content: "You are a helpful, concise assistant."
  content_hash: ghi789...
```

This lineage supports `pv diff` between any two versions — not just adjacent ones.

---

## Version Numbers

Version numbers (`version_number`) are monotonically increasing integers starting at 1, scoped per prompt. Prompt A can have `v1, v2, v3` while Prompt B independently has `v1, v2`.

The UI shows version pills as "v1", "v2", "v3" — clicking switches the component graph to that version's decomposition.

---

## Immutability

Once a `PromptVersion` record is created, it is never modified. All edits — whether via `pv commit` or via the UI's node editor — create new version records.

This guarantees:
- Full audit trail
- Safe rollback to any past state
- Concurrent read safety (old versions never change under you)

---

## Diff Engine

`pv diff <prompt_name> <v1> <v2>` produces a unified diff between any two versions:

```bash
pv diff system_prompt 1 3
```

Output:

```diff
--- system_prompt v1
+++ system_prompt v3
@@ -1,3 +1,4 @@
 You are a helpful assistant.
-Be concise and direct.
+Be concise, direct, and friendly.
+Always respond in the user's language.
```

The diff engine (`storage/diff_engine.py`) uses Python's `difflib.unified_diff` on the `raw_content` of the two `PromptVersion` objects.

---

## Branch Support

PromptView supports prompt branches — useful for experimenting with tone or structure changes:

```bash
pv branch create feature/formal-tone
pv branch list
pv branch delete feature/formal-tone
```

Branches are stored as references in `.promptview/refs/`. The current branch is tracked in `.promptview/HEAD`.

!!! note "Branch Merge"
    Branch merging (`pv merge`) is not yet implemented. Branches currently serve as isolation namespaces for experimentation. Checking out a branch changes which version is the "current" one for each prompt.

---

## Storage Schema Detail

```sql
CREATE TABLE prompt_versions (
    id              TEXT PRIMARY KEY,
    prompt_id       TEXT NOT NULL,
    version_number  INTEGER NOT NULL,
    raw_content     TEXT NOT NULL,
    blocks          TEXT,              -- JSON: list of PromptBlock
    content_hash    TEXT NOT NULL,
    commit_id       TEXT,
    parent_version_id TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE commits (
    id          TEXT PRIMARY KEY,      -- 8-char SHA256
    message     TEXT NOT NULL,
    author      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    version_ids TEXT NOT NULL          -- JSON array
);
```

---

## Next Steps

- [Component Graph](component-graph.md) — how prompts are decomposed into nodes
- [pv add & commit reference](../cli/add-commit.md)
- [pv status, diff, log reference](../cli/status-diff-log.md)
