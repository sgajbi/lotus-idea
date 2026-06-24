from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.outbox_broker_proof import (
    OUTBOX_BROKER_BLOCKERS_CLEARED,
    OUTBOX_BROKER_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS,
    REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS,
    build_outbox_broker_proof_payload,
    outbox_broker_proof_is_valid,
)

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


def validate_outbox_broker_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_outbox_broker_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != OUTBOX_BROKER_PROOF_SCHEMA_VERSION:
        errors.append(f"outbox broker proof schema must be {OUTBOX_BROKER_PROOF_SCHEMA_VERSION}")
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_OUTBOX_BROKER_EVIDENCE_REFS:
        errors.append("outbox broker proof evidence refs must match the governed contract")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != OUTBOX_BROKER_BLOCKERS_CLEARED:
        errors.append(
            "outbox broker proof must clear only broker configuration and runtime proof blockers"
        )
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_BROKER_CERTIFICATION_BLOCKERS
    ):
        errors.append("outbox broker proof must retain downstream, mesh, Workbench, and support blockers")
    if not outbox_broker_proof_is_valid(proof):
        errors.append("outbox broker proof must validate against its contract")
    _validate_forbidden_content(proof, errors)
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
    if isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            _validate_forbidden_content(nested, errors, f"{path}[{index}]")
        return
    if isinstance(value, str):
        for fragment in FORBIDDEN_TEXT_FRAGMENTS:
            if fragment in value:
                errors.append(f"{path}: forbidden source-sensitive text `{fragment}` is present")


def main() -> int:
    errors = validate_outbox_broker_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox broker proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
