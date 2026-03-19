# Evaluations Overview

The eval framework lets you run structured test suites against any prompt version and track quality scores over time. It answers the question: "Did this prompt change make the output better or worse?"

---

## The Problem It Solves

When you edit a prompt, you need to know:
- Do the outputs still match what the application expects?
- Did quality improve or regress?
- Which version performs best on your specific test cases?

Without evals, you rely on manual inspection — which is slow, inconsistent, and doesn't scale to dozens of prompt versions.

---

## Core Concepts

| Concept | Description |
|---|---|
| **Test Case** | A single input + optional expected output |
| **Dataset** | A JSONL file of test cases |
| **Scorer** | A function that grades `actual_output` against `expected_output` |
| **Eval Run** | Execution of a dataset against one prompt version with one scorer |
| **Eval Result** | Per-case record: actual output, pass/fail, scores, latency |
| **Metrics** | Aggregate stats for a run: pass_rate, avg_judge_score, avg_latency |

---

## When to Use Evals

Use evals when:

- You have a set of expected outputs (translation, extraction, classification tasks)
- You want to measure quality regression after prompt edits
- You want to compare two versions systematically
- You want to track quality trends across many iterations
- You need to validate that a prompt change didn't break existing functionality

Evals are most valuable for:
- **High-volume prompts** — run in production many times per day
- **Structured output prompts** — JSON, lists, formatted text
- **Translation / conversion tasks** — where expected output is deterministic
- **Classification prompts** — where outputs are from a fixed set

---

## Workflow

```
1. Write test cases
   → Create a JSONL file with input/expected pairs

2. Run an eval
   → pv eval run my_prompt --dataset evals/cases.jsonl --provider openai

3. View aggregate metrics
   → pv metrics show my_prompt
   → Check pass_rate, judge_score, avg_latency

4. Inspect failures
   → pv metrics results <run_id> --prompt my_prompt --failed
   → See exactly what the LLM said for each failing case

5. Edit the prompt
   → Make changes in the UI or source code
   → pv add . && pv commit -m "Fix output format"

6. Run eval again on the new version
   → pv eval run my_prompt --dataset evals/cases.jsonl --provider openai --version 2

7. Compare
   → pv metrics compare run1 run2 --prompt my_prompt
   → See the delta in pass rate, judge score, latency
```

---

## Choosing a Scorer

| Scorer | Best For | Requires Expected Output |
|---|---|---|
| `exact_match` | Deterministic outputs (translations, IDs, enums) | Yes |
| `contains` | Outputs that must include specific text | Yes |
| `llm_judge` | Open-ended responses, quality assessment | Optional |

- Start with `exact_match` for structured/deterministic tasks
- Use `llm_judge` for conversational or creative tasks
- Use `contains` when the output must mention a specific term or phrase

The default scorer is `exact_match`. A high similarity score (≥ 0.8) also counts as passing even if exact match fails — this handles minor formatting variations.

---

## Example: Full Eval Workflow

```bash
# Create a dataset for a translation prompt
cat > evals/french_translation.jsonl << 'EOF'
{"input": "Translate to French: hello", "expected_output": "Bonjour"}
{"input": "Translate to French: goodbye", "expected_output": "Au revoir"}
{"input": "Translate to French: thank you", "expected_output": "Merci"}
{"input": "Translate to French: please", "expected_output": "S'il vous plaît"}
{"input": "Translate to French: yes", "expected_output": "Oui"}
EOF

# Run eval
pv eval run french_translator --dataset evals/french_translation.jsonl --provider openai

# Check results
pv metrics show french_translator

# See failures
pv metrics results <run_id> --prompt french_translator --failed

# Edit prompt to fix failures, then re-evaluate
pv add french_translator
pv commit -m "Add instruction to give single-word translation only"
pv eval run french_translator --dataset evals/french_translation.jsonl --provider openai

# Compare
pv metrics compare <old_run_id> <new_run_id> --prompt french_translator
```

---

## Data Storage

All eval data is stored in `promptview.db`:

- `eval_runs` — aggregate run records (pass_rate, avg_judge_score, etc.)
- `eval_results` — per-case records (actual_output, passed, scores, reasoning)
- `test_cases` — deduped test case records (input + expected_output)

This means eval history persists across sessions and is included in `pv push-remote` backups.

---

## See Also

- [Datasets](datasets.md) — JSONL format reference
- [Scorers](scorers.md) — how each scorer works
- [Viewing Results](results.md) — CLI and UI result inspection
- [pv eval & metrics CLI](../cli/eval-metrics.md)
