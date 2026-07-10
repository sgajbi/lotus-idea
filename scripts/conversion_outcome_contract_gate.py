from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FRAGMENTS = {
    "src/app/domain/conversion_outcome_policy.py": (
        "CONVERSION_OUTCOME_POLICY_VERSION",
        "class ConversionOutcomeIdentity",
        "def validate_conversion_outcome_history",
        "def validate_conversion_outcome_progression",
        "def current_conversion_outcome_identity",
    ),
    "src/app/application/conversion_workflow.py": (
        "precheck_conversion_outcome_mutation(",
        "conversion_outcomes_for_intent(",
        "existing_outcomes=existing_outcomes",
    ),
    "src/app/domain/persistence.py": (
        "ConversionPersistenceDecision.OUTCOME_CONFLICT",
        "validate_conversion_outcome_progression(",
    ),
    "src/app/domain/persistence_conversion_outcomes.py": (
        "def conversion_outcome_identity_result",
        "ConversionPersistenceDecision.OUTCOME_CONFLICT",
    ),
    "src/app/infrastructure/postgres_conversion_outcome.py": (
        "ON CONFLICT DO NOTHING",
        "raise ConcurrentConversionOutcomeMutationError",
    ),
    "src/app/infrastructure/postgres_mutation_retry.py": (
        "ConcurrentConversionOutcomeMutationError",
    ),
    "migrations/006_conversion_outcome_lifecycle.sql": (
        "UNIQUE (conversion_intent_id, source_event_version)",
        "idea_conversion_outcome_quarantine",
        "invalid_legacy_conversion_outcome_history",
    ),
    "src/app/api/conversion_governance.py": (
        "_CONVERSION_IDEMPOTENCY_CONFLICT",
        "_CONVERSION_OUTCOME_CONFLICT",
        "merged_problem_response_metadata(",
    ),
    "docs/architecture/conversion-outcome-identity-and-lifecycle.md": (
        "Identity Contract",
        "Lifecycle And Correction Policy",
        "PostgreSQL Atomicity And Legacy Quarantine",
        "Runtime Modularity Decision",
    ),
}


def validate_conversion_outcome_contract(repository_root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, fragments in REQUIRED_FRAGMENTS.items():
        path = repository_root / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: required conversion-outcome artifact is missing")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path}: missing required fragment `{fragment}`")
    return sorted(errors)


def main() -> int:
    errors = validate_conversion_outcome_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Conversion outcome contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
