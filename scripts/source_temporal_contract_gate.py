from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_TEMPORAL_MODULE = Path("src/app/domain/source_temporal.py")
SIGNAL_DOMAIN_MODULES = (
    Path("src/app/domain/bond_maturity_signal.py"),
    Path("src/app/domain/low_income_signal.py"),
    Path("src/app/domain/mandate_restriction_signal.py"),
    Path("src/app/domain/missing_benchmark_signal.py"),
    Path("src/app/domain/missing_risk_profile_signal.py"),
    Path("src/app/domain/missing_suitability_signal.py"),
    Path("src/app/domain/signal_evaluation.py"),
)
TEMPORAL_HELPER = "temporal_blocked_signal_result"
SOURCE_TEMPORAL_CONTRACT_FRAGMENTS = (
    "SOURCE_TEMPORAL_CONTRACT_VERSION",
    "for family in OpportunityFamily",
    "NEW_CONTENT_HASH_CREATES_NEW_CANDIDATE_IDENTITY",
)


def validate_source_temporal_contract(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    source_temporal_path = root / SOURCE_TEMPORAL_MODULE
    if not source_temporal_path.is_file():
        errors.append(f"{SOURCE_TEMPORAL_MODULE.as_posix()}: shared temporal policy is missing")
    else:
        source = source_temporal_path.read_text(encoding="utf-8")
        for fragment in SOURCE_TEMPORAL_CONTRACT_FRAGMENTS:
            if fragment not in source:
                errors.append(
                    f"{SOURCE_TEMPORAL_MODULE.as_posix()}: required contract `{fragment}` is missing"
                )

    for relative_path in SIGNAL_DOMAIN_MODULES:
        path = root / relative_path
        if not path.is_file():
            errors.append(f"{relative_path.as_posix()}: signal domain module is missing")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        helper_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == TEMPORAL_HELPER
        ]
        if not helper_calls:
            errors.append(
                f"{relative_path.as_posix()}: signal domain policy must call `{TEMPORAL_HELPER}`"
            )
    return sorted(errors)


def main() -> int:
    errors = validate_source_temporal_contract()
    if errors:
        print("Source temporal contract gate failed:")
        print("\n".join(errors))
        return 1
    print("Source temporal contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
