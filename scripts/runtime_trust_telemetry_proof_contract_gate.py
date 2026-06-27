from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
import sys

from app.application.runtime_trust_telemetry_proof import (
    REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS,
    REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS,
    RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED,
    RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION,
    build_runtime_trust_telemetry_proof_payload,
    runtime_trust_telemetry_proof_is_valid,
)

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_KEYS = {
    "accountId",
    "candidateId",
    "clientId",
    "contentHash",
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
    "candidate_id",
    "client_id",
    "content_hash",
    "portfolio_id",
    "request-body",
    "response-body",
    "/source-owned/",
}


def validate_runtime_trust_telemetry_proof_contract() -> list[str]:
    errors: list[str] = []
    proof = build_runtime_trust_telemetry_proof_payload(
        generated_at_utc=datetime(2026, 6, 21, 10, 10, tzinfo=UTC),
        repository_root=ROOT,
    )
    if proof.get("schemaVersion") != RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION:
        errors.append(
            "runtime trust telemetry proof schema must be "
            f"{RUNTIME_TRUST_TELEMETRY_PROOF_SCHEMA_VERSION}"
        )
    if tuple(proof.get("evidenceRefs") or ()) != REQUIRED_RUNTIME_TRUST_TELEMETRY_EVIDENCE_REFS:
        errors.append(
            "runtime trust telemetry proof evidence refs must match the governed contract"
        )
    if (
        tuple(proof.get("aggregateBlockersCleared") or ())
        != RUNTIME_TRUST_TELEMETRY_BLOCKERS_CLEARED
    ):
        errors.append("runtime trust telemetry proof must clear only runtime telemetry blockers")
    if tuple(proof.get("remainingCertificationBlockers") or ()) != (
        REMAINING_RUNTIME_TRUST_TELEMETRY_CERTIFICATION_BLOCKERS
    ):
        errors.append("runtime trust telemetry proof must retain platform certification blockers")
    if not runtime_trust_telemetry_proof_is_valid(proof):
        errors.append("runtime trust telemetry proof must validate against its contract")
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
    errors = validate_runtime_trust_telemetry_proof_contract()
    if errors:
        print("\n".join(errors))
        return 1
    print("Runtime trust telemetry proof contract gate passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
