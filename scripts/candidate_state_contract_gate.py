from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FRAGMENTS = {
    "src/app/domain/candidate_state.py": (
        'CANDIDATE_STATE_POLICY_VERSION = "idea-candidate-state-v1"',
        "ALLOWED_REVIEW_POSTURES_BY_LIFECYCLE",
        "class InvalidCandidateState",
        "def candidate_state_is_compatible",
        "def validate_candidate_state",
        "def review_posture_for_transition",
    ),
    "src/app/domain/ideas.py": (
        "validate_candidate_state(",
        "review_posture=review_posture_for_transition(",
    ),
    "src/app/domain/review_governance.py": (
        "_REVIEW_ACTION_LIFECYCLE_STATUSES",
        '"prior_lifecycle_status"',
        '"prior_review_posture"',
        '"requested_action"',
        '"policy_version"',
    ),
    "src/app/infrastructure/postgres_review_queue.py": (
        "candidate_record_state_compatibility_sql()",
        "QueueExclusionReason.INVALID_STATE",
        "AS invalid_state",
    ),
    "src/app/api/review_workflow.py": (
        'code="candidate_state_conflict"',
        '"candidate_id":',
        '"lifecycle_status":',
        '"review_posture":',
        '"requested_action":',
        '"policy_version":',
    ),
    "migrations/005_candidate_state_policy.sql": (
        "idea_candidate_state_quarantine",
        "idea-candidate-state-v1",
        "candidate_state_conflict",
        "ck_idea_candidate_record_state_policy_v1",
        "NOT VALID",
    ),
    "migrations/005_candidate_state_policy.rollback.sql": (
        "DROP CONSTRAINT IF EXISTS ck_idea_candidate_record_state_policy_v1",
        "DROP TABLE IF EXISTS idea_candidate_state_quarantine",
    ),
    "docs/architecture/candidate-lifecycle-review-posture-policy.md": (
        "idea-candidate-state-v1",
        "Golden Matrix",
        "Legacy Reconciliation",
        "Runtime Modularity Decision",
    ),
}


def validate_candidate_state_contract(repository_root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    for relative_path, fragments in REQUIRED_FRAGMENTS.items():
        path = repository_root / relative_path
        if not path.exists():
            errors.append(f"{relative_path}: required candidate-state artifact is missing")
            continue
        content = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{relative_path}: missing required fragment `{fragment}`")
    return sorted(errors)


def main() -> int:
    errors = validate_candidate_state_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Candidate state contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
