# Component Graph Editor

The component graph is the central feature of the PromptView UI. It presents a prompt as a vertical stack of labeled nodes, each representing a structural section. You can edit, add, and delete nodes — with changes surgically applied back to the prompt automatically.

---

## Opening a Prompt

1. Click a prompt name in the left sidebar
2. The main area shows the current state:
   - If not yet decomposed: a plain text view with a **Decompose** button
   - If decomposed: the component graph with all nodes

---

## Decomposing a Prompt

Click the **Decompose** button. The UI:
1. Sends a `POST /api/prompts/{id}/decompose` request with your LLM config
2. Shows a loading spinner while the LLM processes
3. Renders the component graph when done

The LLM breaks the prompt into structural nodes. A typical decomposition might produce:

```
┌──────────────────────────────────────────┐
│  Role                                 ×  │
│  You are a senior software engineer...   │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Instructions                         ×  │
│  Review the code carefully. Look for...  │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Output Format                        ×  │
│  Respond with JSON: {"issues": [...]}    │
└──────────────────────────────────────────┘
              ↓
┌──────────────────────────────────────────┐
│  Constraints                          ×  │
│  Be direct. Do not add filler text.      │
└──────────────────────────────────────────┘
```

!!! note "LLM Required"
    Decompose requires a configured LLM. Click the gear icon to set your provider and API key. Ollama works for free with a local model.

---

## Editing a Node

Click any node card to expand it. The node expands to show:
- **Label field** — editable text (e.g. "Role", "Instructions")
- **Content textarea** — the full component text, editable
- **Save button** — applies the edit
- **Cancel button** — discards changes

When you click **Save**:
1. The UI sends a `PUT /api/prompts/{id}/components` request with the updated component list
2. The LLM regenerates the full prompt text using the surgical strategy
3. A new `PromptVersion` is created
4. The version switcher updates to show the new version
5. The footer updates to show the new full prompt text

---

## Adding a Component

Click the `+` button that appears between any two nodes (or at the top/bottom of the stack):

1. A new blank node appears in that position
2. Enter a **label** (e.g. "Context", "Examples")
3. Enter the **content** — what this section should say
4. Click **Save**
5. The LLM inserts this section into the appropriate place in the full prompt text
6. A new version is created

---

## Deleting a Component

Click the `×` button in the top-right of any node:

1. A confirmation prompt appears (for nodes with significant content)
2. Confirm deletion
3. The LLM regenerates the prompt without this section — smoothly joining surrounding text
4. A new version is created

---

## Reordering Components

Click and drag node cards to reorder them. The position is updated visually. When you save (or trigger a regeneration), the new order is reflected in the reconstructed prompt.

---

## The D3 Graph

The component graph is rendered using [D3.js](https://d3js.org/). Each node is an SVG `<g>` element positioned vertically. Arrows connect adjacent nodes to show the linear flow.

Design details:
- **Node height** scales with content length
- **Collapsed nodes** show a single line preview
- **Expanded nodes** show the full content textarea
- **Arrows** are straight vertical lines with arrowheads
- **`+` buttons** appear between nodes on hover

---

## Footer: Full Prompt Text

The collapsible footer at the bottom of the page shows the complete reconstructed prompt:

```
▼ Full prompt (click to expand)

You are a senior software engineer with 15 years of experience.
You specialize in Python and distributed systems.

Review the following code carefully. Look for:
- Security vulnerabilities
- Performance bottlenecks
- Code style issues

Respond with a JSON object containing:
{"issues": [{"severity": "...", "description": "...", "line": N}], "summary": "..."}

Be direct and specific. Do not add praise or filler text.
```

This is the `raw_content` of the current version — the exact string that your application sends to the LLM in production.

---

## Workflow: Full Edit Cycle

```
1. Select prompt in sidebar
2. Click Decompose
3. Review nodes
4. Click "Instructions" node → edit content → Save
5. LLM regenerates prompt surgically
6. New v4 created
7. Footer shows updated full prompt
8. Version switcher now shows [v1] [v2] [v3] [v4●]
9. Click v3 to compare → graph shows v3's nodes
10. Click v4 to go back to current
```

---

## See Also

- [Version Switcher](version-switcher.md)
- [Component Graph internals](../how-it-works/component-graph.md)
- [Decompose & Regenerate](../llm/decompose-regenerate.md)
