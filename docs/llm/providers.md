# LLM Providers

PromptView supports four LLM providers for the decompose, regenerate, eval, and `pv run` features. All four are available without any optional extras — they are core dependencies.

---

## Provider Comparison

| Provider | Default Model | API Key | Cost | Notes |
|---|---|---|---|---|
| **OpenAI** | `gpt-4o-mini` | Required | Per token | Cloud; fast; widely supported |
| **Anthropic** | `claude-haiku-4-5` | Required | Per token | Cloud; excellent at structured output |
| **Google Gemini** | `gemini-2.0-flash` | Required | Per token (free tier available) | Cloud; strong multi-task performance |
| **Ollama** | `llama3` | None | **Free** | Local; private; no data leaves your machine |

---

## OpenAI

### Configuration

=== "Environment Variable"

    ```bash
    export OPENAI_API_KEY="sk-..."
    ```

=== "Config File"

    ```bash
    pv config llm.provider openai
    pv config llm.api_key sk-...
    ```

=== "UI"

    Gear icon → Provider: `openai` → API Key: `sk-...` → Save

=== "CLI Flag"

    ```bash
    pv run my_prompt --call --provider openai --api-key sk-...
    ```

### Available Models

```
gpt-4o              # Most capable
gpt-4o-mini         # Default — fast and cheap
gpt-4-turbo
gpt-3.5-turbo
```

### Notes
- Default model `gpt-4o-mini` is well-suited for decomposition and regeneration tasks
- For production eval runs, consider `gpt-4o` for higher quality scoring

---

## Anthropic

### Configuration

=== "Environment Variable"

    ```bash
    export ANTHROPIC_API_KEY="sk-ant-..."
    ```

=== "Config File"

    ```bash
    pv config llm.provider anthropic
    pv config llm.api_key sk-ant-...
    ```

=== "UI"

    Gear icon → Provider: `anthropic` → API Key: `sk-ant-...` → Save

### Available Models

```
claude-haiku-4-5         # Default — fast and cost-effective
claude-3-5-sonnet-20241022   # Higher quality
claude-3-opus-20240229   # Most capable
claude-3-haiku-20240307  # Fastest/cheapest
```

### Notes
- Anthropic models are excellent at following structured output instructions
- Well-suited for the JSON-output tasks in decomposition and LLM judge scoring
- The `claude-haiku-4-5` default balances speed and quality for the decompose/regenerate workflow

---

## Google Gemini

### Configuration

=== "Environment Variable"

    ```bash
    export GOOGLE_API_KEY="AIza..."
    ```

=== "Config File"

    ```bash
    pv config llm.provider gemini
    pv config llm.api_key AIza...
    ```

=== "UI"

    Gear icon → Provider: `gemini` → API Key: `AIza...` → Save

### Available Models

```
gemini-2.0-flash     # Default — fast and capable
gemini-1.5-pro       # Higher capability
gemini-1.5-flash     # Faster/cheaper
```

### Notes
- Gemini has a generous free tier for personal projects
- `gemini-2.0-flash` is the default for its speed/quality balance

---

## Ollama (Local)

Ollama runs LLMs locally on your machine. No API key, no cloud, no cost, no data leaving your machine.

### Installation

```bash
# macOS / Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS via Homebrew
brew install ollama

# Windows: download from https://ollama.com/download
```

Ollama starts a local server on `http://localhost:11434` automatically.

### Pull Models

```bash
ollama pull llama3      # Meta Llama 3 8B — good general purpose
ollama pull mistral     # Mistral 7B — fast and capable
ollama pull gemma3      # Google Gemma 3 — efficient
ollama pull phi3        # Microsoft Phi-3 mini — very small, fast
ollama pull codellama   # Code-focused Llama — good for code prompts
ollama pull qwen2.5     # Alibaba Qwen — multilingual
```

### Configuration

=== "UI"

    Gear icon → Provider: `ollama` → Model: `llama3` → Save (no API key needed)

=== "CLI Flag"

    ```bash
    pv run my_prompt --call --provider ollama
    pv run my_prompt --call --provider ollama --model mistral
    ```

=== "Config File"

    ```bash
    pv config llm.provider ollama
    pv config llm.model llama3
    ```

### Notes
- PromptView uses `httpx` (always installed) to communicate with Ollama at `http://localhost:11434/api/chat`
- If Ollama is not running, PromptView raises a user-friendly error with instructions
- Performance depends on your hardware — Apple Silicon and NVIDIA GPUs run inference much faster than CPU
- For decompose/regenerate tasks, `llama3` or `mistral` produce good results

---

## How the LLM Client Works

All four providers use the same interface internally:

```python
from promptview.llm.client import LLMClient

client = LLMClient(provider="openai", api_key="sk-...", model="gpt-4o-mini")
response = client.complete(
    system="You are a helpful assistant.",
    user="What is 2 + 2?"
)
# response = "4"
```

The `complete(system, user)` method:
- OpenAI: `chat.completions.create(messages=[{role:system}, {role:user}])`
- Anthropic: `messages.create(system=..., messages=[{role:user}])`
- Gemini: `GenerativeModel.generate_content([system, user])`
- Ollama: `httpx.post("http://localhost:11434/api/chat", json={...})`

---

## Provider Priority for CLI Operations

When no provider is specified, PromptView falls back through:

1. `--provider` flag (highest priority)
2. `pv config llm.provider` value in `.promptview/config.toml`
3. Auto-detect from environment variables:
   - `OPENAI_API_KEY` → openai
   - `ANTHROPIC_API_KEY` → anthropic
   - `GOOGLE_API_KEY` → gemini

---

## Frontend LLM Config Storage

The web UI stores provider settings in browser `localStorage`:

```json
{
  "provider": "openai",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

These values are included in every POST body for decompose and regenerate requests. The server never stores or logs API keys — they are used only for the duration of the LLM API call.

---

## See Also

- [Ollama Setup](ollama.md) — detailed Ollama guide
- [Decompose & Regenerate](decompose-regenerate.md) — how LLMs are used in the editor
- [pv vars & run](../cli/vars-run.md) — using providers in `pv run`
