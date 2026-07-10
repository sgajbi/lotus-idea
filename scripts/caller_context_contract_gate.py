from __future__ import annotations

import ast
import sys
from pathlib import Path

try:
    from scripts.ast_gate_helpers import call_name, keyword_string_value, keyword_string_values
except ModuleNotFoundError:
    from ast_gate_helpers import (  # type: ignore[import-not-found,no-redef]
        call_name,
        keyword_string_value,
        keyword_string_values,
    )


ROOT = Path(__file__).resolve().parents[1]
API_DIR = Path("src/app/api")
CALLER_HEADERS_MODULE = API_DIR / "caller_headers.py"
CALLER_CONTEXT_OPENAPI_MODULE = API_DIR / "caller_context_openapi.py"
PROBLEM_DETAILS_MODULE = API_DIR / "problem_details.py"
MAIN_MODULE = Path("src/app/main.py")
ERRORS_MODULE = Path("src/app/errors.py")
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


def _header_alias(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call) or call_name(node.func) != "Header":
        return None
    for keyword in node.keywords:
        if keyword.arg != "alias":
            continue
        if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
        if isinstance(keyword.value, ast.Name) and keyword.value.id == TRUSTED_HEADER_NAME:
            return TRUSTED_HEADER_VALUE
    return None


def _assigned_policy_names_requiring_strict_route_auth(tree: ast.AST) -> dict[str, int]:
    policies: dict[str, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if call_name(node.value.func) != "CapabilityPolicy.for_roles":
            continue
        required_capability = keyword_string_value(node.value, "required_capability")
        allowed_roles = keyword_string_values(node.value, "allowed_roles")
        if not required_capability or not required_capability.startswith("idea."):
            continue
        if not allowed_roles:
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                policies[target.id] = node.lineno
    return policies


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

    source_text = path.read_text(encoding="utf-8")
    if (
        parser_function is not None
        and "trusted_caller_context" in {arg.arg for arg in parser_function.args.kwonlyargs}
        and "ProblemDetailsHTTPException" not in source_text
    ):
        errors.append(
            f"{relative_path}: caller-context boundary must preserve stable ProblemDetails codes"
        )
    if "ProblemDetailsHTTPException" in source_text:
        for fragment in (
            'code="invalid_request"',
            'error_category="caller_context_invalid_request"',
            'code="permission_denied"',
            'error_category="caller_context_permission_denied"',
        ):
            if fragment not in source_text:
                errors.append(
                    f"{relative_path}: caller-context boundary contract `{fragment}` is missing"
                )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        if call_name(node.exc.func) == "HTTPException":
            errors.append(
                f"{relative_path}:{node.lineno}: caller-context failures must use "
                "ProblemDetailsHTTPException"
            )

    return errors


def _validate_api_module(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    strict_policy_names = _assigned_policy_names_requiring_strict_route_auth(tree)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            aliases = _function_header_aliases(node)
            if aliases.intersection(CALLER_HEADER_ALIASES) and TRUSTED_HEADER_VALUE not in aliases:
                errors.append(
                    f"{relative_path}:{node.lineno}: route-local caller context headers "
                    f"must also bind `{TRUSTED_HEADER_VALUE}`"
                )

        if isinstance(node, ast.Call) and call_name(node.func) == "caller_context_from_headers":
            if not any(keyword.arg == "trusted_caller_context" for keyword in node.keywords):
                errors.append(
                    f"{relative_path}:{node.lineno}: route-local caller_context_from_headers "
                    "calls must forward trusted_caller_context"
                )

        if isinstance(node, ast.Call) and call_name(node.func) == "require_capability":
            policy_arg = node.args[1] if len(node.args) > 1 else None
            if isinstance(policy_arg, ast.Name) and policy_arg.id in strict_policy_names:
                errors.append(
                    f"{relative_path}:{node.lineno}: `{policy_arg.id}` names both "
                    "allowed_roles and an idea.* capability, so route authorization must "
                    "use `require_role_and_capability`"
                )

    return errors


def validate_caller_context_contract(root: Path = ROOT) -> list[str]:
    errors = _validate_caller_headers_module(root / CALLER_HEADERS_MODULE, root)
    for path in sorted((root / API_DIR).glob("*.py")):
        if path.name == CALLER_HEADERS_MODULE.name:
            continue
        errors.extend(_validate_api_module(path, root))
    shared_contracts = {
        MAIN_MODULE: (
            "isinstance(exc, ProblemDetailsHTTPException)",
            "exc.error_category",
        ),
        CALLER_CONTEXT_OPENAPI_MODULE: (
            "_apply_caller_context_problem_responses(operation)",
            '"invalid_request"',
            '"permission_denied"',
            "application/problem+json",
        ),
        PROBLEM_DETAILS_MODULE: ("self.error_category = error_category",),
        ERRORS_MODULE: ('media_type="application/problem+json"',),
    }
    for relative_path, fragments in shared_contracts.items():
        path = root / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                errors.append(
                    f"{relative_path.as_posix()}: caller-context boundary contract "
                    f"`{fragment}` is missing"
                )
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
