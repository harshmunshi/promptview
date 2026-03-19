# pv vars & pv run

Manage template variables in prompts and render them with variable substitution.

---

## pv vars

### Synopsis

```bash
pv vars sync NAME
pv vars show NAME
pv vars set NAME VARIABLE VALUE [OPTIONS]
```

### Description

`pv vars` manages the `{slot}` placeholders found in prompt content. Variables let you reuse a single prompt template with different inputs — like parameterised functions for prompts.

---

### pv vars sync

Scan the latest version of a prompt and automatically register any `{slot}` names that are not yet tracked.

```bash
pv vars sync my_prompt
```

**What it does:**
1. Fetches the latest `raw_content` for the prompt
2. Runs `extract_variables(content)` — finds all `{slot}` names
3. For each new slot: creates a `PromptVariable` record with an empty default
4. Existing variables are **never overwritten** — only new ones are added

**Example:**

Prompt content:
```
You are an assistant for {company_name}.
Help {user_name} complete: {task}
Your response language should be {language}.
```

After `pv vars sync my_prompt`:
```
Synced 4 variables for 'my_prompt':
  + company_name   (no default)
  + user_name      (no default)
  + task           (no default)
  + language       (no default)
```

---

### pv vars show

List all tracked variables for a prompt with their current defaults and descriptions.

```bash
pv vars show my_prompt
```

Output:
```
Variables for 'my_prompt':

  Name           Default          Description
  ─────────────────────────────────────────────
  company_name   AcmeCorp         Customer company name
  user_name      (empty)          The user's first name
  task           (empty)          The task or question
  language       English          Response language
```

---

### pv vars set

Set or update the default value and description for a variable.

```bash
pv vars set my_prompt company_name "AcmeCorp"
pv vars set my_prompt language "English" --desc "Language for the response"
```

**Options:**

| Option | Description |
|---|---|
| `--desc TEXT` | Human-readable description of the variable |

---

## pv run

### Synopsis

```bash
pv run NAME [OPTIONS]
```

### Description

`pv run` renders a prompt by substituting variable defaults (or overrides) into its template. Optionally, with `--call`, it sends the rendered prompt to an LLM and prints the response.

### Options

| Option | Description |
|---|---|
| `-v, --var KEY=VALUE` | Override a variable (can be used multiple times) |
| `--call` | Send rendered prompt to the configured LLM |
| `--provider TEXT` | LLM provider: `openai`, `anthropic`, `gemini`, `ollama` |
| `--api-key TEXT` | API key (falls back to env var) |
| `--model TEXT` | Override default model |
| `--version INTEGER` | Use a specific version number (default: latest) |

### Examples

```bash
# Render using stored defaults
pv run my_prompt

# Override one variable inline
pv run my_prompt --var user_name=Alice

# Override multiple variables
pv run my_prompt -v user_name=Alice -v language=French

# Render and call the LLM
pv run my_prompt -v user_name=Alice --call

# Use a specific provider and model
pv run my_prompt --call --provider anthropic --model claude-3-5-sonnet-20241022

# Use Ollama (local, no API key)
pv run my_prompt --call --provider ollama --model llama3

# Run a specific version
pv run my_prompt --version 2 -v user_name=Bob
```

### Environment Variables

When `--api-key` is not provided, `pv run` falls back through these environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
```

Ollama requires no API key.

---

## The `{{ include: }}` Directive

In addition to `{variable}` slots, prompt content can include other prompts by reference:

```
You are an assistant for {company_name}.

{{ include: base_instructions }}

Now help {user_name} with: {task}
```

When `pv run` renders this prompt, `{{ include: base_instructions }}` is replaced with the latest `raw_content` of the `base_instructions` prompt — before variable substitution.

**Resolution order:**
1. Resolve `{{ include: ... }}` directives — fetch referenced prompt content
2. Substitute `{variable}` slots with provided values or stored defaults

**Example:**

`base_instructions` prompt content:
```
Always be polite and professional.
Respond in {language}.
```

`my_prompt` content:
```
You are a support agent for {company_name}.
{{ include: base_instructions }}
Help {user} with: {task}
```

After `pv run my_prompt --var company_name=AcmeCorp --var language=English --var user=Alice --var task="billing question"`:

```
You are a support agent for AcmeCorp.
Always be polite and professional.
Respond in English.
Help Alice with: billing question
```

Nested includes are supported — `base_instructions` can itself include another prompt.

---

## The Full Render Pipeline

```
raw_content of latest version
  │
  ▼
resolve_includes()     ← expand {{ include: name }} directives
  │
  ▼
render()               ← substitute {variable} values from:
  │                       1. --var overrides (highest priority)
  │                       2. stored defaults (pv vars set)
  ▼
final rendered text

Optional: --call → LLMClient.complete(system=rendered_text, user=input)
```

---

## API: Variables Endpoints

These same operations are available via the REST API when the UI is running:

```
GET    /api/prompts/{id}/variables
       → list variables and defaults

POST   /api/prompts/{id}/variables/sync
       → auto-detect from latest content

PUT    /api/prompts/{id}/variables/{vid}
       → update default_value or description
```

---

## See Also

- [Template Variables](../template-system/variables.md) — in-depth variable documentation
- [Prompt Composition](../template-system/composition.md) — `{{ include }}` in depth
- [LLM Providers](../llm/providers.md) — configure providers for `--call`
