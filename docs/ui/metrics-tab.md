# Metrics & Evals Tab

The Metrics tab in the web UI shows the full eval history for a prompt — aggregate run summaries and, on click, the per-case actual LLM responses with scores and judge reasoning.

---

## Opening the Metrics Tab

Select a prompt in the sidebar, then click the **Metrics** tab in the main area.

---

## Eval Runs Table

The Metrics tab displays a table of all eval runs for the selected prompt:

```
Eval Runs: my_prompt

  Run ID    Version  Date                Pass Rate  Passed/Total  Judge   Latency
  ──────────────────────────────────────────────────────────────────────────────────
  a1b2c3d4  v3       2024-03-16 14:22    70.0%      7/10          0.82    445ms
  b5c6d7e8  v2       2024-03-15 10:15    50.0%      5/10          0.71    512ms
  f9a0b1c2  v1       2024-03-14 09:03    30.0%      3/10          0.58    489ms
```

Columns:
- **Run ID** — 8-character identifier, matches `pv metrics show` output
- **Version** — which prompt version was tested
- **Date** — when the eval was run
- **Pass Rate** — percentage of test cases that passed
- **Passed/Total** — counts
- **Judge** — average LLM judge score (0–1), shown if `llm_judge` scorer was used
- **Latency** — average response time per case

---

## Expanding a Run — Per-Case Results

Click any row in the table to expand it and see per-case results:

```
▼  Run a1b2c3d4 — 10 cases — 70% pass rate

  ─── Case 1  ✓ PASS ──────────────────────────────────────────────
  Input
  │  Translate 'hello' to French

  Actual Response
  │  Bonjour

  Expected
  │  Bonjour

  Scores: similarity=1.00 · latency=432ms

  ─── Case 2  ✗ FAIL ──────────────────────────────────────────────
  Input
  │  Translate 'good morning' to French

  Actual Response
  │  In French, "good morning" can be expressed as "Bonjour" which
  │  is used throughout the day, or "Bon matin" in Quebec French.
  │  The standard formal greeting would be "Bonjour, Madame/Monsieur."

  Expected
  │  Bonjour

  Scores: similarity=0.21 · judge=0.45 · latency=521ms
  Judge reasoning: Technically correct but too verbose; the test
    expects a single-word translation, not an explanation.
```

---

## Case Card Anatomy

Each case card shows:

| Section | Description |
|---|---|
| **Status badge** | Green ✓ PASS or red ✗ FAIL |
| **Input** | The test case's user message sent to the LLM |
| **Actual Response** | The real LLM output, displayed in blue |
| **Expected** | The `expected_output` from the JSONL dataset (if present) |
| **Scores** | `similarity`, `judge`, `latency_ms` — whichever are available |
| **Judge reasoning** | The LLM judge's one-sentence explanation (if `llm_judge` was used) |

---

## Pass/Fail Colour Coding

- **Green border + ✓ PASS** — the case passed scoring
- **Red border + ✗ FAIL** — the case failed scoring

Passing criteria (from `EvalRunner`):
1. `exact_match(actual, expected)` → passes if `True`
2. If exact match fails, `similarity_score >= 0.8` → also counts as pass
3. If `llm_judge` scorer: `judge_score >= 0.6` when no expected output is provided

---

## Judge Reasoning Display

When the `llm_judge` scorer is used, each case shows the LLM judge's reasoning in italic. This explains *why* a response got a particular score:

```
Judge reasoning: Response is coherent and accurate but misses the
  requested JSON format specified in the prompt constraints.
```

This is invaluable for understanding prompt failures — often the actual response is "correct" but not in the expected format, and the reasoning makes that clear.

---

## Running a New Eval from the UI

Click the **Run Eval** button above the table:

1. A modal opens asking for:
   - Dataset path (JSONL file on the server)
   - Scorer type
   - LLM config (uses your localStorage settings by default)
2. Click **Run**
3. The table updates live as results come in
4. Click the new row to see per-case results

---

## Comparing Versions via the UI

To compare how prompt changes affect quality:

1. Note the pass rate for v2 (e.g. 50%)
2. Edit a component → new v3 created
3. Click **Run Eval** again on v3
4. Both rows appear in the table
5. Pass rate for v3 (e.g. 70%) shows improvement

For a structured side-by-side comparison with delta columns, use the CLI:

```bash
pv metrics compare a1b2c3d4 b5c6d7e8 --prompt my_prompt
```

---

## CLI Equivalent

All data in the Metrics tab is also accessible from the CLI:

```bash
# Summary table
pv metrics show my_prompt

# Per-case responses
pv metrics results a1b2c3d4 --prompt my_prompt

# Failures only
pv metrics results a1b2c3d4 --prompt my_prompt --failed

# Side-by-side comparison
pv metrics compare a1b2c3d4 b5c6d7e8 --prompt my_prompt
```

---

## See Also

- [Evaluations Overview](../eval/overview.md)
- [Scorers](../eval/scorers.md)
- [Viewing Results](../eval/results.md)
- [pv eval & metrics CLI](../cli/eval-metrics.md)
