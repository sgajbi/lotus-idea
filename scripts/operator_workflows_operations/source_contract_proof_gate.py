from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.application.operator_workflows_operations.source_contract_proof import (  # noqa: E402
    EXPECTED_ALERT_IDS,
    EXPECTED_DASHBOARD_UID,
    EXPECTED_METRIC_NAME,
    OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED,
    OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION,
    OPERATOR_WORKFLOWS_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES,
    REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS,
    REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS,
    build_operator_workflows_operations_proof_payload,
    operator_workflows_operations_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "conversionIntentId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "rawPayload",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "traceId",
}
FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "account_id",
    "candidate_id",
    "client_id",
    "conversion_intent_id",
    "correlation_id",
    "holding_id",
    "idempotency_key",
    "portfolio_id",
    "raw payload",
    "request-body",
    "response-body",
    "source_payload",
    "trace_id",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_operator_workflows_operations_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_operator_workflows_operations_proof_payload(
        generated_at_utc=datetime(2026, 7, 1, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION:
        errors.append(
            "operator workflows operations proof schema must be "
            f"{OPERATOR_WORKFLOWS_OPERATIONS_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_OPERATOR_WORKFLOWS_OPERATIONS_EVIDENCE_REFS
    ):
        errors.append("operator workflows operations proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS_CLEARED
    ):
        errors.append("operator workflows operations source proof must not clear runtime blockers")
    if proof.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("operator workflows operations proof evidence class must be source_contract")
    if tuple((proof.get("requiredBlockerEvidenceClasses") or {}).items()) != (
        OPERATOR_WORKFLOWS_OPERATIONS_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    ):
        errors.append("operator workflows operations proof blocker evidence classes drifted")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OPERATOR_WORKFLOWS_OPERATIONS_BLOCKERS
    ):
        errors.append("operator workflows operations proof must retain non-operations blockers")
    if proof.get("metricFamily") != EXPECTED_METRIC_NAME:
        errors.append("operator workflows operations proof must use the operation metric")
    if proof.get("dashboardUid") != EXPECTED_DASHBOARD_UID:
        errors.append("operator workflows operations proof dashboard UID drifted")
    if tuple(proof.get("alertIds") or ()) != EXPECTED_ALERT_IDS:
        errors.append("operator workflows operations proof alert IDs drifted")
    if not operator_workflows_operations_proof_is_valid(proof):
        errors.append("operator workflows operations proof must validate repo-owned artifacts")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_operator_workflows_operations_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Operator workflows operations proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
