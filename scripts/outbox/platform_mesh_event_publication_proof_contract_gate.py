from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

try:
    from scripts.outbox._bootstrap import ROOT
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from _bootstrap import ROOT  # type: ignore[import-not-found,no-redef]

from app.application.outbox.platform_mesh_event_publication_proof import (  # noqa: E402
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED,
    OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION,
    REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS,
    REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS,
    build_outbox_platform_mesh_event_publication_proof_payload,
    outbox_platform_mesh_event_publication_proof_is_valid,
)

try:
    from scripts.proof_source_safety import forbidden_content_validator, validate_forbidden_content
except ModuleNotFoundError:
    from proof_source_safety import forbidden_content_validator, validate_forbidden_content  # type: ignore[import-not-found,no-redef]

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


def validate_outbox_platform_mesh_event_publication_proof_contract(
    *,
    platform_root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    proof = build_outbox_platform_mesh_event_publication_proof_payload(
        generated_at_utc=datetime(2026, 6, 27, 0, 0, tzinfo=UTC),
        repository_root=ROOT,
        platform_root=platform_root,
    )
    if proof.get("schemaVersion") != OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION:
        errors.append(
            "outbox platform mesh event publication proof schema must be "
            f"{OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != (
        REQUIRED_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_EVIDENCE_REFS
    ):
        errors.append(
            "outbox platform mesh event publication proof evidence refs must match the contract"
        )
    if tuple(proof.get("aggregateBlockersCleared") or ()) != (
        OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS_CLEARED
    ):
        errors.append("outbox platform mesh event proof must clear only mesh event publication")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_OUTBOX_PLATFORM_MESH_EVENT_PUBLICATION_BLOCKERS
    ):
        errors.append("outbox platform mesh event proof must retain Workbench and support blockers")
    proof_checks = proof.get("proofChecks")
    file_evidence_present = (
        isinstance(proof_checks, Mapping) and proof_checks.get("fileEvidencePresent") is True
    )
    if file_evidence_present and not outbox_platform_mesh_event_publication_proof_is_valid(proof):
        errors.append(
            "outbox platform mesh event publication proof must validate against sibling "
            "platform truth when sibling evidence is present"
        )
    if (
        not file_evidence_present
        and proof.get("outboxPlatformMeshEventPublicationProofValid") is not False
    ):
        errors.append("missing sibling platform evidence must remain an invalid non-proof artifact")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_outbox_platform_mesh_event_publication_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Outbox platform mesh event publication proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
