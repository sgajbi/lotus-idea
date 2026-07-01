from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_DIR = Path("src/app/api")
CALLER_HEADERS_MODULE = API_DIR / "caller_headers.py"
TRUSTED_HEADER_NAME = "TRUSTED_CALLER_CONTEXT_HEADER"
TRUSTED_HEADER_VALUE = "X-Lotus-Trusted-Caller-Context"
CALLER_HEADER_ALIASES = (
    "X-Caller-Subject",
    "X-Caller-Roles",
    "X-Caller-Capabilities",
    "X-Caller-Tenant-Ids",
    "X-Caller-Book-Ids",
    "X-Caller-Portfolio-Ids",
    "X-Caller-Client-Ids",
)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _header_alias(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call) or _call_name(node.func) != "Header":
        return None
    for keyword in node.keywords:
        if keyword.arg != "alias":
            continue
        if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
        if isinstance(keyword.value, ast.Name) and keyword.value.id == TRUSTED_HEADER_NAME:
            return TRUSTED_HEADER_VALUE
    return None


def _function_header_aliases(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    aliases: set[str] = set()
    for default in node.args.defaults:
        alias = _header_alias(default)
        if alias is not None:
            aliases.add(alias)
    for arg in (*node.args.args, *node.args.kwonlyargs):
        if arg.annotation is None:
            continue
        for annotation_node in ast.walk(arg.annotation):
            alias = _header_alias(annotation_node)
            if alias is not None:
                aliases.add(alias)
    return aliases


def _validate_caller_headers_module(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    if not path.exists():
        return [f"{relative_path}: missing caller headers module"]

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    parser_function: ast.FunctionDef | None = None
    standard_dependency_function: ast.FunctionDef | None = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "caller_context_from_headers":
            parser_function = node
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "caller_context_from_standard_headers"
        ):
            standard_dependency_function = node

    if parser_function is None:
        errors.append(f"{relative_path}: missing caller_context_from_headers")
    else:
        parser_args = {arg.arg for arg in parser_function.args.kwonlyargs}
        if "trusted_caller_context" not in parser_args:
            errors.append(
                f"{relative_path}:{parser_function.lineno}: caller_context_from_headers "
                "must require trusted_caller_context provenance input"
            )

    if standard_dependency_function is None:
        errors.append(f"{relative_path}: missing caller_context_from_standard_headers")
    else:
        aliases = _function_header_aliases(standard_dependency_function)
        if TRUSTED_HEADER_VALUE not in aliases:
            errors.append(
                f"{relative_path}:{standard_dependency_function.lineno}: "
                "caller_context_from_standard_headers must bind "
                f"`{TRUSTED_HEADER_VALUE}`"
            )

    return errors


def _validate_api_module(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            aliases = _function_header_aliases(node)
            if aliases.intersection(CALLER_HEADER_ALIASES) and TRUSTED_HEADER_VALUE not in aliases:
                errors.append(
                    f"{relative_path}:{node.lineno}: route-local caller context headers "
                    f"must also bind `{TRUSTED_HEADER_VALUE}`"
                )

        if isinstance(node, ast.Call) and _call_name(node.func) == "caller_context_from_headers":
            if not any(keyword.arg == "trusted_caller_context" for keyword in node.keywords):
                errors.append(
                    f"{relative_path}:{node.lineno}: route-local caller_context_from_headers "
                    "calls must forward trusted_caller_context"
                )

    return errors


def validate_caller_context_contract(root: Path = ROOT) -> list[str]:
    errors = _validate_caller_headers_module(root / CALLER_HEADERS_MODULE, root)
    for path in sorted((root / API_DIR).glob("*.py")):
        if path.name == CALLER_HEADERS_MODULE.name:
            continue
        errors.extend(_validate_api_module(path, root))
    return sorted(errors)


def main() -> int:
    errors = validate_caller_context_contract()
    if errors:
        print("Caller context contract gate failed:")
        print(f"{len(errors)} caller context contract violation(s) found")
        return 1
    print("Caller context contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
