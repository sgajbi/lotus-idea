from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.missing_suitability_live_proof import (
    MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED,
    MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION,
    build_missing_suitability_live_proof_payload,
    missing_suitability_live_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_missing_suitability_live_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "evaluationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "requestBody",
    "responseBody",
    "sourcePayload",
    "sourceRoute",
    "traceId",
    "transactionId",
}

FORBIDDEN_TEXT_FRAGMENTS = {
    "PB_SG_GLOBAL_BAL_001",
    "request-body",
    "response-body",
    "advise-policy-evaluation:",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductId",
    "generatedAtUtc",
    "liveAdviseSourceAttempted",
    "runStatus",
    "evaluationOutcome",
    "candidateGenerated",
    "sourceEvidenceCurrent",
    "clientReadyPublicationBlocked",
    "advisePolicyWorkflowReady",
    "sourceDiagnosticCodes",
    "reasonCodes",
    "unsupportedReasons",
    "suitabilityAuthorityGranted",
    "policyApprovalGranted",
    "proposalApprovalGranted",
    "clientPublicationReady",
    "supportedFeaturePromoted",
    "proofClosed",
    "aggregateBlockersCleared",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_missing_suitability_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_missing_suitability_live_proof.py is required")
        return errors

    payload = build_missing_suitability_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 10, 10, tzinfo=UTC),
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "clientReadyPublicationBlocked": True,
            "advisePolicyWorkflowReady": True,
            "sourceDiagnosticCodes": ["advise_policy_requirements_open"],
            "reasonCodes": ["suitability_context_missing", "review_required"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "missing suitability live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {MISSING_SUITABILITY_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("missing suitability proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("missing suitability proof must not approve client publication")
    for authority_key in (
        "suitabilityAuthorityGranted",
        "policyApprovalGranted",
        "proposalApprovalGranted",
    ):
        if payload.get(authority_key) is not False:
            errors.append(f"missing suitability proof must keep `{authority_key}` false")
    if payload.get("proofClosed") is not False:
        errors.append("missing suitability proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(MISSING_SUITABILITY_LIVE_BLOCKERS_CLEARED):
        errors.append("missing suitability proof must clear only the Advise policy source blocker")
    for blocker in (
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"missing suitability proof must retain remaining blocker `{blocker}`")
    if not missing_suitability_live_proof_is_valid(payload):
        errors.append("valid missing suitability proof fixture should validate")

    blocked_payload = build_missing_suitability_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 10, 10, tzinfo=UTC),
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "errorCode": "advise_policy_workflow_unavailable",
            "sourceEvidenceCurrent": False,
            "clientReadyPublicationBlocked": False,
            "advisePolicyWorkflowReady": False,
            "evaluationOutcome": "blocked",
            "sourceDiagnosticCodes": ["advise_policy_workflow_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if missing_suitability_live_proof_is_valid(blocked_payload):
        errors.append("blocked missing suitability proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_missing_suitability_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Missing suitability live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
