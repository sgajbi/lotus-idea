# ruff: noqa: E402
from __future__ import annotations

from datetime import UTC, datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


from scripts.proof_worktree_import_guard import ensure_worktree_imports

ensure_worktree_imports(__file__)

from app.application.outbox.broker.source_contract_proof import (  # noqa: E402
    OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES,
    REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS,
    REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS,
    build_outbox_broker_source_contract_proof_payload,
    outbox_broker_source_contract_proof_is_valid,
)
from app.domain.proof_evidence import EvidenceClass  # noqa: E402
from scripts.proof_source_safety import (  # noqa: E402
    forbidden_content_validator,
    validate_forbidden_content,
)

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


def validate_outbox_broker_source_contract_proof() -> list[str]:
    errors: list[str] = []
    proof = build_outbox_broker_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION:
        errors.append(
            "outbox broker source-contract proof schema must be "
            f"{OUTBOX_BROKER_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION}"
        )
    if proof.get("evidenceClass") != EvidenceClass.SOURCE_CONTRACT.value:
        errors.append("outbox broker proof evidence class must be source_contract")
    if tuple(proof.get("requiredBlockerEvidenceClasses", {}).items()) != (
        OUTBOX_BROKER_SOURCE_CONTRACT_REQUIRED_BLOCKER_EVIDENCE_CLASSES
    ):
        errors.append("outbox broker source contract must not claim runtime blockers")
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("outbox broker source contract must clear no aggregate blocker")
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_OUTBOX_BROKER_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        errors.append("outbox broker source-contract evidence refs must match the contract")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_BROKER_SOURCE_CONTRACT_BLOCKERS
    ):
        errors.append("outbox broker source contract must retain all runtime blockers")
    if not outbox_broker_source_contract_proof_is_valid(proof):
        errors.append("outbox broker source-contract proof must validate")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_outbox_broker_source_contract_proof()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox broker source-contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
