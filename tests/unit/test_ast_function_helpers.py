from __future__ import annotations

import ast

from scripts.ast_function_helpers import is_non_implementation_stub


def _first_function(source: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    module = ast.parse(source)
    function = module.body[0]
    assert isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
    return function


def test_identifies_ellipsis_only_function_stub() -> None:
    assert is_non_implementation_stub(_first_function("def port_method(): ...")) is True


def test_identifies_pass_only_function_stub() -> None:
    assert is_non_implementation_stub(_first_function("def port_method():\n    pass")) is True


def test_does_not_classify_executable_function_body_as_stub() -> None:
    function = _first_function("def compute():\n    value = 1\n    return value")

    assert is_non_implementation_stub(function) is False
