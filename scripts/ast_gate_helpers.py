from __future__ import annotations

import ast


def call_name(node: ast.AST, *, qualified: bool = True) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        if not qualified:
            return node.attr
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None
