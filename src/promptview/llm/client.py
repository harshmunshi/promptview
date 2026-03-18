"""Provider-agnostic LLM client supporting OpenAI, Anthropic, Gemini, and Ollama."""

from enum import Enum
from typing import Optional

OLLAMA_BASE_URL = "http://localhost:11434"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMClient:
    """Thin wrapper that normalises chat completion across providers."""

    def __init__(self, provider: LLMProvider, api_key: str, model: Optional[str] = None,
                 ollama_base_url: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        self.model = model or _default_model(provider)
        self.ollama_base_url = ollama_base_url or OLLAMA_BASE_URL

    def complete(self, system: str, user: str) -> str:
        """Send a system+user message and return the assistant text."""
        if self.provider == LLMProvider.OPENAI:
            return self._openai(system, user)
        if self.provider == LLMProvider.ANTHROPIC:
            return self._anthropic(system, user)
        if self.provider == LLMProvider.GEMINI:
            return self._gemini(system, user)
        if self.provider == LLMProvider.OLLAMA:
            return self._ollama(system, user)
        raise ValueError(f"Unknown provider: {self.provider}")

    # ── OpenAI ────────────────────────────────────────────────────────────────

    def _openai(self, system: str, user: str) -> str:
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content

    # ── Anthropic ─────────────────────────────────────────────────────────────

    def _anthropic(self, system: str, user: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text

    # ── Gemini ────────────────────────────────────────────────────────────────

    def _gemini(self, system: str, user: str) -> str:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system,
        )
        resp = model.generate_content(user)
        return resp.text

    # ── Ollama ────────────────────────────────────────────────────────────────

    def _ollama(self, system: str, user: str) -> str:
        """Call a locally running Ollama instance via its REST API.

        No API key required. Requires Ollama to be running:
            https://ollama.com  →  ollama pull llama3  →  ollama serve
        """
        import httpx

        url = f"{self.ollama_base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
        }
        try:
            resp = httpx.post(url, json=payload, timeout=120.0)
            resp.raise_for_status()
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.ollama_base_url}. "
                "Make sure Ollama is installed and running: https://ollama.com"
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Ollama returned an error: {e.response.status_code} — {e.response.text}"
            )

        data = resp.json()
        # Ollama returns {"message": {"role": "assistant", "content": "..."}}
        return data["message"]["content"]


def _default_model(provider: LLMProvider) -> str:
    return {
        LLMProvider.OPENAI: "gpt-4o-mini",
        LLMProvider.ANTHROPIC: "claude-haiku-4-5-20251001",
        LLMProvider.GEMINI: "gemini-2.0-flash",
        LLMProvider.OLLAMA: "llama3",
    }[provider]
