# pv hooks & pv cicd

Automate prompt tracking enforcement with git hooks and GitHub Actions.

---

## pv hooks

### Synopsis

```bash
pv hooks install
pv hooks uninstall
pv hooks status
```

### Description

`pv hooks` installs a git pre-commit hook that runs `pv scan` before every `git commit`. If untracked prompts are found, the commit is blocked with a helpful error message — preventing unversioned prompts from sneaking into production.

---

### pv hooks install

```bash
pv hooks install
```

Creates `.git/hooks/pre-commit` with the following content:

```bash
#!/bin/bash
# PromptView pre-commit hook
# Blocks commits when prompts are untracked

pv scan --fail-on-untracked
if [ $? -ne 0 ]; then
  echo ""
  echo "PromptView: Untracked prompts detected."
  echo "Run 'pv add .' and 'pv commit -m ...' before committing."
  exit 1
fi
```

The hook is marked executable (`chmod +x`).

Output:
```
Installed pre-commit hook at .git/hooks/pre-commit
```

!!! note "Existing Hooks"
    If `.git/hooks/pre-commit` already exists, PromptView appends the check to the end of the file rather than overwriting it.

---

### pv hooks uninstall

```bash
pv hooks uninstall
```

Removes the PromptView-managed block from `.git/hooks/pre-commit`. If the hook file becomes empty after removal, the file is deleted entirely.

---

### pv hooks status

```bash
pv hooks status
```

Output when installed:
```
PromptView pre-commit hook: installed (.git/hooks/pre-commit)
```

Output when not installed:
```
PromptView pre-commit hook: not installed
```

---

### Hook Workflow

```
git commit -m "Deploy new agent"
  │
  ├── pre-commit hook fires
  │     └── pv scan --fail-on-untracked
  │           ├── No untracked prompts → exits 0 → commit proceeds
  │           └── Untracked prompts found → exits 1 → commit BLOCKED
  │                 Output:
  │                 "Untracked prompts: user_template (src/agent.py:67)"
  │                 "Run 'pv add .' and 'pv commit -m ...' to track them."
  │
  └── commit proceeds or is blocked
```

---

## pv cicd generate

### Synopsis

```bash
pv cicd generate [OPTIONS]
```

### Description

`pv cicd generate` outputs a ready-to-use GitHub Actions workflow YAML that:
1. Restores the prompt database from a remote backend
2. Scans for untracked prompts (fails the CI run if any are found)
3. Optionally runs eval regression checks

### Options

| Option | Description | Default |
|---|---|---|
| `--output PATH` | Write to a file instead of stdout | stdout |

### Examples

```bash
# Print to terminal
pv cicd generate

# Write directly to the standard location
pv cicd generate --output .github/workflows/promptview.yml
```

---

### Generated Workflow

The generated `.github/workflows/promptview.yml` looks like:

```yaml
name: PromptView — Prompt Tracking

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  prompt-tracking:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install PromptView
        run: pip install "promptview[s3]"

      - name: Initialize PromptView
        run: pv init --no-scan

      - name: Restore prompt database
        run: pv pull-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ secrets.AWS_DEFAULT_REGION }}

      - name: Check for untracked prompts
        run: pv scan --fail-on-untracked

      # Optional: uncomment to run eval regression
      # - name: Run eval regression
      #   run: pv eval run my_prompt --dataset evals/regression.jsonl --provider openai
      #   env:
      #     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

### Workflow Explanation

| Step | What It Does |
|---|---|
| **Checkout** | Standard GitHub Actions checkout |
| **Set up Python** | Install Python 3.11 (compatible with PromptView) |
| **Install PromptView** | `pip install "promptview[s3]"` — add your backend extra |
| **Initialize** | `pv init --no-scan` — create `.promptview/` without scanning |
| **Restore DB** | `pv pull-remote origin` — download the shared DB |
| **Check untracked** | `pv scan --fail-on-untracked` — fail if any prompts are new and untracked |
| **Eval regression** | Optional: run scored test suite against the latest prompt version |

---

### Required Secrets

Add these to your GitHub repository's Settings → Secrets → Actions:

For S3:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION
```

For GCS:
```
GOOGLE_APPLICATION_CREDENTIALS  (base64-encoded service account JSON)
```

For eval with OpenAI:
```
OPENAI_API_KEY
```

---

### Adapting the Workflow

For GCS instead of S3:

```yaml
- name: Install PromptView
  run: pip install "promptview[gcs]"

- name: Restore prompt database
  run: pv pull-remote origin
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_CREDENTIALS }}
```

For HTTP backend (no secrets needed if unauthenticated):

```yaml
- name: Install PromptView
  run: pip install promptview   # no extra needed

- name: Restore prompt database
  run: pv pull-remote https://prompts.my-company.com/project/
```

---

## See Also

- [CI/CD Integration](../advanced/ci-cd.md) — full CI/CD guide with multi-environment setup
- [Team Workflow](../advanced/team-workflow.md)
- [pv remote backends](remote-backends.md)
