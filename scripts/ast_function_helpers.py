from __future__ import annotations

import ast


def is_non_implementation_stub(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    if len(node.body) != 1:
        return False
    statement = node.body[0]
    if isinstance(statement, ast.Pass):
        return True
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and statement.value.value is Ellipsis
    )
