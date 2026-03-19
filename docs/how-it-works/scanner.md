# Prompt Scanner

The scanner is PromptView's discovery engine. It walks your Python codebase, parses each file with Python's built-in `ast` module, and identifies strings that are being used as LLM prompts — without requiring any code changes or annotations.

---

## How It Works

```
Directory walker (base.py)
  └── Recursively visits .py files
  └── Skips: .venv, node_modules, __pycache__, .git, .promptview, dist, build

AST visitor (ast_visitor.py)
  └── Parses each file to AST
  └── Walks the tree looking for function calls matching SDK patterns
  └── Extracts string arguments from matching calls
  └── Assigns confidence score based on match quality

Variable resolver (resolver.py)
  └── If the string argument is a variable name, follows it to its assigned value
  └── Builds a symbol table of Name → string content

Result (result.py)
  └── ScannedPrompt dataclass: name, content, source, file_path, line_number, confidence
```

---

## Supported Detection Patterns

### OpenAI

Detects `client.chat.completions.create(...)` and `openai.chat.completions.create(...)`:

```python
# Detected — system message content extracted
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_message}
    ]
)

# Also detected — variable reference resolved
SYSTEM_PROMPT = "You are a senior engineer. Review this code carefully."

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": SYSTEM_PROMPT}]
)
```

### Anthropic

Detects `client.messages.create(...)`:

```python
# Detected
message = client.messages.create(
    model="claude-haiku-4-5",
    system="You are a helpful assistant that summarizes documents.",
    messages=[{"role": "user", "content": document_text}]
)
```

### LangChain

Detects `ChatPromptTemplate.from_messages(...)` and `PromptTemplate.from_template(...)`:

```python
from langchain.prompts import ChatPromptTemplate

# Detected
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a translation assistant. Translate from {source_lang} to {target_lang}."),
    ("human", "{text}")
])
```

### LiteLLM

Detects `litellm.completion(...)`:

```python
import litellm

response = litellm.completion(
    model="gpt-4o-mini",
    messages=[{"role": "system", "content": "You are a code reviewer."}]
)
```

### Raw String Patterns

Detects string variables with names that suggest they are prompts:

```python
# Detected — name contains "prompt", "system", "instruction", "template"
SUMMARIZE_PROMPT = """
You are a document summarizer. Given an article, produce a 3-sentence summary.
Focus on the key facts, avoid speculation, and maintain a neutral tone.
"""

BASE_INSTRUCTIONS = "Always respond in the user's language. Be concise and friendly."

user_template = "Translate the following text from {source} to {target}: {text}"
```

Variable names that do NOT typically trigger detection: `message`, `text`, `content`, `response` (these are too generic).

---

## Confidence Scoring

Each detected prompt is assigned a confidence score from 0.0 to 1.0:

| Score Range | Meaning |
|---|---|
| 0.90–1.00 | Direct string literal in an SDK call — very reliable |
| 0.75–0.89 | Variable reference resolved to a string — reliable |
| 0.60–0.74 | Heuristic match on variable name — likely a prompt |
| Below 0.60 | Low confidence — might not be a prompt |

```bash
# Show all prompts including low-confidence ones
pv scan --show-all

# Only show prompts above a custom threshold
pv scan --min-confidence 0.8
```

Default minimum confidence for `pv add` is 0.60. You can override:

```bash
pv add . --min-confidence 0.75
```

---

## The ScannedPrompt Dataclass

Each detection result is a `ScannedPrompt`:

```python
@dataclass
class ScannedPrompt:
    name: str           # variable name or generated name
    content: str        # the full prompt string
    source: str         # "openai", "anthropic", "langchain", "litellm", "raw"
    file_path: str      # absolute path to the Python file
    line_number: int    # line where the string was found
    confidence: float   # 0.0–1.0
    variable_name: str  # Python variable name if applicable
```

---

## Variable Resolution

When a prompt call uses a variable (`content=SYSTEM_PROMPT`), the resolver follows the reference:

```python
# In ast_visitor.py: found messages=[{"role": "system", "content": SYSTEM_PROMPT}]
# variable_name = "SYSTEM_PROMPT"

# In resolver.py: symbol table built from module-level assignments
# SYSTEM_PROMPT → "You are a helpful assistant..."
```

The resolver builds a symbol table from:
1. Module-level variable assignments (`NAME = "string"`)
2. Multi-line string assignments (`NAME = """..."""`)
3. F-string detection (marked as dynamic, confidence reduced)

If a variable cannot be resolved (it is dynamic, imported from another module, etc.), PromptView records the variable name as a placeholder and marks it with lower confidence.

---

## What Gets Skipped

The directory walker skips these directories automatically:
- `.venv/`, `venv/`, `env/` — virtual environments
- `node_modules/` — JavaScript dependencies
- `__pycache__/` — Python bytecode
- `.git/` — git internals
- `.promptview/` — PromptView's own storage
- `dist/`, `build/` — build artifacts

Only `.py` files are scanned. Other file types (`.txt`, `.md`, `.json`) are not analyzed.

---

## Code Example: What Gets Detected vs. What Doesn't

```python
# DETECTED: direct string in messages list
client.chat.completions.create(
    messages=[{"role": "system", "content": "You are helpful."}]
)

# DETECTED: variable reference resolved
SYSTEM = "You are helpful."
client.chat.completions.create(
    messages=[{"role": "system", "content": SYSTEM}]
)

# DETECTED: raw string variable with suggestive name
summarize_prompt = "Summarize this document in 3 sentences."

# NOT DETECTED: f-string (dynamic — content cannot be statically resolved)
client.chat.completions.create(
    messages=[{"role": "system", "content": f"You are {role}."}]
)

# NOT DETECTED: imported from another module
from config import SYSTEM_PROMPT
client.chat.completions.create(
    messages=[{"role": "system", "content": SYSTEM_PROMPT}]
)

# NOT DETECTED: string concatenation
prompt = "You are " + role + ". Help the user."
```

!!! tip "Manually Tracking Dynamic Prompts"
    For f-strings and dynamically constructed prompts that the scanner can't resolve, use `pv add --manual my_prompt_name` to create a manually tracked prompt entry.

---

## Running the Scanner

```bash
# Scan current directory
pv scan

# Scan a specific path
pv scan src/

# Show all prompts including low-confidence
pv scan --show-all

# Raise the confidence threshold
pv scan --min-confidence 0.85
```

The scanner output shows each detection with its source badge, confidence score, file, and line number. After scanning, use `pv add` to stage what you want to track.

---

## Next Steps

- [Versioning Model](versioning.md) — what happens after `pv add` and `pv commit`
- [pv scan reference](../cli/scan.md) — all scanner flags
