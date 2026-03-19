# CI/CD Integration

Integrate PromptView into your CI/CD pipeline to enforce prompt tracking, prevent regressions, and automate quality checks.

---

## What CI/CD with PromptView Achieves

- **Enforce tracking**: fail builds when prompts are modified without being committed to PromptView
- **Prevent regressions**: fail builds when eval scores drop below a threshold
- **Automate sync**: push/pull the prompt DB as part of deployment
- **Audit trail**: every deployment links to a specific prompt commit ID

---

## Quick Start: Generate a Workflow

```bash
pv cicd generate --output .github/workflows/promptview.yml
git add .github/workflows/promptview.yml
git commit -m "Add PromptView CI workflow"
```

---

## Full GitHub Actions Example

```yaml
name: PromptView — Prompt Tracking & Quality

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  prompt-checks:
    runs-on: ubuntu-latest

    steps:
      # ── Checkout ──────────────────────────────────────────────────
      - name: Checkout code
        uses: actions/checkout@v4

      # ── Python ────────────────────────────────────────────────────
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      # ── Install PromptView ────────────────────────────────────────
      - name: Install PromptView
        run: pip install "promptview[s3]"

      # ── Initialize ────────────────────────────────────────────────
      - name: Initialize PromptView
        run: pv init --no-scan

      # ── Restore shared DB ─────────────────────────────────────────
      - name: Restore prompt database
        run: pv pull-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1

      # ── Check for untracked prompts ───────────────────────────────
      - name: Check for untracked prompts
        run: pv scan --fail-on-untracked

      # ── Eval regression ───────────────────────────────────────────
      - name: Run eval regression
        run: |
          pv eval run support_agent \
            --dataset evals/regression.jsonl \
            --scorer llm_judge \
            --provider openai
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # ── Push updated DB on main merge ─────────────────────────────
      - name: Push prompt database (on main only)
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: pv push-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
```

---

## Step-by-Step Explanation

### 1. Initialize Without Scanning

```yaml
- name: Initialize PromptView
  run: pv init --no-scan
```

`--no-scan` skips the auto-scan that normally happens after `pv init`. We don't want CI to discover "new" prompts — we want it to check against the shared database.

### 2. Restore the Shared Database

```yaml
- name: Restore prompt database
  run: pv pull-remote origin
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    ...
```

Downloads the `promptview.db` from S3, GCS, or HTTP. This gives the CI runner the same state as the team.

### 3. Check for Untracked Prompts

```yaml
- name: Check for untracked prompts
  run: pv scan --fail-on-untracked
```

Scans all Python files. If any prompt strings are found that aren't tracked in the DB, the step fails with exit code 1 — blocking the build.

This is the key enforcement step: it's impossible to merge a PR that adds an untracked prompt.

### 4. Eval Regression

```yaml
- name: Run eval regression
  run: pv eval run support_agent --dataset evals/regression.jsonl --scorer llm_judge --provider openai
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Runs your regression test suite. The step fails if the eval command returns non-zero (which happens if no cases pass or if there's a connection error).

!!! tip "Threshold-Based Failure"
    Currently `pv eval run` doesn't support `--fail-if-pass-rate-below X`. To add this, pipe through a check:
    ```bash
    pv eval run my_prompt --dataset evals/regression.jsonl --provider openai
    # Then check pv metrics show my_prompt and parse pass_rate
    ```

### 5. Push on Merge to Main

```yaml
- name: Push prompt database (on main only)
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: pv push-remote origin
```

After a PR is merged to main, the updated DB (which may have new eval results) is pushed back to S3. This keeps the shared database in sync without every PR triggering a write.

---

## Required Secrets

Add these to your GitHub repository's Settings → Secrets and variables → Actions:

### For S3

```
AWS_ACCESS_KEY_ID          Your AWS access key
AWS_SECRET_ACCESS_KEY      Your AWS secret key
```

### For GCS

```
GOOGLE_APPLICATION_CREDENTIALS    Base64-encoded service account JSON
```

Usage in workflow:
```yaml
- name: Restore prompt database
  run: |
    echo "$GOOGLE_APPLICATION_CREDENTIALS" | base64 --decode > /tmp/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
    pv pull-remote origin
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GCP_SA_KEY_B64 }}
```

### For Eval with OpenAI

```
OPENAI_API_KEY             sk-...
ANTHROPIC_API_KEY          sk-ant-...   (if using Anthropic)
```

---

## Multi-Environment Setup

Use different remotes for different environments:

```yaml
# On PRs: pull from staging remote
- name: Restore staging database
  if: github.event_name == 'pull_request'
  run: pv pull-remote staging

# On main merge: pull from and push to production remote
- name: Restore production database
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: pv pull-remote origin
```

Register multiple remotes:

```bash
pv remote add origin  s3://my-company/prompts/production/
pv remote add staging s3://my-company/prompts/staging/
```

---

## Using Ollama in CI to Avoid API Costs

For eval runs that don't need top-tier quality, use Ollama in CI to avoid OpenAI costs:

```yaml
- name: Start Ollama
  run: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    sleep 5
    ollama pull phi3

- name: Run eval regression (free with Ollama)
  run: pv eval run my_prompt --dataset evals/cases.jsonl --provider ollama --model phi3
```

!!! note "CI Performance"
    Ollama on standard GitHub Actions runners (2 vCPU, 7GB RAM) is slow without a GPU. For large eval datasets, use a cloud provider or a GPU-enabled self-hosted runner.

---

## Parallel Eval Matrix

Test multiple prompt versions in parallel:

```yaml
strategy:
  matrix:
    prompt: [support_agent, code_reviewer, summarizer]

steps:
  - name: Run eval for ${{ matrix.prompt }}
    run: pv eval run ${{ matrix.prompt }} --dataset evals/${{ matrix.prompt }}_cases.jsonl --provider openai
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## See Also

- [Team Workflow](team-workflow.md)
- [pv hooks & cicd](../cli/hooks-cicd.md)
- [Remote Backends](../integrations/remote-backends.md)
