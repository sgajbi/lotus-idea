from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

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

REQUIRED_SHARED_HELPERS = (
    "CallerContextHeaders",
    "signal_permission_problem_or_none",
    "emit_signal_evaluation_event",
    "signal_problem_responses",
    "source_authority_from_refs",
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


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return None


def _keyword_value(node: ast.Call, keyword_name: str) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == keyword_name and isinstance(keyword.value, ast.Constant):
            if isinstance(keyword.value.value, str):
                return keyword.value.value
    return None


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
            if _call_name(value.func) == "signal_problem_responses":
                return True
    return False


def _validate_signal_api_module(path: Path, root: Path) -> list[str]:
    relative_path = _relative(path, root)
    if not path.exists():
        return [f"{relative_path}: missing signal API module"]

    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    errors: list[str] = []

    for helper in REQUIRED_SHARED_HELPERS:
        if helper not in text:
            errors.append(
                f"{relative_path}: caller-supplied signal APIs must use shared `{helper}` support"
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

        if isinstance(node, ast.Call) and _call_name(node.func) == "CapabilityPolicy.for_roles":
            if _keyword_value(node, "required_capability") == "idea.signal.evaluate":
                errors.append(
                    f"{relative_path}:{node.lineno}: signal evaluation permission policy "
                    "must be centralized in signal_api_support"
                )

        if isinstance(node, ast.Call) and _call_name(node.func) == "Header":
            alias = _keyword_value(node, "alias")
            if alias in CALLER_HEADER_ALIASES:
                errors.append(
                    f"{relative_path}:{node.lineno}: signal API caller context headers "
                    "must use `CallerContextHeaders` from caller_headers"
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


def validate_signal_api_contract(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
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
