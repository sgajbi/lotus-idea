from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.core_portfolio_state_live_proof import (
    CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED,
    CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION,
    build_core_portfolio_state_live_proof_payload,
    core_portfolio_state_live_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_core_portfolio_state_live_proof.py"

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
    "sourceProductId",
    "generatedAtUtc",
    "liveCoreSourceAttempted",
    "runStatus",
    "portfolioStateRefPresent",
    "sourceEvidenceCurrent",
    "sourceEvidenceAvailable",
    "sourceDiagnosticCodes",
    "rebalanceExecutionAuthorityGranted",
    "orderExecutionReady",
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


def validate_core_portfolio_state_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_core_portfolio_state_live_proof.py is required")
        return errors

    payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
            "portfolioStateRefPresent": True,
            "sourceEvidenceCurrent": True,
            "sourceEvidenceAvailable": True,
            "sourceDiagnosticCodes": ["core_portfolio_state_ready"],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "core portfolio-state live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {CORE_PORTFOLIO_STATE_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("core portfolio-state proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("core portfolio-state proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(CORE_PORTFOLIO_STATE_LIVE_BLOCKERS_CLEARED):
        errors.append("core portfolio-state proof must clear only its source-ref blocker")
    for blocker in (
        "opportunity_archetype_portfolio_scoped_manage_source_proof_missing",
        "opportunity_archetype_mandate_performance_health_source_ref_missing",
        "opportunity_archetype_mandate_risk_health_source_ref_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"core portfolio-state proof must retain blocker `{blocker}`")
    if not core_portfolio_state_live_proof_is_valid(payload):
        errors.append("valid core portfolio-state proof fixture should validate")

    blocked_payload = build_core_portfolio_state_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:PortfolioStateSnapshot:v1",
            "errorCode": "core_portfolio_state_source_unavailable",
            "portfolioStateRefPresent": False,
            "sourceEvidenceCurrent": False,
            "sourceEvidenceAvailable": False,
            "sourceDiagnosticCodes": ["core_portfolio_state_source_unavailable"],
        },
    )
    if core_portfolio_state_live_proof_is_valid(blocked_payload):
        errors.append("blocked core portfolio-state proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_core_portfolio_state_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Core portfolio-state live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
