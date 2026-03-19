# pv scan

Scan the codebase for LLM prompts using AST analysis.

---

## Synopsis

```bash
pv scan [PATH] [OPTIONS]
```

---

## Description

`pv scan` recursively walks your Python source files and uses the Python AST to detect strings being used as LLM prompts. It supports OpenAI, Anthropic, LangChain, LiteLLM, and raw string patterns.

Scanning does not modify any files or create any versions. It only identifies candidates for you to review and stage with `pv add`.

---

## Arguments

| Argument | Description | Default |
|---|---|---|
| `PATH` | Directory to scan | Project root (from `.promptview/` discovery) |

---

## Options

| Option | Description | Default |
|---|---|---|
| `--min-confidence FLOAT` | Only show prompts above this confidence threshold | `0.60` |
| `--show-all` | Show all prompts including very low confidence ones | Off |

---

## Examples

```bash
# Scan the whole project
pv scan

# Scan a specific subdirectory
pv scan src/agents/

# Only show high-confidence detections
pv scan --min-confidence 0.85

# Show everything the scanner found, including questionable matches
pv scan --show-all
```

---

## Reading the Output

```
Scanning /my-project/src ...

  src/agent.py:42        system_prompt          openai     confidence=0.95
  src/agent.py:67        user_template          openai     confidence=0.88
  src/summarizer.py:15   summarize_prompt       anthropic  confidence=0.92
  src/utils.py:8         BASE_INSTRUCTIONS      raw        confidence=0.72
  src/utils.py:31        response_schema        raw        confidence=0.61

Found 5 prompts across 3 files.
2 already tracked, 3 new.
```

Columns:
- **File + Line**: where in the source code the string was found
- **Name**: the Python variable name or a generated name
- **Source**: which SDK pattern matched (`openai`, `anthropic`, `langchain`, `litellm`, `raw`)
- **Confidence**: 0.0–1.0 reliability score

---

## Confidence Score Ranges

| Score | Meaning |
|---|---|
| 0.90–1.00 | Direct string literal in an SDK call — highly reliable |
| 0.75–0.89 | Variable reference resolved to a string |
| 0.60–0.74 | Heuristic match on variable name |
| Below 0.60 | Uncertain — shown only with `--show-all` |

---

## What Gets Detected

### OpenAI Pattern
```python
# Detected — direct string
client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "You are a helpful assistant."}]
)

# Detected — variable reference
SYSTEM = "You are a helpful assistant."
client.chat.completions.create(
    messages=[{"role": "system", "content": SYSTEM}]
)
```

### Anthropic Pattern
```python
# Detected
client.messages.create(
    model="claude-haiku-4-5",
    system="You are a code reviewer. Look for bugs and security issues.",
    messages=[{"role": "user", "content": code}]
)
```

### LangChain Pattern
```python
from langchain.prompts import ChatPromptTemplate

# Detected
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a translation assistant."),
    ("human", "Translate this: {text}")
])
```

### Raw String Pattern
```python
# Detected — name suggests it is a prompt
SUMMARIZE_PROMPT = """
You are a summarizer. Produce a 3-sentence summary of the document.
Focus on facts. Avoid opinions.
"""

# Detected — name suggests it is a template
response_template = "Format your response as: {format}"

# NOT detected — too generic
message = "Hello"
text = "some text"
```

---

## What Gets Skipped

The scanner skips these directories automatically:
- `.venv/`, `venv/`, `env/`
- `node_modules/`
- `__pycache__/`
- `.git/`
- `.promptview/`
- `dist/`, `build/`

Only `.py` files are processed.

---

## Nothing Found?

If `pv scan` finds nothing:

1. **Check your directory**: are you in the project root? Try `pv scan src/`
2. **Variable references**: if your prompts are imported from another module, the scanner can't resolve them. Consider using `pv add --manual`
3. **Dynamic strings**: f-strings and concatenated strings cannot be statically resolved
4. **Lower the threshold**: try `pv scan --show-all` to see everything the scanner finds

---

## After Scanning

The scan results are held in memory. Use `pv add` to move them to the staging area:

```bash
pv scan
pv add .                          # stage all found prompts
pv add system_prompt              # stage by name
pv add --file src/agent.py        # stage all prompts from one file
pv add . --min-confidence 0.80    # stage only high-confidence ones
```

---

## Scanning in CI

```bash
# Fail if there are untracked prompts
pv scan --fail-on-untracked
```

Use this in your GitHub Actions workflow to enforce that all prompts are tracked before merging.

---

## See Also

- [pv add & commit](add-commit.md)
- [Prompt Scanner internals](../how-it-works/scanner.md)
- [pv hooks & cicd](hooks-cicd.md)
