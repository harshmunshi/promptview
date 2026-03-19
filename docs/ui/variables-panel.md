# Variables Panel

The Variables panel shows all `{slot}` placeholders detected in a prompt, with their default values and descriptions. Use it to manage what values get substituted when the prompt is rendered.

---

## Opening the Variables Panel

With a prompt selected in the sidebar, click the **Variables** tab in the main area (next to "Components" and "Metrics").

---

## What You See

```
Variables for: my_prompt (v3)

  Name            Default           Description
  ─────────────────────────────────────────────────────────
  company_name    AcmeCorp          Customer company name
  user_name       (empty)           The user's first name
  task            (empty)           The task or question
  language        English           Response language

  [Sync Variables]
```

Each row shows:
- **Name** — the `{slot}` name from the prompt content
- **Default** — the value used when `pv run` or the render API is called without an override
- **Description** — optional human-readable explanation

---

## Editing Defaults

Click any cell in the **Default** or **Description** columns to edit it inline. Press Enter or click outside to save. The change is sent to `PUT /api/prompts/{id}/variables/{vid}`.

---

## Sync Variables Button

Click **Sync Variables** to scan the current version's content and register any `{slot}` names not yet tracked.

What happens:
1. Calls `POST /api/prompts/{id}/variables/sync`
2. The server runs `extract_variables(raw_content)` on the latest version
3. New variables are created with empty defaults
4. Existing variables are **never overwritten**
5. The table refreshes

After **Decompose**, the UI automatically calls Sync Variables to ensure any slots in the newly decomposed content are registered.

---

## Auto-Sync After Decompose

When you decompose a prompt or edit a component that introduces new `{slot}` names, the UI automatically syncs variables. You will see the Variables panel update with any newly detected placeholders.

This means you can edit the "Instructions" component to add `{user_name}` and the variable row appears in the Variables panel immediately after saving.

---

## Variables and `pv run`

Variables set in the panel are the defaults used by `pv run`:

```bash
# Uses stored defaults (company_name=AcmeCorp, language=English)
pv run my_prompt

# Override one default
pv run my_prompt --var user_name=Alice

# Override all
pv run my_prompt -v company_name=Globex -v user_name=Homer -v task="help me" -v language=Spanish
```

---

## Variables API

The same data is accessible directly:

```
GET    /api/prompts/{id}/variables
       Returns: [{"id": "...", "name": "company_name", "default_value": "AcmeCorp", "description": "..."}]

POST   /api/prompts/{id}/variables/sync
       Triggers auto-detection

PUT    /api/prompts/{id}/variables/{vid}
       Body: {"default_value": "NewCo", "description": "Updated description"}
```

---

## See Also

- [Template Variables](../template-system/variables.md) — the `{slot}` syntax in depth
- [pv vars & run](../cli/vars-run.md) — CLI commands for variables
- [Prompt Composition](../template-system/composition.md) — `{{ include }}` syntax
