# pv status, pv diff & pv log

Inspect the state of your prompt repository — what has changed, how it changed, and the full history.

---

## pv status

### Synopsis

```bash
pv status
```

### Description

`pv status` shows the current state of the repository at a glance — what is staged, what has changed since the last commit, and what prompts are untracked (found by the scanner but not yet added).

This is the direct equivalent of `git status`.

### Output

```
Staged (ready to commit):
  + system_prompt           src/agent.py:42         (new)
  ~ summarize_prompt        src/summarizer.py:15    (modified)

Modified (not staged):
  ~ code_reviewer           src/reviewer.py:8       (content changed)

Untracked:
  ? user_template           src/agent.py:67
  ? base_instructions       src/utils.py:3
```

**Symbols:**
- `+` New prompt — not yet committed
- `~` Modified — content changed since last commit
- `?` Untracked — found by scanner but never staged

### Git Equivalent

```
git status:
  Changes to be committed:    →  Staged
  Changes not staged:         →  Modified (not staged)
  Untracked files:            →  Untracked
```

---

## pv diff

### Synopsis

```bash
pv diff [NAME] [V1] [V2] [OPTIONS]
```

### Description

`pv diff` shows a unified diff between two versions of a prompt. You can diff:
- Any two version numbers for a specific prompt
- The staged version against the last commit
- The current working content against the last commit

### Arguments

| Argument | Description |
|---|---|
| `NAME` | Prompt name to diff |
| `V1` | First version number (defaults to second-to-last) |
| `V2` | Second version number (defaults to latest) |

### Options

| Option | Description |
|---|---|
| `--staged` | Diff staged content against last committed version |

### Examples

```bash
# Diff latest two versions of a prompt
pv diff system_prompt

# Diff specific versions
pv diff system_prompt 1 3

# Diff staged content against last commit
pv diff system_prompt --staged

# Diff any two versions
pv diff summarize_prompt 2 5
```

### Output

```diff
--- system_prompt v2
+++ system_prompt v3
@@ -1,5 +1,6 @@
 You are a senior software engineer.
-Review the code for security issues.
+Review the code for security issues, performance bottlenecks,
+and code readability problems.

 Respond in JSON format with an array of findings.
 Each finding must have: severity, description, and line number.
```

The diff uses unified diff format — the same as `git diff`. Lines starting with `-` were removed, lines with `+` were added, and lines with ` ` (space) are unchanged context.

### Git Equivalent

```bash
git diff          →  pv diff --staged
git diff HEAD     →  pv diff <name>
git diff v1 v3    →  pv diff <name> 1 3
```

---

## pv log

### Synopsis

```bash
pv log [NAME] [OPTIONS]
```

### Description

`pv log` shows the commit history for the repository or for a specific prompt. Most recent commits appear first.

### Arguments

| Argument | Description |
|---|---|
| `NAME` | Filter log to commits affecting this prompt |

### Options

| Option | Description | Default |
|---|---|---|
| `--oneline` | One commit per line | Off |
| `-n N` | Show last N commits | 20 |

### Examples

```bash
# Full log for all commits
pv log

# One-line format
pv log --oneline

# Log for a specific prompt
pv log system_prompt

# Last 5 commits
pv log -n 5

# One-line log for a specific prompt
pv log system_prompt --oneline
```

### Full Output

```
commit a3f2c891
Author: Alice Smith
Date:   2024-03-16 14:22:07

    Add chain-of-thought instructions to improve accuracy

    Prompts: system_prompt (v3), code_reviewer (v2)

commit b7e1d234
Author: Alice Smith
Date:   2024-03-15 10:32:11

    Initial prompt capture

    Prompts: system_prompt (v1), summarize_prompt (v1), code_reviewer (v1)
```

### One-Line Output

```
a3f2c891  Add chain-of-thought instructions    2024-03-16  Alice Smith
b7e1d234  Initial prompt capture               2024-03-15  Alice Smith
```

### Git Equivalent

```bash
git log                 →  pv log
git log --oneline       →  pv log --oneline
git log -- <file>       →  pv log <prompt_name>
git log -n 5            →  pv log -n 5
```

---

## Complete Workflow Example

```bash
# Make changes to your prompt in source code
vim src/agent.py

# Check what changed
pv status
# Modified (not staged):
#   ~ system_prompt   src/agent.py:42  (content changed)

# See exactly what changed
pv diff system_prompt

# Stage and commit
pv add system_prompt
pv commit -m "Make tone more professional"

# Verify commit was created
pv log --oneline
# d1e2f3a4  Make tone more professional    2024-03-17  Alice Smith
# a3f2c891  Add chain-of-thought          2024-03-16  Alice Smith
# b7e1d234  Initial prompt capture        2024-03-15  Alice Smith

# Compare current with initial
pv diff system_prompt 1 3
```

---

## See Also

- [pv add & commit](add-commit.md)
- [Versioning Model](../how-it-works/versioning.md)
