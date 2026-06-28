from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.mandate_restriction_live_proof import (
    MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED,
    MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION,
    build_mandate_restriction_live_proof_payload,
    mandate_restriction_live_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_mandate_restriction_live_proof.py"

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
    "restrictionReviewReady",
    "sourceDiagnosticCodes",
    "reasonCodes",
    "unsupportedReasons",
    "mandateStateChanged",
    "restrictionCleared",
    "suitabilityAuthorityGranted",
    "policyApprovalGranted",
    "proposalApprovalGranted",
    "rebalanceAuthorityGranted",
    "orderAuthorityGranted",
    "clientPublicationReady",
    "typedRestrictionSourceProductCertified",
    "supportedFeaturePromoted",
    "proofClosed",
    "aggregateBlockersCleared",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


def validate_mandate_restriction_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_mandate_restriction_live_proof.py is required")
        return errors

    payload = build_mandate_restriction_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "restrictionReviewReady": True,
            "sourceDiagnosticCodes": ["mandate_restriction_review_required"],
            "reasonCodes": ["mandate_restriction_review", "review_required"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "mandate/restriction live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {MANDATE_RESTRICTION_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("mandate/restriction proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("mandate/restriction proof must not approve client publication")
    for authority_key in (
        "mandateStateChanged",
        "restrictionCleared",
        "suitabilityAuthorityGranted",
        "policyApprovalGranted",
        "proposalApprovalGranted",
        "rebalanceAuthorityGranted",
        "orderAuthorityGranted",
    ):
        if payload.get(authority_key) is not False:
            errors.append(f"mandate/restriction proof must keep `{authority_key}` false")
    if payload.get("typedRestrictionSourceProductCertified") is not False:
        errors.append("mandate/restriction proof must not certify typed restriction source product")
    if payload.get("proofClosed") is not False:
        errors.append("mandate/restriction proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(MANDATE_RESTRICTION_LIVE_BLOCKERS_CLEARED):
        errors.append(
            "mandate/restriction proof must clear only the restriction live-source blocker"
        )
    for blocker in (
        "opportunity_archetype_typed_restriction_source_product_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"mandate/restriction proof must retain remaining blocker `{blocker}`")
    if not mandate_restriction_live_proof_is_valid(payload):
        errors.append("valid mandate/restriction proof fixture should validate")

    blocked_payload = build_mandate_restriction_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        live_advise_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-advise",
            "sourceProductId": "lotus-advise:AdvisoryPolicyEvaluationRecord:v1",
            "errorCode": "advise_policy_workflow_unavailable",
            "sourceEvidenceCurrent": False,
            "restrictionReviewReady": False,
            "evaluationOutcome": "blocked",
            "sourceDiagnosticCodes": ["advise_policy_workflow_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if mandate_restriction_live_proof_is_valid(blocked_payload):
        errors.append("blocked mandate/restriction proof fixture must not validate")

    _validate_forbidden_content(payload, errors)
    _validate_forbidden_content(blocked_payload, errors)
    return errors


def _validate_forbidden_content(value: object, errors: list[str], path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}"
            if key_text in FORBIDDEN_KEYS:
                errors.append(f"{next_path}: forbidden source-sensitive key is present")
            _validate_forbidden_content(nested, errors, next_path)
        return
    if isinstance(value, list):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def main() -> int:
    errors = validate_mandate_restriction_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Mandate/restriction live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
