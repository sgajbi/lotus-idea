from __future__ import annotations

import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

from app.application.ai_lineage_store_proof import (
    AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION,
    REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS,
    ai_lineage_store_proof_is_valid,
    build_ai_lineage_store_proof_payload,
)


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "correlationId",
    "holdingId",
    "idempotencyKey",
    "portfolioId",
    "prompt",
    "providerResponse",
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


def validate_ai_lineage_store_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_ai_lineage_store_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION:
        errors.append(
            f"AI lineage store proof schema must be {AI_LINEAGE_STORE_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_AI_LINEAGE_STORE_EVIDENCE_REFS:
        errors.append("AI lineage store proof evidence refs must match the governed contract")
    if not ai_lineage_store_proof_is_valid(proof):
        errors.append("AI lineage store proof must validate against its contract")
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
    errors = validate_ai_lineage_store_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("AI lineage store proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
