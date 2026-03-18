"""Template variable detection and rendering for PromptView."""
import re
from typing import Any

# Matches {variable_name} — single-brace, valid Python identifier inside
# Does NOT match {{include: ...}} (those are composition directives)
VARIABLE_PATTERN = re.compile(r'(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})')

# Matches {{ include: prompt_name }} with flexible spacing
INCLUDE_PATTERN = re.compile(r'\{\{\s*include\s*:\s*([^\}]+?)\s*\}\}')


def extract_variables(text: str) -> list[str]:
    """Return sorted list of unique variable names found in text.

    Ignores {{ include: ... }} directives.
    """
    # Remove include directives first so their content isn't scanned
    cleaned = INCLUDE_PATTERN.sub('', text)
    names = VARIABLE_PATTERN.findall(cleaned)
    return sorted(set(names))


def extract_includes(text: str) -> list[str]:
    """Return list of prompt names referenced via {{ include: name }}."""
    return INCLUDE_PATTERN.findall(text)


def render(text: str, variables: dict[str, Any]) -> str:
    """Substitute {variable} slots with values from the dict.

    Missing variables are left as-is (not an error).
    """
    def replacer(m: re.Match) -> str:
        name = m.group(1)
        return str(variables[name]) if name in variables else m.group(0)
    # Don't touch {{ include: ... }} directives
    return VARIABLE_PATTERN.sub(replacer, text)


def resolve_includes(text: str, prompt_lookup: dict[str, str]) -> str:
    """Replace {{ include: name }} with the raw content of the named prompt.

    prompt_lookup: {prompt_name: raw_content}
    Unresolved includes are left as-is.
    """
    def replacer(m: re.Match) -> str:
        name = m.group(1).strip()
        return prompt_lookup.get(name, m.group(0))
    return INCLUDE_PATTERN.sub(replacer, text)


def render_full(
    text: str,
    variables: dict[str, Any],
    prompt_lookup: dict[str, str] | None = None,
) -> str:
    """Resolve includes then substitute variables."""
    if prompt_lookup:
        text = resolve_includes(text, prompt_lookup)
    return render(text, variables)
