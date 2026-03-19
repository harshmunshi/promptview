# Team Workflow

This guide describes how a team of engineers can collaborate on prompts using PromptView as the shared source of truth.

---

## Architecture

```
Engineer A                    S3 Remote                   Engineer B
─────────────────────         ──────────────────          ─────────────────────
.promptview/                  s3://bucket/prompts/        .promptview/
  promptview.db    ──push──►  promptview.db    ◄──pull──    promptview.db
```

One S3 bucket (or GCS bucket, or HTTP server) holds the shared `promptview.db`. All team members push their changes and pull others' changes.

---

## Initial Setup (One Person, Once)

The first person on the team:

```bash
# 1. Initialize in the project repo
cd my-ai-project
pv init --author "Alice Smith"

# 2. Scan and capture all prompts
pv scan
pv add .
pv commit -m "Initial prompt capture"

# 3. Register the remote
pv remote add origin s3://my-company/ai-project/prompts/

# 4. Push to shared storage
pv push-remote origin

# 5. Commit the remote configuration to git
git add .promptview/config.toml
git commit -m "Add PromptView remote config"
git push
```

---

## Onboarding New Team Members

Each new team member:

```bash
# 1. Clone the repo (config.toml is already there)
git clone https://github.com/my-company/ai-project.git
cd ai-project

# 2. Install PromptView
pip install "promptview[s3]"

# 3. Initialize (creates .promptview/ structure)
pv init --no-scan

# 4. Pull the shared DB
pv pull-remote origin

# 5. Start the UI
pv ui
```

They now have the full prompt history, all committed versions, eval results, and component data.

---

## Daily Development Workflow

### Making Changes

```bash
# 1. Pull latest from shared storage
pv pull-remote origin

# 2. Work on your AI code — modify prompts in source files

# 3. Scan for changes
pv scan

# 4. Review what changed
pv status
pv diff system_prompt

# 5. Stage and commit
pv add .
pv commit -m "Add escalation path to support agent"

# 6. Push to shared storage
pv push-remote origin
```

### Using the Visual Editor

```bash
# 1. Pull latest
pv pull-remote origin

# 2. Open editor
pv ui

# 3. Edit prompts via the component graph

# 4. When done, push
pv push-remote origin
```

---

## Branch-Per-Feature Workflow

For large prompt changes, use prompt branches to isolate experiments:

```bash
# Create a feature branch
pv branch create feature/improve-code-reviewer-tone

# Work on prompts
pv ui
# ... edit and iterate ...

# Commit changes on the branch
pv add .
pv commit -m "Softer tone with actionable feedback"

# When ready, push to shared storage
pv push-remote origin

# Team members can pull and review
pv pull-remote origin
pv log code_reviewer   # see commits on this branch
```

!!! note "Branch Merging"
    `pv merge` is not yet implemented. For now, share branch changes by using `pv push-remote` and coordinating via your normal code review process.

---

## Using with Git

PromptView works alongside git — it is not a replacement.

### Option 1: `.promptview/` in `.gitignore` (Recommended for Teams)

Use S3/GCS as the shared store and keep `.promptview/` out of git:

```gitignore
# .gitignore
.promptview/
```

This keeps the git repo clean and avoids merge conflicts on the binary SQLite file.

### Option 2: Commit `.promptview/` to Git

For small solo projects or when you want git to be the sharing mechanism:

```gitignore
# .gitignore — intentionally NOT ignoring .promptview/
# (only exclude large binary files if any)
```

Team members get the prompt history with `git pull`. No separate S3 setup needed.

!!! warning "SQLite and Git Merges"
    SQLite is a binary file. Git cannot merge two versions of it — you'll get binary merge conflicts. Only use Option 2 if one person works on prompts at a time.

---

## Preventing Drift: Git Pre-Commit Hook

Install the pre-commit hook to prevent untracked prompts from reaching main:

```bash
# Each developer runs this once
pv hooks install
```

Now if a developer adds a new LLM call with an untracked prompt and tries to `git commit`, the commit is blocked:

```
Running PromptView pre-commit check...

Untracked prompts found:
  ? new_agent_prompt   src/new_agent.py:42

Run 'pv add .' and 'pv commit -m ...' to track them.

Commit blocked.
```

---

## Code Review Checklist

When reviewing PRs that modify LLM calls:

- [ ] `pv scan` finds no new untracked prompts (`pv scan --fail-on-untracked`)
- [ ] The prompt diff looks intentional (`pv diff` or `pv status`)
- [ ] Eval pass rate is maintained or improved (check metrics table)
- [ ] Commit message describes why the prompt changed

---

## Preventing Eval Regressions in CI

Add an eval step to your CI pipeline that fails if quality drops below a threshold:

```yaml
# .github/workflows/ci.yml
- name: Run eval regression
  run: |
    pv eval run my_prompt --dataset evals/regression.jsonl --provider openai
    # Check that pass rate is still >= 70%
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

Use `pv metrics show my_prompt` output to monitor trends over time.

---

## See Also

- [CI/CD Integration](ci-cd.md)
- [Remote Backends](../integrations/remote-backends.md)
- [pv hooks & cicd](../cli/hooks-cicd.md)
