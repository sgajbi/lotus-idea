from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR_MODULE = "app.application.supported_feature_promotion"
EVALUATOR_NAME = "evaluate_supported_feature_promotion"
REQUIRED_CALLERS = {
    "scripts/supported_features_gate.py": EVALUATOR_MODULE,
    "src/app/application/implementation_proof_readiness.py": EVALUATOR_MODULE,
}
TRUTHFUL_PROJECTIONS = {
    "src/app/api/implementation_proof_readiness.py": (
        "supportedFeaturePromoted=snapshot.supported_features_promoted"
    ),
    "scripts/generate_implementation_proof_readiness.py": (
        '"supportedFeaturePromoted": snapshot.supported_features_promoted'
    ),
}


def validate_supported_feature_promotion_contract(
    repository_root: Path = ROOT,
) -> list[str]:
    errors: list[str] = []
    for relative_path, module in REQUIRED_CALLERS.items():
        path = repository_root / relative_path
        if not path.exists():
            errors.append(f"missing supported-feature promotion caller: {relative_path}")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if not _imports_name(tree, module=module, name=EVALUATOR_NAME):
            errors.append(f"{relative_path} must import {EVALUATOR_NAME} from {module}")
        if EVALUATOR_NAME not in _called_names(tree):
            errors.append(f"{relative_path} must call {EVALUATOR_NAME}")
        if "_supported_feature_count" in path.read_text(encoding="utf-8"):
            errors.append(f"{relative_path} must not restore status-only feature counting")

    for relative_path, required_fragment in TRUTHFUL_PROJECTIONS.items():
        path = repository_root / relative_path
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if required_fragment not in text:
            errors.append(
                f"{relative_path} must project supportedFeaturePromoted from the domain snapshot"
            )
    return sorted(errors)


def _imports_name(tree: ast.AST, *, module: str, name: str) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == module
        and any(alias.name == name for alias in node.names)
        for node in ast.walk(tree)
    )


def _called_names(tree: ast.AST) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def main() -> int:
    errors = validate_supported_feature_promotion_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Supported-feature promotion contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
