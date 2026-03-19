# Version Switcher

The version switcher lets you browse any historical version of a prompt's components, compare changes between versions, and understand how a prompt evolved over time.

---

## Location

The version switcher is the row of pill buttons at the top of the main area, visible whenever a prompt is selected.

```
[v1]  [v2]  [v3●]  [v4]
```

The currently active version is highlighted with a solid background. The `●` indicates the most recent version.

---

## Switching Versions

Click any version pill to switch to that version:

1. The UI calls `GET /api/prompts/{id}/components?version_id=<uuid>`
2. The component graph re-renders with the nodes from that historical version
3. The footer updates to show that version's `raw_content`
4. The Variables panel updates to show variables from that version

The switch is instant — no LLM call needed. All component data is already stored in the database.

---

## What Changes When You Switch

| Element | Changes |
|---|---|
| Component graph | Shows nodes for the selected version |
| Footer | Shows `raw_content` of the selected version |
| Variables panel | Shows variables detected in the selected version |
| Metrics tab | Not affected — all eval runs are visible regardless of which version is selected |

---

## Version Number vs Version ID

The pills show the **version number** (1, 2, 3…) — a user-friendly sequential integer scoped per prompt. Internally, each version has a UUID. The version switcher maps between them transparently.

---

## How Versions Are Created

New versions are created by:

1. **`pv commit`** from the CLI after staging changed content
2. **Saving an edit** in the component graph UI (creates a new version via the API)
3. **Adding or deleting a component** in the UI

Viewing a historical version never creates a new version. You can browse freely without creating noise in the history.

---

## Comparing Two Versions

To compare two versions:

1. Note the component graph for version `N`
2. Switch to version `N+1`
3. Observe the differences visually — changed components will have different content

For a text diff, use the CLI:

```bash
pv diff my_prompt 1 3
```

Or via the API:

```bash
curl "http://localhost:8765/api/diff/<prompt_id>?v1=<uuid1>&v2=<uuid2>"
```

!!! tip "Diff View in UI"
    A side-by-side diff view in the UI is on the roadmap. For now, use `pv diff` in the terminal.

---

## Version Count

The sidebar shows the version count next to each prompt name. A prompt with 5 committed versions shows `v5`. This gives you a quick sense of how much iteration has happened.

---

## See Also

- [Component Graph Editor](component-graph.md)
- [Versioning Model](../how-it-works/versioning.md)
- [pv diff](../cli/status-diff-log.md)
