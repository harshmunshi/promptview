"""Langfuse integration for PromptView."""

import os
from ..storage.models import Prompt, PromptVersion


class LangfuseIntegration:
    """Push/pull prompts to/from Langfuse."""

    def __init__(self):
        try:
            from langfuse import Langfuse
        except ImportError:
            raise ImportError("pip install promptview[langfuse]")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
        if not secret_key or not public_key:
            raise ValueError(
                "Set LANGFUSE_SECRET_KEY and LANGFUSE_PUBLIC_KEY environment variables."
            )
        self._client = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
        )

    def push_version(self, version: PromptVersion, prompt: Prompt) -> str:
        """Push a PromptVersion to Langfuse. Returns the Langfuse prompt name."""
        # Langfuse prompt: if multi-role, use chat format; else text
        if len(version.blocks) == 1 and version.blocks[0].role.value == "full":
            result = self._client.create_prompt(
                name=prompt.name,
                prompt=version.raw_content,
                labels=[f"v{version.version_number}"],
                type="text",
            )
        else:
            messages = [{"role": b.role.value, "content": b.content} for b in version.blocks]
            result = self._client.create_prompt(
                name=prompt.name,
                prompt=messages,
                labels=[f"v{version.version_number}"],
                type="chat",
            )
        return f"{prompt.name}@{version.version_number}"

    def pull_versions(self, prompt_name: str) -> list[dict]:
        """Fetch prompt versions from Langfuse."""
        try:
            prompt = self._client.get_prompt(prompt_name)
            return [{"name": prompt_name, "content": prompt.prompt, "version": 1}]
        except Exception:
            return []

    def list_remote_prompts(self) -> list[dict]:
        """List all prompts in Langfuse (requires API access)."""
        # Langfuse SDK doesn't expose a list method; return empty
        return []
