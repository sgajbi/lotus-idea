from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from app.application.outbox.platform_mesh.source_contract_proof import (  # noqa: E402
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_BLOCKERS_CLEARED,
    OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_BLOCKERS,
    REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_EVIDENCE_REFS,
    build_outbox_platform_mesh_event_source_contract_proof_payload,
    outbox_platform_mesh_event_source_contract_proof_is_valid,
)

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
    "supported feature is promoted",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_outbox_platform_mesh_event_source_contract_proof(
    *,
    platform_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    proof = build_outbox_platform_mesh_event_source_contract_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )
    if (
        proof.get("schemaVersion")
        != OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION
    ):
        errors.append(
            "outbox platform mesh event source-contract proof schema must be "
            f"{OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_EVIDENCE_REFS
    ):
        errors.append(
            "outbox platform mesh event source-contract proof evidence refs must match the contract"
        )
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_BLOCKERS_CLEARED
    ):
        errors.append("outbox platform mesh event source contract must clear no runtime blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_PLATFORM_MESH_EVENT_SOURCE_CONTRACT_BLOCKERS
    ):
        errors.append("outbox platform mesh event source contract must retain runtime blockers")
    proof_checks = proof.get("proofChecks")
    file_evidence_present = (
        isinstance(proof_checks, Mapping) and proof_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not outbox_platform_mesh_event_source_contract_proof_is_valid(
        proof
    ):
        errors.append(
            "outbox platform mesh event source-contract proof must validate against sibling "
            "platform truth when sibling evidence is present"
        )
    if (
        not file_evidence_present
        and proof.get("outboxPlatformMeshEventSourceContractValid") is not False
    ):
        errors.append("missing sibling platform evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_outbox_platform_mesh_event_source_contract_proof()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox platform mesh event source-contract proof gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
