from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.core_benchmark_assignment_live_proof import (
    CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED,
    CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION,
    build_core_benchmark_assignment_live_proof_payload,
    core_benchmark_assignment_live_proof_is_valid,
)


ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_core_benchmark_assignment_live_proof.py"

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
    "benchmarkAssignmentRefPresent",
    "benchmarkIdentityResolved",
    "assignmentEffectiveForAsOfDate",
    "assignmentStatus",
    "assignmentVersionPresent",
    "sourceEvidenceCurrent",
    "sourceDiagnosticCodes",
    "supportedFeaturePromoted",
    "proofClosed",
    "aggregateBlockersCleared",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


def validate_core_benchmark_assignment_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_core_benchmark_assignment_live_proof.py is required")
        return errors

    payload = build_core_benchmark_assignment_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "completed",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
            "benchmarkAssignmentRefPresent": True,
            "benchmarkIdentityResolved": True,
            "assignmentEffectiveForAsOfDate": True,
            "assignmentStatus": "active",
            "assignmentVersionPresent": True,
            "sourceEvidenceCurrent": True,
            "sourceDiagnosticCodes": ["core_benchmark_assignment_ready"],
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "core benchmark assignment live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION:
        errors.append(
            f"schemaVersion must be {CORE_BENCHMARK_ASSIGNMENT_LIVE_PROOF_SCHEMA_VERSION}"
        )
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("core benchmark assignment proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("core benchmark assignment proof must remain open while blockers remain")
    if payload.get("aggregateBlockersCleared") != list(
        CORE_BENCHMARK_ASSIGNMENT_LIVE_BLOCKERS_CLEARED
    ):
        errors.append("core benchmark assignment proof must clear only its source-ref blocker")
    for blocker in (
        "opportunity_archetype_live_performance_source_proof_missing",
        "opportunity_archetype_data_mesh_not_certified",
        "opportunity_archetype_workbench_product_proof_missing",
        "opportunity_archetype_supported_feature_promotion_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"core benchmark assignment proof must retain blocker `{blocker}`")
    if not core_benchmark_assignment_live_proof_is_valid(payload):
        errors.append("valid core benchmark assignment proof fixture should validate")

    blocked_payload = build_core_benchmark_assignment_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        evidence_summary={
            "runStatus": "blocked",
            "sourceAuthority": "lotus-core",
            "sourceProductId": "lotus-core:BenchmarkAssignment:v1",
            "errorCode": "core_benchmark_assignment_source_unavailable",
            "benchmarkAssignmentRefPresent": False,
            "benchmarkIdentityResolved": False,
            "assignmentEffectiveForAsOfDate": False,
            "assignmentStatus": "unknown",
            "assignmentVersionPresent": False,
            "sourceEvidenceCurrent": False,
            "sourceDiagnosticCodes": ["core_benchmark_assignment_source_unavailable"],
        },
    )
    if core_benchmark_assignment_live_proof_is_valid(blocked_payload):
        errors.append("blocked core benchmark assignment proof fixture must not validate")

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
    errors = validate_core_benchmark_assignment_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Core benchmark assignment live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
