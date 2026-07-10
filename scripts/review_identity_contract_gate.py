from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FRAGMENTS = {
    "src/app/domain/review_governance.py": (
        "class ReviewMutationIdentity",
        "class ReviewMutationType",
        "def review_mutation_identity_from_command",
        "def feedback_mutation_identity_from_command",
    ),
    "src/app/application/review_workflow.py": (
        "identity=review_mutation_identity_from_command(",
        "identity=feedback_mutation_identity_from_command(",
    ),
    "src/app/domain/persistence.py": (
        "ReviewPersistenceDecision.IDENTITY_CONFLICT",
        "def _review_identity_result",
        "def _review_identity_record",
    ),
    "src/app/infrastructure/postgres_repository.py": (
        "ON CONFLICT (review_decision_id) DO NOTHING",
        "ON CONFLICT (feedback_event_id) DO NOTHING",
        "raise ConcurrentReviewIdentityMutationError",
    ),
    "src/app/infrastructure/postgres_repository_delta.py": (
        "_insert_review_identity_delta(writer, cursor, before_record, after_record)",
        "def _insert_review_identity_delta",
    ),
    "src/app/infrastructure/postgres_mutation_retry.py": ("ConcurrentReviewIdentityMutationError",),
    "src/app/api/review_workflow_operations.py": ('code="review_identity_conflict"',),
    "src/app/api/review_workflow.py": (
        "_REVIEW_IDENTITY_CONFLICT",
        "_REVIEW_IDEMPOTENCY_CONFLICT",
        "merged_problem_response_metadata(",
    ),
    "docs/architecture/review-feedback-identity-and-idempotency.md": (
        "Identity Contract",
        "Decision Matrix",
        "PostgreSQL Atomicity",
        "Runtime Modularity Decision",
    ),
}


def validate_review_identity_contract(repository_root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, fragments in REQUIRED_FRAGMENTS.items():
        path = repository_root / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: required review-identity artifact is missing")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path}: missing required fragment `{fragment}`")
    return sorted(errors)


def main() -> int:
    errors = validate_review_identity_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Review identity contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
