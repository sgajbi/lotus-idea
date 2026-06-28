from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.missing_risk_profile_source_product_proof import (
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED,
    MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION,
    build_missing_risk_profile_source_product_proof_payload,
    missing_risk_profile_source_product_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]
PROOF_SCRIPT = ROOT / "scripts" / "generate_missing_risk_profile_source_product_proof.py"

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
    "proofScope",
    "sourceAuthority",
    "sourceProductId",
    "sourceProductContractRef",
    "sourceTelemetryContractRef",
    "generatedAtUtc",
    "typedRiskProfileDiagnosticContractReady",
    "requiredRiskProfileDiagnostics",
    "riskProfileDiagnosticsOwnedByAdvise",
    "lotusIdeaDoesNotApproveRiskProfile",
    "riskProfileAuthorityGranted",
    "suitabilityAuthorityGranted",
    "policyApprovalGranted",
    "proposalApprovalGranted",
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


def validate_missing_risk_profile_source_product_proof_contract() -> list[str]:
    errors: list[str] = []
    if not PROOF_SCRIPT.exists():
        errors.append("scripts/generate_missing_risk_profile_source_product_proof.py is required")
        return errors

    payload = build_missing_risk_profile_source_product_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "missing risk-profile source-product proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {MISSING_RISK_PROFILE_SOURCE_PRODUCT_PROOF_SCHEMA_VERSION}"
        )
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("source-product proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("source-product proof must not approve client publication")
    if payload.get("liveAdviseSourceProofCertified") is not False:
        errors.append("source-product proof must not certify live Advise source proof")
    for authority_key in (
        "riskProfileAuthorityGranted",
        "suitabilityAuthorityGranted",
        "policyApprovalGranted",
        "proposalApprovalGranted",
    ):
        if payload.get(authority_key) is not False:
            errors.append(f"source-product proof must keep `{authority_key}` false")
    if payload.get("aggregateBlockersCleared") != list(
        MISSING_RISK_PROFILE_SOURCE_PRODUCT_BLOCKERS_CLEARED
    ):
        errors.append("source-product proof must clear only the typed Advise source blocker")
    for blocker in (
        "opportunity_archetype_advise_risk_profile_live_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"source-product proof must retain remaining blocker `{blocker}`")
    if not missing_risk_profile_source_product_proof_is_valid(payload):
        errors.append("valid missing risk-profile source-product proof fixture should validate")

    blocked_payload = build_missing_risk_profile_source_product_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        source_product_summary={
            "sourceProductId": "lotus-advise:GenericPolicyRecord:v1",
            "requiredRiskProfileDiagnostics": ["risk_profile_missing"],
        },
    )
    if missing_risk_profile_source_product_proof_is_valid(blocked_payload):
        errors.append("blocked source-product proof fixture must not validate")

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
    errors = validate_missing_risk_profile_source_product_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Missing risk-profile source-product proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
