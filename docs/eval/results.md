# Viewing Eval Results

After running an eval, you can inspect every test case's actual LLM response, pass/fail status, scores, and judge reasoning — both in the CLI and the web UI.

---

## What Gets Stored Per Result

For each test case in an eval run, PromptView stores an `EvalResult` record:

| Field | Description |
|---|---|
| `eval_run_id` | Which eval run this belongs to |
| `test_case_id` | Which test case was used |
| `actual_output` | The actual LLM response text |
| `passed` | Boolean — did this case pass? |
| `similarity_score` | difflib ratio against expected (0.0–1.0) |
| `judge_score` | LLM judge score normalized to 0.0–1.0 (if used) |
| `judge_reasoning` | One-sentence explanation from the judge LLM |
| `latency_ms` | Time to get the LLM response (milliseconds) |
| `tokens_used` | Token count (when available) |
| `cost_usd` | Estimated cost in USD |

---

## CLI: pv metrics results

### View All Cases

```bash
pv metrics results <run_id> --prompt my_prompt
```

You can use a prefix of the run ID — whatever is unique enough:

```bash
pv metrics results a1b2 --prompt my_prompt
```

### View Only Failures

```bash
pv metrics results a1b2c3d4 --prompt my_prompt --failed
```

This shows only the cases that did not pass — useful for debugging prompt failures.

### Full Output Format

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
  In French, "good morning" can be expressed as "Bonjour" which
  is used throughout the day, or "Bon matin" in Quebec French.

Expected:
  Bonjour

similarity=0.21 · judge=0.45 · latency=521ms
Judge reasoning: Technically correct but too verbose; expected a
  single-word translation.

─── Case 3 ✓ PASS ───────────────────────────
Input:
  Translate 'thank you' to French

Actual response:
  Merci

Expected:
  Merci

similarity=1.00 · latency=398ms

...

Summary: 7/10 passed
```

### What Each Section Shows

| Section | Description |
|---|---|
| **Case N STATUS** | Pass (green ✓) or Fail (red ✗) |
| **Input** | The `input` field from the JSONL dataset |
| **Actual response** | What the LLM actually said (shown in cyan) |
| **Expected** | The `expected_output` from the dataset (omitted if not set) |
| **Scores** | `similarity`, `judge`, `latency` — whichever are available |
| **Judge reasoning** | The LLM judge's explanation (italic) |

---

## UI: Metrics Tab

In `pv ui`, click the **Metrics** tab for a prompt, then click any run row to expand per-case results.

### Case Cards

Each case displays as an expandable card:

```
─────────────────────────────────────────────────────
✗ FAIL  Case 2
─────────────────────────────────────────────────────
Input
│  Translate 'good morning' to French

Actual Response
│  In French, "good morning" can be expressed as "Bonjour"
│  which is used throughout the day...

Expected
│  Bonjour

similarity=0.21  judge=0.45  latency=521ms
Judge reasoning: Technically correct but too verbose.
─────────────────────────────────────────────────────
```

**Colour coding:**
- Green card border = PASS
- Red card border = FAIL
- Blue text for actual response (makes it visually distinct from input/expected)

---

## Understanding Failure Patterns

When reviewing failures, look for:

### Format Failures
```
Expected: "positive"
Actual:   "The sentiment is positive."
```
Fix: Add "Respond with a single word only." to your Output Format component.

### Verbosity Failures
```
Expected: "Bonjour"
Actual:   "In French, 'Bonjour' is the standard greeting..."
```
Fix: Add "Give a direct single-word answer only." to Constraints.

### Hallucination Failures
```
Expected: "Au revoir"
Actual:   "À bientôt"
```
Fix: May require more specific instructions or examples.

### Refusal Failures
```
Expected: "Yes"
Actual:   "I can't provide a definitive yes/no answer..."
```
Fix: Clarify that the model should commit to an answer.

---

## Using Results to Improve Prompts

The typical improvement loop:

```
1. Run eval → see 50% pass rate

2. pv metrics results <run_id> --prompt my_prompt --failed
   → Identify: 3 failures are format issues, 2 are hallucinations

3. Edit prompt in UI:
   → Add to Output Format: "Respond with a single word or short phrase only."
   → Add to Examples: correct examples for the tricky cases

4. pv commit -m "Fix verbosity failures in translation prompt"

5. pv eval run my_prompt --dataset evals/cases.jsonl --provider openai
   → 80% pass rate (improvement!)

6. pv metrics compare <old_run> <new_run> --prompt my_prompt
   → Confirm +30% pass rate, +0.15 judge score
```

---

## Filtering and Analysis

### Failed Cases Only (CLI)

```bash
pv metrics results a1b2c3d4 --prompt my_prompt --failed
```

### All Cases for a Version

```bash
# Show all eval runs for version 3
pv metrics show my_prompt --version 3

# Get the run ID, then show results
pv metrics results <run_id_for_v3> --prompt my_prompt
```

---

## See Also

- [Scorers](scorers.md) — how pass/fail is determined
- [Metrics & Evals UI](../ui/metrics-tab.md) — viewing results in the browser
- [pv eval & metrics CLI](../cli/eval-metrics.md)
