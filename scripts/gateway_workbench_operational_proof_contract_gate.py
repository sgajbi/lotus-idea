from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.gateway_workbench_operational_proof import (
    GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS_CLEARED,
    GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION,
    REMAINING_GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS,
    REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_EXTERNAL_EVIDENCE_REFS,
    REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_LOCAL_EVIDENCE_REFS,
    build_gateway_workbench_operational_proof_payload,
    gateway_workbench_operational_proof_is_valid,
)
from app.application.workbench_read_path_proof import (
    build_workbench_read_path_proof_payload,
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
    "eventId",
    "holdingId",
    "idempotencyKey",
    "payload",
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
    "client_id",
    "clientId",
    "correlation_id",
    "event_id",
    "idea_high_cash_001",
    "portfolio_id",
    "portfolioId",
    "request-body",
    "response-body",
    "/source/",
    "supported feature is promoted",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_gateway_workbench_operational_proof_contract() -> list[str]:
    errors: list[str] = []
    workbench_read_path_proof = build_workbench_read_path_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    proof = build_gateway_workbench_operational_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
        workbench_read_path_proof=workbench_read_path_proof,
        workbench_read_path_proof_ref="output/workbench/workbench-read-path-proof.json",
    )
    if proof.get("schemaVersion") != GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION:
        errors.append(
            "Gateway/Workbench operational proof schema must be "
            f"{GATEWAY_WORKBENCH_OPERATIONAL_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("localEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_LOCAL_EVIDENCE_REFS
    ):
        errors.append("Gateway/Workbench operational local evidence refs must match contract")
    if tuple(proof.get("externalEvidenceRefs") or ()) != (
        REQUIRED_GATEWAY_WORKBENCH_OPERATIONAL_EXTERNAL_EVIDENCE_REFS
    ):
        errors.append("Gateway/Workbench operational external evidence refs must match contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS_CLEARED
    ):
        errors.append("Gateway/Workbench operational proof must clear only its bounded blocker")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_GATEWAY_WORKBENCH_OPERATIONAL_BLOCKERS
    ):
        errors.append("Gateway/Workbench operational proof must retain product/support blockers")
    if not gateway_workbench_operational_proof_is_valid(proof):
        errors.append("Gateway/Workbench operational proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_gateway_workbench_operational_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Gateway/Workbench operational proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
