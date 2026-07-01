from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.manage_mandate_live_proof import (
    MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED,
    MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION,
    build_manage_mandate_live_proof_payload,
    manage_mandate_live_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_manage_mandate_live_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "orderId",
    "portfolioId",
    "rebalanceRunId",
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
    "rebalance-run:",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductId",
    "generatedAtUtc",
    "liveManageSourceAttempted",
    "runStatus",
    "evaluationOutcome",
    "candidateGenerated",
    "sourceEvidenceCurrent",
    "portfolioScopeConfirmed",
    "manageActionRegisterReady",
    "mandatePerformanceHealthSourceRefCurrent",
    "mandateRiskHealthSourceRefCurrent",
    "workflowDecisionCount",
    "lineageEdgeCount",
    "sourceDiagnosticCodes",
    "reasonCodes",
    "unsupportedReasons",
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


def validate_manage_mandate_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_manage_mandate_live_proof.py is required")
        return errors

    payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 10, 10, tzinfo=UTC),
        live_manage_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-manage",
            "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "portfolioScopeConfirmed": True,
            "manageActionRegisterReady": True,
            "mandatePerformanceHealthSourceRefCurrent": True,
            "mandateRiskHealthSourceRefCurrent": True,
            "workflowDecisionCount": 2,
            "lineageEdgeCount": 1,
            "sourceDiagnosticCodes": ["manage_action_register_ready_portfolio_scope"],
            "reasonCodes": ["review_required"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "manage mandate live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {MANAGE_MANDATE_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("manage mandate proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("manage mandate proof must not approve client publication")
    for authority_key in ("rebalanceExecutionAuthorityGranted", "orderExecutionReady"):
        if payload.get(authority_key) is not False:
            errors.append(f"manage mandate proof must keep `{authority_key}` false")
    if payload.get("proofClosed") is not False:
        errors.append("manage mandate proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(MANAGE_MANDATE_LIVE_BLOCKERS_CLEARED):
        errors.append(
            "manage mandate proof must clear only portfolio-scoped Manage plus "
            "source-owned mandate performance/risk health source-ref blockers"
        )
    for blocker in (
        "opportunity_archetype_core_portfolio_state_source_ref_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"manage mandate proof must retain remaining blocker `{blocker}`")
    if not manage_mandate_live_proof_is_valid(payload):
        errors.append("valid manage mandate proof fixture should validate")

    blocked_payload = build_manage_mandate_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 10, 10, tzinfo=UTC),
        live_manage_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-manage",
            "sourceProductId": "lotus-manage:PortfolioActionRegister:v1",
            "errorCode": "manage_supportability_unavailable",
            "sourceEvidenceCurrent": False,
            "portfolioScopeConfirmed": False,
            "manageActionRegisterReady": False,
            "mandatePerformanceHealthSourceRefCurrent": False,
            "mandateRiskHealthSourceRefCurrent": False,
            "workflowDecisionCount": 0,
            "lineageEdgeCount": 0,
            "evaluationOutcome": "blocked",
            "sourceDiagnosticCodes": ["manage_supportability_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if manage_mandate_live_proof_is_valid(blocked_payload):
        errors.append("blocked manage mandate proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_manage_mandate_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Manage mandate live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
