# Remote Backends (S3, GCS, HTTP)

Remote backends let you share the PromptView database across machines, team members, and CI runners without using Langfuse or LangSmith. The entire `.promptview/promptview.db` SQLite file is pushed to or pulled from cloud storage.

---

## Overview

Unlike Langfuse/LangSmith integrations which sync individual prompt versions, remote backends copy the **entire database**. This includes:
- All prompts and versions
- All commits
- All components and variables
- All eval runs and results
- All remote backend configurations (from `config.toml`)

Think of it as `rsync` for your prompt database.

---

## Supported Backends

| Backend | URL Scheme | Extra Install |
|---|---|---|
| Amazon S3 | `s3://bucket/prefix/` | `pip install "promptview[s3]"` |
| Google Cloud Storage | `gcs://bucket/prefix/` | `pip install "promptview[gcs]"` |
| HTTP/HTTPS | `https://host/path/` | None (uses built-in `httpx`) |

---

## Amazon S3

### Setup

```bash
pip install "promptview[s3]"
```

Configure AWS credentials using any standard method:

=== "Environment Variables"

    ```bash
    export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
    export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    export AWS_DEFAULT_REGION="us-east-1"
    ```

=== "~/.aws/credentials"

    ```ini
    [default]
    aws_access_key_id = AKIAIOSFODNN7EXAMPLE
    aws_secret_access_key = wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    ```

=== "IAM Role"

    On EC2, ECS, Lambda, or GitHub Actions with OIDC — credentials are provided automatically.

### URL Format

```
s3://bucket-name/prefix/path/
```

The database file is stored at `s3://bucket-name/prefix/path/promptview.db`.

### Example

```bash
pv remote add origin s3://my-company-data/promptview/production/
pv push-remote origin
pv pull-remote origin
```

### Required IAM Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
      "Resource": "arn:aws:s3:::my-company-data/promptview/*"
    }
  ]
}
```

---

## Google Cloud Storage

### Setup

```bash
pip install "promptview[gcs]"
```

Configure GCP credentials:

=== "Service Account Key"

    ```bash
    export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
    ```

=== "gcloud CLI"

    ```bash
    gcloud auth application-default login
    ```

=== "Workload Identity (GKE)"

    Annotate your Kubernetes service account — no key file needed.

### URL Format

```
gcs://bucket-name/prefix/path/
```

### Example

```bash
pv remote add staging gcs://my-company-storage/prompts/staging/
pv push-remote staging
```

### Required GCS Permissions

The service account needs `storage.objects.get`, `storage.objects.create`, `storage.objects.update` on the bucket.

---

## HTTP/HTTPS Backend

The HTTP backend uses `httpx` — always installed as a core PromptView dependency. No extras needed.

### URL Format

```
https://host/path/
http://internal-server:8080/prompts/
```

### How It Works

| Operation | Method | Endpoint |
|---|---|---|
| Push (upload) | `PUT` | `{base_url}/promptview.db` |
| Pull (download) | `GET` | `{base_url}/promptview.db` |
| Exists check | `HEAD` | `{base_url}/promptview.db` |

### Simple Self-Hosted Server

You can run a minimal HTTP server as a shared remote:

```python
# promptview_server.py
from fastapi import FastAPI, Request, Response
from pathlib import Path

app = FastAPI()
DB_DIR = Path("/var/data/promptview")
DB_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/promptview.db")
def download_db():
    db_path = DB_DIR / "promptview.db"
    if not db_path.exists():
        return Response(status_code=404)
    return Response(
        content=db_path.read_bytes(),
        media_type="application/octet-stream"
    )

@app.put("/promptview.db")
async def upload_db(request: Request):
    db_path = DB_DIR / "promptview.db"
    db_path.write_bytes(await request.body())
    return {"status": "ok"}

@app.head("/promptview.db")
def check_db():
    db_path = DB_DIR / "promptview.db"
    return Response(status_code=200 if db_path.exists() else 404)
```

Start it:
```bash
pip install fastapi uvicorn
uvicorn promptview_server:app --host 0.0.0.0 --port 8080
```

Use it:
```bash
pv remote add origin http://my-server:8080/
pv push-remote origin
```

---

## Named Remotes

Register frequently-used backends by name:

```bash
# Register
pv remote add origin s3://my-bucket/production/
pv remote add staging gcs://staging-bucket/prompts/

# List
pv remote list
# origin   s3://my-bucket/production/
# staging  gcs://staging-bucket/prompts/

# Use by name
pv push-remote origin
pv pull-remote staging

# Remove
pv remote remove staging
```

Named remotes are stored in `.promptview/config.toml`:
```toml
[remotes]
origin  = "s3://my-bucket/production/"
staging = "gcs://staging-bucket/prompts/"
```

---

## Direct URLs

You don't need a named remote — use the URL directly:

```bash
pv push-remote s3://my-bucket/project/
pv pull-remote gcs://my-bucket/prompts/
pv pull-remote https://prompts.my-company.com/project/
```

---

## Backup on Pull

Before `pv pull-remote` overwrites the local database, it creates a timestamped backup:

```
.promptview/promptview.db.backup.20240316142207
```

To recover:
```bash
cp .promptview/promptview.db.backup.20240316142207 .promptview/promptview.db
```

---

## CI/CD Usage Pattern

```yaml
# .github/workflows/ci.yml
- name: Install PromptView
  run: pip install "promptview[s3]"

- name: Restore prompt database
  run: |
    pv init --no-scan
    pv pull-remote origin
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

- name: Run eval regression
  run: pv eval run my_prompt --dataset evals/regression.jsonl --provider openai
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## See Also

- [pv remote CLI reference](../cli/remote-backends.md)
- [Team Workflow](../advanced/team-workflow.md)
- [CI/CD Integration](../advanced/ci-cd.md)
