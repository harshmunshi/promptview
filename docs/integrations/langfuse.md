# Langfuse Integration

PromptView integrates with [Langfuse](https://langfuse.com/) for two-way prompt synchronization. Use PromptView as the version control and visual editing layer, and Langfuse as the runtime serving and observability layer.

---

## Installation

```bash
pip install "promptview[langfuse]"
```

---

## Configuration

### Via CLI

```bash
pv config langfuse.public_key pk-lf-abc123...
pv config langfuse.secret_key sk-lf-xyz789...

# Optional: self-hosted Langfuse instance
pv config langfuse.host https://langfuse.my-company.com
```

### Via Environment Variables

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-abc123..."
export LANGFUSE_SECRET_KEY="sk-lf-xyz789..."
export LANGFUSE_HOST="https://cloud.langfuse.com"   # default
```

### Where to Find Keys

Log into [cloud.langfuse.com](https://cloud.langfuse.com) → Settings → API Keys → Create new key pair. The public key starts with `pk-lf-` and the secret key with `sk-lf-`.

---

## Commands

### Push to Langfuse

```bash
pv push langfuse
```

Pushes all committed prompt versions from the local database to Langfuse.

**What gets pushed:**
- Each `Prompt` (by name) is created or updated in Langfuse
- Each `PromptVersion.raw_content` is pushed as a new version in Langfuse
- Version metadata (number, commit message) is included as labels

### Pull from Langfuse

```bash
pv pull langfuse
```

Pulls prompt versions from Langfuse into the local PromptView database.

**What gets pulled:**
- Each Langfuse prompt is fetched by name
- Prompts not in the local DB are created with `source=MANUAL`
- Prompts that exist locally get new versions if the content differs
- Existing local versions are not modified

### Two-Way Sync

```bash
pv sync langfuse
```

Runs `pv push langfuse` then `pv pull langfuse` — a full two-way sync. Use this as a daily or pre-deployment operation.

---

## Typical Workflow

```bash
# Initial setup — push existing prompts to Langfuse
pv push langfuse

# Daily development
pv scan
pv add .
pv commit -m "Improve tone in support agent"
pv sync langfuse      # push changes, pull any remote edits

# Before deployment — verify prompts are synced
pv sync langfuse
pv scan --fail-on-untracked
```

---

## What Gets Synced

| PromptView Data | Langfuse Data |
|---|---|
| `Prompt.name` | Prompt name |
| `PromptVersion.raw_content` | Prompt version text |
| `Commit.message` | Version label |
| `PromptVersion.version_number` | Version number |

Eval runs, components, and variables are not synced to Langfuse — they are PromptView-specific.

---

## Using Langfuse in Production

After pushing, use the Langfuse Python SDK to fetch prompts at runtime:

```python
from langfuse import Langfuse

langfuse = Langfuse()

# Fetch the latest version of a prompt
prompt = langfuse.get_prompt("support_agent")
system_message = prompt.compile(company_name="AcmeCorp", user_name="Alice")
```

PromptView handles version control and editing. Langfuse handles runtime serving and usage tracking.

---

## Self-Hosted Langfuse

For teams running their own Langfuse instance:

```bash
pv config langfuse.host https://langfuse.internal.my-company.com
```

All API calls go to your self-hosted instance instead of `cloud.langfuse.com`.

---

## See Also

- [pv push / pull / sync CLI](../cli/integrations.md)
- [LangSmith Integration](langsmith.md)
- [Team Workflow](../advanced/team-workflow.md)
