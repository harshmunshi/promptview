"""Scanner result types."""

from dataclasses import dataclass, field
from ..storage.models import PromptBlock, PromptSource


@dataclass
class ScannedPrompt:
    file_path: str
    line_number: int
    end_line_number: int
    variable_name: str
    source: PromptSource
    blocks: list
    raw_content: str
    context_code: str = ""
    confidence: float = 1.0
    pattern_name: str = ""
