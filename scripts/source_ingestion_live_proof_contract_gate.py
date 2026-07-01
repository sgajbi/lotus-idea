from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

from app.application.source_ingestion_live_proof import (
    LIVE_PROOF_SCHEMA_VERSION,
    build_source_ingestion_live_proof_payload,
    live_core_source_proof_is_valid,
)


try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]
LIVE_PROOF_SCRIPT = ROOT / "scripts" / "generate_source_ingestion_live_proof.py"

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
    "signal-ingestion:high-cash:lotus-core",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schemaVersion",
    "repository",
    "proofFamily",
    "sourceAuthority",
    "generatedAtUtc",
    "workerSchemaVersion",
    "workerMode",
    "liveCoreSourceAttempted",
    "runStatus",
    "durableStorageBacked",
    "supportedFeaturePromoted",
    "proofClosed",
    "totalCount",
    "decisionCounts",
    "blockReasonCounts",
    "proofBlockers",
    "remainingCertificationBlockers",
    "evidenceRefs",
    "nonProofBoundaries",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_source_ingestion_live_proof_contract() -> list[str]:
    errors: list[str] = []
    if not LIVE_PROOF_SCRIPT.exists():
        errors.append("scripts/generate_source_ingestion_live_proof.py is required")
        return errors

    payload = build_source_ingestion_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        worker_summary={
            "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
            "mode": "run_once",
            "sourceAuthority": "lotus-core",
            "durableStorageBacked": True,
            "totalCount": 1,
            "decisionCounts": {
                "accepted": 1,
                "replayed": 0,
                "conflict": 0,
                "duplicate_candidate": 0,
                "skipped_not_eligible": 0,
                "blocked": 0,
                "suppressed": 0,
            },
            "blockReasonCounts": {},
        },
    )

    if set(payload) != REQUIRED_TOP_LEVEL_KEYS:
        errors.append(
            "live proof payload keys must be "
            f"{sorted(REQUIRED_TOP_LEVEL_KEYS)}; got {sorted(payload)}"
        )
    if payload.get("schemaVersion") != LIVE_PROOF_SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {LIVE_PROOF_SCHEMA_VERSION}")
    if payload.get("supportedFeaturePromoted") is not False:
        errors.append("live proof must not promote supported features")
    if payload.get("proofClosed") is not False:
        errors.append("live proof must remain open while certification blockers remain")
    if "live_core_source_proof_missing" in payload.get("proofBlockers", []):
        errors.append("valid live proof payload must clear live_core_source_proof_missing")
    for blocker in (
        "scheduled_worker_deploy_proof_missing",
        "data_mesh_runtime_telemetry_not_certified",
        "gateway_workbench_proof_missing",
    ):
        if blocker not in payload.get("remainingCertificationBlockers", []):
            errors.append(f"live proof must retain remaining blocker `{blocker}`")
    if not live_core_source_proof_is_valid(payload):
        errors.append("valid live proof fixture should satisfy live_core_source_proof_is_valid")

    blocked_payload = build_source_ingestion_live_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        live_core_source_attempted=True,
        worker_summary={
            "schemaVersion": "lotus-idea.source-ingestion.high-cash.run-once.v1",
            "mode": "run_once",
            "status": "blocked",
            "sourceAuthority": "lotus-core",
            "durableStorageBacked": True,
            "totalCount": 0,
            "decisionCounts": {"accepted": 0, "replayed": 0},
            "blockReasonCounts": {"core_source_unavailable": 1},
            "errorCode": "core_source_unavailable",
        },
    )
    if live_core_source_proof_is_valid(blocked_payload):
        errors.append("blocked live proof fixture must not validate as live Core proof")

    validate_forbidden_content(payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    validate_forbidden_content(blocked_payload, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_source_ingestion_live_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Source ingestion live proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
