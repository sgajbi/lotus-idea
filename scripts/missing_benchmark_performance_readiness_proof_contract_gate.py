from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.missing_benchmark_performance_readiness_proof import (
    MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED,
    MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION,
    build_missing_benchmark_performance_readiness_proof_payload,
    missing_benchmark_performance_readiness_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_missing_benchmark_performance_readiness_proof.py"

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
    "returns-series-request",
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
    "sourceEvidenceCurrent",
    "performanceBenchmarkReadinessSourceRefPresent",
    "benchmarkReadinessEvaluated",
    "benchmarkContextAvailable",
    "benchmarkReadinessDiagnostic",
    "sourceDiagnosticCodes",
    "benchmarkAssignmentAuthorityGranted",
    "benchmarkReturnCalculationAuthorityGranted",
    "benchmarkMethodologyCertified",
    "performanceCalculationAuthorityGranted",
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


def validate_missing_benchmark_performance_readiness_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append(
            "scripts/generate_missing_benchmark_performance_readiness_proof.py is required"
        )
        return errors

    payload = build_missing_benchmark_performance_readiness_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_performance_source_attempted=True,
        performance_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "sourceEvidenceCurrent": True,
            "performanceBenchmarkReadinessSourceRefPresent": True,
            "benchmarkContextAvailable": False,
            "benchmarkReadinessDiagnostic": "performance_benchmark_context_missing",
            "sourceDiagnosticCodes": ["performance_benchmark_context_missing"],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "missing benchmark Performance readiness proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {MISSING_BENCHMARK_PERFORMANCE_READINESS_PROOF_SCHEMA_VERSION}"
        )
    if payload.get("benchmarkContextAvailable") is not False:
        errors.append("missing-benchmark proof fixture should tolerate missing benchmark context")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("missing-benchmark Performance readiness proof must not promote support")
    if payload.get("proofClosed") is not False:
        errors.append("missing-benchmark Performance readiness proof must remain open")
    if payload.get("aggregateBlockersCleared") != list(
        MISSING_BENCHMARK_PERFORMANCE_READINESS_BLOCKERS_CLEARED
    ):
        errors.append(
            "Performance readiness proof must clear only the Performance source-ref blocker"
        )
    for blocker in (
        "opportunity_archetype_missing_benchmark_live_core_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"Performance readiness proof must retain remaining blocker `{blocker}`")
    if not missing_benchmark_performance_readiness_proof_is_valid(payload):
        errors.append("valid missing-benchmark Performance readiness proof fixture should validate")

    blocked_payload = build_missing_benchmark_performance_readiness_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_performance_source_attempted=True,
        performance_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-performance",
            "sourceProductId": "lotus-performance:ReturnsSeriesBundle:v1",
            "errorCode": "performance_source_unavailable",
            "sourceEvidenceCurrent": False,
            "performanceBenchmarkReadinessSourceRefPresent": False,
            "benchmarkContextAvailable": False,
            "benchmarkReadinessDiagnostic": "performance_source_unavailable",
            "sourceDiagnosticCodes": ["performance_source_unavailable"],
        },
    )
    if missing_benchmark_performance_readiness_proof_is_valid(blocked_payload):
        errors.append("blocked missing-benchmark Performance readiness proof must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_missing_benchmark_performance_readiness_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Missing benchmark Performance readiness proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
