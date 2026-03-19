# Component Graph

The component graph is the central feature of PromptView's visual editor. It breaks a monolithic prompt string into labeled structural nodes and lets you edit each one independently — with changes surgically reflected back into the original prompt.

---

## What Decomposition Does

A raw prompt like:

```
You are a senior software engineer with 15 years of experience.
You specialize in Python and distributed systems.

Review the following code carefully. Look for:
- Security vulnerabilities
- Performance bottlenecks
- Code style issues

Respond with a JSON object containing:
{
  "issues": [{"severity": "high|medium|low", "description": "...", "line": N}],
  "summary": "one-sentence overall assessment"
}

Be direct and specific. Do not add praise or filler text.
```

Gets decomposed into:

| Position | Label | Content |
|---|---|---|
| 1 | Role | `You are a senior software engineer with 15 years of experience. You specialize in Python and distributed systems.` |
| 2 | Instructions | `Review the following code carefully. Look for: - Security vulnerabilities - Performance bottlenecks - Code style issues` |
| 3 | Output Format | `Respond with a JSON object containing: {"issues": [...], "summary": "..."}` |
| 4 | Constraints | `Be direct and specific. Do not add praise or filler text.` |

These become nodes in the D3 graph — a vertical linear stack with arrows connecting them.

---

## How the LLM Decompose Prompt Works

The decomposer sends the raw prompt to the configured LLM with a structured request:

**System prompt** (to the LLM):
```
You are an expert at analyzing LLM system prompts and identifying their structural components.
Given a prompt, identify its distinct sections and label each one.
Common labels: Role, Context, Instructions, Output Format, Examples, Constraints, Persona.
Return a JSON array: [{"label": "Role", "content": "..."}, ...]
Each component must contain the verbatim text from the original prompt.
All text from the original must be accounted for — no content should be lost.
```

**User message** (to the LLM):
```
Decompose this prompt into its structural components:

<prompt>
[raw prompt text]
</prompt>
```

The response is parsed as JSON and stored as `PromptComponent` rows with position indices.

---

## Surgical Regeneration

When you edit a component, PromptView does **not** ask the LLM to rewrite the entire prompt from scratch. Instead it uses a surgical strategy:

**The LLM receives:**
1. The original prompt text (unchanged)
2. The full list of old components
3. The full list of new components (with your changes highlighted)

**The regeneration system prompt:**
```
You are an expert at editing LLM prompts. You will be given:
1. The original prompt
2. The old component list
3. The new component list (with changes)

Your task: produce an updated version of the original prompt that incorporates
ONLY the changed components. Preserve the original tone, style, whitespace,
and all unchanged text exactly. Do not paraphrase or reformat unchanged sections.
```

**Result:** only the changed section is rewritten. Everything else stays word-for-word identical to the original.

---

## Why Surgical?

Consider editing the "Instructions" component from:
```
Review the code for security issues.
```
to:
```
Review the code for security issues, performance bottlenecks, and code readability.
```

A naive "rewrite the whole prompt" approach would:
- Change unrelated sections
- Alter your carefully tuned tone
- Lose specific formatting choices
- Make it hard to diff what actually changed

The surgical approach changes exactly one sentence. The rest of the prompt is preserved character-for-character.

---

## Adding a New Component

Click the `+` button between any two nodes in the graph:

1. A new component form appears
2. Enter a label and content, or let the LLM suggest content
3. Click Save
4. The regeneration LLM inserts the new section into the appropriate place in the prompt
5. A new `PromptVersion` is created

The LLM is given context about where the new node falls in the sequence (after "Role", before "Instructions") so it can insert the content in the right place.

---

## Deleting a Component

Click the `×` button on any node:

1. The component is removed from the list
2. The regeneration LLM rewrites the prompt without that section
3. Surrounding sections are smoothly joined — no abrupt gaps
4. A new `PromptVersion` is created

---

## Storage Model

Components are stored per `(prompt_id, version_id)` pair:

```sql
CREATE TABLE prompt_components (
    id          TEXT PRIMARY KEY,
    prompt_id   TEXT NOT NULL,
    version_id  TEXT NOT NULL,
    label       TEXT NOT NULL,
    content     TEXT NOT NULL,
    position    INTEGER NOT NULL
);
```

When you switch versions in the UI, the frontend calls:
```
GET /api/prompts/{id}/components?version_id=<uuid>
```

This returns the components for that specific historical version — perfect for seeing what the "Instructions" section looked like in v2 vs. v5.

---

## Component Labels

PromptView does not enforce a fixed set of labels. The LLM is encouraged to use common ones but can create custom labels when appropriate:

**Common labels:**
- `Role` — the persona the LLM should adopt
- `Context` — background information
- `Instructions` — the main task
- `Output Format` — how to structure the response
- `Examples` — few-shot examples
- `Constraints` — rules to follow or avoid
- `Persona` — detailed character description
- `Chain of Thought` — reasoning instructions

**Custom labels** are perfectly valid — use whatever makes sense for your domain.

---

## Footer: Reconstructed Prompt

The collapsible footer in the UI always shows the current reconstructed full prompt text. This is the `raw_content` of the current version — the actual string that gets sent to the LLM in production.

Edits in the component graph are only "real" once they are regenerated and saved as a new version. The footer shows the ground truth.

---

## Example: Before and After

**Original prompt (v2):**
```
You are a helpful customer support agent for AcmeCorp.
Answer customer questions about our software products.
Always be polite and professional.
If you don't know the answer, say so and offer to escalate.
```

**After editing "Instructions" to add escalation path:**
```
You are a helpful customer support agent for AcmeCorp.
Answer customer questions about our software products. When answering,
check against the knowledge base first. For billing questions, route to
the billing team by saying "I'll connect you with our billing team."
Always be polite and professional.
If you don't know the answer, say so and offer to escalate.
```

The surgical regeneration changed only the "Instructions" section. The "Role", "Persona", and "Constraints" components are byte-for-byte identical.

---

## Next Steps

- [Component Graph Editor](../ui/component-graph.md) — how to use it in the web UI
- [Decompose & Regenerate](../llm/decompose-regenerate.md) — the LLM strategy in depth
- [Version Switcher](../ui/version-switcher.md) — how to compare versions
