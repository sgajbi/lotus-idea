from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.outbox_consumer_runtime_proof import (
    OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED,
    OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS,
    REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS,
    build_outbox_consumer_runtime_proof_payload,
    outbox_consumer_runtime_proof_is_valid,
)

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "aggregateId",
    "candidateId",
    "clientId",
    "contentHash",
    "correlationId",
    "eventId",
    "holdingId",
    "idempotencyFingerprint",
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
    "aggregate_id",
    "candidate_id",
    "client_id",
    "content_hash",
    "correlation_id",
    "event_id",
    "idea_high_cash_001",
    "idempotency",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_outbox_consumer_runtime_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_outbox_consumer_runtime_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION:
        errors.append(
            "outbox consumer runtime proof schema must be "
            f"{OUTBOX_CONSUMER_RUNTIME_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (REQUIRED_OUTBOX_CONSUMER_RUNTIME_EVIDENCE_REFS):
        errors.append("outbox consumer runtime proof evidence refs must match the contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_CONSUMER_RUNTIME_BLOCKERS_CLEARED
    ):
        errors.append("outbox consumer runtime proof must clear only consumer runtime proof")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_CONSUMER_RUNTIME_CERTIFICATION_BLOCKERS
    ):
        errors.append(
            "outbox consumer runtime proof must retain mesh, Workbench, and support blockers"
        )
    if not outbox_consumer_runtime_proof_is_valid(proof):
        errors.append("outbox consumer runtime proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_outbox_consumer_runtime_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox consumer runtime proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
