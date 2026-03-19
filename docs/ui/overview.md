# Web UI Overview

The PromptView web UI is a single-page application served by `pv ui`. It provides a visual interface for all prompt management operations that are awkward in the command line — particularly the component graph editor, version browsing, and eval result inspection.

---

## Launching the UI

```bash
pv ui
```

Opens `http://localhost:8765` in your default browser.

```bash
pv ui --port 9000          # custom port
pv ui --host 0.0.0.0       # accessible from other machines on the network
pv ui --no-browser         # start server without opening browser
```

---

## Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  TOOLBAR: [Scan] [Commit] [Status]              [⚙ LLM Config] │
├───────────────────┬─────────────────────────────────────────────┤
│                   │                                             │
│  SIDEBAR          │  MAIN AREA                                  │
│                   │                                             │
│  Search bar       │  ┌────────────────────────────────────────┐ │
│                   │  │ VERSION SWITCHER: [v1] [v2] [v3●] [v4] │ │
│  my_prompt        │  └────────────────────────────────────────┘ │
│  ● openai  v3     │                                             │
│                   │  TABS: [Components] [Variables] [Metrics]  │
│  summarizer       │                                             │
│  ● anthropic v2   │  COMPONENT GRAPH:                          │
│                   │  ┌──────────────────────────────┐          │
│  code_reviewer    │  │  Role                      × │          │
│  ● openai  v5     │  └──────────────────────────────┘          │
│                   │              ↓                              │
│  user_template    │  ┌──────────────────────────────┐          │
│  ● openai  v1     │  │  Instructions              × │          │
│                   │  └──────────────────────────────┘          │
│                   │              ↓                              │
│                   │  ┌──────────────────────────────┐          │
│                   │  │  Output Format             × │          │
│                   │  └──────────────────────────────┘          │
│                   │                                             │
│                   │  [+ Add Component]  [Decompose]  [Save]    │
│                   │                                             │
├───────────────────┴─────────────────────────────────────────────┤
│  FOOTER (collapsible): Full reconstructed prompt text           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Sidebar

The left sidebar shows all tracked prompts with:
- **Name** — the prompt's identifier
- **Source badge** — `openai`, `anthropic`, `langchain`, `raw`, etc. (colored)
- **Version count** — how many committed versions exist
- **Search bar** — filter by name in real time

Click any prompt to load it in the main area.

---

## Toolbar

The top toolbar provides quick access to the most common actions:

| Button | Action |
|---|---|
| **Scan** | Trigger `POST /api/scan` — runs the AST scanner on the project |
| **Commit** | Open a commit dialog — enter a message and commit all staged prompts |
| **Status** | Show a status panel (staged / modified / untracked) |
| **⚙ (gear)** | Open the LLM configuration modal |

---

## Main Area Tabs

### Components Tab

The default view — shows the D3 component graph for the selected prompt and version. See [Component Graph Editor](component-graph.md) for full details.

### Variables Tab

Shows the `{slot}` variables detected in the prompt with their defaults and descriptions. See [Variables Panel](variables-panel.md).

### Metrics Tab

Shows eval run history for the selected prompt. Clicking a run expands per-case results. See [Metrics & Evals](metrics-tab.md).

---

## Version Switcher

The row of pill buttons at the top of the main area — one pill per committed version. Click any version to reload the component graph and variables for that historical snapshot. See [Version Switcher](version-switcher.md).

---

## Edit Panel

Clicking any component node opens an edit panel that slides in from the right. You can:
- Edit the label
- Edit the full content in a textarea
- Click **Save** to trigger surgical LLM regeneration
- Click **Cancel** to discard changes

---

## Footer

A collapsible section at the bottom showing the complete reconstructed prompt text for the current version. This is the actual `raw_content` that gets sent to production LLMs — the ground truth of what the component graph represents.

Click the footer bar to expand or collapse it.

---

## LLM Config Modal

Opened with the gear icon. Configure which LLM provider to use for decompose and regenerate operations:

| Field | Options | Notes |
|---|---|---|
| Provider | `openai`, `anthropic`, `gemini`, `ollama` | Required for decompose/regenerate |
| API Key | Free text | Not needed for Ollama |
| Model | Free text | Defaults: gpt-4o-mini, claude-haiku-4-5, gemini-2.0-flash, llama3 |

Settings are stored in browser `localStorage`. They are never sent to any backend — only used in the browser to construct POST bodies for decompose/regenerate requests.

!!! warning "API Key Security"
    The UI includes the API key in POST request bodies to the local FastAPI server. The server never stores or logs API keys. They exist only in memory for the duration of the API call. On a public server, use Ollama or configure keys server-side via environment variables instead.

---

## Toast Notifications

All async operations (decompose, save, scan, commit) show toast notifications in the top-right corner:

- :material-check-circle: Green — success
- :material-alert-circle: Red — error with message
- :material-information: Blue — informational

---

## GitHub Dark Theme

The UI uses a GitHub Dark color scheme:
- Background: `#0d1117`
- Panel/card: `#161b22`
- Border: `#30363d`
- Text: `#c9d1d9`
- Accent: `#58a6ff` (blue), `#3fb950` (green), `#f85149` (red)

---

## Technology

The UI is a **single-file vanilla JavaScript SPA** — no framework, no build step, no CDN dependencies (D3.js is bundled inline). It is served as a static file by the FastAPI backend.

This design means:
- Works offline after first load
- No npm, no webpack, no React
- Easy to inspect in browser DevTools
- The entire frontend is in `src/promptview/server/static/index.html`

---

## See Also

- [pv ui CLI reference](../cli/ui.md)
- [Component Graph Editor](component-graph.md)
- [Version Switcher](version-switcher.md)
- [Variables Panel](variables-panel.md)
- [Metrics & Evals](metrics-tab.md)
