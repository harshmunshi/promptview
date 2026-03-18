"""LangSmith integration for PromptView."""

import os
from ..storage.models import Prompt, PromptVersion


class LangSmithIntegration:
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
