# CLI Reference Overview

PromptView registers two identical CLI entry points: `pv` and `promptview`. All documentation uses `pv` — the shorter alias.

---

## Getting Help

```bash
pv --help                  # list all commands
pv <command> --help        # help for a specific command
pv <group> <subcommand> --help   # help for a subcommand
```

---

## All Commands

| Command | Description | Key Flags |
|---|---|---|
| `pv init [PATH]` | Initialize `.promptview/` repository | `--author`, `--force`, `--no-scan` |
| `pv scan [PATH]` | AST-scan for prompts in codebase | `--min-confidence`, `--show-all` |
| `pv add [NAME\|.]` | Stage prompts for next commit | `--file`, `--min-confidence`, `--unstage` |
| `pv commit` | Commit staged prompts | `-m "message"` |
| `pv status` | Show staged / modified / untracked | — |
| `pv diff [NAME] [V1] [V2]` | Unified diff between versions | `--staged` |
| `pv log [NAME]` | Commit history | `--oneline`, `-n N` |
| `pv ui` | Launch web UI | `--port`, `--host`, `--no-browser` |
| `pv config [KEY] [VALUE]` | Read or write config | `--show` |
| `pv branch create NAME` | Create a new prompt branch | — |
| `pv branch list` | List all branches | — |
| `pv branch delete NAME` | Delete a branch | — |
| `pv remote add NAME URL` | Register a named remote backend | — |
| `pv remote list` | List all named remotes | — |
| `pv remote remove NAME` | Remove a named remote | — |
| `pv push-remote NAME\|URL` | Push DB to remote backend | — |
| `pv pull-remote NAME\|URL` | Pull DB from remote backend | — |
| `pv push TARGET` | Push to Langfuse or LangSmith | — |
| `pv pull TARGET` | Pull from Langfuse or LangSmith | — |
| `pv sync TARGET` | Push + pull in one step | — |
| `pv vars sync NAME` | Auto-detect `{slots}` from latest version | — |
| `pv vars show NAME` | List variables with defaults | — |
| `pv vars set NAME VAR VALUE` | Set a variable default | `--desc` |
| `pv run NAME` | Render prompt with variable substitution | `--var`, `--call`, `--provider`, `--api-key`, `--model` |
| `pv eval run NAME` | Run eval suite against a prompt version | `--dataset`, `--scorer`, `--provider`, `--version` |
| `pv metrics show NAME` | Show eval metrics history | `--last`, `--version`, `--plot` |
| `pv metrics compare V1 V2` | Compare two eval runs side-by-side | `--prompt` |
| `pv metrics results RUN_ID` | Show per-case inputs and responses | `--prompt`, `--failed` |
| `pv hooks install` | Install git pre-commit hook | — |
| `pv hooks uninstall` | Remove git pre-commit hook | — |
| `pv hooks status` | Check hook installation status | — |
| `pv cicd generate` | Generate GitHub Actions workflow YAML | `--output` |
| `pv version` | Show installed version | — |

---

## Command Groups

Commands are organized into logical groups:

### Repository Commands
Core git-like workflow: `init`, `scan`, `add`, `commit`, `status`, `diff`, `log`

### UI
`ui` — launches the visual editor web server

### Configuration
`config` — read and write project configuration

### Branching
`branch create/list/delete` — manage prompt branches

### Remote Backends
`remote add/list/remove`, `push-remote`, `pull-remote` — S3/GCS/HTTP sharing

### External Integrations
`push`, `pull`, `sync` — Langfuse and LangSmith

### Template Variables
`vars sync/show/set`, `run` — variable management and prompt rendering

### Evaluations
`eval run`, `metrics show/compare/results` — testing and quality tracking

### CI/CD
`hooks install/uninstall/status`, `cicd generate` — automation

---

## `pv` vs `promptview`

Both names are registered as entry points in `pyproject.toml`:

```toml
[project.scripts]
promptview = "promptview.cli.main:app"
pv         = "promptview.cli.main:app"
```

They are completely identical. Use whichever you prefer — the documentation always uses `pv`.

---

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Error (repository not initialized, prompt not found, etc.) |
| 2 | Usage error (wrong flags, missing arguments) |

---

## Shell Completion

Typer supports tab completion for all major shells:

```bash
# bash
pv --install-completion bash

# zsh
pv --install-completion zsh

# fish
pv --install-completion fish
```

After installing, restart your shell and tab-complete `pv <TAB>` to see all commands.

---

## Detailed References

- [pv init](init.md)
- [pv scan](scan.md)
- [pv add & commit](add-commit.md)
- [pv status, diff & log](status-diff-log.md)
- [pv ui](ui.md)
- [pv vars & run](vars-run.md)
- [pv eval & metrics](eval-metrics.md)
- [pv remote backends](remote-backends.md)
- [pv integrations](integrations.md)
- [pv hooks & cicd](hooks-cicd.md)
