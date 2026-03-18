"""
Decompose a prompt into labeled components and regenerate a prompt from components.
"""

import json
import re
from typing import Optional

from .client import LLMClient
from ..storage.models import PromptComponent

# ── Decompose ─────────────────────────────────────────────────────────────────

DECOMPOSE_SYSTEM = """You are an expert prompt engineer. Your job is to analyze a prompt and
break it down into its distinct functional components. Each component has a short label
and the exact text that belongs to it.

Common component labels (use these when they apply, or invent a clear label):
- Role          → who the assistant is / its persona
- Context       → background information or situational setup
- Instructions  → what the assistant must do, step by step
- Constraints   → what the assistant must NOT do, limitations, rules
- Output Format → how the response should be structured (JSON, bullets, length, etc.)
- Examples      → few-shot examples of input/output
- Tone          → style, formality, voice guidance
- Variables     → placeholder variables like {name} or {{code}} described here

Rules:
- Split at natural boundaries; do not split mid-sentence unless clearly distinct.
- Every word of the original prompt must appear in exactly one component.
- Return ONLY a JSON array. No prose, no markdown fences.

Format:
[
  {"label": "Role", "content": "...exact text..."},
  {"label": "Instructions", "content": "...exact text..."}
]"""

DECOMPOSE_USER = """Decompose this prompt into components:

---
{prompt}
---"""

# ── Surgical regeneration (when we have original context) ─────────────────────

REGENERATE_SURGICAL_SYSTEM = """You are a surgical prompt editor.

You will receive three things:
1. ORIGINAL — the existing prompt text (the authoritative source of truth for formatting, style, and structure)
2. OLD_COMPONENTS — the original prompt broken into labeled sections
3. NEW_COMPONENTS — the updated sections (some may be added, deleted, or modified)

Your task: produce an updated prompt that:
- Reflects ALL changes from NEW_COMPONENTS vs OLD_COMPONENTS
- For sections that have NOT changed: copy their text from ORIGINAL verbatim (same wording, whitespace, punctuation)
- For modified sections: integrate the new content at the correct position, matching the surrounding tone and style
- For added sections: insert them at the correct position naturally
- For deleted sections: remove them cleanly with no leftover whitespace artifacts

Return ONLY the final prompt text. No labels, no JSON, no preamble, no explanation."""

REGENERATE_SURGICAL_USER = """ORIGINAL:
---
{original}
---

OLD_COMPONENTS:
{old_components}

NEW_COMPONENTS:
{new_components}

Produce the updated prompt now:"""

# ── Fallback regeneration (no original context available) ─────────────────────

REGENERATE_SIMPLE_SYSTEM = """You are an expert prompt engineer. You will receive a list of labeled
prompt components and must combine them into a single, coherent, well-written prompt.

Rules:
- Preserve all information from every component.
- Merge smoothly — use natural transitions where needed.
- Do NOT add new instructions, constraints, or content beyond what is given.
- Return ONLY the final prompt text. No labels, no JSON, no explanation."""

REGENERATE_SIMPLE_USER = """Combine these components into a single cohesive prompt:

{components}"""


# ── Public API ────────────────────────────────────────────────────────────────

def decompose(llm: LLMClient, raw_prompt: str) -> list[dict]:
    """
    Call the LLM to decompose `raw_prompt` into a list of {label, content} dicts.
    Falls back to a single 'Full Prompt' component if parsing fails.
    """
    user_msg = DECOMPOSE_USER.format(prompt=raw_prompt)
    response = llm.complete(DECOMPOSE_SYSTEM, user_msg)

    json_text = _extract_json(response)
    try:
        components = json.loads(json_text)
        if not isinstance(components, list):
            raise ValueError("Expected a JSON array")
        validated = []
        for item in components:
            if isinstance(item, dict) and "label" in item and "content" in item:
                validated.append({"label": str(item["label"]), "content": str(item["content"])})
        if validated:
            return validated
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: return the whole prompt as one block
    return [{"label": "Prompt", "content": raw_prompt}]


def regenerate(
    llm: LLMClient,
    new_components: list[dict],
    original_content: str = "",
    old_components: Optional[list[dict]] = None,
) -> str:
    """
    Regenerate a full prompt from components.

    When `original_content` and `old_components` are provided the LLM performs a
    surgical edit — only the sections that changed are rewritten while the rest of
    the original text is preserved verbatim.  Without that context it falls back to
    plain composition.
    """
    if original_content and old_components is not None:
        old_fmt = _fmt_components(old_components)
        new_fmt = _fmt_components(new_components)
        user_msg = REGENERATE_SURGICAL_USER.format(
            original=original_content,
            old_components=old_fmt,
            new_components=new_fmt,
        )
        return llm.complete(REGENERATE_SURGICAL_SYSTEM, user_msg).strip()

    # Fallback — no original context
    formatted = _fmt_components(new_components)
    user_msg = REGENERATE_SIMPLE_USER.format(components=formatted)
    return llm.complete(REGENERATE_SIMPLE_SYSTEM, user_msg).strip()


def components_to_models(
    components: list[dict],
    prompt_id: str,
    version_id: str,
) -> list[PromptComponent]:
    return [
        PromptComponent.new(
            prompt_id=prompt_id,
            version_id=version_id,
            label=c["label"],
            content=c["content"],
            position=i,
        )
        for i, c in enumerate(components)
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_components(components: list[dict]) -> str:
    return "\n\n".join(f"[{c['label']}]\n{c['content']}" for c in components)


def _extract_json(text: str) -> str:
    """Strip markdown fences and find the first JSON array."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("[")
    if start == -1:
        return text
    depth = 0
    for i, ch in enumerate(text[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]
