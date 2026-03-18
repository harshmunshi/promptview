"""AST string resolution utilities."""

import ast
from typing import Optional


def resolve_string_node(node: ast.expr, symbol_table: dict) -> Optional[str]:
    """
    Try to extract a string value from an AST expression node.
    Returns None if the node cannot be resolved to a plain string.
    """
    if isinstance(node, ast.Constant) and isinstance(node.s, str):
        return node.s

    # f-string: extract literal parts, replace interpolations with {VAR} placeholders
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.s, str):
                parts.append(value.s)
            elif isinstance(value, ast.FormattedValue):
                # Try to resolve the expression
                expr_str = _expr_to_placeholder(value.value, symbol_table)
                parts.append(f"{{{expr_str}}}")
        return "".join(parts)

    # String concatenation: "part1" + "part2"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = resolve_string_node(node.left, symbol_table)
        right = resolve_string_node(node.right, symbol_table)
        if left is not None and right is not None:
            return left + right
        if left is not None:
            return left + "{...}"
        if right is not None:
            return "{...}" + right
        return None

    # Variable reference - look up in symbol table
    if isinstance(node, ast.Name) and node.id in symbol_table:
        return symbol_table[node.id]

    return None


def _expr_to_placeholder(node: ast.expr, symbol_table: dict) -> str:
    """Convert an expression node to a readable placeholder string."""
    if isinstance(node, ast.Name):
        # If it resolves to a string, inline it; otherwise use var name
        if node.id in symbol_table:
            val = symbol_table[node.id]
            if len(val) < 30:
                return val
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_expr_to_placeholder(node.value, symbol_table)}.{node.attr}"
    if isinstance(node, ast.Call):
        return f"{_expr_to_placeholder(node.func, symbol_table)}(...)"
    return "..."
