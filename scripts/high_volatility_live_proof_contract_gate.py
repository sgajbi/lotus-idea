from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.high_volatility_live_proof import (
    HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED,
    HIGH_VOLATILITY_LIVE_PROOF_SCHEMA_VERSION,
    build_high_volatility_live_proof_payload,
    high_volatility_live_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_high_volatility_live_proof.py"

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
    "signal-ingestion:high-volatility",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductId",
    "generatedAtUtc",
    "liveRiskSourceAttempted",
    "runStatus",
    "evaluationOutcome",
    "candidateGenerated",
    "sourceEvidenceCurrent",
    "riskSupportabilityReady",
    "sourceDiagnosticCodes",
    "reasonCodes",
    "unsupportedReasons",
    "supportedFeaturePromoted",
    "proofClosed",
    "aggregateBlockersCleared",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


def validate_high_volatility_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_high_volatility_live_proof.py is required")
        return errors

    payload = build_high_volatility_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_risk_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-risk",
            "sourceProductId": "lotus-risk:RiskMetricsReport:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "riskSupportabilityReady": True,
            "sourceDiagnosticCodes": ["risk_volatility_source_ready"],
            "reasonCodes": ["volatility_attention"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "high volatility live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != HIGH_VOLATILITY_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {HIGH_VOLATILITY_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("high volatility live proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("high volatility proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(HIGH_VOLATILITY_LIVE_BLOCKERS_CLEARED):
        errors.append("high volatility proof must clear only the live-risk-volatility blocker")
    for blocker in (
        "opportunity_archetype_drawdown_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"high volatility proof must retain remaining blocker `{blocker}`")
    if not high_volatility_live_proof_is_valid(payload):
        errors.append("valid high volatility proof fixture should validate")

    blocked_payload = build_high_volatility_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_risk_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-risk",
            "sourceProductId": "lotus-risk:RiskMetricsReport:v1",
            "errorCode": "risk_source_unavailable",
            "sourceEvidenceCurrent": False,
            "riskSupportabilityReady": False,
            "evaluationOutcome": "blocked",
            "sourceDiagnosticCodes": ["risk_source_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if high_volatility_live_proof_is_valid(blocked_payload):
        errors.append("blocked high volatility proof fixture must not validate")

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
    errors = validate_high_volatility_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("High volatility live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
