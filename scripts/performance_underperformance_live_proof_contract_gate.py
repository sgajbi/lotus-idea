from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.performance_underperformance_live_proof import (
    PERFORMANCE_UNDERPERFORMANCE_LIVE_BLOCKERS_CLEARED,
    PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_SCHEMA_VERSION,
    build_performance_underperformance_live_proof_payload,
    performance_underperformance_live_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_performance_underperformance_live_proof.py"

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
    "signal-ingestion:underperformance",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "sourceProductId",
    "generatedAtUtc",
    "livePerformanceSourceAttempted",
    "runStatus",
    "evaluationOutcome",
    "candidateGenerated",
    "sourceEvidenceCurrent",
    "benchmarkContextAvailable",
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


def validate_performance_underperformance_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_performance_underperformance_live_proof.py is required")
        return errors

    payload = build_performance_underperformance_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_performance_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "evaluationOutcome": "candidate_created",
            "sourceEvidenceCurrent": True,
            "benchmarkContextAvailable": True,
            "sourceDiagnosticCodes": ["performance_benchmark_context_ready"],
            "reasonCodes": ["underperformance_attention"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "performance underperformance live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {PERFORMANCE_UNDERPERFORMANCE_LIVE_PROOF_SCHEMA_VERSION}"
        )
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("performance underperformance live proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("performance underperformance proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(
        PERFORMANCE_UNDERPERFORMANCE_LIVE_BLOCKERS_CLEARED
    ):
        errors.append("performance proof must clear only the live-performance-source blocker")
    for blocker in (
        "opportunity_archetype_benchmark_assignment_source_ref_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"performance proof must retain remaining blocker `{blocker}`")
    if not performance_underperformance_live_proof_is_valid(payload):
        errors.append("valid performance underperformance proof fixture should validate")

    blocked_payload = build_performance_underperformance_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_performance_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "errorCode": "performance_source_unavailable",
            "sourceEvidenceCurrent": False,
            "benchmarkContextAvailable": False,
            "evaluationOutcome": "blocked",
            "sourceDiagnosticCodes": ["performance_source_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if performance_underperformance_live_proof_is_valid(blocked_payload):
        errors.append("blocked performance underperformance proof fixture must not validate")

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
    errors = validate_performance_underperformance_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Performance underperformance live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
