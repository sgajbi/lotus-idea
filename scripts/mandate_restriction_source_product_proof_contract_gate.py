from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.mandate_restriction_source_product_proof import (
    MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED,
    MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION,
    build_mandate_restriction_source_product_proof_payload,
    mandate_restriction_source_product_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
PROOF_SCRIPT = ROOT / "scripts" / "generate_mandate_restriction_source_product_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "evaluationId",
    "holdingId",
    "idempotencyKey",
    "mandateId",
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
    "proofScope",
    "sourceAuthority",
    "sourceProductId",
    "sourceProductContractRef",
    "sourceTelemetryContractRef",
    "generatedAtUtc",
    "typedRestrictionDiagnosticContractReady",
    "requiredRestrictionDiagnostics",
    "restrictionDiagnosticsOwnedByAdvise",
    "lotusIdeaDoesNotClearRestrictions",
    "mandateStateAuthorityGranted",
    "restrictionClearanceAuthorityGranted",
    "suitabilityAuthorityGranted",
    "policyApprovalGranted",
    "proposalApprovalGranted",
    "rebalanceAuthorityGranted",
    "orderAuthorityGranted",
    "liveAdviseSourceProofCertified",
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


def validate_mandate_restriction_source_product_proof_contract() -> list[str]:
    errors: list[str] = []
    if not PROOF_SCRIPT.exists():
        errors.append("scripts/generate_mandate_restriction_source_product_proof.py is required")
        return errors

    payload = build_mandate_restriction_source_product_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "mandate/restriction source-product proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {MANDATE_RESTRICTION_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION}"
        )
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("source-product proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("source-product proof must not approve client publication")
    if payload.get("liveAdviseSourceProofCertified") is not False:
        errors.append("source-product proof must not certify live Advise source proof")
    for authority_key in (
        "mandateStateAuthorityGranted",
        "restrictionClearanceAuthorityGranted",
        "suitabilityAuthorityGranted",
        "policyApprovalGranted",
        "proposalApprovalGranted",
        "rebalanceAuthorityGranted",
        "orderAuthorityGranted",
    ):
        if payload.get(authority_key) is not False:
            errors.append(f"source-product proof must keep `{authority_key}` false")
    if payload.get("aggregateBlockersCleared") != list(
        MANDATE_RESTRICTION_SOURCE_PRODUCT_BLOCKERS_CLEARED
    ):
        errors.append("source-product proof must clear only the typed restriction source blocker")
    for blocker in (
        "opportunity_archetype_live_restriction_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"source-product proof must retain remaining blocker `{blocker}`")
    if not mandate_restriction_source_product_proof_is_valid(payload):
        errors.append("valid mandate/restriction source-product proof fixture should validate")

    blocked_payload = build_mandate_restriction_source_product_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        source_product_summary={
            "sourceProductId": "lotus-advise:GenericPolicyRecord:v1",
            "requiredRestrictionDiagnostics": ["mandate_restriction_review_required"],
        },
    )
    if mandate_restriction_source_product_proof_is_valid(blocked_payload):
        errors.append("blocked source-product proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_mandate_restriction_source_product_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Mandate/restriction source-product proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
