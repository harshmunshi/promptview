# Prompt Composition

Prompt composition lets you embed one prompt inside another using `{{ include: prompt_name }}` directives. This enables reusable building blocks — write shared instructions once and include them in many prompts.

---

## The `{{ include: }}` Syntax

```
{{ include: prompt_name }}
```

At render time, this directive is replaced with the latest `raw_content` of the named prompt.

Whitespace inside the braces is flexible:

```
{{ include: base_instructions }}          ← standard
{{include:base_instructions}}             ← also valid
{{ include :  base_instructions  }}       ← also valid (extra spaces OK)
```

---

## Basic Example

**`base_instructions` prompt:**
```
Always be polite and professional.
Respond in the user's language.
Keep responses concise — under 3 sentences unless complexity requires more.
```

**`support_agent` prompt:**
```
You are a customer support agent for {company_name}.

{{ include: base_instructions }}

Help {user_name} with: {task}
```

After resolution, `support_agent` renders as:

```
You are a customer support agent for AcmeCorp.

Always be polite and professional.
Respond in the user's language.
Keep responses concise — under 3 sentences unless complexity requires more.

Help Alice with: billing question
```

---

## Resolution Order

The full render pipeline runs in this order:

1. **Resolve includes** — replace `{{ include: name }}` with referenced content
2. **Substitute variables** — replace `{slot}` with provided values or defaults

This means the included content is rendered *before* variable substitution. Variables in the included prompt content are also substituted.

**Example:**

`base_instructions` content:
```
Always respond in {language}.
Be concise and helpful.
```

`support_agent` content:
```
You are an agent for {company_name}.
{{ include: base_instructions }}
Help {user} with: {task}
```

After `pv run support_agent -v company_name=AcmeCorp -v language=English -v user=Alice -v task="reset password"`:

```
You are an agent for AcmeCorp.
Always respond in English.
Be concise and helpful.
Help Alice with: reset password
```

The `{language}` variable from `base_instructions` is substituted with the value passed to `pv run`.

---

## Nested Includes

Included prompts can themselves include other prompts:

```
base_tone (prompt)
└── "Be polite and concise."

base_instructions (prompt)
└── "Always follow company policy. {{ include: base_tone }}"
    (resolves to: "Always follow company policy. Be polite and concise.")

support_agent (prompt)
└── "You are an agent. {{ include: base_instructions }} Help {user}."
    (resolves to: "You are an agent. Always follow company policy. Be polite and concise. Help {user}.")
```

Nesting is supported to arbitrary depth. PromptView resolves from the inside out.

!!! warning "Circular Includes"
    Circular references (`A includes B which includes A`) will cause infinite recursion. PromptView does not currently detect and break cycles — avoid circular includes.

---

## Use Cases

### Shared Safety/Guardrail Instructions

```
{{ include: safety_guidelines }}

Now help the user with: {task}
```

One `safety_guidelines` prompt updated centrally — all prompts that include it update automatically on next render.

### Role + Task Separation

```
{{ include: senior_engineer_persona }}

Your task today: {task_description}
Output format: {{ include: json_output_format }}
```

### Multi-Environment Configuration

```
You are an assistant.
{{ include: production_constraints }}
{{ include: output_schema }}
Help {user} with: {request}
```

For testing, switch `production_constraints` content to a relaxed version.

### Shared Output Formats

```
{{ include: json_schema_v2 }}
```

Update the JSON schema once; all 20 prompts that include it get the update.

---

## How Resolution Works in Code

```python
from promptview.template import resolve_includes, render_full

# Build a lookup from prompt name → raw content
lookup = {
    "base_instructions": "Always be helpful. Respond in {language}.",
    "base_tone": "Be concise and friendly.",
}

# Source prompt
text = """
You are an assistant for {company}.
{{ include: base_instructions }}
Help {user} with: {task}
"""

# Step 1: resolve includes
after_includes = resolve_includes(text, lookup)
# → "You are an assistant for {company}.\nAlways be helpful. Respond in {language}.\nHelp {user} with: {task}"

# Step 2: substitute variables
result = render_full(text,
    variables={"company": "AcmeCorp", "language": "English", "user": "Alice", "task": "help"},
    prompt_lookup=lookup
)
```

`render_full()` combines both steps in one call.

---

## Unresolved Includes

If a referenced prompt does not exist in the lookup, the include directive is left as-is in the output:

```
{{ include: nonexistent_prompt }}
```

This lets you safely add include directives to a prompt before the referenced prompt has been created.

---

## `pv run` and Includes

`pv run` automatically resolves includes using all tracked prompts in the repository as the lookup:

```bash
pv run support_agent -v user=Alice -v task="billing question" -v company_name=AcmeCorp
```

The `base_instructions` prompt (and any prompts it includes) are fetched from the database and embedded before variable substitution.

---

## Variables Panel and Includes

The Variables panel in the UI shows variables from the *resolved* content — meaning variables defined in included prompts also appear. After syncing variables for a prompt that includes `base_instructions` (which has `{language}`), you'll see `language` in the variables table.

---

## See Also

- [Template Variables](variables.md) — `{slot}` variable system
- [pv vars & run CLI](../cli/vars-run.md)
- [Variables Panel](../ui/variables-panel.md)
