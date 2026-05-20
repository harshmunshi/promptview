"""Base integration protocol."""

from abc import ABC, abstractmethod
from typing import List
from ..storage.models import Prompt, PromptVersion


class RemoteIntegration(ABC):
    """Abstract base class for remote integrations (Langfuse, LangSmith, etc.)."""

    @abstractmethod
    def push_version(self, version: PromptVersion, prompt: Prompt) -> str:
        """Push a version to the remote. Returns remote version ID."""
        ...

    @abstractmethod
    def pull_versions(self, prompt_name: str) -> list[dict]:
        """Pull versions from the remote for a given prompt name."""
        ...

    @abstractmethod
    def list_remote_prompts(self) -> list[dict]:
        """List all prompts available in the remote."""
        ...

    @abstractmethod
    def pull_prompts(self) -> List[dict]:
        """Return list of prompt dicts:
        {name, content, version, labels, created_at}
        """
        ...

    @abstractmethod
    def pull_evals(self, prompt_name: str, content_hash: str) -> List[dict]:
        """Return list of eval score dicts:
        {score, name, comment, created_at}
        Match to local version by content_hash.
        Returns empty list if no scores found.
        """
        ...
