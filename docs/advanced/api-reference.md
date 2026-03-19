# API Reference

Complete reference for all REST endpoints exposed by `pv ui` (the FastAPI server at `http://localhost:8765`).

---

## Base URL

```
http://localhost:8765
```

All API endpoints are prefixed with `/api`. The root `/` serves the web UI.

---

## Health

### GET /health

```
GET /health
```

**Response:**
```json
{"status": "ok"}
```

---

## Prompts

### GET /api/prompts

List all tracked prompts.

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "system_prompt",
    "description": "",
    "source": "openai",
    "file_path": "/project/src/agent.py",
    "line_number": 42,
    "variable_name": "SYSTEM_PROMPT",
    "tags": [],
    "version_count": 3,
    "created_at": "2024-03-15T10:32:11Z",
    "updated_at": "2024-03-16T14:22:07Z"
  }
]
```

---

### POST /api/prompts

Create a prompt manually.

**Request body:**
```json
{
  "name": "my_prompt",
  "content": "You are a helpful assistant.",
  "source": "manual",
  "description": "Optional description"
}
```

**Response:** The created prompt object.

---

### GET /api/prompts/{id}

Get a single prompt by ID.

**Response:** Single prompt object (same schema as list).

---

### PATCH /api/prompts/{id}

Update prompt metadata (name, description, tags).

**Request body:**
```json
{
  "name": "new_name",
  "description": "Updated description",
  "tags": ["production", "v2"]
}
```

---

### DELETE /api/prompts/{id}

Delete a prompt and all its versions, components, and variables.

**Response:** `{"deleted": true}`

---

### GET /api/prompts/{id}/versions

List all versions of a prompt.

**Response:**
```json
[
  {
    "id": "uuid",
    "prompt_id": "uuid",
    "version_number": 1,
    "raw_content": "You are a helpful assistant.",
    "content_hash": "abc123...",
    "commit_id": "a3f2c891",
    "parent_version_id": null,
    "created_at": "2024-03-15T10:32:11Z"
  },
  {
    "id": "uuid",
    "version_number": 2,
    ...
  }
]
```

---

## Scan & Commit

### POST /api/scan

Trigger an AST scan of the project.

**Request body (optional):**
```json
{
  "path": "/project/src/",
  "min_confidence": 0.7
}
```

**Response:**
```json
{
  "found": 5,
  "new": 2,
  "prompts": [
    {"name": "system_prompt", "source": "openai", "confidence": 0.95, "file_path": "..."},
    ...
  ]
}
```

---

### POST /api/commit

Commit all staged prompts.

**Request body:**
```json
{
  "message": "Initial prompt capture",
  "author": "Alice Smith"
}
```

**Response:**
```json
{
  "commit_id": "a3f2c891",
  "message": "Initial prompt capture",
  "version_count": 4
}
```

---

## Components

### GET /api/prompts/{id}/components

Get components for the latest version (or a specific version).

**Query params:**
- `version_id` (optional) — UUID of a specific version

**Response:**
```json
[
  {
    "id": "uuid",
    "prompt_id": "uuid",
    "version_id": "uuid",
    "label": "Role",
    "content": "You are a senior engineer.",
    "position": 0
  },
  {
    "id": "uuid",
    "label": "Instructions",
    "content": "Review the code...",
    "position": 1
  }
]
```

---

### POST /api/prompts/{id}/decompose

Decompose a prompt into structural components using an LLM.

**Request body:**
```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

**Response:** List of components (same schema as GET components).

---

### POST /api/prompts/{id}/components/add

Add a new component to the prompt.

**Request body:**
```json
{
  "label": "Context",
  "content": "The user has a Pro subscription.",
  "position": 1,
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

**Response:** Updated list of components after regeneration.

---

### PUT /api/prompts/{id}/components

Update one or more components and regenerate the prompt.

**Request body:**
```json
{
  "components": [
    {"id": "uuid", "label": "Role", "content": "...", "position": 0},
    {"id": "uuid", "label": "Instructions", "content": "Updated instructions.", "position": 1}
  ],
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

**Response:** The new version object with updated components.

---

### DELETE /api/prompts/{id}/components/{component_id}

Delete a component and regenerate the prompt without it.

**Query params:**
- `provider` — LLM provider
- `api_key` — LLM API key
- `model` — LLM model (optional)

**Response:** Updated prompt version and component list.

---

## Variables

### GET /api/prompts/{id}/variables

List all variables for a prompt.

**Response:**
```json
[
  {
    "id": "uuid",
    "prompt_id": "uuid",
    "name": "company_name",
    "default_value": "AcmeCorp",
    "description": "Customer company name",
    "created_at": "2024-03-15T10:32:11Z"
  }
]
```

---

### POST /api/prompts/{id}/variables

Create a new variable manually.

**Request body:**
```json
{
  "name": "user_name",
  "default_value": "",
  "description": "The user's first name"
}
```

---

### PUT /api/prompts/{id}/variables/{variable_id}

Update a variable's default value or description.

**Request body:**
```json
{
  "default_value": "English",
  "description": "Response language"
}
```

---

### POST /api/prompts/{id}/variables/sync

Auto-detect `{slot}` names from the latest version and create missing variables.

**Response:**
```json
{
  "synced": 2,
  "new_variables": ["user_name", "task"],
  "existing_unchanged": ["company_name", "language"]
}
```

---

## Diff

### GET /api/diff/{prompt_id}

Get a unified diff between two versions.

**Query params:**
- `v1` — UUID of the first version
- `v2` — UUID of the second version

**Response:**
```json
{
  "diff": "--- v1\n+++ v2\n@@ ... @@\n ...",
  "prompt_name": "system_prompt",
  "v1_number": 1,
  "v2_number": 3
}
```

---

## Branches

### GET /api/branches

List all branches.

**Response:**
```json
[
  {"name": "main", "is_current": true},
  {"name": "feature/new-tone", "is_current": false}
]
```

---

### POST /api/branches

Create a new branch.

**Request body:**
```json
{"name": "feature/formal-tone"}
```

---

### DELETE /api/branches/{name}

Delete a branch.

---

### POST /api/branches/{name}/checkout

Switch to a branch.

**Response:**
```json
{"branch": "feature/formal-tone", "checked_out": true}
```

---

## Evals

### GET /api/evals

List all eval runs.

**Response:**
```json
[
  {
    "id": "uuid",
    "prompt_id": "uuid",
    "version_id": "uuid",
    "total_cases": 10,
    "passed": 7,
    "pass_rate": 70.0,
    "avg_judge_score": 0.82,
    "avg_latency_ms": 445.0,
    "source": "local",
    "dataset_path": "evals/cases.jsonl",
    "run_at": "2024-03-16T14:22:07Z"
  }
]
```

---

### POST /api/evals

Trigger an eval run.

**Request body:**
```json
{
  "prompt_id": "uuid",
  "dataset_path": "evals/cases.jsonl",
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini",
  "use_judge": false,
  "version_id": null
}
```

**Response:** The completed `EvalRun` object with aggregate stats.

---

### GET /api/evals/{run_id}

Get a specific eval run including per-case results.

**Response:**
```json
{
  "run": { ...EvalRun object... },
  "results": [
    {
      "id": "uuid",
      "test_case_id": "uuid",
      "actual_output": "Bonjour",
      "passed": true,
      "similarity_score": 1.0,
      "judge_score": null,
      "judge_reasoning": null,
      "latency_ms": 432.0
    }
  ]
}
```

---

### GET /api/prompts/{id}/metrics

Get the eval metrics history for a prompt.

**Query params:**
- `last` (optional) — number of most recent runs (default: 10)

**Response:** List of `EvalRun` objects sorted by `run_at` descending.

---

## Graph

### GET /api/graph

Get the full prompt relationship graph (for the graph visualization endpoint).

**Response:**
```json
{
  "nodes": [
    {"id": "uuid", "name": "system_prompt", "source": "openai", "version_count": 3}
  ],
  "edges": [
    {"source": "uuid1", "target": "uuid2", "type": "includes"}
  ]
}
```

---

## Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|---|---|
| `400` | Bad request — missing required field or invalid value |
| `404` | Not found — prompt, version, or component ID doesn't exist |
| `500` | Internal server error — check server logs |

Error body:
```json
{
  "detail": "Prompt 'nonexistent' not found"
}
```

---

## See Also

- [pv ui CLI reference](../cli/ui.md)
- [Web UI Overview](../ui/overview.md)
