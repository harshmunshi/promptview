# pv init

Initialize a PromptView repository in your project.

---

## Synopsis

```bash
pv init [PATH] [OPTIONS]
```

---

## Description

`pv init` creates the `.promptview/` directory inside your project and sets up all the scaffolding needed for prompt versioning. It is the first command you run in a new project — analogous to `git init`.

By default it also runs `pv scan` automatically after initialization so you immediately see what prompts are available.

---

## Arguments

| Argument | Description | Default |
|---|---|---|
| `PATH` | Directory to initialize | Current directory (`.`) |

---

## Options

| Option | Description |
|---|---|
| `--author TEXT` | Your name — used for commit attribution. Saved to config. |
| `--force` | Re-initialize even if `.promptview/` already exists. Preserves existing data. |
| `--no-scan` | Skip the automatic post-init scan. |

---

## Examples

```bash
# Initialize in current directory
pv init

# Initialize in a specific directory
pv init /path/to/my-ai-project

# Set author at init time
pv init --author "Alice Smith"

# Re-initialize without losing data
pv init --force

# Skip the auto-scan (useful in CI where you want explicit control)
pv init --no-scan
```

---

## What It Creates

```
.promptview/
├── promptview.db    # SQLite database — all prompts, versions, commits, evals
├── config.toml      # project configuration
├── HEAD             # current branch (default: "main")
├── index.json       # staging area (initially empty)
├── objects/         # content-addressed storage for large objects
├── refs/            # branch and tag references
│   ├── heads/
│   │   └── main     # pointer to latest commit on main
│   └── tags/
└── logs/            # per-prompt append-only commit logs
```

### `config.toml`

After `pv init --author "Alice"`, the config file looks like:

```toml
[project]
author = "Alice"
version = "0.1.0"

[llm]
provider = ""
api_key = ""
model = ""

[remotes]
# Add remotes with: pv remote add origin s3://bucket/path/
```

### `promptview.db`

The SQLite database is created with all 9 tables on first connection:
- `prompts`
- `prompt_versions`
- `commits`
- `prompt_components`
- `prompt_variables`
- `remotes`
- `eval_runs`
- `eval_results`
- `test_cases`

All tables are created with `CREATE TABLE IF NOT EXISTS` so re-initializing with `--force` never loses data.

---

## `.gitignore` Recommendation

Add `.promptview/` to your `.gitignore` if you are using a remote backend for sharing, or **do not** add it if you want to commit the DB to your repo directly. Both approaches work.

For remote-backend teams:

```gitignore
# .gitignore
.promptview/
```

For small solo projects where git is the sharing mechanism:

```gitignore
# .gitignore — intentionally NOT ignoring .promptview/
.promptview/*.log    # optional: exclude logs but keep the DB
```

---

## Already Initialized?

```bash
pv init
# Error: .promptview/ already exists. Use --force to re-initialize.

pv init --force
# Re-initialized PromptView repository in /my-project/.promptview/
```

---

## After Init

```bash
pv scan        # find prompts in the codebase
pv status      # see what was found
pv add .       # stage all found prompts
pv commit -m "Initial capture"
```

---

## See Also

- [Quick Start](../getting-started/quick-start.md)
- [pv scan](scan.md)
- [pv config](../cli/overview.md)
