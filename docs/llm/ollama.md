# Ollama (Local LLM)

Ollama lets you run LLMs entirely on your own machine — no API key, no cloud, no cost, no data leaving your network. It is the recommended provider for privacy-sensitive projects and for teams that want to avoid recurring API costs.

---

## Why Ollama?

| Benefit | Details |
|---|---|
| **Free** | No per-token costs — run as many prompts as you want |
| **Private** | All inference happens locally; no data sent to any cloud |
| **Offline** | Works without internet after the model is downloaded |
| **Fast** | Very fast on Apple Silicon (M1/M2/M3/M4) and NVIDIA GPUs |
| **No API key** | Zero configuration for PromptView — just select "ollama" in the UI |

---

## Installing Ollama

=== "macOS"

    ```bash
    # Via install script
    curl -fsSL https://ollama.com/install.sh | sh

    # Via Homebrew
    brew install ollama
    ```

=== "Linux"

    ```bash
    curl -fsSL https://ollama.com/install.sh | sh
    ```

=== "Windows"

    Download and run the installer from [ollama.com/download](https://ollama.com/download).

After installation, Ollama starts automatically as a background service and listens on `http://localhost:11434`.

Verify it's running:

```bash
ollama list     # shows downloaded models
curl http://localhost:11434  # returns {"status":"ok"}
```

---

## Pulling Models

Download a model before using it:

```bash
ollama pull llama3       # Meta Llama 3 8B — recommended for general use
ollama pull mistral      # Mistral 7B — fast and capable
ollama pull gemma3       # Google Gemma 3
ollama pull phi3         # Microsoft Phi-3 mini (~2GB) — very fast
ollama pull codellama    # Code-focused Llama — good for code prompt review
ollama pull qwen2.5      # Alibaba Qwen — strong multilingual
ollama pull deepseek-r1  # DeepSeek R1 — strong reasoning
```

Model sizes:
- `phi3` (~2GB) — very fast, good for quick tasks
- `llama3` (~4.7GB) — good quality/speed balance
- `mistral` (~4GB) — fast, great for structured output
- `gemma3:27b` (~16GB) — high quality, requires 16GB+ RAM

---

## Using Ollama with PromptView

### In the Web UI

1. Open `pv ui`
2. Click the gear icon (⚙)
3. Select **Provider: ollama**
4. Set **Model** to `llama3` (or any model you have downloaded)
5. Leave **API Key** empty
6. Click **Save**

All decompose and regenerate operations now run locally.

### In the CLI

```bash
# pv run with Ollama
pv run my_prompt --call --provider ollama

# Override model
pv run my_prompt --call --provider ollama --model mistral

# pv eval with Ollama
pv eval run my_prompt --dataset evals/cases.jsonl --provider ollama --model llama3
```

### In Config File

```bash
pv config llm.provider ollama
pv config llm.model llama3
```

Now all CLI operations that need an LLM will use Ollama without any flags.

---

## How PromptView Talks to Ollama

PromptView uses `httpx` (a core dependency) to make HTTP requests to Ollama's API:

```python
# Internally in llm/client.py
response = httpx.post(
    "http://localhost:11434/api/chat",
    json={
        "model": "llama3",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "stream": False
    },
    timeout=120.0
)
```

No Ollama Python SDK is needed. `httpx` is already installed.

---

## Model Recommendations by Task

| Task | Recommended Model | Why |
|---|---|---|
| Decompose prompts | `llama3` or `mistral` | Good instruction following |
| Surgical regeneration | `llama3` or `mistral` | Preserves style well |
| LLM judge scoring | `llama3` | Reliable JSON output |
| `pv run --call` | Any | Depends on your use case |
| Code-related prompts | `codellama` | Optimised for code |

---

## Troubleshooting

### "Connection refused" Error

```
RuntimeError: Cannot connect to Ollama at http://localhost:11434.
Is Ollama running? Try: ollama serve
```

**Fix:** Start Ollama:

```bash
ollama serve
```

Or on macOS, start the Ollama app from Applications.

### Model Not Found

```
Error: model 'llama3' not found
```

**Fix:** Pull the model:

```bash
ollama pull llama3
```

### Slow Response

Ollama without a GPU runs on CPU and can be slow for large models.

**Options:**
- Use a smaller model: `phi3` (~2GB) is much faster than `llama3` on CPU
- Use a cloud provider for decompose/regenerate and Ollama only for quick runs
- On macOS with Apple Silicon, performance is excellent even without a dedicated GPU

### Wrong Port

If Ollama is running on a different port, PromptView currently only supports `localhost:11434`. You can work around this with port forwarding:

```bash
ssh -L 11434:localhost:11434 remote-host
```

---

## Comparing Ollama to Cloud Providers

For PromptView's specific use cases (decompose and regenerate):

| Aspect | Ollama (llama3) | OpenAI (gpt-4o-mini) |
|---|---|---|
| Cost | Free | ~$0.001/request |
| Latency | 2–10s on M2 Mac | 0.5–2s |
| Quality | Good | Excellent |
| Privacy | Complete | Data sent to OpenAI |
| Offline | Yes | No |

For most users on Apple Silicon, Ollama with `llama3` is fully adequate for day-to-day prompt editing and provides excellent privacy.

---

## See Also

- [LLM Providers Overview](providers.md)
- [Decompose & Regenerate](decompose-regenerate.md)
