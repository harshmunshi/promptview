# pv remote — Remote Backends

Manage named remote storage backends and push/pull the prompt database.

---

## Overview

Remote backends let you share the `.promptview/promptview.db` file across machines, team members, and CI runners. Think of it as `git push/pull` — but instead of pushing source code, you push the entire prompt database.

Supported backends:

| Backend | URL Scheme | Extra Install |
|---|---|---|
| Amazon S3 | `s3://bucket/path/` | `pip install "promptview[s3]"` |
| Google Cloud Storage | `gcs://bucket/path/` | `pip install "promptview[gcs]"` |
| HTTP/HTTPS | `https://host/path/` | None (built-in `httpx`) |

---

## pv remote add

Register a named remote backend.

```bash
pv remote add NAME URL
```

### Examples

```bash
# S3
pv remote add origin s3://my-bucket/my-project/

# GCS
pv remote add staging gcs://staging-bucket/prompts/team/

# HTTP (self-hosted)
pv remote add internal https://prompts.internal.company.com/project/
```

Named remotes are stored in `.promptview/config.toml`:

```toml
[remotes]
origin  = "s3://my-bucket/my-project/"
staging = "gcs://staging-bucket/prompts/team/"
```

---

## pv remote list

Show all registered remotes.

```bash
pv remote list
```

Output:
```
  origin   s3://my-bucket/my-project/
  staging  gcs://staging-bucket/prompts/team/
```

---

## pv remote remove

Unregister a named remote.

```bash
pv remote remove staging
```

---

## pv push-remote

Upload the local `promptview.db` to a named remote or a direct URL.

```bash
pv push-remote NAME
pv push-remote URL
```

### Examples

```bash
# Push to named remote
pv push-remote origin

# Push directly to a URL (no need to register)
pv push-remote s3://my-bucket/my-project/
pv push-remote gcs://my-bucket/prompts/
pv push-remote https://prompts.example.com/project/
```

The entire `.promptview/promptview.db` file is uploaded atomically. The remote path is `<prefix>/promptview.db`.

---

## pv pull-remote

Download the remote `promptview.db` and overwrite the local one.

```bash
pv pull-remote NAME
pv pull-remote URL
```

### Examples

```bash
# Pull from named remote
pv pull-remote origin

# Pull from direct URL
pv pull-remote s3://my-bucket/my-project/
```

### Backup Behaviour

Before overwriting the local database, `pv pull-remote` creates a backup:

```
.promptview/promptview.db.backup.<timestamp>
```

This ensures you can recover if the pull brings unexpected changes.

Output:
```
Backed up local DB to .promptview/promptview.db.backup.20240316142207
Pulled promptview.db from s3://my-bucket/my-project/
```

---

## S3 Configuration

### Installation

```bash
pip install "promptview[s3]"
```

### Authentication

Use standard AWS credential methods:

=== "Environment Variables"

    ```bash
    export AWS_ACCESS_KEY_ID="AKIA..."
    export AWS_SECRET_ACCESS_KEY="secret..."
    export AWS_DEFAULT_REGION="us-east-1"
    ```

=== "AWS Profile"

    ```bash
    aws configure --profile my-profile
    export AWS_PROFILE=my-profile
    ```

=== "IAM Role (EC2/Lambda)"

    No configuration needed — boto3 picks up the instance role automatically.

### URL Format

```
s3://bucket-name/path/to/project/
```

The actual file is stored at `s3://bucket-name/path/to/project/promptview.db`.

### Required S3 Permissions

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject",
    "s3:PutObject",
    "s3:HeadObject"
  ],
  "Resource": "arn:aws:s3:::my-bucket/my-project/*"
}
```

---

## GCS Configuration

### Installation

```bash
pip install "promptview[gcs]"
```

### Authentication

=== "Service Account Key"

    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
    ```

=== "gcloud CLI"

    ```bash
    gcloud auth application-default login
    ```

=== "Workload Identity (GKE)"

    Configured via GKE annotation — no key file needed.

### URL Format

```
gcs://bucket-name/path/to/project/
```

---

## HTTP Backend Configuration

The HTTP backend uses `httpx` — already installed as a core dependency. No extras needed.

### URL Format

```
https://prompts.example.com/project/
http://internal-server:8080/prompts/
```

### How It Works

| Operation | HTTP Method | Path |
|---|---|---|
| Push | `PUT` | `{base_url}/promptview.db` |
| Pull | `GET` | `{base_url}/promptview.db` |
| Exists | `HEAD` | `{base_url}/promptview.db` |

### Self-Hosted Backend Example

You can run a simple file server as an HTTP remote:

```python
# server.py — minimal FastAPI file server
from fastapi import FastAPI, Request, Response
from pathlib import Path

app = FastAPI()
DB_PATH = Path("/data/promptview.db")

@app.get("/promptview.db")
def download():
    return Response(DB_PATH.read_bytes(), media_type="application/octet-stream")

@app.put("/promptview.db")
async def upload(request: Request):
    DB_PATH.write_bytes(await request.body())
    return {"status": "ok"}

@app.head("/promptview.db")
def check():
    return Response(status_code=200 if DB_PATH.exists() else 404)
```

```bash
uvicorn server:app --host 0.0.0.0 --port 8080
pv remote add origin http://localhost:8080/
```

---

## CI/CD Usage

```yaml
# .github/workflows/promptview.yml
- name: Restore prompt DB
  run: |
    pip install "promptview[s3]"
    pv init --no-scan
    pv pull-remote origin
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

- name: Check for untracked prompts
  run: pv scan --fail-on-untracked
```

---

## See Also

- [Team Workflow](../advanced/team-workflow.md)
- [CI/CD Integration](../advanced/ci-cd.md)
- [pv push / pull / sync](integrations.md) — Langfuse and LangSmith integration
