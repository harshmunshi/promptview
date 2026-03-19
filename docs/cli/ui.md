# pv ui

Launch the PromptView visual editor.

---

## Synopsis

```bash
pv ui [OPTIONS]
```

---

## Description

`pv ui` starts a FastAPI web server and opens the PromptView visual editor in your default browser. The editor provides a point-and-click interface for browsing prompts, decomposing them into structural components, editing nodes, viewing version history, managing variables, and reviewing eval results.

---

## Options

| Option | Description | Default |
|---|---|---|
| `--port INTEGER` | Port to bind to | `8765` |
| `--host TEXT` | Host to bind to | `127.0.0.1` |
| `--no-browser` | Start server without opening a browser | Off |

---

## Examples

```bash
# Default — http://localhost:8765
pv ui

# Custom port
pv ui --port 9000

# Bind to all interfaces (for team access on local network)
pv ui --host 0.0.0.0 --port 8765

# Headless — useful in CI or SSH sessions
pv ui --no-browser

# Specific host and port
pv ui --host 0.0.0.0 --port 9999
```

---

## What Gets Served

The server mounts:

```
GET  /              → index.html (the D3.js SPA)
GET  /health        → {"status": "ok"}
GET  /api/...       → all REST endpoints
```

The SPA is a single `index.html` file containing all JavaScript and CSS inline. No external CDN requests — works offline.

---

## API Endpoints Exposed

When you run `pv ui`, the following REST API is available at `http://localhost:8765`:

### Prompts

```
GET    /api/prompts                    List all prompts
POST   /api/prompts                    Create a prompt manually
GET    /api/prompts/{id}               Get a single prompt
PATCH  /api/prompts/{id}               Update prompt metadata
DELETE /api/prompts/{id}               Delete a prompt
GET    /api/prompts/{id}/versions      List all versions of a prompt
```

### Scanning & Committing

```
POST   /api/scan                       Trigger a scan
POST   /api/commit                     Commit staged prompts
```

### Components

```
GET    /api/prompts/{id}/components    Get components for latest version
GET    /api/prompts/{id}/components?version_id=X   Get for specific version
POST   /api/prompts/{id}/decompose     Decompose prompt into components (LLM)
POST   /api/prompts/{id}/components/add            Add a new component
PUT    /api/prompts/{id}/components    Update component and regenerate (LLM)
DELETE /api/prompts/{id}/components/{cid}          Delete a component
```

### Variables

```
GET    /api/prompts/{id}/variables         List variables + defaults
POST   /api/prompts/{id}/variables         Create a variable
PUT    /api/prompts/{id}/variables/{vid}   Update default / description
POST   /api/prompts/{id}/variables/sync    Auto-detect variables from content
```

### Diff

```
GET    /api/diff/{id}?v1=X&v2=Y            Unified diff between versions
```

### Branches

```
GET    /api/branches                   List branches
POST   /api/branches                   Create a branch
DELETE /api/branches/{name}            Delete a branch
POST   /api/branches/{name}/checkout   Checkout a branch
```

### Evals

```
GET    /api/evals                      List eval runs
POST   /api/evals                      Trigger an eval run
GET    /api/evals/{id}                 Get a specific eval run
GET    /api/prompts/{id}/metrics       Get metrics history for a prompt
```

### Graph

```
GET    /api/graph                      Get full prompt relationship graph
```

---

## Network Access

By default `pv ui` binds to `127.0.0.1` (localhost only). To allow team members on the same network to access the UI:

```bash
pv ui --host 0.0.0.0 --port 8765
```

!!! warning "Security"
    Binding to `0.0.0.0` exposes the API to your entire network. The API has no authentication. Only do this on trusted networks (e.g. your office LAN or a private subnet). Never expose to the public internet without a reverse proxy with authentication.

---

## Using the API Programmatically

You can use the API endpoints directly without the browser UI — useful for scripting or integration testing:

```bash
# List all prompts
curl http://localhost:8765/api/prompts | python -m json.tool

# Get components for a prompt
PROMPT_ID="your-prompt-uuid"
curl "http://localhost:8765/api/prompts/$PROMPT_ID/components"

# Trigger a scan
curl -X POST http://localhost:8765/api/scan

# Diff two versions
curl "http://localhost:8765/api/diff/$PROMPT_ID?v1=uuid1&v2=uuid2"
```

---

## Stopping the Server

Press `Ctrl+C` in the terminal where `pv ui` is running. The server shuts down gracefully.

---

## See Also

- [Web UI Overview](../ui/overview.md)
- [Component Graph Editor](../ui/component-graph.md)
- [API Reference](../advanced/api-reference.md)
