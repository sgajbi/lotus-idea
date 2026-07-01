from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from app.application.durable_repository_proof import (
    DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION,
    REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS,
    build_durable_repository_proof_payload,
    durable_repository_proof_is_valid,
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
    "postgresql://",
    "request-body",
    "response-body",
    "/source/",
}


_validate_forbidden_content = forbidden_content_validator(
    FORBIDDEN_KEYS,
    FORBIDDEN_TEXT_FRAGMENTS,
)


def validate_durable_repository_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_durable_repository_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION:
        errors.append(
            f"durable repository proof schema must be {DURABLE_REPOSITORY_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_DURABLE_REPOSITORY_EVIDENCE_REFS:
        errors.append("durable repository proof evidence refs must match the governed contract")
    if not durable_repository_proof_is_valid(proof):
        errors.append("durable repository proof must validate against its contract")
    validate_forbidden_content(proof, errors, FORBIDDEN_KEYS, FORBIDDEN_TEXT_FRAGMENTS)
    return errors


def main() -> int:
    errors = validate_durable_repository_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Durable repository proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
