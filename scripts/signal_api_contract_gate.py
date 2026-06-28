from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SIGNAL_API_MODULES = (
    Path("src/app/api/idea_signals.py"),
    Path("src/app/api/bond_maturity_signals.py"),
    Path("src/app/api/concentration_risk_signals.py"),
    Path("src/app/api/low_income_signals.py"),
    Path("src/app/api/missing_benchmark_signals.py"),
    Path("src/app/api/missing_risk_profile_signals.py"),
    Path("src/app/api/missing_suitability_signals.py"),
)

REQUIRED_SHARED_HELPERS = (
    "signal_permission_problem_or_none",
    "emit_signal_evaluation_event",
    "source_authority_from_refs",
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
