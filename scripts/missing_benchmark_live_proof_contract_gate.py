from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.missing_benchmark_live_proof import (
    MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED,
    MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION,
    build_missing_benchmark_live_proof_payload,
    missing_benchmark_live_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_missing_benchmark_live_proof.py"

FORBIDDEN_KEYS = {
    "accountId",
    "benchmarkId",
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
    "BMK_PB_GLOBAL_BALANCED_60_40",
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
    "evaluationOutcome",
    "candidateGenerated",
    "benchmarkAssignmentRefPresent",
    "benchmarkIdentityResolved",
    "assignmentEffectiveForAsOfDate",
    "assignmentStatus",
    "assignmentVersionPresent",
    "sourceEvidenceCurrent",
    "sourceDiagnosticCodes",
    "reasonCodes",
    "unsupportedReasons",
    "benchmarkAssignmentAuthorityGranted",
    "benchmarkMethodologyCertified",
    "performanceBenchmarkReadinessCertified",
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


def validate_missing_benchmark_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_missing_benchmark_live_proof.py is required")
        return errors

    payload = build_missing_benchmark_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evaluation_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
            "evaluationOutcome": "candidate_created",
            "benchmarkAssignmentRefPresent": True,
            "benchmarkIdentityResolved": False,
            "assignmentEffectiveForAsOfDate": False,
            "assignmentStatus": "active",
            "assignmentVersionPresent": True,
            "sourceEvidenceCurrent": True,
            "sourceDiagnosticCodes": ["core_benchmark_assignment_benchmark_identity_missing"],
            "reasonCodes": ["missing_benchmark", "review_required"],
            "unsupportedReasons": [],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "missing benchmark live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {MISSING_BENCHMARK_LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("missing benchmark proof must not promote supported features")
    if payload.get("clientPublicationReady") is not False:
        errors.append("missing benchmark proof must not approve client publication")
    for authority_key in (
        "benchmarkAssignmentAuthorityGranted",
        "benchmarkMethodologyCertified",
        "performanceBenchmarkReadinessCertified",
    ):
        if payload.get(authority_key) is not False:
            errors.append(f"missing benchmark proof must keep `{authority_key}` false")
    if payload.get("proofClosed") is not False:
        errors.append("missing benchmark proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(MISSING_BENCHMARK_LIVE_BLOCKERS_CLEARED):
        errors.append("missing benchmark proof must clear only the live Core source blocker")
    for blocker in (
        "opportunity_archetype_performance_benchmark_readiness_source_ref_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_client_publication_not_ready",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"missing benchmark proof must retain remaining blocker `{blocker}`")
    if not missing_benchmark_live_proof_is_valid(payload):
        errors.append("valid missing benchmark proof fixture should validate")

    blocked_payload = build_missing_benchmark_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 28, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evaluation_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
            "errorCode": "core_benchmark_assignment_source_unavailable",
            "evaluationOutcome": "blocked",
            "benchmarkAssignmentRefPresent": False,
            "benchmarkIdentityResolved": False,
            "assignmentEffectiveForAsOfDate": False,
            "assignmentStatus": "unknown",
            "assignmentVersionPresent": False,
            "sourceEvidenceCurrent": False,
            "sourceDiagnosticCodes": ["core_benchmark_assignment_source_unavailable"],
            "reasonCodes": ["source_partial"],
            "unsupportedReasons": ["source_unavailable"],
        },
    )
    if missing_benchmark_live_proof_is_valid(blocked_payload):
        errors.append("blocked missing benchmark proof fixture must not validate")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_missing_benchmark_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Missing benchmark live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
