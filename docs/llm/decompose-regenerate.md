# Decompose & Regenerate

The two LLM-powered operations at the heart of the PromptView visual editor.

---

## Overview

PromptView uses LLMs for exactly two tasks:

1. **Decompose** — break a raw prompt string into labeled structural components
2. **Regenerate** — after an edit, rewrite only the changed section back into the original prompt

Everything else (scanning, versioning, diff, status, variable management) is pure Python with no LLM needed.

---

## Decompose

### What It Does

Given a raw prompt string, decompose asks an LLM to identify its structural sections and label each one. The output is a JSON array of `{label, content}` objects.

### The Strategy

The decompose system prompt:

```
You are an expert at analyzing LLM system prompts and identifying their
structural components. Given a prompt, identify its distinct sections
and label each one.

Common labels: Role, Context, Instructions, Output Format, Examples,
Constraints, Persona, Chain of Thought.

Rules:
1. Return a JSON array: [{"label": "Role", "content": "..."}, ...]
2. Each component must contain the verbatim text from the original prompt
3. All text from the original must be accounted for — no content should be lost
4. Do not rewrite, summarize, or paraphrase — preserve exact wording
5. Use custom labels when common ones don't fit
```

The user message is simply the raw prompt wrapped in XML tags for clarity:

```
Decompose this prompt into its structural components:

<prompt>
[raw content here]
</prompt>
```

### Why XML Tags?

XML tags help the LLM understand exactly where the prompt being analyzed starts and ends — preventing it from interpreting the prompt content as instructions to itself.

### Example

**Input:**
```
You are a senior software engineer.
Review the following Python code.
Look for security vulnerabilities, performance issues, and style problems.
Respond with JSON: {"issues": [{"severity": "...", "description": "...", "line": N}]}
Be direct. No filler text.
```

**LLM Response:**
```json
[
  {"label": "Role", "content": "You are a senior software engineer."},
  {"label": "Instructions", "content": "Review the following Python code.\nLook for security vulnerabilities, performance issues, and style problems."},
  {"label": "Output Format", "content": "Respond with JSON: {\"issues\": [{\"severity\": \"...\", \"description\": \"...\", \"line\": N}]}"},
  {"label": "Constraints", "content": "Be direct. No filler text."}
]
```

Each `content` field contains the verbatim text from the original — no paraphrasing.

---

## Regenerate

### What It Does

After a component is edited, added, or deleted, regenerate asks an LLM to incorporate the change into the original prompt text — while preserving everything else exactly.

### The Surgical Strategy

The regenerate system prompt:

```
You are an expert editor of LLM prompts. You will receive:
1. The original prompt text
2. The old list of components (before the edit)
3. The new list of components (with the change)

Your task: produce an updated version of the original prompt that
incorporates ONLY the changed components.

Critical rules:
- Preserve the original tone, style, voice, and whitespace exactly
- Do not rewrite, expand, or improve unchanged sections
- Do not add new content beyond what is in the new component list
- Do not remove content from unchanged components
- The output must read as a single coherent prompt
```

The user message provides all three artifacts:

```
ORIGINAL PROMPT:
<original>
[full raw content]
</original>

OLD COMPONENTS:
<old_components>
[JSON array of components before edit]
</old_components>

NEW COMPONENTS (with your changes applied):
<new_components>
[JSON array of components after edit]
</new_components>

Produce the updated prompt text only. No explanation.
```

### Why This Approach?

A naive "rewrite the whole prompt" approach would:
- Change your carefully tuned tone
- Expand or contract other sections unpredictably
- Make it hard to diff what actually changed
- Lose specific formatting you spent time on

The surgical approach gives the LLM full context to understand *what changed* (by comparing old vs. new components) while explicitly instructing it to preserve everything else.

### Example: Editing One Component

**Original prompt (v2):**
```
You are a helpful customer support agent.
Answer questions about our software products.
Always be polite and professional.
If you don't know the answer, say so.
```

**Old components:**
```json
[
  {"label": "Role", "content": "You are a helpful customer support agent."},
  {"label": "Instructions", "content": "Answer questions about our software products."},
  {"label": "Constraints", "content": "Always be polite and professional.\nIf you don't know the answer, say so."}
]
```

**Edit: Change "Instructions" to add escalation path**

**New components:**
```json
[
  {"label": "Role", "content": "You are a helpful customer support agent."},
  {"label": "Instructions", "content": "Answer questions about our software products. For billing questions, route the customer to the billing team by saying 'I'll connect you with our billing team.'"},
  {"label": "Constraints", "content": "Always be polite and professional.\nIf you don't know the answer, say so."}
]
```

**Regenerated prompt (v3):**
```
You are a helpful customer support agent.
Answer questions about our software products. For billing questions,
route the customer to the billing team by saying 'I'll connect you
with our billing team.'
Always be polite and professional.
If you don't know the answer, say so.
```

The "Role" and "Constraints" sections are byte-for-byte identical. Only the "Instructions" section changed.

---

## Adding a Component

When a new component is added between two existing ones:

**New components list with "Context" added:**
```json
[
  {"label": "Role", "content": "..."},
  {"label": "Context", "content": "The user has a Pro subscription and has been a customer for 3+ years."},
  {"label": "Instructions", "content": "..."},
  {"label": "Constraints", "content": "..."}
]
```

The LLM inserts the context section in the appropriate place — after the Role and before the Instructions — maintaining natural paragraph flow.

---

## Deleting a Component

When a component is removed:

**New components list without "Constraints":**
```json
[
  {"label": "Role", "content": "..."},
  {"label": "Instructions", "content": "..."}
]
```

The LLM regenerates the prompt without the constraints section, joining the remaining sections smoothly without leaving gaps or awkward transitions.

---

## Model Choice for Decompose/Regenerate

| Model | Quality | Speed | Notes |
|---|---|---|---|
| `gpt-4o-mini` | Excellent | Fast | Recommended default |
| `claude-haiku-4-5` | Excellent | Very fast | Best at JSON fidelity |
| `gemini-2.0-flash` | Good | Very fast | Cost-effective |
| `llama3` (Ollama) | Good | Moderate | Free, private |
| `mistral` (Ollama) | Good | Fast | Good instruction following |

For decompose, any model that reliably outputs JSON works well. For regenerate (style preservation), `gpt-4o-mini` and Claude models tend to be most faithful to the original tone and formatting.

---

## See Also

- [Component Graph](../how-it-works/component-graph.md) — the data model
- [Component Graph Editor](../ui/component-graph.md) — using the UI
- [LLM Providers](providers.md) — configuring which provider to use
