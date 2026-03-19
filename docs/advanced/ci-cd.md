# CI/CD Integration for Auto-Evaluation

Integrate PromptView into your CI/CD pipeline to automatically evaluate prompts on every pull request, block regressions before they reach production, and maintain a full audit trail of prompt quality over time.

---

## What You Get

| Capability | Description |
|---|---|
| **Untracked prompt detection** | Build fails if a developer edits a prompt without committing it to PromptView |
| **Regression blocking** | Build fails if eval pass rate drops below your threshold |
| **Per-PR eval comments** | Automatically post eval scores as a PR comment |
| **Score trending** | Track quality over time across every merge |
| **Provider flexibility** | Use OpenAI/Anthropic in CI or Ollama locally to keep costs low |
| **DB sync** | Share one prompt database across all runners and machines |

---

## How Auto-Evaluation Works in CI

```
PR opened / push to main
        │
        ▼
  pv init --no-scan          ← initialise without auto-scanning
        │
        ▼
  pv pull-remote origin      ← restore shared DB from S3/GCS/HTTP
        │
        ▼
  pv scan --fail-on-untracked  ← block if any prompt is untracked
        │
        ▼
  pv eval run <prompt>       ← run test suite against latest version
        │
        ▼
  check pass rate            ← fail build if below threshold
        │
        ▼
  post PR comment            ← report scores back to the PR
        │
        ▼
  pv push-remote origin      ← (main only) write updated DB back to S3
```

---

## GitHub Actions

### Minimal — just untracked prompt detection

```yaml
# .github/workflows/promptview.yml
name: PromptView

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  prompt-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install PromptView
        run: pip install promptview

      - name: Init
        run: pv init --no-scan

      - name: Check no untracked prompts
        run: pv scan --fail-on-untracked
```

---

### Full — eval regression with threshold + PR comment

```yaml
# .github/workflows/promptview-full.yml
name: PromptView — Eval Regression

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  eval:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write      # needed to post PR comments
      contents: read

    steps:
      # ── Setup ─────────────────────────────────────────────────────────
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      # ── Cache the prompt DB between runs ──────────────────────────────
      - name: Cache PromptView DB
        uses: actions/cache@v4
        with:
          path: .promptview/
          key: promptview-db-${{ github.sha }}
          restore-keys: promptview-db-

      # ── Install ───────────────────────────────────────────────────────
      - name: Install PromptView
        run: pip install "promptview[s3]"

      # ── Init + restore DB ─────────────────────────────────────────────
      - name: Init PromptView
        run: pv init --no-scan

      - name: Pull shared prompt database
        run: pv pull-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ secrets.AWS_REGION }}

      # ── Tracking enforcement ───────────────────────────────────────────
      - name: Fail on untracked prompts
        run: pv scan --fail-on-untracked

      # ── Eval regression ───────────────────────────────────────────────
      - name: Run eval — support_agent
        id: eval_support
        run: |
          pv eval run support_agent \
            --dataset evals/support_agent.jsonl \
            --scorer llm_judge \
            --provider openai

          # Extract pass rate and fail if below threshold
          PASS_RATE=$(pv metrics show support_agent --last 1 --json | python3 -c "
          import sys, json
          data = json.load(sys.stdin)
          print(data[-1]['pass_rate'] if data else 0)
          ")
          echo "pass_rate=$PASS_RATE" >> $GITHUB_OUTPUT

          THRESHOLD=75
          if python3 -c "import sys; sys.exit(0 if float('$PASS_RATE') >= $THRESHOLD else 1)"; then
            echo "✅ Pass rate $PASS_RATE% >= threshold $THRESHOLD%"
          else
            echo "❌ Pass rate $PASS_RATE% is below threshold $THRESHOLD%"
            exit 1
          fi
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      # ── Post PR comment with results ───────────────────────────────────
      - name: Post eval summary to PR
        if: github.event_name == 'pull_request' && always()
        uses: actions/github-script@v7
        with:
          script: |
            const passRate = '${{ steps.eval_support.outputs.pass_rate }}';
            const status   = parseFloat(passRate) >= 75 ? '✅ PASSED' : '❌ FAILED';
            const body = `## PromptView Eval Results

            | Prompt | Pass Rate | Threshold | Status |
            |---|---|---|---|
            | \`support_agent\` | ${passRate}% | 75% | ${status} |

            > Run \`pv metrics results <run_id> --prompt support_agent\` locally to see per-case responses.
            `;
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body
            });

      # ── Push DB back on main merge ─────────────────────────────────────
      - name: Push updated prompt database
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: pv push-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: ${{ secrets.AWS_REGION }}
```

---

### Multi-prompt matrix eval

Run evals for several prompts in parallel using a matrix strategy:

```yaml
jobs:
  eval:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false          # run all prompts even if one fails
      matrix:
        include:
          - prompt: support_agent
            dataset: evals/support_agent.jsonl
            threshold: 80
          - prompt: code_reviewer
            dataset: evals/code_reviewer.jsonl
            threshold: 70
          - prompt: summarizer
            dataset: evals/summarizer.jsonl
            threshold: 75

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install "promptview[s3]"
      - run: pv init --no-scan
      - run: pv pull-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Eval ${{ matrix.prompt }}
        run: |
          pv eval run ${{ matrix.prompt }} \
            --dataset ${{ matrix.dataset }} \
            --scorer llm_judge \
            --provider openai

          PASS_RATE=$(pv metrics show ${{ matrix.prompt }} --last 1 --json \
            | python3 -c "import sys,json; d=json.load(sys.stdin); print(d[-1]['pass_rate'] if d else 0)")

          echo "Pass rate for ${{ matrix.prompt }}: $PASS_RATE%"
          python3 -c "
          import sys
          rate = float('$PASS_RATE')
          threshold = ${{ matrix.threshold }}
          if rate < threshold:
              print(f'FAIL: {rate:.1f}% < {threshold}% threshold')
              sys.exit(1)
          print(f'PASS: {rate:.1f}% >= {threshold}% threshold')
          "
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
```

---

## GitLab CI

```yaml
# .gitlab-ci.yml

stages:
  - prompt-check
  - eval
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip
    - .promptview/

# ── Stage 1: enforce tracking ─────────────────────────────────────────
prompt-tracking:
  stage: prompt-check
  image: python:3.11-slim
  script:
    - pip install promptview --quiet
    - pv init --no-scan
    - pv scan --fail-on-untracked

# ── Stage 2: eval regression ──────────────────────────────────────────
eval-regression:
  stage: eval
  image: python:3.11-slim
  script:
    - pip install "promptview[s3]" --quiet
    - pv init --no-scan
    - pv pull-remote origin
    - |
      pv eval run support_agent \
        --dataset evals/support_agent.jsonl \
        --scorer llm_judge \
        --provider openai
    - |
      python3 -c "
      import subprocess, json, sys
      result = subprocess.run(
          ['pv', 'metrics', 'show', 'support_agent', '--last', '1', '--json'],
          capture_output=True, text=True
      )
      data = json.loads(result.stdout)
      rate = data[-1]['pass_rate'] if data else 0
      threshold = 75
      print(f'Pass rate: {rate:.1f}%  threshold: {threshold}%')
      sys.exit(0 if rate >= threshold else 1)
      "
  variables:
    AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
    OPENAI_API_KEY: $OPENAI_API_KEY
  only:
    - main
    - merge_requests

# ── Push DB after deploy ─────────────────────────────────────────────
push-prompt-db:
  stage: deploy
  image: python:3.11-slim
  script:
    - pip install "promptview[s3]" --quiet
    - pv push-remote origin
  variables:
    AWS_ACCESS_KEY_ID: $AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY: $AWS_SECRET_ACCESS_KEY
  only:
    - main
  when: on_success
```

---

## CircleCI

```yaml
# .circleci/config.yml
version: 2.1

orbs:
  python: circleci/python@2.1.1

jobs:
  prompt-eval:
    docker:
      - image: cimg/python:3.11
    steps:
      - checkout

      - restore_cache:
          keys:
            - promptview-db-v1-{{ .Branch }}-{{ .Revision }}
            - promptview-db-v1-{{ .Branch }}-
            - promptview-db-v1-

      - run:
          name: Install PromptView
          command: pip install "promptview[s3]"

      - run:
          name: Init and restore DB
          command: |
            pv init --no-scan
            pv pull-remote origin

      - run:
          name: Check untracked prompts
          command: pv scan --fail-on-untracked

      - run:
          name: Run eval regression
          command: |
            pv eval run support_agent \
              --dataset evals/support_agent.jsonl \
              --scorer llm_judge \
              --provider openai

            python3 -c "
            import subprocess, json, sys
            r = subprocess.run(
                ['pv', 'metrics', 'show', 'support_agent', '--last', '1', '--json'],
                capture_output=True, text=True
            )
            d = json.loads(r.stdout)
            rate = d[-1]['pass_rate'] if d else 0
            sys.exit(0 if rate >= 75 else 1)
            "

      - save_cache:
          key: promptview-db-v1-{{ .Branch }}-{{ .Revision }}
          paths:
            - .promptview/

      - run:
          name: Push DB (main only)
          command: |
            if [ "$CIRCLE_BRANCH" = "main" ]; then
              pv push-remote origin
            fi

workflows:
  eval-workflow:
    jobs:
      - prompt-eval
```

---

## Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main
      - feature/*

pr:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

variables:
  PY_VERSION: "3.11"

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: $(PY_VERSION)

  - script: pip install "promptview[s3]"
    displayName: Install PromptView

  - script: |
      pv init --no-scan
      pv pull-remote origin
    displayName: Init and restore DB
    env:
      AWS_ACCESS_KEY_ID: $(AWS_ACCESS_KEY_ID)
      AWS_SECRET_ACCESS_KEY: $(AWS_SECRET_ACCESS_KEY)
      AWS_DEFAULT_REGION: $(AWS_REGION)

  - script: pv scan --fail-on-untracked
    displayName: Check untracked prompts

  - script: |
      pv eval run support_agent \
        --dataset evals/support_agent.jsonl \
        --scorer llm_judge \
        --provider openai

      python3 -c "
      import subprocess, json, sys
      r = subprocess.run(
          ['pv', 'metrics', 'show', 'support_agent', '--last', '1', '--json'],
          capture_output=True, text=True
      )
      d = json.loads(r.stdout)
      rate = d[-1]['pass_rate'] if d else 0
      print(f'Pass rate: {rate:.1f}%')
      sys.exit(0 if rate >= 75 else 1)
      "
    displayName: Run eval regression
    env:
      OPENAI_API_KEY: $(OPENAI_API_KEY)

  - script: pv push-remote origin
    displayName: Push prompt DB
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    env:
      AWS_ACCESS_KEY_ID: $(AWS_ACCESS_KEY_ID)
      AWS_SECRET_ACCESS_KEY: $(AWS_SECRET_ACCESS_KEY)
      AWS_DEFAULT_REGION: $(AWS_REGION)
```

---

## Jenkins (Declarative Pipeline)

```groovy
// Jenkinsfile
pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
        }
    }

    environment {
        AWS_ACCESS_KEY_ID     = credentials('aws-access-key-id')
        AWS_SECRET_ACCESS_KEY = credentials('aws-secret-access-key')
        OPENAI_API_KEY        = credentials('openai-api-key')
        PASS_RATE_THRESHOLD   = '75'
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install "promptview[s3]" --quiet'
            }
        }

        stage('Restore DB') {
            steps {
                sh '''
                    pv init --no-scan
                    pv pull-remote origin
                '''
            }
        }

        stage('Check Tracking') {
            steps {
                sh 'pv scan --fail-on-untracked'
            }
        }

        stage('Eval Regression') {
            steps {
                sh '''
                    pv eval run support_agent \
                        --dataset evals/support_agent.jsonl \
                        --scorer llm_judge \
                        --provider openai

                    python3 -c "
                    import subprocess, json, sys
                    r = subprocess.run(
                        ['pv', 'metrics', 'show', 'support_agent', '--last', '1', '--json'],
                        capture_output=True, text=True
                    )
                    d = json.loads(r.stdout)
                    rate = d[-1]['pass_rate'] if d else 0
                    threshold = float('${PASS_RATE_THRESHOLD}')
                    print(f'Pass rate: {rate:.1f}%  Threshold: {threshold}%')
                    sys.exit(0 if rate >= threshold else 1)
                    "
                '''
            }
        }

        stage('Push DB') {
            when {
                branch 'main'
            }
            steps {
                sh 'pv push-remote origin'
            }
        }
    }

    post {
        failure {
            emailext(
                subject: "PromptView eval failed — ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Eval pass rate dropped below threshold. Check: ${env.BUILD_URL}",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
```

---

## Bitbucket Pipelines

```yaml
# bitbucket-pipelines.yml
image: python:3.11-slim

definitions:
  caches:
    promptview: .promptview/

pipelines:
  pull-requests:
    '**':
      - step:
          name: PromptView Eval
          caches:
            - pip
            - promptview
          script:
            - pip install "promptview[s3]" --quiet
            - pv init --no-scan
            - pv pull-remote origin
            - pv scan --fail-on-untracked
            - pv eval run support_agent
                --dataset evals/support_agent.jsonl
                --scorer llm_judge
                --provider openai
            - python3 -c "
                import subprocess, json, sys
                r = subprocess.run(['pv','metrics','show','support_agent','--last','1','--json'],capture_output=True,text=True)
                d = json.loads(r.stdout)
                rate = d[-1]['pass_rate'] if d else 0
                sys.exit(0 if rate >= 75 else 1)"

  branches:
    main:
      - step:
          name: Push prompt DB
          script:
            - pip install "promptview[s3]" --quiet
            - pv push-remote origin
```

---

## Threshold-Based Failure

The most important pattern is failing the build automatically when quality drops. Here is a reusable shell script you can call from any CI system:

```bash
#!/usr/bin/env bash
# scripts/check_eval_threshold.sh
# Usage: ./scripts/check_eval_threshold.sh <prompt_name> <threshold_percent>
#
# Example: ./scripts/check_eval_threshold.sh support_agent 75

set -e

PROMPT="$1"
THRESHOLD="${2:-75}"

if [ -z "$PROMPT" ]; then
  echo "Usage: $0 <prompt_name> [threshold_percent]"
  exit 1
fi

echo "Checking eval threshold for '$PROMPT' (threshold: $THRESHOLD%)..."

PASS_RATE=$(pv metrics show "$PROMPT" --last 1 --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data[-1]['pass_rate'] if data else 0)
except Exception:
    print(0)
")

echo "Latest pass rate: $PASS_RATE%"

python3 -c "
import sys
rate = float('$PASS_RATE')
threshold = float('$THRESHOLD')
if rate < threshold:
    print(f'❌ FAIL: {rate:.1f}% is below threshold {threshold:.0f}%')
    sys.exit(1)
else:
    print(f'✅ PASS: {rate:.1f}% meets threshold {threshold:.0f}%')
"
```

Call it from any CI step:

```yaml
- name: Check eval threshold
  run: bash scripts/check_eval_threshold.sh support_agent 75
```

---

## Posting Eval Results as PR Comments

### GitHub Actions (built-in)

```yaml
- name: Post eval results
  if: github.event_name == 'pull_request' && always()
  uses: actions/github-script@v7
  with:
    script: |
      const { execSync } = require('child_process');

      // Gather results for all evaluated prompts
      const prompts = ['support_agent', 'code_reviewer', 'summarizer'];
      let rows = '';

      for (const prompt of prompts) {
        try {
          const output = execSync(
            `pv metrics show ${prompt} --last 1 --json`,
            { encoding: 'utf8' }
          );
          const data = JSON.parse(output);
          if (data.length > 0) {
            const run  = data[0];
            const icon = run.pass_rate >= 75 ? '✅' : '❌';
            const judge = run.avg_judge_score != null
              ? run.avg_judge_score.toFixed(2) : '—';
            rows += `| \`${prompt}\` | ${run.pass_rate.toFixed(1)}% | ${judge} | ${run.passed}/${run.total_cases} | ${icon} |\n`;
          }
        } catch (e) {
          rows += `| \`${prompt}\` | — | — | — | ⚠️ error |\n`;
        }
      }

      const body = `## 🔍 PromptView Eval Report

      | Prompt | Pass Rate | Judge Score | Cases | Status |
      |---|---|---|---|---|
      ${rows}
      <sub>Threshold: 75% · Commit: \`${context.sha.slice(0,7)}\` · [View full results](${context.payload.pull_request?.html_url})</sub>
      `;

      // Update existing comment if present, otherwise create new
      const { data: comments } = await github.rest.issues.listComments({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: context.issue.number,
      });

      const existing = comments.find(c =>
        c.user.login === 'github-actions[bot]' &&
        c.body.includes('PromptView Eval Report')
      );

      if (existing) {
        await github.rest.issues.updateComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          comment_id: existing.id,
          body
        });
      } else {
        await github.rest.issues.createComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          issue_number: context.issue.number,
          body
        });
      }
```

---

## Caching the Prompt Database

Pulling the DB from S3/GCS on every CI run adds latency. Use layer caching to speed things up:

### GitHub Actions

```yaml
- name: Cache prompt database
  uses: actions/cache@v4
  with:
    path: .promptview/
    # Bust cache only when the DB actually changes
    key: promptview-${{ hashFiles('**/*.py') }}-${{ github.sha }}
    restore-keys: |
      promptview-${{ hashFiles('**/*.py') }}-
      promptview-
```

!!! tip
    Use `hashFiles('**/*.py')` as part of the cache key so the cache busts whenever any Python file changes — which is when new prompts might appear.

---

## Running Ollama in CI (Free Evals)

Skip API costs entirely by running Ollama on a self-hosted runner with a GPU, or on standard runners for smaller datasets:

```yaml
- name: Install and start Ollama
  run: |
    curl -fsSL https://ollama.com/install.sh | sh
    ollama serve &
    # Wait for the server to be ready
    until curl -sf http://localhost:11434/api/tags > /dev/null; do sleep 1; done
    echo "Ollama is ready"

- name: Pull model
  run: ollama pull phi3

- name: Run eval with Ollama (no API cost)
  run: |
    pv eval run support_agent \
      --dataset evals/support_agent.jsonl \
      --scorer contains \
      --provider ollama \
      --model phi3
```

!!! warning "GitHub-hosted runner speed"
    Standard GitHub-hosted runners (2 vCPU, no GPU) run Ollama slowly. For production eval pipelines, use a **self-hosted runner** with a GPU, or limit Ollama runs to a small representative subset of your dataset (5–10 cases) during PRs, and run full evals on merge to main with a cloud provider.

### Self-hosted GPU runner setup

```yaml
jobs:
  eval-gpu:
    runs-on: [self-hosted, gpu]   # label your runner with 'gpu'
    steps:
      - name: Pull model if not cached
        run: ollama pull llama3 || true

      - name: Run full eval with Llama 3
        run: |
          pv eval run support_agent \
            --dataset evals/full_regression.jsonl \
            --scorer llm_judge \
            --provider ollama \
            --model llama3
```

---

## Scheduled Nightly Evals

Run evals nightly against production prompts, even without a code change:

```yaml
# .github/workflows/nightly-eval.yml
name: Nightly Eval

on:
  schedule:
    - cron: '0 2 * * *'    # 2am UTC every night
  workflow_dispatch:         # allow manual trigger

jobs:
  nightly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - run: pip install "promptview[s3]"
      - run: pv init --no-scan
      - run: pv pull-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      # Run all registered prompts against their datasets
      - name: Run nightly regression suite
        run: |
          for PROMPT in support_agent code_reviewer summarizer; do
            DATASET="evals/${PROMPT}.jsonl"
            if [ -f "$DATASET" ]; then
              echo "Evaluating $PROMPT..."
              pv eval run "$PROMPT" \
                --dataset "$DATASET" \
                --scorer llm_judge \
                --provider anthropic
            fi
          done
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

      # Push updated metrics DB
      - run: pv push-remote origin
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      # Send Slack alert if any prompt regressed
      - name: Check for regressions and alert
        run: |
          python3 scripts/check_all_thresholds.py \
            --prompts support_agent code_reviewer summarizer \
            --threshold 75 \
            --slack-webhook "$SLACK_WEBHOOK"
        env:
          SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Slack Notifications on Regression

Create `scripts/notify_slack.py`:

```python
#!/usr/bin/env python3
"""Post eval results to Slack when a prompt regresses."""
import argparse
import json
import subprocess
import sys
import urllib.request

def get_pass_rate(prompt: str) -> float | None:
    try:
        r = subprocess.run(
            ["pv", "metrics", "show", prompt, "--last", "1", "--json"],
            capture_output=True, text=True
        )
        data = json.loads(r.stdout)
        return data[-1]["pass_rate"] if data else None
    except Exception:
        return None

def post_slack(webhook: str, message: str) -> None:
    payload = json.dumps({"text": message}).encode()
    req = urllib.request.Request(
        webhook,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    urllib.request.urlopen(req)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", nargs="+", required=True)
    parser.add_argument("--threshold", type=float, default=75.0)
    parser.add_argument("--slack-webhook", required=True)
    args = parser.parse_args()

    regressions = []
    for prompt in args.prompts:
        rate = get_pass_rate(prompt)
        if rate is not None and rate < args.threshold:
            regressions.append((prompt, rate))

    if regressions:
        lines = "\n".join(
            f"  • `{p}` — {r:.1f}% (threshold: {args.threshold:.0f}%)"
            for p, r in regressions
        )
        message = (
            f":rotating_light: *PromptView Regression Detected*\n\n"
            f"The following prompts are below threshold:\n{lines}\n\n"
            f"Run `pv metrics show <prompt>` or open the UI to investigate."
        )
        post_slack(args.slack_webhook, message)
        print(message)
        sys.exit(1)
    else:
        print(f"All prompts above {args.threshold:.0f}% threshold. ✅")

if __name__ == "__main__":
    main()
```

---

## Secrets Reference

Configure these secrets in your CI provider's secret store:

### AWS S3 remote

| Secret name | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `AWS_REGION` | Region (e.g. `us-east-1`) |

Minimum IAM permissions:
```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject", "s3:PutObject", "s3:HeadObject"],
  "Resource": "arn:aws:s3:::your-bucket/promptview/*"
}
```

### GCS remote

| Secret name | Description |
|---|---|
| `GCP_SA_KEY_B64` | Base64-encoded service account JSON |

Usage:
```yaml
- run: |
    echo "$GCP_SA_KEY_B64" | base64 --decode > /tmp/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp-key.json
    pv pull-remote origin
  env:
    GCP_SA_KEY_B64: ${{ secrets.GCP_SA_KEY_B64 }}
```

### LLM providers

| Secret | Environment variable |
|---|---|
| `OPENAI_API_KEY` | `OPENAI_API_KEY` |
| `ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` |
| `GOOGLE_API_KEY` | `GOOGLE_API_KEY` |

---

## Multi-Environment Workflow

Use different remotes for staging vs production:

```bash
# Register two remotes locally
pv remote add production  s3://my-company/prompts/production/
pv remote add staging     s3://my-company/prompts/staging/
```

```yaml
# In CI:
# PRs pull from staging — cheaper, lower stakes
- name: Restore staging DB
  if: github.event_name == 'pull_request'
  run: pv pull-remote staging

# Merges to main pull from production, then push back
- name: Restore production DB
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: pv pull-remote production

- name: Push updated production DB
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: pv push-remote production
```

---

## Quick Reference — What to Put Where

| Step | When | Purpose |
|---|---|---|
| `pv init --no-scan` | Every run | Set up `.promptview/` without auto-scan |
| `pv pull-remote origin` | Every run | Restore shared DB |
| `pv scan --fail-on-untracked` | Every PR | Block untracked prompts |
| `pv eval run ...` | Every PR | Run regression suite |
| `check_eval_threshold.sh` | Every PR | Fail if pass rate drops |
| PR comment with scores | Every PR | Visibility into quality |
| `pv push-remote origin` | Merge to main | Write updated DB back |
| Nightly workflow | Daily | Full regression + alerts |

---

## See Also

- [Remote Backends](../integrations/remote-backends.md) — S3, GCS, HTTP setup
- [Evaluations Overview](../eval/overview.md) — datasets and scorers
- [Viewing Eval Results](../eval/results.md) — per-case actual responses
- [Team Workflow](team-workflow.md) — how the whole team uses PromptView together
- [pv hooks & cicd CLI](../cli/hooks-cicd.md) — `pv hooks install` and `pv cicd generate`
