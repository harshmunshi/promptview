"""Core data models for PromptView."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
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


@dataclass
class TestCase:
    id: str
    prompt_id: str
    input: str
    expected_output: Optional[str]
    tags: List[str]
    created_at: str

    @classmethod
    def new(
        cls,
        prompt_id: str,
        input: str,
        expected_output: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> "TestCase":
        import uuid as _uuid
        import datetime as _dt
        return cls(
            id=str(_uuid.uuid4()),
            prompt_id=prompt_id,
            input=input,
            expected_output=expected_output,
            tags=tags or [],
            created_at=_dt.datetime.utcnow().isoformat(),
        )


@dataclass
class EvalRun:
    id: str
    prompt_id: str
    version_id: str
    source: str  # 'local' | 'langfuse' | 'langsmith'
    run_at: str
    dataset_path: Optional[str]
    provider: Optional[str]
    model: Optional[str]
    total_cases: int
    passed: int
    avg_latency_ms: float
    avg_cost_usd: float
    avg_judge_score: Optional[float]
    custom_metrics: Dict[str, Any]

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total_cases * 100) if self.total_cases > 0 else 0.0

    @classmethod
    def new(cls, prompt_id: str, version_id: str, source: str = "local", **kwargs) -> "EvalRun":
        import uuid as _uuid
        import datetime as _dt
        return cls(
            id=str(_uuid.uuid4()),
            prompt_id=prompt_id,
            version_id=version_id,
            source=source,
            run_at=_dt.datetime.utcnow().isoformat(),
            dataset_path=kwargs.get("dataset_path"),
            provider=kwargs.get("provider"),
            model=kwargs.get("model"),
            total_cases=0,
            passed=0,
            avg_latency_ms=0.0,
            avg_cost_usd=0.0,
            avg_judge_score=None,
            custom_metrics={},
        )


@dataclass
class EvalResult:
    id: str
    eval_run_id: str
    test_case_id: Optional[str]
    actual_output: str
    passed: bool
    similarity_score: Optional[float]
    judge_score: Optional[float]
    judge_reasoning: Optional[str]
    latency_ms: float
    tokens_used: int
    cost_usd: float

    @classmethod
    def new(cls, eval_run_id: str, actual_output: str, passed: bool, **kwargs) -> "EvalResult":
        import uuid as _uuid
        return cls(
            id=str(_uuid.uuid4()),
            eval_run_id=eval_run_id,
            test_case_id=kwargs.get("test_case_id"),
            actual_output=actual_output,
            passed=passed,
            similarity_score=kwargs.get("similarity_score"),
            judge_score=kwargs.get("judge_score"),
            judge_reasoning=kwargs.get("judge_reasoning"),
            latency_ms=kwargs.get("latency_ms", 0.0),
            tokens_used=kwargs.get("tokens_used", 0),
            cost_usd=kwargs.get("cost_usd", 0.0),
        )
