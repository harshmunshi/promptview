# Scorers

A scorer is a function that takes the LLM's actual output and optionally an expected output, and returns a pass/fail result plus a numeric score.

---

## Built-in Scorers

### `exact_match`

**What it does:** Compares the actual output to the expected output after stripping leading/trailing whitespace and converting both to lowercase.

**Use when:**
- The output is deterministic or near-deterministic (translations, classifications, IDs)
- You want zero tolerance for variation
- Outputs are short single words or short phrases

**How it works:**
```python
def exact_match(actual: str, expected: str) -> bool:
    return actual.strip().lower() == expected.strip().lower()
```

**Example:**
```jsonl
{"input": "What is 2 + 2?", "expected_output": "4"}
```
- Actual: `"4"` → PASS
- Actual: `" 4 "` → PASS (whitespace stripped)
- Actual: `"4."` → FAIL
- Actual: `"The answer is 4"` → FAIL

**Similarity fallback:** If exact match fails but `similarity_score >= 0.8` (from difflib SequenceMatcher), the case still counts as passed. This handles minor formatting variations like trailing punctuation.

---

### `contains`

**What it does:** Checks if the actual output contains the expected string as a substring (case-insensitive after stripping).

**Use when:**
- The output must mention a specific term, phrase, or value
- You don't care about surrounding text
- The expected output is a keyword or required phrase within a longer response

**How it works:**
```python
def contains(actual: str, expected: str) -> bool:
    return expected.strip().lower() in actual.strip().lower()
```

**Example:**
```jsonl
{"input": "Name the capital of France", "expected_output": "Paris"}
```
- Actual: `"Paris"` → PASS
- Actual: `"The capital of France is Paris."` → PASS
- Actual: `"Paris is the most populous city of France and serves as its capital."` → PASS
- Actual: `"Lyon"` → FAIL

**Note:** `contains` is not currently a separate `--scorer` option in `pv eval run`. It is implemented as a utility function. The primary CLI options are `exact_match` and `llm_judge`. For contains-style checking with more flexibility, use `llm_judge` with a custom criterion.

---

### `llm_judge`

**What it does:** Asks a separate LLM to grade the quality of the actual output on a 1–5 scale based on criteria. Returns a normalized score (0.0–1.0) and a one-sentence reasoning string.

**Use when:**
- Outputs are open-ended or creative
- You want to evaluate tone, coherence, accuracy without exact matching
- You have no expected output
- Quality matters beyond binary pass/fail

**How it works:**

The judge LLM receives:
```
System:
  You are an expert evaluator. Score LLM outputs on a 1-5 scale based
  on the given criteria. Respond ONLY with valid JSON:
  {"score": <1-5>, "reasoning": "<one sentence>"}

User:
  Criteria: relevance, coherence, accuracy
  Actual output:
  [the actual LLM response]

  Expected output:    ← only if expected_output is present
  [the expected response]

  Respond with JSON only.
```

**Score normalization:**
- Raw score 1 → 0.0 (worst)
- Raw score 3 → 0.5 (average)
- Raw score 5 → 1.0 (best)
- Formula: `(raw_score - 1) / 4`

**Pass threshold:** A case passes if `judge_score >= 0.6` (raw score ≥ 3.4) when there is no expected output. When there IS an expected output, exact_match / similarity is used for pass/fail and the judge score is supplementary.

**Example:**

```jsonl
{"input": "Summarize this article: [article...]"}
```

Judge response:
```json
{"score": 4, "reasoning": "Summary is accurate and concise but omits one key fact about the timeline."}
```

Normalized score: `(4-1)/4 = 0.75` → PASS (above 0.6 threshold)

**Custom criteria:**

```bash
pv eval run my_prompt \
  --dataset evals/cases.jsonl \
  --scorer llm_judge \
  --judge-criteria "accuracy,professional_tone,follows_json_format"
```

---

## Similarity Score

In addition to pass/fail, PromptView always computes a `similarity_score` (0.0–1.0) using Python's `difflib.SequenceMatcher` when `expected_output` is present:

```python
import difflib

score = difflib.SequenceMatcher(
    None,
    actual.strip(),
    expected.strip()
).ratio()
```

This provides a continuous quality signal even when exact match fails. A score of 0.8+ causes a case to pass even if exact match fails (accounts for minor formatting differences).

---

## Choosing the Right Scorer

```
Is the output deterministic?
  Yes → Use exact_match
  No  ↓

Does the output need to contain a specific phrase?
  Yes → Use contains logic (or llm_judge with "must contain X" criterion)
  No  ↓

Is quality more important than exact format?
  Yes → Use llm_judge

Do you have a reference output to compare against?
  Yes → Use llm_judge with expected_output for grounding
  No  → Use llm_judge with general criteria
```

---

## Using Multiple Scorers

Currently, each eval run uses one scorer. For comprehensive evaluation, run the same dataset twice with different scorers:

```bash
# Run 1: check format compliance
pv eval run my_prompt --dataset evals/cases.jsonl --scorer exact_match --provider openai

# Run 2: check quality
pv eval run my_prompt --dataset evals/cases.jsonl --scorer llm_judge --provider openai
```

Compare both runs in the metrics table to get a complete picture.

---

## See Also

- [Eval Overview](overview.md)
- [Datasets](datasets.md)
- [Viewing Results](results.md)
- [pv eval & metrics CLI](../cli/eval-metrics.md)
