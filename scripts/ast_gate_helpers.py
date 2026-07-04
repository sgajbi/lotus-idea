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


def keyword_string_value(node: ast.Call, keyword_name: str) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == keyword_name and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                return keyword.value.value
    return None


def keyword_string_values(node: ast.Call, keyword_name: str) -> tuple[str, ...]:
    for keyword in node.keywords:
        if keyword.arg != keyword_name:
            continue
        if isinstance(keyword.value, (ast.Tuple, ast.List, ast.Set)):
            values: list[str] = []
            for item in keyword.value.elts:
                if isinstance(item, ast.Constant) and isinstance(item.value, str):
                    values.append(item.value)
                else:
                    return ()
            return tuple(values)
    return ()
