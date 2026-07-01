from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.workbench_read_path_proof import (
    REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS,
    REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS,
    REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS,
    WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION,
    build_workbench_read_path_proof_payload,
    workbench_read_path_proof_is_valid,
)

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]

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
    "candidateId",
    "clientId",
    "portfolioId",
    "request-body",
    "response-body",
    "/source/",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_workbench_read_path_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION:
        errors.append(
            f"workbench read-path proof schema must be {WORKBENCH_READ_PATH_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("localEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_LOCAL_EVIDENCE_REFS
    ):
        errors.append("workbench read-path local evidence refs must match the governed contract")
    if tuple(proof.get("externalEvidenceRefs") or ()) != (
        REQUIRED_WORKBENCH_READ_PATH_EXTERNAL_EVIDENCE_REFS
    ):
        errors.append("workbench read-path external evidence refs must match the governed contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        "workbench_gateway_bff_consumption_proof_missing",
    ):
        errors.append(
            "workbench read-path proof must clear only "
            "workbench_gateway_bff_consumption_proof_missing"
        )
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_WORKBENCH_READ_PATH_CERTIFICATION_BLOCKERS
    ):
        errors.append("workbench read-path proof must retain product and certification blockers")
    if not workbench_read_path_proof_is_valid(proof):
        errors.append("workbench read-path proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_workbench_read_path_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Workbench read-path proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
