"""Base integration protocol."""

from typing import Protocol, runtime_checkable
from ..storage.models import Prompt, PromptVersion


@runtime_checkable
class BaseIntegration(Protocol):
    def push_version(self, version: PromptVersion, prompt: Prompt) -> str:
        """Push a version to the remote. Returns remote version ID."""
        ...

    def pull_versions(self, prompt_name: str) -> list[PromptVersion]:
        """Pull versions from the remote for a given prompt name."""
        ...

    def list_remote_prompts(self) -> list[dict]:
        """List all prompts available in the remote."""
        ...
