# Template Variables

Template variables let you parameterize prompts with `{slot}` placeholders — making a single prompt reusable across different contexts, users, and environments.

---

## The `{slot}` Syntax

A variable is any `{name}` surrounded by single curly braces where `name` is a valid Python identifier (letters, numbers, underscores, starting with a letter or underscore):

```
You are an assistant for {company_name}.
Help {user_name} with: {task}
Respond in {language}.
```

This prompt has four variables: `company_name`, `user_name`, `task`, and `language`.

### What Is NOT a Variable

Double curly braces `{{ }}` are reserved for include directives, not variables:

```
{{ include: base_instructions }}   ← NOT a variable — this is a composition directive
{user_name}                        ← YES — this is a variable
```

PromptView's `extract_variables()` function strips include directives before scanning for variable names, so include placeholders never show up as variables.

---

## Auto-Detecting Variables

### Via CLI

```bash
pv vars sync my_prompt
```

Scans the latest version's `raw_content`, finds all `{slot}` names, and creates `PromptVariable` records for any that aren't already tracked. Existing defaults are never overwritten.

### Via UI

Click **Sync Variables** in the Variables panel. The UI calls `POST /api/prompts/{id}/variables/sync`.

### Automatic Sync After Decompose

After decomposing or editing a prompt in the UI, variable sync runs automatically. If your edit introduced a new `{slot}` name, it appears in the Variables panel immediately.

---

## Viewing Variables

```bash
pv vars show my_prompt
```

Output:
```
Variables for 'my_prompt':

  Name           Default          Description
  ─────────────────────────────────────────────────────────────
  company_name   AcmeCorp         Customer company name
  user_name      (empty)          -
  task           (empty)          -
  language       English          Response language
```

---

## Setting Defaults

```bash
# Set a default value
pv vars set my_prompt company_name "AcmeCorp"

# Set a default with a description
pv vars set my_prompt language "English" --desc "Language for the response"

# Clear a default (set to empty string)
pv vars set my_prompt user_name ""
```

Defaults are stored in the `prompt_variables` table and used by `pv run` when no override is provided.

---

## Rendering with Variables

### Using Stored Defaults

```bash
pv run my_prompt
```

Output:
```
You are an assistant for AcmeCorp.
Help  with:
Respond in English.
```

(Empty slots are left as-is in the output — they are not errors.)

### Overriding at Runtime

```bash
pv run my_prompt --var user_name=Alice --var task="billing question"
```

Output:
```
You are an assistant for AcmeCorp.
Help Alice with: billing question
Respond in English.
```

### Multiple Overrides (short form)

```bash
pv run my_prompt -v user_name=Alice -v task="reset password" -v language=French
```

### Calling the LLM with Rendered Prompt

```bash
pv run my_prompt -v user_name=Alice -v task="reset password" --call --provider openai
```

The rendered prompt is sent as the system message. The user message is empty by default.

---

## Variables in the Render Pipeline

```python
from promptview.template import extract_variables, render

text = """
You are an assistant for {company_name}.
Help {user_name} with: {task}
Respond in {language}.
"""

# Auto-detect variable names
vars_found = extract_variables(text)
# → ['company_name', 'language', 'task', 'user_name']

# Render with substitution
result = render(text, {
    "company_name": "AcmeCorp",
    "user_name": "Alice",
    "task": "billing question",
    "language": "English"
})
```

Missing variables (not in the dict) are left as-is — they are not errors.

---

## Variables API

When `pv ui` is running:

```bash
# List all variables and defaults
curl http://localhost:8765/api/prompts/{id}/variables

# Sync (auto-detect from latest content)
curl -X POST http://localhost:8765/api/prompts/{id}/variables/sync

# Update a default value
curl -X PUT http://localhost:8765/api/prompts/{id}/variables/{vid} \
  -H "Content-Type: application/json" \
  -d '{"default_value": "AcmeCorp", "description": "Company name"}'
```

---

## Best Practices

### Name Variables Clearly

```
{user_name}         ✓ clear
{lang}              ✓ acceptable abbreviation
{x}                 ✗ too cryptic
{the_user_s_name}   ✗ unnecessarily verbose
```

### Always Set Defaults for Non-Optional Slots

If a slot has no reasonable universal default, document it:

```bash
pv vars set my_prompt user_name "" --desc "Required: the user's first name"
```

### Use Descriptions for Non-Obvious Variables

```bash
pv vars set my_prompt context "" --desc "Background context from RAG retrieval — max 500 tokens"
pv vars set my_prompt format "bullet_list" --desc "Output format: bullet_list, numbered_list, or paragraph"
```

---

## See Also

- [Prompt Composition](composition.md) — `{{ include }}` for embedding other prompts
- [pv vars & run CLI](../cli/vars-run.md) — CLI reference
- [Variables Panel](../ui/variables-panel.md) — UI guide
