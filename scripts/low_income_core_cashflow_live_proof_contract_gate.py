from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.low_income_core_cashflow_live_proof import (
    LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED,
    LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION,
    build_low_income_core_cashflow_live_proof_payload,
    low_income_core_cashflow_live_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_low_income_core_cashflow_live_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
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
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductIds",
    "generatedAtUtc",
    "liveCoreSourceAttempted",
    "runStatus",
    "cashMovementRefPresent",
    "cashflowProjectionRefPresent",
    "cashMovementCountPresent",
    "projectedCumulativeCashflowPresent",
    "sourceEvidenceCurrent",
    "cashflowDiagnostic",
    "sourceDiagnosticCodes",
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


def validate_low_income_core_cashflow_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_low_income_core_cashflow_live_proof.py is required")
        return errors

    payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "cashMovementRefPresent": True,
            "cashflowProjectionRefPresent": True,
            "cashMovementCountPresent": True,
            "projectedCumulativeCashflowPresent": True,
            "sourceEvidenceCurrent": True,
            "cashflowDiagnostic": "core_cashflow_liquidity_evidence_ready",
            "sourceDiagnosticCodes": ["core_cashflow_liquidity_evidence_ready"],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "low-income Core cashflow live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {LOW_INCOME_CORE_CASHFLOW_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("low-income Core cashflow proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("low-income Core cashflow proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(
        LOW_INCOME_CORE_CASHFLOW_LIVE_BLOCKERS_CLEARED
    ):
        errors.append("low-income Core cashflow proof must clear only its source blocker")
    for blocker in (
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"low-income Core cashflow proof must retain blocker `{blocker}`")
    if not low_income_core_cashflow_live_proof_is_valid(payload):
        errors.append("valid low-income Core cashflow proof fixture should validate")

    blocked_payload = build_low_income_core_cashflow_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "errorCode": "core_cashflow_source_unavailable",
            "cashMovementRefPresent": False,
            "cashflowProjectionRefPresent": False,
            "cashMovementCountPresent": False,
            "projectedCumulativeCashflowPresent": False,
            "sourceEvidenceCurrent": False,
            "cashflowDiagnostic": "core_cashflow_source_unavailable",
            "sourceDiagnosticCodes": ["core_cashflow_source_unavailable"],
        },
    )
    if low_income_core_cashflow_live_proof_is_valid(blocked_payload):
        errors.append("blocked low-income Core cashflow proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_low_income_core_cashflow_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Low-income Core cashflow live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
