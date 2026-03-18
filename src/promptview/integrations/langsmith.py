"""LangSmith integration for PromptView."""

import os
from typing import List
from ..storage.models import Prompt, PromptVersion
from .base import RemoteIntegration


class LangSmithIntegration(RemoteIntegration):
    """Push/pull prompts to/from LangSmith Hub."""

    def __init__(self):
        try:
            from langsmith import Client
        except ImportError:
            raise ImportError("pip install promptview[langsmith]")
        api_key = os.environ.get("LANGSMITH_API_KEY", "")
        if not api_key:
            raise ValueError("Set LANGSMITH_API_KEY environment variable.")
        self._client = Client(api_key=api_key)

    def push_version(self, version: PromptVersion, prompt: Prompt) -> str:
        """Push a PromptVersion to LangSmith Hub."""
        try:
            from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
        except ImportError:
            raise ImportError("Install langchain-core: pip install langchain-core")

        if len(version.blocks) == 1 and version.blocks[0].role.value == "full":
            template = PromptTemplate.from_template(version.raw_content)
        else:
            messages = [(b.role.value, b.content) for b in version.blocks]
            template = ChatPromptTemplate.from_messages(messages)

        self._client.push_prompt(prompt.name, object=template)
        return f"{prompt.name}"

    def pull_versions(self, prompt_name: str) -> list[dict]:
        """Fetch prompt from LangSmith Hub."""
        try:
            template = self._client.pull_prompt(prompt_name)
            content = str(template)
            return [{"name": prompt_name, "content": content, "version": 1}]
        except Exception:
            return []

    def list_remote_prompts(self) -> list[dict]:
        """List prompts in LangSmith (requires API)."""
        try:
            prompts = list(self._client.list_prompts())
            return [{"name": p.repo_handle} for p in prompts]
        except Exception:
            return []

    def pull_prompts(self) -> List[dict]:
        """Fetch all prompts from LangSmith Hub.

        Returns list of dicts:
            {"name": str, "content": str, "version": int, "labels": list, "created_at": str}
        """
        try:
            from langsmith import Client
        except ImportError:
            raise ImportError("pip install promptview[langsmith]")

        results = []
        try:
            prompts = list(self._client.list_prompts())
        except Exception:
            return []

        for prompt_item in prompts:
            try:
                prompt_name = getattr(prompt_item, "repo_handle", None) or getattr(
                    prompt_item, "name", None
                )
                if not prompt_name:
                    continue

                # Pull the actual prompt content
                try:
                    template = self._client.pull_prompt(prompt_name)
                    # Convert template to string representation
                    content = str(template)
                except Exception:
                    content = ""

                # Extract version info if available
                version_num = 1
                try:
                    if hasattr(prompt_item, "last_commit_hash") and prompt_item.last_commit_hash:
                        # LangSmith uses commit hashes; treat as version 1 since no integer version
                        version_num = 1
                except Exception:
                    pass

                labels: list = []
                try:
                    tags = getattr(prompt_item, "tags", None)
                    if tags:
                        labels = list(tags)
                except Exception:
                    pass

                created_at = ""
                try:
                    created_at_val = getattr(prompt_item, "created_at", None)
                    if created_at_val is not None:
                        created_at = str(created_at_val)
                except Exception:
                    pass

                results.append({
                    "name": prompt_name,
                    "content": content,
                    "version": version_num,
                    "labels": labels,
                    "created_at": created_at,
                })
            except Exception:
                continue

        return results

    def pull_evals(self, prompt_name: str, content_hash: str) -> List[dict]:
        """Fetch eval-related data from LangSmith for a given prompt.

        LangSmith does not have a direct per-prompt eval scores API in the same
        way Langfuse does. This method returns an empty list as the eval model
        in LangSmith (datasets + runs) requires a different integration approach.

        Returns:
            Always returns [] — LangSmith eval data is not directly mappable
            to prompt-level score dicts without dataset context.
        """
        return []
