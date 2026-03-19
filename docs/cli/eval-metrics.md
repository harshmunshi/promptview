# pv eval & pv metrics

Run structured test suites against prompt versions and track quality scores over time.

---

## pv eval run

### Synopsis

```bash
pv eval run NAME [OPTIONS]
```

### Description

`pv eval run` executes a JSONL test dataset against a specific prompt version using a real LLM. It scores each test case, records the actual LLM responses, and stores all results for later inspection.

### Arguments

| Argument | Description |
|---|---|
| `NAME` | Prompt name to evaluate |

### Options

| Option | Description | Default |
|---|---|---|
| `--dataset PATH` | Path to JSONL test cases file | Required |
| `--scorer TEXT` | Scoring method: `exact_match`, `contains`, `llm_judge` | `exact_match` |
| `--provider TEXT` | LLM provider for running the prompt | `openai` |
| `--api-key TEXT` | API key (falls back to env var) | — |
| `--model TEXT` | Model override | Provider default |
| `--version INTEGER` | Evaluate a specific version (default: latest) | Latest |
| `--judge-provider TEXT` | Separate LLM provider for judging (defaults to same as `--provider`) | Same |

### Examples

```bash
# Basic eval with exact_match
pv eval run my_prompt --dataset evals/cases.jsonl --provider openai

# Use LLM judge for open-ended scoring
pv eval run my_prompt --dataset evals/cases.jsonl --scorer llm_judge --provider openai

# Evaluate a specific version
pv eval run my_prompt --dataset evals/cases.jsonl --provider openai --version 3

# Use Anthropic for running, OpenAI for judging
pv eval run my_prompt \
  --dataset evals/cases.jsonl \
  --scorer llm_judge \
  --provider anthropic \
  --judge-provider openai

# Use Ollama (free, local)
pv eval run my_prompt --dataset evals/cases.jsonl --provider ollama --model llama3
```

### JSONL Dataset Format

Each line in the dataset file is a JSON object:

```jsonl
{"input": "Translate 'hello' to French", "expected_output": "Bonjour"}
{"input": "Translate 'goodbye' to French", "expected_output": "Au revoir"}
{"input": "Translate 'thank you' to French", "expected_output": "Merci"}
```

Fields:
- `input` (required) — the user message sent to the LLM
- `expected_output` (optional) — the expected response for scoring
- `tags` (optional) — list of strings for filtering

If `expected_output` is omitted, exact_match and contains scorers will not pass any cases. Use `llm_judge` for open-ended quality scoring without expected outputs.

### Output

```
Running eval: my_prompt (v3) against 10 cases
Provider: openai (gpt-4o-mini)
Scorer: exact_match

  Case 1/10  ✓  PASS   latency=432ms
  Case 2/10  ✗  FAIL   latency=521ms
  Case 3/10  ✓  PASS   latency=398ms
  ...

Results:
  Pass rate:    7/10 (70.0%)
  Avg latency:  445ms
  Run ID:       a1b2c3d4

Use 'pv metrics results a1b2c3d4 --prompt my_prompt' to see per-case responses.
```

---

## pv metrics show

### Synopsis

```bash
pv metrics show NAME [OPTIONS]
```

### Description

Show aggregated eval metrics for all runs against a prompt, organized by version.

### Options

| Option | Description | Default |
|---|---|---|
| `--last, -n N` | Show last N eval runs | 10 |
| `--version INTEGER` | Filter to a specific version number | All |
| `--plot` | Show ASCII sparkline of pass rate over time | Off |

### Examples

```bash
pv metrics show my_prompt
pv metrics show my_prompt --last 20
pv metrics show my_prompt --version 3
pv metrics show my_prompt --plot
```

### Output

```
                    Metrics: my_prompt
┌──────────┬─────────┬──────────┬───────────┬─────────────┬────────────┬─────────────┬─────────────────────┐
│ Run ID   │ Version │ Source   │ Pass Rate │ Passed/Total│ Judge Score│ Avg Latency │ Run At              │
├──────────┼─────────┼──────────┼───────────┼─────────────┼────────────┼─────────────┼─────────────────────┤
│ a1b2c3d4 │ v3      │ local    │ 70.0%     │ 7/10        │ 0.82       │ 445ms       │ 2024-03-16 14:22:07 │
│ b5c6d7e8 │ v2      │ local    │ 50.0%     │ 5/10        │ 0.71       │ 512ms       │ 2024-03-15 10:15:33 │
│ f9a0b1c2 │ v1      │ local    │ 30.0%     │ 3/10        │ 0.58       │ 489ms       │ 2024-03-14 09:03:21 │
└──────────┴─────────┴──────────┴───────────┴─────────────┴────────────┴─────────────┴─────────────────────┘
```

---

## pv metrics results

### Synopsis

```bash
pv metrics results RUN_ID --prompt NAME [OPTIONS]
```

### Description

Show the per-case inputs, actual LLM responses, expected outputs, and all scores for a specific eval run. This is the command for debugging failures and understanding what the LLM actually said.

### Arguments

| Argument | Description |
|---|---|
| `RUN_ID` | Full or prefix of the eval run ID (from `pv metrics show`) |

### Options

| Option | Description |
|---|---|
| `--prompt, -p NAME` | Prompt name (required) |
| `--failed, -f` | Show only failed test cases |

### Examples

```bash
# Show all cases for a run
pv metrics results a1b2c3d4 --prompt my_prompt

# Show only failed cases
pv metrics results a1b2c3d4 --prompt my_prompt --failed

# Use just a prefix of the run ID
pv metrics results a1b2 --prompt my_prompt
```

### Output

```
Eval run a1b2c3d4 — 10 case(s)

─── Case 1 ✓ PASS ───────────────────────────
Input:
  Translate 'hello' to French

Actual response:
  Bonjour

Expected:
  Bonjour

similarity=1.00 · latency=432ms

─── Case 2 ✗ FAIL ───────────────────────────
Input:
  Translate 'good morning' to French

Actual response:
  Good morning in French is "Bonjour" which is used as a general
  greeting. However, the more precise morning greeting would be
  "Bonjour" or "Bon matin" depending on regional usage.

Expected:
  Bonjour

similarity=0.21 · judge=0.45 · latency=521ms
Judge reasoning: Response is technically correct but overly verbose
  for the expected concise translation format.

...

Summary: 7/10 passed
```

---

## pv metrics compare

### Synopsis

```bash
pv metrics compare V1 V2 --prompt NAME
```

### Description

Compare two eval runs side-by-side with a delta column — useful for measuring the impact of prompt changes.

### Examples

```bash
pv metrics compare a1b2c3d4 b5c6d7e8 --prompt my_prompt

# Also works with version numbers (uses most recent run for that version)
pv metrics compare 3 2 --prompt my_prompt
```

### Output

```
                  Comparison
┌─────────────┬───────────────────┬───────────────────┬────────────┐
│ Metric      │ Run a1b2c3d4 (v3) │ Run b5c6d7e8 (v2) │ Delta      │
├─────────────┼───────────────────┼───────────────────┼────────────┤
│ Pass Rate   │ 70.0%             │ 50.0%             │ +20.0%     │
│ Passed      │ 7                 │ 5                 │ +2         │
│ Total Cases │ 10                │ 10                │ -          │
│ Judge Score │ 0.82              │ 0.71              │ +0.11      │
│ Avg Latency │ 445ms             │ 512ms             │ -67ms      │
│ Source      │ local             │ local             │ -          │
└─────────────┴───────────────────┴───────────────────┴────────────┘
```

Positive deltas are shown in green, negative in red.

---

## See Also

- [Evaluations Overview](../eval/overview.md)
- [Datasets](../eval/datasets.md)
- [Scorers](../eval/scorers.md)
- [Viewing Results](../eval/results.md)
- [Metrics & Evals UI](../ui/metrics-tab.md)
