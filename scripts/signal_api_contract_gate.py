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

SIGNAL_API_SUPPORT_MODULE = Path("src/app/api/signal_api_support.py")

SIGNAL_API_MODULES = (
    Path("src/app/api/allocation_drift_signals.py"),
    Path("src/app/api/idea_signals.py"),
    Path("src/app/api/bond_maturity_signals.py"),
    Path("src/app/api/concentration_risk_signals.py"),
    Path("src/app/api/drawdown_review_signals.py"),
    Path("src/app/api/high_volatility_signals.py"),
    Path("src/app/api/low_income_signals.py"),
    Path("src/app/api/missing_benchmark_signals.py"),
    Path("src/app/api/missing_risk_profile_signals.py"),
    Path("src/app/api/missing_suitability_signals.py"),
    Path("src/app/api/underperformance_signals.py"),
)

CORE_SOURCE_SIGNAL_MODULES = frozenset(
    {
        Path("src/app/api/bond_maturity_signals.py"),
        Path("src/app/api/idea_signals.py"),
        Path("src/app/api/low_income_signals.py"),
        Path("src/app/api/missing_benchmark_signals.py"),
    }
)

REQUIRED_SHARED_HELPERS = (
    "CallerContextHeaders",
    "signal_permission_problem_or_none",
    "evaluate_caller_supplied_signal",
    "emit_signal_evaluation_event",
    "signal_problem_responses",
)

SOURCE_SIGNAL_SHARED_HELPER = "evaluate_source_signal"

SOURCE_AUTHORITY_HELPERS = (
    "source_authority_from_refs",
    "source_authority_from_contracts",
)

CALLER_HEADER_ALIASES = (
    "X-Caller-Subject",
    "X-Caller-Roles",
    "X-Caller-Capabilities",
)


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _route_dict_value(node: ast.Dict, key_name: str) -> ast.AST | None:
    for key, value in zip(node.keys, node.values, strict=True):
        if isinstance(key, ast.Constant) and key.value == key_name:
            return value
    return None


def _responses_include_signal_problem_responses(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Dict):
        return False
    for key, value in zip(node.keys, node.values, strict=True):
        if key is None and isinstance(value, ast.Call):
            if call_name(value.func) == "signal_problem_responses":
                return True
    return False


def _validate_signal_api_module(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    if not path.exists():
        return [f"{relative_path}: missing signal API module"]

    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    errors: list[str] = []
    uses_shared_source_boundary = "_from_source" in text and SOURCE_SIGNAL_SHARED_HELPER in text

    for helper in REQUIRED_SHARED_HELPERS:
        if uses_shared_source_boundary and helper in {
            "signal_permission_problem_or_none",
            "emit_signal_evaluation_event",
        }:
            continue
        if helper not in text:
            errors.append(
                f"{relative_path}: caller-supplied signal APIs must use shared `{helper}` support"
            )
    if not any(helper in text for helper in SOURCE_AUTHORITY_HELPERS):
        errors.append(
            f"{relative_path}: caller-supplied signal APIs must use shared source-authority support "
            "(`source_authority_from_refs` or `source_authority_from_contracts`)"
        )

    if "_from_source" in text and SOURCE_SIGNAL_SHARED_HELPER not in text:
        errors.append(
            f"{relative_path}: source-backed signal APIs must use shared "
            f"`{SOURCE_SIGNAL_SHARED_HELPER}` orchestration"
        )

    if (
        path in CORE_SOURCE_SIGNAL_MODULES
        and "_from_source" in text
        and SOURCE_SIGNAL_SHARED_HELPER in text
        and not _requires_tenant_context(tree)
    ):
        errors.append(
            f"{relative_path}: Core-backed source APIs must require one trusted tenant context"
        )

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "_operation_outcome_from_signal_evaluation"
        ):
            errors.append(
                f"{relative_path}:{node.lineno}: signal API modules must use "
                "`operation_outcome_from_signal_evaluation` from signal_api_support"
            )

        if isinstance(node, ast.Call) and call_name(node.func) == "CapabilityPolicy.for_roles":
            if keyword_string_value(node, "required_capability") == "idea.signal.evaluate":
                errors.append(
                    f"{relative_path}:{node.lineno}: signal evaluation permission policy "
                    "must be centralized in signal_api_support"
                )

        if isinstance(node, ast.Call) and call_name(node.func) == "Header":
            alias = keyword_string_value(node, "alias")
            if alias in CALLER_HEADER_ALIASES:
                errors.append(
                    f"{relative_path}:{node.lineno}: signal API caller context headers "
                    "must use `CallerContextHeaders` from caller_headers"
                )

        if (
            isinstance(node, ast.Call)
            and call_name(node.func) == "signal_permission_problem_or_none"
        ):
            if not any(keyword.arg == "requested_access_scope" for keyword in node.keywords):
                errors.append(
                    f"{relative_path}:{node.lineno}: signal permission checks must pass "
                    "`requested_access_scope` for entitlement-scope intersection"
                )

        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Dict)
            and any(
                isinstance(target, ast.Name) and target.id.endswith("_EVALUATE_ROUTE")
                for target in node.targets
            )
        ):
            responses = _route_dict_value(node.value, "responses")
            if not _responses_include_signal_problem_responses(responses):
                errors.append(
                    f"{relative_path}:{node.lineno}: signal evaluation routes must compose "
                    "`signal_problem_responses()` for product-safe OpenAPI 400/403 examples"
                )

    return errors


def _requires_tenant_context(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Call)
        and call_name(node.func) == SOURCE_SIGNAL_SHARED_HELPER
        and any(
            keyword.arg == "require_tenant_context"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
            for keyword in node.keywords
        )
        for node in ast.walk(tree)
    )


def _validate_signal_api_support(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    if not path.exists():
        return [f"{relative_path}: missing shared signal API support module"]

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[str] = []
    signal_permission_function: ast.FunctionDef | None = None
    signal_policy: ast.Call | None = None

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "signal_permission_problem_or_none":
            signal_permission_function = node
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "SIGNAL_EVALUATION_POLICY"
                for target in node.targets
            ):
                if isinstance(node.value, ast.Call):
                    signal_policy = node.value

    if signal_permission_function is None:
        return [
            f"{relative_path}: shared signal API support must define "
            "`signal_permission_problem_or_none`"
        ]
    if signal_policy is None or call_name(signal_policy.func) != "CapabilityPolicy.for_roles":
        errors.append(
            f"{relative_path}: shared signal API support must define "
            "`SIGNAL_EVALUATION_POLICY` with `CapabilityPolicy.for_roles`"
        )
    elif keyword_string_value(
        signal_policy, "required_capability"
    ) != "idea.signal.evaluate" or keyword_string_values(signal_policy, "allowed_roles") != (
        "advisor",
    ):
        errors.append(
            f"{relative_path}:{signal_policy.lineno}: signal evaluation policy must require "
            "`idea.signal.evaluate` capability and `advisor` role"
        )

    uses_strict_policy = False
    for node in ast.walk(signal_permission_function):
        if isinstance(node, ast.Call):
            function_name = call_name(node.func)
            if function_name == "require_capability":
                errors.append(
                    f"{relative_path}:{node.lineno}: signal evaluation must require both "
                    "`advisor` role and `idea.signal.evaluate` capability"
                )
            if function_name == "require_role_and_capability":
                uses_strict_policy = True

    if not uses_strict_policy:
        errors.append(
            f"{relative_path}: signal evaluation must use `require_role_and_capability` "
            "for least-privilege route authorization"
        )

    return errors


def validate_signal_api_contract(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_signal_api_support(root / SIGNAL_API_SUPPORT_MODULE, root))
    for relative_path in SIGNAL_API_MODULES:
        errors.extend(_validate_signal_api_module(root / relative_path, root))
    return sorted(errors)


def main() -> int:
    errors = validate_signal_api_contract()
    if errors:
        print("Signal API contract gate failed:")
        print("\n".join(errors))
        return 1
    print("Signal API contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
