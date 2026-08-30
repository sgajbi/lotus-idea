from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.proof_worktree_import_guard import ensure_worktree_imports  # noqa: E402


ensure_worktree_imports(__file__)

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.application.feedback_evaluation import (  # noqa: E402
    MAX_OFFLINE_FEEDBACK_OBSERVATIONS,
    OFFLINE_FEEDBACK_EVALUATION_POLICY_VERSION,
    OFFLINE_FEEDBACK_EVALUATION_SCHEMA_VERSION,
)
from app.domain.feedback_taxonomy import (  # noqa: E402
    ALLOWED_FEEDBACK_REASONS,
    FEEDBACK_TAXONOMY_VERSION,
    FeedbackOutcome,
    InvalidFeedbackTaxonomyCombination,
)
from app.domain.outbox.events import SUPPORTED_OUTBOX_EVENT_TYPES  # noqa: E402


CONTRACT_PATH = Path("contracts/review-feedback/lotus-idea-feedback-evaluation.v1.json")
EXPECTED_PRODUCTION_MUTATION_AUTHORITY = "none_read_only_offline_evidence"
EXPECTED_FEEDBACK_EVENT_TYPE = "idea.feedback.recorded.v2"
EXPECTED_MIGRATION = "017_governed_feedback_taxonomy"
EXPECTED_FORBIDDEN_CONTENT = {
    "raw tenant identifier",
    "raw client identifier",
    "raw portfolio identifier",
    "actor subject",
    "free text",
    "prompt or model content",
    "downstream reference",
}
EXPECTED_COHORT_DIMENSIONS = [
    "opportunityFamily",
    "candidateIdentityPolicyVersion",
    "scorePolicyVersion",
    "score",
    "rankingPolicyVersion",
    "rankContext",
    "evidenceSupportability",
    "reviewAction",
    "feedbackTaxonomyVersion",
    "feedbackOutcome",
    "feedbackReason",
    "downstreamTarget",
    "downstreamStatus",
    "downstreamSourceSystem",
]


def validate_feedback_evaluation_contract(repository_root: Path = ROOT) -> list[str]:
    contract_path = repository_root / CONTRACT_PATH
    if not contract_path.exists():
        return [f"{CONTRACT_PATH.as_posix()}: required contract is missing"]

    try:
        contract: dict[str, Any] = json.loads(contract_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{CONTRACT_PATH.as_posix()}: invalid JSON: {exc}"]

    errors: list[str] = []
    taxonomy = contract.get("taxonomy", {})
    _expect(errors, "taxonomy.version", taxonomy.get("version"), FEEDBACK_TAXONOMY_VERSION)
    _expect(
        errors,
        "taxonomy.invalidCombinationErrorCode",
        taxonomy.get("invalidCombinationErrorCode"),
        InvalidFeedbackTaxonomyCombination.code,
    )
    _expect(
        errors,
        "taxonomy.reviewActionsRemainSeparate",
        taxonomy.get("reviewActionsRemainSeparate"),
        True,
    )

    expected_combinations = {
        outcome.value: sorted(reason.value for reason in ALLOWED_FEEDBACK_REASONS[outcome])
        for outcome in FeedbackOutcome
    }
    actual_combinations = {
        str(outcome): sorted(str(reason) for reason in reasons)
        for outcome, reasons in taxonomy.get("allowedCombinations", {}).items()
        if isinstance(reasons, list)
    }
    _expect(
        errors,
        "taxonomy.allowedCombinations",
        actual_combinations,
        expected_combinations,
    )

    persistence = contract.get("persistence", {})
    _expect(
        errors,
        "persistence.schemaMigration",
        persistence.get("schemaMigration"),
        EXPECTED_MIGRATION,
    )
    migration_path = repository_root / "migrations" / f"{EXPECTED_MIGRATION}.sql"
    rollback_path = repository_root / "migrations" / f"{EXPECTED_MIGRATION}.rollback.sql"
    for path in (migration_path, rollback_path):
        if not path.exists():
            errors.append(
                f"{path.relative_to(repository_root).as_posix()}: required migration artifact is missing"
            )

    outbox = contract.get("outbox", {})
    _expect(errors, "outbox.eventType", outbox.get("eventType"), EXPECTED_FEEDBACK_EVENT_TYPE)
    if EXPECTED_FEEDBACK_EVENT_TYPE not in SUPPORTED_OUTBOX_EVENT_TYPES:
        errors.append(f"domain outbox support is missing {EXPECTED_FEEDBACK_EVENT_TYPE}")

    evaluation = contract.get("offlineEvaluation", {})
    _expect(
        errors,
        "offlineEvaluation.schemaVersion",
        evaluation.get("schemaVersion"),
        OFFLINE_FEEDBACK_EVALUATION_SCHEMA_VERSION,
    )
    _expect(
        errors,
        "offlineEvaluation.policyVersion",
        evaluation.get("policyVersion"),
        OFFLINE_FEEDBACK_EVALUATION_POLICY_VERSION,
    )
    _expect(
        errors,
        "offlineEvaluation.maximumSourceObservations",
        evaluation.get("maximumSourceObservations"),
        MAX_OFFLINE_FEEDBACK_OBSERVATIONS,
    )
    _expect(
        errors,
        "offlineEvaluation.productionMutationAuthority",
        evaluation.get("productionMutationAuthority"),
        EXPECTED_PRODUCTION_MUTATION_AUTHORITY,
    )
    _expect(
        errors,
        "offlineEvaluation.cohortDimensions",
        evaluation.get("cohortDimensions"),
        EXPECTED_COHORT_DIMENSIONS,
    )
    _expect(
        errors,
        "offlineEvaluation.forbiddenContent",
        set(evaluation.get("forbiddenContent", [])),
        EXPECTED_FORBIDDEN_CONTENT,
    )
    _expect(errors, "supportedFeaturePromoted", contract.get("supportedFeaturePromoted"), False)
    return sorted(errors)


def _expect(errors: list[str], field: str, actual: object, expected: object) -> None:
    if actual != expected:
        errors.append(f"{field}: expected {expected!r}, got {actual!r}")


def main() -> int:
    errors = validate_feedback_evaluation_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Feedback evaluation contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
