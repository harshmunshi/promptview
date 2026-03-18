"""Langfuse integration for PromptView."""

import os
from typing import List
from ..storage.models import Prompt, PromptVersion
from .base import RemoteIntegration


class LangfuseIntegration(RemoteIntegration):
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
        """List all prompts in Langfuse."""
        try:
            result = self._client.client.prompts.list(limit=100)
            prompts = []
            for item in result.data:
                prompts.append({"name": item.name})
            return prompts
        except Exception:
            return []

    def pull_prompts(self) -> List[dict]:
        """Fetch all prompts and their versions from Langfuse.

        Returns list of dicts:
            {"name": str, "content": str, "version": int, "labels": list, "created_at": str}
        """
        try:
            from langfuse import Langfuse
        except ImportError:
            raise ImportError("pip install promptview[langfuse]")

        results = []
        try:
            # List all prompts (with pagination support)
            page = 1
            while True:
                try:
                    listing = self._client.client.prompts.list(limit=100, page=page)
                except Exception:
                    # If pagination is not supported, just list once
                    listing = self._client.client.prompts.list(limit=100)
                    items = list(getattr(listing, "data", listing))
                    for item in items:
                        try:
                            prompt_name = item.name
                            # Fetch the latest version
                            prompt_obj = self._client.get_prompt(prompt_name)
                            content = prompt_obj.prompt
                            # content may be a list of messages (chat) or a string (text)
                            if isinstance(content, list):
                                # Flatten chat messages to a single string
                                content_str = "\n".join(
                                    f"{m.get('role', 'user')}: {m.get('content', '')}"
                                    for m in content
                                )
                            else:
                                content_str = str(content)
                            version_num = getattr(prompt_obj, "version", 1) or 1
                            labels = list(getattr(prompt_obj, "labels", []) or [])
                            created_at = str(getattr(item, "created_at", "") or "")
                            results.append({
                                "name": prompt_name,
                                "content": content_str,
                                "version": version_num,
                                "labels": labels,
                                "created_at": created_at,
                            })
                        except Exception:
                            continue
                    break

                items = list(getattr(listing, "data", listing))
                if not items:
                    break

                for item in items:
                    try:
                        prompt_name = item.name
                        prompt_obj = self._client.get_prompt(prompt_name)
                        content = prompt_obj.prompt
                        if isinstance(content, list):
                            content_str = "\n".join(
                                f"{m.get('role', 'user')}: {m.get('content', '')}"
                                for m in content
                            )
                        else:
                            content_str = str(content)
                        version_num = getattr(prompt_obj, "version", 1) or 1
                        labels = list(getattr(prompt_obj, "labels", []) or [])
                        created_at = str(getattr(item, "created_at", "") or "")
                        results.append({
                            "name": prompt_name,
                            "content": content_str,
                            "version": version_num,
                            "labels": labels,
                            "created_at": created_at,
                        })
                    except Exception:
                        continue

                # Check if there are more pages
                total = getattr(listing, "meta", None)
                if total is None:
                    break
                total_pages = getattr(total, "total_pages", 1)
                if page >= total_pages:
                    break
                page += 1

        except Exception:
            return []

        return results

    def pull_evals(self, prompt_name: str, content_hash: str) -> List[dict]:
        """Fetch eval scores from Langfuse for a given prompt.

        Returns list of dicts:
            {"score": float, "name": str, "comment": str, "created_at": str}
        """
        try:
            results = []
            # Use the Langfuse scores API to fetch scores related to this prompt
            try:
                scores_response = self._client.client.score.get_many(
                    name=prompt_name,
                    limit=100,
                )
                scores = list(getattr(scores_response, "data", scores_response) or [])
            except Exception:
                try:
                    # Alternative: fetch via get_scores if available
                    scores_response = self._client.get_scores(name=prompt_name, limit=100)
                    scores = list(getattr(scores_response, "data", scores_response) or [])
                except Exception:
                    return []

            for score in scores:
                try:
                    results.append({
                        "score": float(getattr(score, "value", 0) or 0),
                        "name": str(getattr(score, "name", "") or ""),
                        "comment": str(getattr(score, "comment", "") or ""),
                        "created_at": str(getattr(score, "created_at", "") or ""),
                    })
                except Exception:
                    continue

            return results
        except Exception:
            return []
