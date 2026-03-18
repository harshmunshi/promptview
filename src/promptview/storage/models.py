"""Core data models for PromptView."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import uuid


class PromptSource(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LANGCHAIN = "langchain"
    LITELLM = "litellm"
    RAW = "raw"
    MANUAL = "manual"


class PromptRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FULL = "full"


@dataclass
class PromptBlock:
    role: PromptRole
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role.value, "content": self.content}

    @classmethod
    def from_dict(cls, d: dict) -> "PromptBlock":
        return cls(role=PromptRole(d["role"]), content=d["content"])


@dataclass
class Prompt:
    id: str
    name: str
    description: str = ""
    source: PromptSource = PromptSource.RAW
    file_path: str = ""
    line_number: int = 0
    variable_name: str = ""
    tags: list = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new(cls, name: str, **kwargs) -> "Prompt":
        return cls(id=str(uuid.uuid4()), name=name, **kwargs)


@dataclass
class PromptVersion:
    id: str
    prompt_id: str
    version_number: int
    blocks: list
    raw_content: str
    content_hash: str
    commit_id: Optional[str] = None
    parent_version_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new(cls, prompt_id: str, version_number: int, blocks: list,
            raw_content: str, content_hash: str, **kwargs) -> "PromptVersion":
        return cls(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            version_number=version_number,
            blocks=blocks,
            raw_content=raw_content,
            content_hash=content_hash,
            **kwargs,
        )


@dataclass
class Commit:
    id: str
    message: str
    author: str
    timestamp: datetime
    version_ids: list

    @classmethod
    def new(cls, message: str, author: str, version_ids: list) -> "Commit":
        import hashlib, time
        sha = hashlib.sha256(f"{message}{time.time()}".encode()).hexdigest()[:8]
        return cls(
            id=sha,
            message=message,
            author=author,
            timestamp=datetime.utcnow(),
            version_ids=version_ids,
        )


@dataclass
class DiffHunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list


@dataclass
class PromptDiff:
    prompt_id: str
    prompt_name: str
    old_version: int
    new_version: int
    hunks: list
    additions: int
    deletions: int


@dataclass
class PromptComponent:
    """A single labeled section that makes up a prompt (e.g. Role, Instructions)."""
    id: str
    prompt_id: str
    version_id: str        # which PromptVersion these components belong to
    label: str             # e.g. "Role", "Context", "Instructions", "Format", "Examples"
    content: str
    position: int          # order in the linear graph (0-indexed)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def new(cls, prompt_id: str, version_id: str, label: str,
            content: str, position: int) -> "PromptComponent":
        return cls(
            id=str(uuid.uuid4()),
            prompt_id=prompt_id,
            version_id=version_id,
            label=label,
            content=content,
            position=position,
        )


@dataclass
class IndexEntry:
    prompt_id: str
    prompt_name: str
    version_id: str
    staged_at: datetime
    change_type: str  # "added" | "modified" | "deleted"
