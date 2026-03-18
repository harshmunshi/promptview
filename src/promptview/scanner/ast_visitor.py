"""Core AST visitor for detecting prompts in Python source files."""

import ast
import re
from pathlib import Path
from typing import Optional

from .resolver import resolve_string_node
from .result import ScannedPrompt
from ..storage.models import PromptBlock, PromptRole, PromptSource

# Variable name hints that suggest prompt content
PROMPT_HINT_WORDS = re.compile(
    r"(prompt|system|instruction|template|persona|context|message|"
    r"assistant|user_msg|human|chat|llm|completion|task|behavior)",
    re.IGNORECASE,
)

# Minimum character count for a string to be considered a prompt
MIN_PROMPT_LENGTH = 30


def _get_func_name(node: ast.expr) -> str:
    """Extract dotted function name from a Call's func attribute."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_get_func_name(node.value)}.{node.attr}"
    return ""


def _get_kwarg(call: ast.Call, name: str) -> Optional[ast.expr]:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _extract_messages_blocks(messages_node: ast.expr, symbol_table: dict) -> list[PromptBlock]:
    """Extract role-content blocks from a messages=[...] list literal."""
    blocks = []
    if not isinstance(messages_node, ast.List):
        return blocks
    for elt in messages_node.elts:
        if not isinstance(elt, ast.Dict):
            continue
        role_val = None
        content_val = None
        for key, val in zip(elt.keys, elt.values):
            if isinstance(key, ast.Constant):
                if key.s == "role":
                    role_val = resolve_string_node(val, symbol_table)
                elif key.s == "content":
                    content_val = resolve_string_node(val, symbol_table)
        if content_val:
            try:
                role = PromptRole(role_val) if role_val else PromptRole.USER
            except ValueError:
                role = PromptRole.USER
            blocks.append(PromptBlock(role=role, content=content_val))
    return blocks


class PromptASTVisitor(ast.NodeVisitor):
    """Visits a Python AST and collects ScannedPrompt results."""

    def __init__(self, file_path: str, source_lines: list[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.results: list[ScannedPrompt] = []
        # Maps variable name -> resolved string content
        self.symbol_table: dict[str, str] = {}
        # Maps variable name -> line number
        self.symbol_lines: dict[str, int] = {}

    def _context_code(self, lineno: int, radius: int = 3) -> str:
        start = max(0, lineno - radius - 1)
        end = min(len(self.source_lines), lineno + radius)
        return "".join(self.source_lines[start:end])

    def _add_result(
        self,
        lineno: int,
        end_lineno: int,
        variable_name: str,
        source: PromptSource,
        blocks: list[PromptBlock],
        confidence: float,
        pattern_name: str,
    ) -> None:
        raw_content = "\n".join(b.content for b in blocks if b.content)
        if len(raw_content) < MIN_PROMPT_LENGTH:
            return
        # Deduplicate by line
        for r in self.results:
            if r.line_number == lineno and r.file_path == self.file_path:
                return
        self.results.append(ScannedPrompt(
            file_path=self.file_path,
            line_number=lineno,
            end_line_number=end_lineno,
            variable_name=variable_name,
            source=source,
            blocks=blocks,
            raw_content=raw_content,
            context_code=self._context_code(lineno),
            confidence=confidence,
            pattern_name=pattern_name,
        ))

    # ------------------------------------------------------------------
    # Visit assignments to capture variable definitions
    # ------------------------------------------------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                resolved = resolve_string_node(node.value, self.symbol_table)
                if resolved is not None:
                    self.symbol_table[target.id] = resolved
                    self.symbol_lines[target.id] = node.lineno

                    # Raw pattern: variable name hints + long string
                    if (PROMPT_HINT_WORDS.search(target.id)
                            and len(resolved) >= MIN_PROMPT_LENGTH):
                        blocks = [PromptBlock(role=PromptRole.FULL, content=resolved)]
                        self._add_result(
                            lineno=node.lineno,
                            end_lineno=node.end_lineno or node.lineno,
                            variable_name=target.id,
                            source=PromptSource.RAW,
                            blocks=blocks,
                            confidence=0.7,
                            pattern_name="raw_variable",
                        )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.value is not None:
            resolved = resolve_string_node(node.value, self.symbol_table)
            if resolved is not None:
                self.symbol_table[node.target.id] = resolved
                self.symbol_lines[node.target.id] = node.lineno
                if (PROMPT_HINT_WORDS.search(node.target.id)
                        and len(resolved) >= MIN_PROMPT_LENGTH):
                    blocks = [PromptBlock(role=PromptRole.FULL, content=resolved)]
                    self._add_result(
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        variable_name=node.target.id,
                        source=PromptSource.RAW,
                        blocks=blocks,
                        confidence=0.7,
                        pattern_name="raw_annotated_variable",
                    )
        self.generic_visit(node)

    # ------------------------------------------------------------------
    # Visit function calls
    # ------------------------------------------------------------------

    def visit_Call(self, node: ast.Call) -> None:
        func_name = _get_func_name(node.func)

        # ---- OpenAI: client.chat.completions.create(messages=[...]) ----
        if func_name.endswith(".chat.completions.create") or func_name.endswith("ChatCompletion.create"):
            messages_node = _get_kwarg(node, "messages")
            if messages_node is not None:
                blocks = _extract_messages_blocks(messages_node, self.symbol_table)
                if blocks:
                    self._add_result(
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        variable_name=f"openai_call_l{node.lineno}",
                        source=PromptSource.OPENAI,
                        blocks=blocks,
                        confidence=0.95,
                        pattern_name="openai_chat",
                    )

        # ---- Anthropic: client.messages.create(system=..., messages=[...]) ----
        elif func_name.endswith(".messages.create") or func_name.endswith(".messages.stream"):
            system_node = _get_kwarg(node, "system")
            messages_node = _get_kwarg(node, "messages")
            blocks = []
            if system_node is not None:
                system_str = resolve_string_node(system_node, self.symbol_table)
                if system_str:
                    blocks.append(PromptBlock(role=PromptRole.SYSTEM, content=system_str))
            if messages_node is not None:
                blocks.extend(_extract_messages_blocks(messages_node, self.symbol_table))
            if blocks:
                self._add_result(
                    lineno=node.lineno,
                    end_lineno=node.end_lineno or node.lineno,
                    variable_name=f"anthropic_call_l{node.lineno}",
                    source=PromptSource.ANTHROPIC,
                    blocks=blocks,
                    confidence=0.95,
                    pattern_name="anthropic_messages",
                )

        # ---- LangChain: ChatPromptTemplate.from_messages([...]) ----
        elif "ChatPromptTemplate" in func_name and "from_messages" in func_name:
            if node.args:
                msgs_node = node.args[0]
                blocks = []
                if isinstance(msgs_node, ast.List):
                    for elt in msgs_node.elts:
                        if isinstance(elt, ast.Tuple) and len(elt.elts) == 2:
                            role_node, content_node = elt.elts
                            role_str = resolve_string_node(role_node, self.symbol_table)
                            content_str = resolve_string_node(content_node, self.symbol_table)
                            if content_str:
                                try:
                                    role = PromptRole(role_str) if role_str else PromptRole.USER
                                except ValueError:
                                    role = PromptRole.USER
                                blocks.append(PromptBlock(role=role, content=content_str))
                if blocks:
                    self._add_result(
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        variable_name=f"langchain_chat_l{node.lineno}",
                        source=PromptSource.LANGCHAIN,
                        blocks=blocks,
                        confidence=0.90,
                        pattern_name="langchain_chat_template",
                    )

        # ---- LangChain: PromptTemplate(template="...") ----
        elif "PromptTemplate" in func_name and "Chat" not in func_name:
            template_node = _get_kwarg(node, "template")
            if template_node is None and node.args:
                template_node = node.args[0]
            if template_node is not None:
                content = resolve_string_node(template_node, self.symbol_table)
                if content and len(content) >= MIN_PROMPT_LENGTH:
                    blocks = [PromptBlock(role=PromptRole.FULL, content=content)]
                    self._add_result(
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        variable_name=f"langchain_template_l{node.lineno}",
                        source=PromptSource.LANGCHAIN,
                        blocks=blocks,
                        confidence=0.85,
                        pattern_name="langchain_prompt_template",
                    )

        # ---- LiteLLM: litellm.completion(messages=[...]) ----
        elif "litellm" in func_name.lower() and "completion" in func_name.lower():
            messages_node = _get_kwarg(node, "messages")
            if messages_node is not None:
                blocks = _extract_messages_blocks(messages_node, self.symbol_table)
                if blocks:
                    self._add_result(
                        lineno=node.lineno,
                        end_lineno=node.end_lineno or node.lineno,
                        variable_name=f"litellm_call_l{node.lineno}",
                        source=PromptSource.LITELLM,
                        blocks=blocks,
                        confidence=0.90,
                        pattern_name="litellm_completion",
                    )

        self.generic_visit(node)
